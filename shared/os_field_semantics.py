"""
KB-driven field semantics for ERP-OS payload building and validation.

Resolves clarity entity keys → ERP field specs using KB-04 mappings,
KB-07 doctype graph (name_field, setup layers), and os_validation.json.
No hardcoded doctype lists in callers.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from containers.knowledge_base.erpnext.schema.compose import compose_field_mappings, doctype_mapping

_SCHEMA_DIR = Path(__file__).resolve().parent.parent / "containers" / "knowledge_base" / "erpnext"
_GRAPH_PATH = _SCHEMA_DIR / "erpnext_doctype_graph.json"
_OS_VALIDATION_PATH = _SCHEMA_DIR / "schema" / "shared" / "os_validation.json"

# Entity keys handled outside generic field mapping (child tables, etc.)
_NON_FIELD_ENTITY_KEYS = frozenset({
    "items", "amount", "currency", "payment_type", "party_type", "mode_of_payment",
    "stock_entry_type", "project", "from_warehouse", "to_warehouse", "limit",
    "from_date", "to_date", "document_name", "is_stock_item", "extra",
})

# KB placeholder defaults — not real user-provided values
_PSEUDO_DEFAULT_VALUES = frozenset({
    "today",
    "fetch_from_customer_or_company_default",
    "transaction_date + 10 days",
    "{customer_name}",
})


def _read_json(path: Path) -> dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


@lru_cache(maxsize=1)
def _doctype_graph() -> dict[str, Any]:
    return _read_json(_GRAPH_PATH)


@lru_cache(maxsize=1)
def _os_validation_config() -> dict[str, Any]:
    return _read_json(_OS_VALIDATION_PATH)


def get_doctype_config(doctype: str) -> dict[str, Any]:
    cfg = doctype_mapping(doctype)
    return cfg if isinstance(cfg, dict) else {}


def get_field_mappings(doctype: str) -> dict[str, Any]:
    return get_doctype_config(doctype).get("field_mappings") or {}


def get_name_field(doctype: str) -> Optional[str]:
    dt = (_doctype_graph().get("doctypes") or {}).get(doctype) or {}
    name = dt.get("name_field")
    return str(name).strip() if name else None


# KB-07 layers 0–3: Company, Item, Customer, Supplier, etc. (not SO/PO/invoices)
_MASTER_SETUP_LAYER_KEYS = frozenset({
    "layer_0_system",
    "layer_1_config",
    "layer_2_masters",
    "layer_3_parties",
})


def get_setup_layer_doctypes() -> frozenset[str]:
    """All doctypes listed in setup_layers (includes transactions)."""
    layers = _doctype_graph().get("setup_layers") or {}
    names: set[str] = set()
    for layer_key, layer_dts in layers.items():
        if layer_key == "description":
            continue
        if isinstance(layer_dts, list):
            names.update(str(x) for x in layer_dts if x)
    return frozenset(names)


def get_master_setup_doctypes() -> frozenset[str]:
    """Doctypes that are master/config records (layers 0–3 only)."""
    layers = _doctype_graph().get("setup_layers") or {}
    names: set[str] = set()
    for layer_key, layer_dts in layers.items():
        if layer_key not in _MASTER_SETUP_LAYER_KEYS:
            continue
        if isinstance(layer_dts, list):
            names.update(str(x) for x in layer_dts if x)
    return frozenset(names)


def is_master_create_doctype(doctype: str) -> bool:
    """
    True for master/config creates (Customer, Item, Supplier, …).
    False for transactions (Sales Order, Purchase Order, invoices, …).
    """
    return doctype in get_master_setup_doctypes()


def resolve_entity_to_field(doctype: str, entity_key: str) -> Optional[tuple[str, dict[str, Any]]]:
    """
    Map a clarity entity key to (entity_key_in_kb, field_spec).
    Matches direct field_mappings keys or user_input_synonyms (case-insensitive).
    """
    key = str(entity_key or "").strip()
    if not key or key in _NON_FIELD_ENTITY_KEYS:
        return None

    fm = get_field_mappings(doctype)
    if not fm:
        return None

    if key in fm and isinstance(fm[key], dict):
        return key, fm[key]

    key_cf = key.casefold()
    for spec_key, spec in fm.items():
        if not isinstance(spec, dict):
            continue
        if spec_key.casefold() == key_cf:
            return spec_key, spec
        synonyms = spec.get("user_input_synonyms") or []
        if any(str(s).casefold() == key_cf for s in synonyms if s):
            return spec_key, spec

    return None


def field_spec_for_fieldname(doctype: str, fieldname: str) -> Optional[dict[str, Any]]:
    """Return KB field spec for an ERP fieldname on a doctype."""
    fn = str(fieldname or "").strip()
    if not fn:
        return None
    for spec in get_field_mappings(doctype).values():
        if isinstance(spec, dict) and str(spec.get("fieldname") or "") == fn:
            return spec
    return None


def is_link_field_spec(field_spec: dict[str, Any]) -> bool:
    return str(field_spec.get("fieldtype") or "") == "Link"


def link_target_doctype(field_spec: dict[str, Any]) -> Optional[str]:
    options = field_spec.get("options")
    if options and isinstance(options, str) and options.strip():
        return options.strip()
    return None


def cvs_registry_key_for_link(link_target: str) -> Optional[str]:
    mapping = _os_validation_config().get("link_target_to_cvs_registry") or {}
    return mapping.get(link_target)


def should_validate_link_in_cvs(
    action: str,
    target_doctype: str,
    field_spec: dict[str, Any],
) -> bool:
    """
    Validate Link field existence in CVS when referencing master data.
    Skip when creating the master record itself (name field or self-referential create).
    """
    if not is_link_field_spec(field_spec):
        return False

    if str(action or "").casefold() != "create":
        return True

    fieldname = str(field_spec.get("fieldname") or "")
    name_field = get_name_field(target_doctype)
    if name_field and fieldname == name_field:
        return False

    link_target = link_target_doctype(field_spec)
    if link_target and link_target == target_doctype:
        return False

    return True


def apply_kb_defaults_to_entities(doctype: str, entities: dict[str, Any]) -> dict[str, Any]:
    """Return entities with KB default_value applied for missing mandatory fields."""
    out = dict(entities)
    dt_cfg = get_doctype_config(doctype)
    fm = dt_cfg.get("field_mappings") or {}
    for field in dt_cfg.get("mandatory_fields") or []:
        if out.get(field) not in (None, "", [], {}):
            continue
        spec = fm.get(field) if isinstance(fm.get(field), dict) else {}
        default = spec.get("default_value")
        if default not in (None, ""):
            out[field] = default
    return out


def normalize_entities_for_doctype(doctype: str, entities: dict[str, Any]) -> dict[str, Any]:
    """Map clarity entity keys onto KB field keys via synonym resolution."""
    out = dict(entities)
    for entity_key, value in list(entities.items()):
        if value in (None, "", [], {}):
            continue
        resolved = resolve_entity_to_field(doctype, entity_key)
        if resolved:
            kb_key, _ = resolved
            if kb_key != entity_key and kb_key not in out:
                out[kb_key] = value
    return apply_kb_defaults_to_entities(doctype, out)


def tier1_mandatory_missing(
    doctype: str,
    entities: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (missing_fields, applied_defaults) using modular KB layout."""
    entities = normalize_entities_for_doctype(doctype, entities)
    dt_cfg = get_doctype_config(doctype)
    fm = dt_cfg.get("field_mappings") or {}
    mandatory = dt_cfg.get("mandatory_fields") or []
    missing: list[dict[str, Any]] = []
    applied: list[dict[str, Any]] = []

    for field in mandatory:
        if entities.get(field) not in (None, "", [], {}):
            continue
        spec = fm.get(field) if isinstance(fm.get(field), dict) else {}
        default = spec.get("default_value")
        if default not in (None, ""):
            applied.append({"field": field, "value": default, "reason": "kb_default"})
            continue
        missing.append({
            "field": field,
            "tier": 1,
            "question": f"Please provide `{field}` for {doctype}.",
            "reasoning": "Tier1 schema: mandatory field missing.",
            "suggested_default": None,
            "apqc_reference": None,
            "erpnext_reference": None,
        })
    return missing, applied


def get_erp_autofill_fields() -> frozenset[str]:
    cfg = _os_validation_config()
    raw = cfg.get("erp_autofill_fields") or []
    return frozenset(str(x) for x in raw if x)


def get_optional_business_fields(doctype: str) -> list[str]:
    cfg = _os_validation_config()
    per_dt = cfg.get("optional_business_fields") or {}
    if isinstance(per_dt, dict):
        fields = per_dt.get(doctype) or []
        if isinstance(fields, list):
            return [str(f) for f in fields if f]
    return []


def get_delivery_date_skip_phrases() -> frozenset[str]:
    cfg = _os_validation_config()
    raw = cfg.get("delivery_date_skip_phrases") or []
    return frozenset(str(x).casefold() for x in raw if x)


def _entity_value_present(value: Any) -> bool:
    if value in (None, "", [], {}):
        return False
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return False
        if stripped.casefold() in _PSEUDO_DEFAULT_VALUES:
            return False
    return True


def is_delivery_date_skipped(entities: dict[str, Any]) -> bool:
    extra = entities.get("extra")
    if isinstance(extra, dict) and extra.get("delivery_date_skipped"):
        return True
    return False


def is_schedule_date_skipped(entities: dict[str, Any]) -> bool:
    extra = entities.get("extra")
    if isinstance(extra, dict) and extra.get("schedule_date_skipped"):
        return True
    return False


def is_skip_answer(answer: str) -> bool:
    """True when the user declines an optional field (e.g. delivery date)."""
    text = (answer or "").strip().casefold()
    if not text:
        return False
    phrases = get_delivery_date_skip_phrases()
    if text in phrases:
        return True
    return any(text.startswith(p) for p in phrases)


def apply_erp_autofill_from_profile(
    doctype: str,
    entities: dict[str, Any],
    profile: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """
    Fill ERP-internal fields from company profile / KB — never ask the user.
    """
    out = dict(entities)
    applied: list[dict[str, Any]] = []
    profile = profile if isinstance(profile, dict) else {}

    def _apply(field: str, value: Any, reason: str) -> None:
        if value in (None, ""):
            return
        if not _entity_value_present(out.get(field)):
            out[field] = value
            applied.append({"field": field, "value": value, "reason": reason})

    company = (
        profile.get("company")
        or profile.get("default_company")
        or profile.get("company_name")
    )
    currency = profile.get("default_currency") or "INR"
    price_list = profile.get("default_price_list") or "Standard Selling"
    purchase_pl = profile.get("purchase_price_list") or "Standard Buying"

    _apply("company", company, "company_profile")
    _apply("currency", currency, "company_profile")
    _apply("conversion_rate", 1.0, "company_profile")
    _apply("price_list_currency", currency, "company_profile")
    _apply("plc_conversion_rate", 1.0, "company_profile")

    if doctype in ("Sales Order", "Sales Invoice", "Delivery Note", "Quotation"):
        _apply("selling_price_list", price_list, "company_profile")
        _apply("order_type", "Sales", "kb_default")
    if doctype in ("Purchase Order", "Purchase Invoice", "Purchase Receipt"):
        _apply("buying_price_list", purchase_pl, "company_profile")

    fm = get_field_mappings(doctype)
    spec = fm.get("naming_series") if isinstance(fm.get("naming_series"), dict) else {}
    options = spec.get("options") or []
    if options and not _entity_value_present(out.get("naming_series")):
        series = options[0] if isinstance(options[0], str) else str(options[0])
        _apply("naming_series", series, "kb_options")

    from datetime import date as _date

    today = _date.today().isoformat()
    if doctype in ("Sales Order", "Purchase Order", "Quotation"):
        _apply("transaction_date", today, "default_today")
    if doctype in ("Sales Invoice", "Payment Entry", "Stock Entry", "Delivery Note",
                   "Purchase Invoice", "Purchase Receipt"):
        _apply("posting_date", today, "default_today")

    _apply("status", "Draft", "erp_default")
    return out, applied


def business_fields_missing(
    doctype: str,
    entities: dict[str, Any],
    profile: Optional[dict[str, Any]] = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Return fields the *user* must supply — not ERP schema internals.
    Optional fields (delivery date) use tier 2 with skip semantics.
    """
    profile = profile if isinstance(profile, dict) else {}
    entities = normalize_entities_for_doctype(doctype, dict(entities))
    entities, applied = apply_erp_autofill_from_profile(doctype, entities, profile)

    cfg = _os_validation_config()
    sales_dts = frozenset(cfg.get("sales_doctypes_require_customer") or [])
    purchase_dts = frozenset(cfg.get("purchase_doctypes_require_supplier") or [])

    missing: list[dict[str, Any]] = []

    if doctype in sales_dts and not _entity_value_present(entities.get("customer")):
        missing.append({
            "field": "customer",
            "tier": 1,
            "question": f"Which customer is this {doctype} for?",
            "reasoning": "Party required for sales transaction.",
            "suggested_default": None,
        })

    if doctype in purchase_dts and not _entity_value_present(entities.get("supplier")):
        missing.append({
            "field": "supplier",
            "tier": 1,
            "question": f"Which supplier is this {doctype} for?",
            "reasoning": "Party required for purchase transaction.",
            "suggested_default": None,
        })

    items = entities.get("items")
    if doctype in _ITEMS_DOCTYPES() and (not isinstance(items, list) or len(items) == 0):
        missing.append({
            "field": "items",
            "tier": 1,
            "question": (
                f"What item(s) should be included in this {doctype}, "
                "and what quantity for each?"
            ),
            "reasoning": "Line items required.",
            "suggested_default": None,
        })

    for field in get_optional_business_fields(doctype):
        if field == "delivery_date" and is_delivery_date_skipped(entities):
            continue
        if _entity_value_present(entities.get(field)):
            continue
        if field == "delivery_date":
            question = (
                "When should this order be delivered? "
                "(Optional — reply with a date, or say 'skip' / 'not needed' if no delivery date.)"
            )
        elif field == "schedule_date":
            question = (
                "When should this purchase be scheduled? "
                "(Optional — reply with a date, or say 'skip' / 'not needed'.)"
            )
        else:
            question = f"Please provide {field} (optional — say 'skip' if not needed)."
        missing.append({
            "field": field,
            "tier": 2,
            "question": question,
            "reasoning": "Optional business field.",
            "suggested_default": None,
        })

    return missing, applied


def apply_business_clarification_answers(
    intent: dict[str, Any],
    clarification_qa: list[Any],
) -> dict[str, Any]:
    """Merge skip/decline answers for optional business fields into intent entities."""
    if not isinstance(intent, dict):
        return intent
    out = dict(intent)
    entities = out.get("entities")
    if not isinstance(entities, dict):
        entities = {}
    else:
        entities = dict(entities)
    extra = entities.get("extra")
    if not isinstance(extra, dict):
        extra = {}
    else:
        extra = dict(extra)

    for qa in clarification_qa or []:
        if not isinstance(qa, dict):
            continue
        question = str(qa.get("question") or "").casefold()
        answer = str(qa.get("answer") or "").strip()
        if not answer:
            continue
        if "delivery" in question or "deliver" in question or "schedule" in question:
            if is_skip_answer(answer):
                if "delivery" in question or "deliver" in question:
                    entities["delivery_date"] = None
                    extra["delivery_date_skipped"] = True
                if "schedule" in question:
                    entities["schedule_date"] = None
                    extra["schedule_date_skipped"] = True
            elif ("delivery" in question or "deliver" in question) and not entities.get("delivery_date"):
                entities["delivery_date"] = answer
                extra.pop("delivery_date_skipped", None)
            elif "schedule" in question and not entities.get("schedule_date"):
                entities["schedule_date"] = answer
                extra.pop("schedule_date_skipped", None)

    entities["extra"] = extra
    out["entities"] = entities
    return out


def filter_missing_for_doctype(doctype: str, missing: list[Any]) -> list[dict[str, Any]]:
    """Drop LLM-suggested fields that do not apply to this doctype's KB schema."""
    fm = get_field_mappings(doctype)
    mandatory = set(get_doctype_config(doctype).get("mandatory_fields") or [])
    autofill = get_erp_autofill_fields()
    kept: list[dict[str, Any]] = []
    for entry in missing:
        if not isinstance(entry, dict):
            continue
        field = str(entry.get("field") or "")
        top = field.split(".", 1)[0]
        if top in autofill:
            continue
        if top == "items" and top not in fm:
            if doctype not in _ITEMS_DOCTYPES():
                continue
        if top in fm or top in mandatory:
            kept.append(entry)
    return kept


@lru_cache(maxsize=1)
def _ITEMS_DOCTYPES() -> frozenset[str]:
    """Doctypes whose KB schema includes an items child table entity."""
    names: set[str] = set()
    raw = compose_field_mappings()
    for dt_name, cfg in (raw.get("doctypes") or {}).items():
        if isinstance(cfg, dict) and "items" in (cfg.get("field_mappings") or {}):
            names.add(str(dt_name))
    return frozenset(names)


def map_entities_to_payload_fields(
    doctype: str,
    entities: dict[str, Any],
) -> dict[str, Any]:
    """
    Map clarity entities → ERP payload keys using KB-04 only.
    Skips entity keys with no mapping for this doctype.
    """
    payload: dict[str, Any] = {}
    entities = normalize_entities_for_doctype(doctype, entities)

    for entity_key, value in entities.items():
        if value in (None, "", [], {}):
            continue
        if entity_key in _NON_FIELD_ENTITY_KEYS:
            continue
        resolved = resolve_entity_to_field(doctype, entity_key)
        if not resolved:
            continue
        _, spec = resolved
        fn = str(spec.get("fieldname") or entity_key)
        payload[fn] = value

    return payload


def apply_field_defaults_to_payload(doctype: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Fill payload fields from KB default_value when not already set."""
    for _key, spec in get_field_mappings(doctype).items():
        if not isinstance(spec, dict):
            continue
        fn = str(spec.get("fieldname") or _key)
        if fn in payload and payload[fn] not in (None, "", [], {}):
            continue
        default = spec.get("default_value")
        if default not in (None, ""):
            payload[fn] = default
    return payload


def clear_semantics_cache() -> None:
    """Clear cached KB reads (for tests)."""
    _doctype_graph.cache_clear()
    _os_validation_config.cache_clear()
    _ITEMS_DOCTYPES.cache_clear()
    doctype_mapping.cache_clear()
    compose_field_mappings.cache_clear()
