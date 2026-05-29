"""
KB-driven field semantics for ERP-OS payload building and validation.

Resolves clarity entity keys → ERP field specs using KB-04 mappings,
KB-07 doctype graph (name_field, setup layers), and os_validation.json.
No hardcoded doctype lists in callers.
"""

from __future__ import annotations

import copy
import json
import re
from datetime import date
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

_FIELD_IN_QUESTION_RE = re.compile(
    r"field\s+['\"]?([a-zA-Z_][a-zA-Z0-9_]*)['\"]?",
    re.IGNORECASE,
)

_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12,
}


def is_pseudo_erp_value(value: Any) -> bool:
    """True for KB placeholders that must not be sent to ERP or shown to users."""
    if value is None:
        return False
    if not isinstance(value, str):
        return False
    s = value.strip()
    if not s:
        return False
    sl = s.casefold()
    if sl in _PSEUDO_DEFAULT_VALUES:
        return True
    if sl.startswith("user_default_") or sl.startswith("fetch_from_"):
        return True
    if "transaction_date" in sl and "+" in sl:
        return True
    if "{" in s and "}" in s:
        return True
    return False


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
        if _entity_value_present(out.get(field)):
            continue
        spec = fm.get(field) if isinstance(fm.get(field), dict) else {}
        default = spec.get("default_value")
        if default not in (None, "") and not is_pseudo_erp_value(str(default)):
            out[field] = default
    return out


def parse_natural_date(value: Any, *, default_year: Optional[int] = None) -> Optional[str]:
    """
    Parse user/clarification dates like '5th june' → ISO using current year by default.
    Returns None if not parseable.
    """
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    v = raw.casefold()
    year = default_year if default_year is not None else date.today().year

    if v in ("today",):
        return date.today().isoformat()
    if v == "tomorrow":
        from datetime import timedelta
        return (date.today() + timedelta(days=1)).isoformat()

    if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
        try:
            d = date.fromisoformat(raw)
            if d.year < 2000:
                d = d.replace(year=year)
            return d.isoformat()
        except ValueError:
            pass

    m = re.search(
        r"(\d{1,2})(?:st|nd|rd|th)?\s+([a-z]+)(?:\s+(\d{4}))?",
        v,
    )
    if m:
        day = int(m.group(1))
        mon = _MONTHS.get(m.group(2))
        yr = int(m.group(3)) if m.group(3) else year
        if mon:
            try:
                return date(yr, mon, day).isoformat()
            except ValueError:
                pass

    m2 = re.search(r"([a-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s+(\d{4}))?", v)
    if m2:
        mon = _MONTHS.get(m2.group(1))
        day = int(m2.group(2))
        yr = int(m2.group(3)) if m2.group(3) else year
        if mon:
            try:
                return date(yr, mon, day).isoformat()
            except ValueError:
                pass

    for sep in ("-", "/"):
        parts = v.split(sep)
        if len(parts) == 3 and len(parts[2]) == 4:
            try:
                d = date(int(parts[2]), int(parts[1]), int(parts[0]))
                return d.isoformat()
            except ValueError:
                pass

    return None


def normalize_item_row(row: Any) -> dict[str, Any]:
    """Map LLM/clarification item keys → payload keys (item_code, qty, uom)."""
    if not isinstance(row, dict):
        return {}
    out: dict[str, Any] = dict(row)
    if not out.get("item_code") and out.get("item_name"):
        out["item_code"] = out["item_name"]
    if out.get("qty") is None and out.get("quantity") is not None:
        out["qty"] = out["quantity"]
    uom = out.get("uom") or out.get("unit")
    if uom and not out.get("uom"):
        out["uom"] = uom
    return out


def normalize_items_list(items: Any) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    norm: list[dict[str, Any]] = []
    for row in items:
        r = normalize_item_row(row)
        if r.get("item_code") or r.get("qty") is not None:
            norm.append(r)
    return norm


def _items_have_line_codes(items: list[dict[str, Any]]) -> bool:
    return any(isinstance(r, dict) and r.get("item_code") for r in items)


def preserve_transaction_entities(
    merged: dict[str, Any],
    partial: dict[str, Any],
    doctype: str,
) -> dict[str, Any]:
    """
    After any clarification merge, keep good Clarity extraction (customer, item lines).
    """
    out = copy.deepcopy(merged) if isinstance(merged, dict) else {}
    if not isinstance(partial, dict):
        return out

    p_ent = partial.get("entities") if isinstance(partial.get("entities"), dict) else {}
    m_ent = out.get("entities") if isinstance(out.get("entities"), dict) else {}
    if not isinstance(m_ent, dict):
        m_ent = {}
    entities = dict(m_ent)

    cfg = _os_validation_config()
    sales_dts = frozenset(cfg.get("sales_doctypes_require_customer") or [])
    purchase_dts = frozenset(cfg.get("purchase_doctypes_require_supplier") or [])

    pc = p_ent.get("customer")
    mc = entities.get("customer")
    if pc and (
        not mc
        or (isinstance(pc, str) and isinstance(mc, str) and len(pc) > len(mc) and pc.lower().startswith(mc.lower()))
    ):
        entities["customer"] = copy.deepcopy(pc)

    ps = p_ent.get("supplier")
    ms = entities.get("supplier")
    if ps and (
        not ms
        or (isinstance(ps, str) and isinstance(ms, str) and len(ps) > len(ms) and ps.lower().startswith(ms.lower()))
    ):
        entities["supplier"] = copy.deepcopy(ps)

    if doctype in sales_dts and entities.get("supplier") and not p_ent.get("supplier"):
        entities.pop("supplier", None)
    if doctype in purchase_dts and entities.get("customer") and not p_ent.get("customer"):
        entities.pop("customer", None)

    p_items = normalize_items_list(p_ent.get("items"))
    m_items = normalize_items_list(entities.get("items"))
    p_codes = {str(r.get("item_code")) for r in p_items if r.get("item_code")}
    m_codes = {str(r.get("item_code")) for r in m_items if r.get("item_code")}
    if p_codes and (not m_codes or p_codes != m_codes):
        entities["items"] = copy.deepcopy(p_items)
    elif m_items:
        entities["items"] = m_items
    elif p_items:
        entities["items"] = copy.deepcopy(p_items)

    for key in list(entities.keys()):
        if key in _NON_FIELD_ENTITY_KEYS:
            continue
        if is_pseudo_erp_value(entities.get(key)):
            entities.pop(key, None)

    out["entities"] = entities
    if _empty_scalar(out.get("intent_id")) and partial.get("intent_id"):
        out["intent_id"] = partial["intent_id"]
    if _empty_scalar(out.get("target_doctype")) and partial.get("target_doctype"):
        out["target_doctype"] = partial["target_doctype"]
    return out


def _empty_scalar(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, str) and not v.strip():
        return True
    return False


def sanitize_entities_for_transaction(
    doctype: str,
    entities: dict[str, Any],
    profile: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Normalize items, strip pseudo defaults, apply profile autofill on entity dict."""
    ent = dict(entities) if isinstance(entities, dict) else {}
    ent["items"] = normalize_items_list(ent.get("items"))
    for key in list(ent.keys()):
        if key in ("items", "extra"):
            continue
        if is_pseudo_erp_value(ent.get(key)):
            ent.pop(key, None)
    ent, _applied = apply_erp_autofill_from_profile(doctype, ent, profile or {})
    return ent


def clarification_is_simple(clarification_qa: list[Any], *, doctype: str = "") -> bool:
    """Date/skip/ERP-autofill answers should not trigger a full LLM intent rewrite."""
    if not clarification_qa:
        return False
    last = clarification_qa[-1]
    if not isinstance(last, dict):
        return False
    q = str(last.get("question") or "").casefold()
    if "validation" in q and ("json" in q or "field→value" in q or "numbered" in q):
        return False
    if "naming_series" in q or "conversion_rate" in q or "selling_price_list" in q:
        return False

    autofill = get_erp_autofill_fields()
    mentioned: list[str] = []
    for qa in clarification_qa:
        if isinstance(qa, dict):
            mentioned.extend(extract_fields_from_clarification_question(str(qa.get("question") or "")))
    if mentioned and all(f in autofill for f in mentioned):
        return True

    return any(tok in q for tok in (
        "deliver", "delivery", "schedule", "business info", "business_requirements",
    )) or len(clarification_qa) == 1


def merge_clarification_into_intent(
    partial_intent: dict[str, Any],
    clarification_qa: list[Any],
    *,
    profile: Optional[dict[str, Any]] = None,
) -> Optional[dict[str, Any]]:
    """
    Deterministic clarification merge (no LLM). Returns None if LLM path is required.
    """
    doctype = str(partial_intent.get("target_doctype") or "")
    if not clarification_is_simple(clarification_qa, doctype=doctype):
        return None

    out = copy.deepcopy(partial_intent)
    out = apply_business_clarification_answers(out, clarification_qa)

    entities = out.get("entities") if isinstance(out.get("entities"), dict) else {}
    for qa in clarification_qa or []:
        if not isinstance(qa, dict):
            continue
        q_raw = str(qa.get("question") or "")
        q = q_raw.casefold()
        ans = str(qa.get("answer") or "").strip()
        if not ans or is_skip_answer(ans):
            continue
        for field in extract_fields_from_clarification_question(q_raw):
            resolved = resolve_entity_to_field(doctype, field)
            kb_key = resolved[0] if resolved else field
            entities[kb_key] = ans
        if "deliver" in q or "delivery" in q:
            parsed = parse_natural_date(ans)
            if parsed:
                entities["delivery_date"] = parsed
                extra = entities.get("extra") if isinstance(entities.get("extra"), dict) else {}
                extra = dict(extra)
                extra.pop("delivery_date_skipped", None)
                entities["extra"] = extra
        if "schedule" in q:
            parsed = parse_natural_date(ans)
            if parsed:
                entities["schedule_date"] = parsed

    out["entities"] = sanitize_entities_for_transaction(doctype, entities, profile)
    out = preserve_transaction_entities(out, partial_intent, doctype)
    out["ambiguities"] = []
    out["has_ambiguities"] = False
    return out


def apply_profile_autofill_to_payload(
    doctype: str,
    payload: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    """Inject ERP-internal mandatory fields from company profile (not user input)."""
    profile = context.get("company_profile") if isinstance(context.get("company_profile"), dict) else {}
    company = (
        profile.get("erp_resolved_company")
        or profile.get("company")
        or profile.get("default_company")
        or profile.get("company_name")
    )
    currency = profile.get("default_currency") or "INR"
    price_list = profile.get("default_price_list") or "Standard Selling"
    purchase_pl = profile.get("purchase_price_list") or "Standard Buying"

    if company and (not payload.get("company") or is_pseudo_erp_value(payload.get("company"))):
        payload["company"] = company
    if currency and (not payload.get("currency") or is_pseudo_erp_value(payload.get("currency"))):
        payload["currency"] = currency
    payload.setdefault("conversion_rate", 1.0)
    payload.setdefault("price_list_currency", currency)
    payload.setdefault("plc_conversion_rate", 1.0)

    if doctype in ("Sales Order", "Sales Invoice", "Delivery Note", "Quotation"):
        if not payload.get("selling_price_list") or is_pseudo_erp_value(payload.get("selling_price_list")):
            payload["selling_price_list"] = price_list
        payload.setdefault("order_type", "Sales")
    if doctype in ("Purchase Order", "Purchase Invoice", "Purchase Receipt"):
        if not payload.get("buying_price_list") or is_pseudo_erp_value(payload.get("buying_price_list")):
            payload["buying_price_list"] = purchase_pl

    fm = get_field_mappings(doctype)
    spec = fm.get("naming_series") if isinstance(fm.get("naming_series"), dict) else {}
    options = spec.get("options") or []
    if options and not payload.get("naming_series"):
        payload["naming_series"] = options[0] if isinstance(options[0], str) else str(options[0])

    payload.setdefault("status", "Draft")
    if "title" in (get_doctype_config(doctype).get("mandatory_fields") or []):
        if not _entity_value_present(payload.get("title")):
            ent_from_pay = {
                k: payload[k]
                for k in ("supplier", "customer", "items", "supplier_name", "customer_name")
                if k in payload
            }
            title = build_transaction_title(doctype, ent_from_pay, payload)
            if title:
                payload["title"] = title
            else:
                bindings = build_entity_bindings(doctype, ent_from_pay, profile, payload)
                for _key, spec in get_field_mappings(doctype).items():
                    if not isinstance(spec, dict) or str(spec.get("fieldname") or _key) != "title":
                        continue
                    default = spec.get("default_value")
                    if isinstance(default, str) and "{" in default:
                        val = resolve_template_string(default, bindings)
                        if val:
                            payload["title"] = val
                    break
    return payload


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


def get_transaction_party_field(doctype: str) -> Optional[str]:
    """KB-driven party field for sales/purchase transactions (customer or supplier)."""
    cfg = _os_validation_config()
    if doctype in frozenset(cfg.get("sales_doctypes_require_customer") or []):
        return "customer"
    if doctype in frozenset(cfg.get("purchase_doctypes_require_supplier") or []):
        return "supplier"
    fm = get_field_mappings(doctype)
    for key, spec in fm.items():
        if not isinstance(spec, dict):
            continue
        if spec.get("options") == "Customer":
            return str(spec.get("fieldname") or key)
        if spec.get("options") == "Supplier":
            return str(spec.get("fieldname") or key)
    return None


def _slug_part(text: Any, *, max_len: int = 48) -> str:
    raw = str(text or "").strip()
    if not raw:
        return ""
    cleaned = re.sub(r"[^\w\s-]", "", raw, flags=re.UNICODE)
    cleaned = re.sub(r"[\s_]+", "-", cleaned).strip("-").casefold()
    return cleaned[:max_len] if cleaned else ""


def _first_item_label(items: Any) -> str:
    rows = normalize_items_list(items)
    if not rows:
        return ""
    row = rows[0]
    return str(row.get("item_code") or row.get("item_name") or row.get("name") or "").strip()


def build_entity_bindings(
    doctype: str,
    entities: dict[str, Any],
    profile: Optional[dict[str, Any]] = None,
    payload: Optional[dict[str, Any]] = None,
) -> dict[str, str]:
    """Bindings for KB template placeholders ({supplier_name}, {item_code}, …)."""
    ent = entities if isinstance(entities, dict) else {}
    pay = payload if isinstance(payload, dict) else {}
    prof = profile if isinstance(profile, dict) else {}
    bindings: dict[str, str] = {}

    party_field = get_transaction_party_field(doctype)
    party_val = ""
    if party_field:
        party_val = str(ent.get(party_field) or pay.get(party_field) or "").strip()
    bindings["party"] = party_val
    bindings["supplier_name"] = str(
        ent.get("supplier_name") or ent.get("supplier") or pay.get("supplier") or pay.get("supplier_name") or ""
    ).strip()
    bindings["customer_name"] = str(
        ent.get("customer_name") or ent.get("customer") or pay.get("customer") or pay.get("customer_name") or ""
    ).strip()
    item_label = _first_item_label(ent.get("items") or pay.get("items"))
    bindings["item_code"] = item_label
    bindings["item_name"] = item_label
    bindings["company"] = str(
        pay.get("company")
        or ent.get("company")
        or prof.get("erp_resolved_company")
        or prof.get("default_company")
        or prof.get("company_name")
        or ""
    ).strip()
    return bindings


def resolve_template_string(template: str, bindings: dict[str, str]) -> Optional[str]:
    """Expand {supplier_name}-style KB templates; return None if placeholders remain."""
    if not template or "{" not in template:
        return None
    out = template
    for key, val in bindings.items():
        if val:
            out = out.replace("{" + key + "}", val)
    if "{" in out and "}" in out:
        return None
    out = out.strip()
    return out or None


def resolve_link_value_from_options(
    desired: Any,
    options: list[str],
    *,
    allow_first_fallback: bool = False,
) -> Optional[str]:
    """
    Match a link field value against live ERP options.
    Pseudo tokens (user_default_company_or_first_company) use first live option when allowed.
    """
    opts = [str(o).strip() for o in options if o and str(o).strip()]
    if not opts:
        if desired in (None, "") or is_pseudo_erp_value(desired):
            return None
        return str(desired).strip() or None

    normalized = {name.casefold(): name for name in opts}
    candidates: list[str] = []
    if desired not in (None, ""):
        candidates.append(str(desired).strip())
    for cand in candidates:
        if not cand or is_pseudo_erp_value(cand):
            continue
        hit = normalized.get(cand.casefold())
        if hit:
            return hit

    if allow_first_fallback or not candidates or all(is_pseudo_erp_value(c) for c in candidates):
        return opts[0]
    return None


def resolve_company_for_payload(
    preferred: Any,
    context: dict[str, Any],
) -> Optional[str]:
    """Resolve Company link from profile + live link_cache (any client/site)."""
    profile = context.get("company_profile") if isinstance(context.get("company_profile"), dict) else {}
    link_cache = context.get("link_cache") if isinstance(context.get("link_cache"), dict) else {}
    options = link_cache.get("Company") or link_cache.get("company") or []
    if not isinstance(options, list):
        options = []

    for cand in (
        profile.get("erp_resolved_company"),
        preferred,
        profile.get("default_company"),
        profile.get("company_name"),
        context.get("defaults", {}).get("company") if isinstance(context.get("defaults"), dict) else None,
    ):
        resolved = resolve_link_value_from_options(
            cand,
            options,
            allow_first_fallback=is_pseudo_erp_value(cand) if cand else bool(options),
        )
        if resolved:
            return resolved
    if options:
        return resolve_link_value_from_options(None, options, allow_first_fallback=True)
    return None


def build_transaction_title(
    doctype: str,
    entities: dict[str, Any],
    payload: Optional[dict[str, Any]] = None,
) -> Optional[str]:
    """
    KB policy: transaction_title_pattern → {party_slug}-{item_slug}.
    Works for any doctype with party + line items (PO, SO, etc.).
    """
    cfg = _os_validation_config()
    pattern = str(cfg.get("transaction_title_pattern") or "{party_slug}-{item_slug}")
    bindings = build_entity_bindings(doctype, entities, payload=payload)
    party = bindings.get("party") or bindings.get("supplier_name") or bindings.get("customer_name")
    item = bindings.get("item_code") or bindings.get("item_name")
    if not party or not item:
        resolved = resolve_template_string("{supplier_name}", bindings) or resolve_template_string(
            "{customer_name}", bindings
        )
        if resolved:
            party = party or resolved
    party_slug = _slug_part(party)
    item_slug = _slug_part(item)
    if not party_slug and not item_slug:
        return None
    title_bindings = {
        "party_slug": party_slug or "doc",
        "item_slug": item_slug or "item",
        "party": party or "",
        "item_code": item or "",
    }
    built = pattern
    for key, val in title_bindings.items():
        built = built.replace("{" + key + "}", val)
    built = built.strip("- ")
    return built[:140] if built else None


def extract_fields_from_clarification_question(question: str) -> list[str]:
    """Parse 'Field title is mandatory' style validation prompts."""
    return list(dict.fromkeys(_FIELD_IN_QUESTION_RE.findall(question or "")))


def apply_computed_defaults_to_payload(
    doctype: str,
    payload: dict[str, Any],
    entities: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    """
    Resolve KB templates, transaction titles, and Company links before validation/execute.
    Single policy path for all doctypes/clients.
    """
    out = dict(payload)
    ent = entities if isinstance(entities, dict) else {}
    profile = context.get("company_profile") if isinstance(context.get("company_profile"), dict) else {}
    bindings = build_entity_bindings(doctype, ent, profile, out)

    resolved_company = resolve_company_for_payload(out.get("company"), context)
    if resolved_company:
        out["company"] = resolved_company
        bindings["company"] = resolved_company

    mandatory = get_doctype_config(doctype).get("mandatory_fields") or []
    fm = get_field_mappings(doctype)
    autofill = get_erp_autofill_fields()

    for field in mandatory:
        if field not in autofill and field != "title":
            continue
        if _entity_value_present(out.get(field)):
            continue
        if field == "title":
            title = build_transaction_title(doctype, ent, out)
            if title:
                out["title"] = title
                bindings["title"] = title
                continue
        spec = fm.get(field) if isinstance(fm.get(field), dict) else {}
        default = spec.get("default_value")
        if default not in (None, "") and isinstance(default, str) and "{" in default:
            val = resolve_template_string(default, bindings)
            if val:
                out[field] = val
                bindings[field] = val

    for _key, spec in fm.items():
        if not isinstance(spec, dict):
            continue
        fn = str(spec.get("fieldname") or _key)
        if _entity_value_present(out.get(fn)) and not is_pseudo_erp_value(out.get(fn)):
            continue
        default = spec.get("default_value")
        if default in (None, "") or not isinstance(default, str):
            continue
        if "{" not in default:
            continue
        val = resolve_template_string(default, bindings)
        if val:
            out[fn] = val

    link_cache = context.get("link_cache") if isinstance(context.get("link_cache"), dict) else {}
    for _key, spec in fm.items():
        if not isinstance(spec, dict):
            continue
        fn = str(spec.get("fieldname") or _key)
        link_dt = spec.get("options")
        if not link_dt or not isinstance(link_dt, str):
            continue
        opts = link_cache.get(link_dt)
        if not isinstance(opts, list) or not opts:
            continue
        if out.get(fn) in (None, "") or is_pseudo_erp_value(out.get(fn)):
            resolved = resolve_link_value_from_options(
                out.get(fn) or spec.get("default_value"),
                opts,
                allow_first_fallback=True,
            )
            if resolved:
                out[fn] = resolved

    return out


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
        profile.get("erp_resolved_company")
        or profile.get("company")
        or profile.get("default_company")
        or profile.get("company_name")
    )
    currency = profile.get("default_currency") or "INR"
    price_list = profile.get("default_price_list") or "Standard Selling"
    purchase_pl = profile.get("purchase_price_list") or "Standard Buying"

    _apply("company", company, "company_profile")
    if "title" in (get_doctype_config(doctype).get("mandatory_fields") or []):
        title = build_transaction_title(doctype, out, None)
        if title:
            _apply("title", title, "transaction_title_pattern")
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
            elif "delivery" in question or "deliver" in question:
                parsed = parse_natural_date(answer)
                if parsed:
                    entities["delivery_date"] = parsed
                    extra.pop("delivery_date_skipped", None)
                elif not is_skip_answer(answer):
                    entities["delivery_date"] = answer
                    extra.pop("delivery_date_skipped", None)
            elif "schedule" in question:
                parsed = parse_natural_date(answer)
                if parsed:
                    entities["schedule_date"] = parsed
                    extra.pop("schedule_date_skipped", None)
                elif not is_skip_answer(answer):
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


def apply_field_defaults_to_payload(
    doctype: str,
    payload: dict[str, Any],
    *,
    entities: Optional[dict[str, Any]] = None,
    context: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Fill payload from KB default_value; resolve {template} tokens when bindings allow."""
    ent = entities if isinstance(entities, dict) else {}
    prof = {}
    if isinstance(context, dict):
        prof = context.get("company_profile") if isinstance(context.get("company_profile"), dict) else {}
    bindings = build_entity_bindings(doctype, ent, prof, payload)

    for _key, spec in get_field_mappings(doctype).items():
        if not isinstance(spec, dict):
            continue
        fn = str(spec.get("fieldname") or _key)
        if fn in payload and payload[fn] not in (None, "", [], {}) and not is_pseudo_erp_value(payload[fn]):
            continue
        default = spec.get("default_value")
        if default in (None, ""):
            continue
        default_s = str(default)
        if "{" in default_s:
            val = resolve_template_string(default_s, bindings)
            if val:
                payload[fn] = val
            continue
        if not is_pseudo_erp_value(default_s):
            payload[fn] = default
    return payload


def clear_semantics_cache() -> None:
    """Clear cached KB reads (for tests)."""
    _doctype_graph.cache_clear()
    _os_validation_config.cache_clear()
    _ITEMS_DOCTYPES.cache_clear()
    doctype_mapping.cache_clear()
    compose_field_mappings.cache_clear()
