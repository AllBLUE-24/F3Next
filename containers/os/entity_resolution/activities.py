"""
OS resolve_entities activity — Live Entity Registry (LER) gate.
"""

from __future__ import annotations

import logging
from typing import Any

from temporalio import activity

from shared.entity_resolution.gaps import resolution_gaps_from_unresolved
from shared.entity_resolution.ler import (
    BRAIN_VERSION,
    apply_resolved_to_intent,
    build_link_cache,
    build_resolution_map,
)
from shared.entity_resolution.resolve import resolve_entities_batch
from shared.entity_resolution.snapshot import empty_brain_overlay
from shared.entity_resolution.targets import (
    collect_link_targets_from_intent,
    link_field_index_from_intent,
)
from shared.erp_semantics import resolve_company_for_payload
from shared.gate_contracts import utc_now_iso

logger = logging.getLogger(__name__)


def _merge_link_caches(existing: dict[str, list[str]], new: dict[str, list[str]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = dict(existing or {})
    for dt, names in (new or {}).items():
        if not names:
            continue
        prior = out.get(dt) or []
        seen = {str(x) for x in prior}
        merged = list(prior)
        for n in names:
            if n and n not in seen:
                seen.add(n)
                merged.append(n)
        out[dt] = merged
    return out


@activity.defn(name="resolve_entities")
async def resolve_entities(data: dict) -> dict:
    """
    RESOLVE gate: prefetch live ERP link names and rewrite intent entities.

    Input:
      intent_dict, context (with erp_credentials / company_profile)

    Returns:
      intent_dict (updated entities),
      context_overlay (link_cache, resolved_entities, resolution_gaps, …)
    """
    intent_dict = dict(data.get("intent_dict") or {})
    context = dict(data.get("context") or {})
    doctype = str(intent_dict.get("target_doctype") or "").strip()

    overlay = empty_brain_overlay()
    profile = context.get("company_profile") if isinstance(context.get("company_profile"), dict) else {}
    creds = context.get("erp_credentials") if isinstance(context.get("erp_credentials"), dict) else {}

    if profile.get("is_dummy") or not creds.get("erp_url") or not creds.get("api_key"):
        logger.info("resolve_entities: skipped (dummy or missing credentials)")
        overlay["live_fetched_at"] = utc_now_iso()
        return {"intent_dict": intent_dict, "context_overlay": overlay, "skipped": True}

    try:
        from shared.erp_adapters.registry import get_adapter

        adapter = get_adapter({**profile, **creds})
        targets = collect_link_targets_from_intent(intent_dict, doctype)
        if not targets:
            overlay["live_fetched_at"] = utc_now_iso()
            return {"intent_dict": intent_dict, "context_overlay": overlay, "skipped": True}

        try:
            activity.heartbeat(f"LER fetch {len(targets)} doctype(s)")
        except RuntimeError:
            pass

        preferred_abbr = None
        if isinstance(profile.get("company_abbr"), str):
            preferred_abbr = profile.get("company_abbr")

        link_cache = await build_link_cache(
            adapter, targets, preferred_abbr=preferred_abbr, log=logger,
        )
        resolution_map = await build_resolution_map(
            adapter, targets, preferred_abbr=preferred_abbr, log=logger,
        )

        existing_cache = context.get("link_cache") if isinstance(context.get("link_cache"), dict) else {}
        link_cache = _merge_link_caches(existing_cache, link_cache)

        entities = intent_dict.get("entities") if isinstance(intent_dict.get("entities"), dict) else {}
        resolved = resolve_entities_batch(
            entities,
            link_cache,
            doctype=doctype,
            preferred_abbr=preferred_abbr,
        )

        index = link_field_index_from_intent(intent_dict, doctype)
        intent_dict = apply_resolved_to_intent(intent_dict, resolution_map, link_field_index=index)

        ent_after = intent_dict.get("entities") if isinstance(intent_dict.get("entities"), dict) else {}
        if resolved.customer:
            ent_after["customer"] = resolved.customer
        if resolved.supplier:
            ent_after["supplier"] = resolved.supplier
        if resolved.company:
            ent_after["company"] = resolved.company
        if resolved.items:
            ent_after["items"] = resolved.items
        intent_dict["entities"] = ent_after

        company_resolved = resolve_company_for_payload(
            profile.get("default_company") or profile.get("company_name"),
            {
                "company_profile": profile,
                "link_cache": link_cache,
                "defaults": context.get("defaults") or {},
            },
        )
        if company_resolved:
            profile = dict(profile)
            profile["erp_resolved_company"] = company_resolved
            overlay["erp_resolved_company"] = company_resolved

        gaps = resolution_gaps_from_unresolved(resolved, doctype=doctype, link_cache=link_cache)

        overlay["link_cache"] = link_cache
        overlay["resolved_entities"] = resolved.to_dict()
        overlay["resolution_gaps"] = [g.to_dict() for g in gaps]
        overlay["live_fetched_at"] = utc_now_iso()
        overlay["brain_version"] = BRAIN_VERSION

        activity.logger.info(
            "resolve_entities: doctype=%s targets=%s gaps=%d cache_keys=%s",
            doctype,
            list(targets.keys()),
            len(gaps),
            list(link_cache.keys()),
        )

        return {
            "intent_dict": intent_dict,
            "context_overlay": overlay,
            "company_profile_patch": profile,
            "skipped": False,
        }

    except Exception as e:
        logger.exception("resolve_entities failed: %s", e)
        overlay["live_fetched_at"] = utc_now_iso()
        overlay["ler_error"] = str(e)
        return {"intent_dict": intent_dict, "context_overlay": overlay, "skipped": True, "error": str(e)}
