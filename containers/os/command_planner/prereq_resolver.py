from __future__ import annotations

import logging
from typing import Any, Optional

from containers.os.payload_generator.kb_fields import field_kb
from shared.models.plan import ExecutionPlan, PlanStep

logger = logging.getLogger(__name__)

_BOOTSTRAP_MASTER_PAYLOADS: dict[str, dict[str, Any]] = {
    "Customer Group": {
        "customer_group_name": "All Customer Groups",
        "is_group": 1,
    },
    "Territory": {
        "territory_name": "All Territories",
        "is_group": 1,
    },
    "Supplier Group": {
        "supplier_group_name": "All Supplier Groups",
        "is_group": 1,
    },
    "UOM": {
        "uom_name": "Nos",
        "enabled": 1,
    },
}

_NAME_FIELD_BY_DOCTYPE: dict[str, str] = {
    "Customer Group": "customer_group_name",
    "Territory": "territory_name",
    "Supplier Group": "supplier_group_name",
    "Item Group": "item_group_name",
    "UOM": "uom_name",
}


def _parse_depends_on(depends_on: Optional[str]) -> Optional[int]:
    if not depends_on:
        return None
    if not depends_on.startswith("step_"):
        return None
    try:
        return int(depends_on.split("step_")[-1])
    except ValueError:
        return None


def _bootstrap_display_value(doctype: str, payload: dict[str, Any]) -> str:
    name_field = _NAME_FIELD_BY_DOCTYPE.get(doctype, "name")
    value = payload.get(name_field) or payload.get("name") or ""
    return str(value).strip()


async def _list_master_names(
    adapter,
    doctype: str,
    limit: int = 100,
) -> list[str]:
    """
    Fetch list of master data names using ERPAdapter.
    
    NOW USES ERPAdapter instead of direct aiohttp calls.
    """
    try:
        rows = await adapter.list_records(doctype, fields=["name"], limit=limit)
        names = [str(row.get("name", "")).strip() for row in rows if row.get("name")]
        logger.info("Planner prereq lookup: %s has %d option(s)", doctype, len(names))
        return names
    except Exception as exc:
        logger.warning("Planner prereq lookup failed for %s: %s", doctype, exc)
        return []


async def _bootstrap_master_options(
    adapter,
    doctype: str,
) -> list[str]:
    """
    Create a bootstrap master record if missing.
    
    NOW USES ERPAdapter instead of direct aiohttp calls.
    """
    payload = _BOOTSTRAP_MASTER_PAYLOADS.get(doctype)
    if not payload:
        return []

    try:
        await adapter.create_record(doctype, payload)
        display_value = _bootstrap_display_value(doctype, payload)
        logger.info("Bootstrapped missing %s record via %s", doctype, display_value)
    except Exception as exc:
        logger.warning("Bootstrap create failed for %s: %s", doctype, exc)
        return []

    return await _list_master_names(adapter, doctype, limit=100)


async def _resolve_link_field(
    doctype: str,
    field_key: str,
    field_spec: dict[str, Any],
    current_entities: dict[str, Any],
    adapter,
) -> tuple[Optional[str], Optional[PlanStep], str]:
    """
    Resolve a link field value by checking if it exists in ERP.
    
    NOW USES ERPAdapter instead of direct HTTP calls.
    """
    link_doctype = field_spec.get("options", "")
    desired = current_entities.get(field_key)
    default = field_spec.get("default_value")

    desired_value = str(desired or default or "").strip()
    if not link_doctype or not desired_value:
        return None, None, "no_resolution_needed"

    options = await _list_master_names(adapter, link_doctype, limit=100)

    if options:
        normalized = {name.casefold(): name for name in options}
        for candidate in [desired_value, str(default or "").strip()]:
            if not candidate:
                continue
            match = normalized.get(candidate.casefold())
            if match:
                return match, None, "matched_existing"

        chosen = options[0]
        logger.warning(
            "Planner prereq resolution: %s.%s='%s' not found, using existing '%s'",
            doctype,
            field_key,
            desired_value,
            chosen,
        )
        return chosen, None, "fallback_existing"

    bootstrap_payload = _BOOTSTRAP_MASTER_PAYLOADS.get(link_doctype)
    if bootstrap_payload:
        bootstrap_value = _bootstrap_display_value(link_doctype, bootstrap_payload)
        logger.warning(
            "Planner prereq resolution: %s.%s has no %s options — inserting bootstrap step for '%s'",
            doctype,
            field_key,
            link_doctype,
            bootstrap_value,
        )
        prereq_step = PlanStep(
            step_number=0,
            action="create",
            doctype=link_doctype,
            required_fields=[],
            optional_fields=[],
            entities={field_key: bootstrap_value, "name": bootstrap_value},
            payload_template=dict(bootstrap_payload),
            description=f"Ensure {link_doctype} '{bootstrap_value}' exists",
            step_role="prerequisite",
            prerequisite_for=doctype,
            resolution_source="planner_bootstrap",
            rollback_if_failed=False,
        )
        return bootstrap_value, prereq_step, "bootstrap_inserted"

    logger.warning(
        "Planner prereq resolution: %s.%s='%s' unresolved — no ERP options and no bootstrap policy",
        doctype,
        field_key,
        desired_value,
    )
    return desired_value, None, "unresolved"


async def _resolve_create_step_prerequisites(
    step: PlanStep,
    adapter,
) -> tuple[PlanStep, list[PlanStep]]:
    """
    Resolve all link field prerequisites for a create step.
    
    NOW USES ERPAdapter instead of direct HTTP calls.
    """
    kb = field_kb()
    field_mappings = kb.field_mappings(step.doctype)
    if not field_mappings:
        return step, []

    resolved_step = step.model_copy(deep=True)
    prereq_steps: list[PlanStep] = []

    for field_key, field_spec in field_mappings.items():
        if field_spec.get("fieldtype") != "Link":
            continue
        if not field_spec.get("mandatory"):
            continue

        resolved_value, prereq_step, strategy = await _resolve_link_field(
            doctype=step.doctype,
            field_key=field_key,
            field_spec=field_spec,
            current_entities=resolved_step.entities,
            adapter=adapter,
        )

        if resolved_value:
            resolved_step.entities[field_key] = resolved_value
            logger.info(
                "Planner prereq resolution: %s.%s -> %s (%s)",
                step.doctype,
                field_key,
                resolved_value,
                strategy,
            )

        if prereq_step:
            prereq_steps.append(prereq_step)

    return resolved_step, prereq_steps


async def enrich_plan_with_prerequisites(
    plan: ExecutionPlan,
    context: dict[str, Any],
) -> ExecutionPlan:
    """
    Enrich an execution plan with prerequisite steps for missing master data.
    
    NOW USES ERPAdapter for all ERP operations.
    """
    creds = context.get("erp_credentials", {})
    erp_url = creds.get("erp_url", "")
    api_key = creds.get("api_key", "")
    api_secret = creds.get("api_secret", "")
    verify_ssl = creds.get("verify_ssl", True)
    allow_insecure_ssl = creds.get("allow_insecure_ssl", True)

    if not erp_url or not api_key or not api_secret:
        logger.info("Planner prereq resolution skipped — ERP credentials unavailable")
        return plan

    # Build ERPAdapter for all lookups
    from shared.erp_adapters.registry import get_adapter

    profile = {
        "erp_type": "erpnext",
        "erp_url": erp_url,
        "api_key": api_key,
        "api_secret": api_secret,
        "verify_ssl": verify_ssl,
        "allow_insecure_ssl": allow_insecure_ssl,
    }
    adapter = get_adapter(profile)

    records: list[dict[str, Any]] = []

    for step in plan.steps:
        original_dep = step.depends_on
        original_source = step.source_step
        old_step_number = step.step_number

        prereq_steps: list[PlanStep] = []
        resolved_step = step.model_copy(deep=True)

        if step.action == "create":
            resolved_step, prereq_steps = await _resolve_create_step_prerequisites(
                resolved_step,
                adapter=adapter,
            )

        for idx, prereq in enumerate(prereq_steps):
            records.append({
                "step": prereq,
                "role": "prerequisite",
                "applies_to_old": old_step_number,
                "prereq_index": idx,
                "original_dep": original_dep if idx == 0 else None,
                "old_step_number": None,
                "original_source": None,
            })

        records.append({
            "step": resolved_step,
            "role": "main",
            "applies_to_old": old_step_number,
            "prereq_index": None,
            "original_dep": original_dep,
            "old_step_number": old_step_number,
            "original_source": original_source,
        })

    old_to_new: dict[int, int] = {}
    prereq_nums_by_old: dict[int, list[int]] = {}

    for new_num, record in enumerate(records, start=1):
        step = record["step"]
        step.step_number = new_num
        if record["role"] == "main" and record["old_step_number"] is not None:
            old_to_new[record["old_step_number"]] = new_num
        elif record["role"] == "prerequisite":
            prereq_nums_by_old.setdefault(record["applies_to_old"], []).append(new_num)

    for record in records:
        step = record["step"]
        if record["role"] == "prerequisite":
            chain = prereq_nums_by_old.get(record["applies_to_old"], [])
            idx = record["prereq_index"] or 0
            if idx == 0:
                dep_old = _parse_depends_on(record["original_dep"])
                step.depends_on = f"step_{old_to_new[dep_old]}" if dep_old and dep_old in old_to_new else None
            else:
                step.depends_on = f"step_{chain[idx - 1]}"
            continue

        old_num = record["old_step_number"]
        dep_old = _parse_depends_on(record["original_dep"])
        prereq_chain = prereq_nums_by_old.get(old_num, [])

        if prereq_chain:
            step.depends_on = f"step_{prereq_chain[-1]}"
        elif dep_old and dep_old in old_to_new:
            step.depends_on = f"step_{old_to_new[dep_old]}"
        else:
            step.depends_on = None

        source_old = record["original_source"]
        if source_old and source_old in old_to_new:
            step.source_step = old_to_new[source_old]

    enriched_steps = [record["step"] for record in records]
    if len(enriched_steps) == len(plan.steps):
        logger.info("Planner prereq resolution: no prerequisite steps added")
    else:
        logger.warning(
            "Planner prereq resolution: expanded plan from %d to %d step(s)",
            len(plan.steps),
            len(enriched_steps),
        )

    return plan.model_copy(update={
        "steps": enriched_steps,
        "estimated_api_calls": len(enriched_steps),
        "is_multi_step": len(enriched_steps) > 1,
    })
