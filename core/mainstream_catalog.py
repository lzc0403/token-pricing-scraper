from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from math import isfinite
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import yaml

RENDERABLE = {"official", "preview"}
AVAILABILITY = RENDERABLE | {"invite_only", "tracking"}
MODALITIES = {"text", "image", "video"}
TEXT_UNIT = "per_million_tokens"
PRICING_KINDS = {"paid", "free"}

_CLAUDE_OFFICIAL = {
    "Claude Fable 5": ("Fable 5", "claude-fable-5"),
    "Claude Opus 4.8": ("Opus 4.8", "claude-opus-4-8"),
    "Claude Sonnet 5": ("Sonnet 5", "claude-sonnet-5"),
    "Claude Haiku 4.5": ("Haiku 4.5", "claude-haiku-4-5-20251001"),
}

_CATALOG_FIELDS = ("updated_at", "sections")
_SECTION_FIELDS = ("title", "vendors")
_VENDOR_FIELDS = ("id", "name", "source_id", "models")
_MODEL_FIELDS = (
    "canonical",
    "display_name",
    "api_id",
    "openrouter_id",
    "role",
    "availability",
    "modality",
    "context_tokens",
    "pricing_kind",
    "pricing",
    "currency",
    "unit",
    "source_url",
    "verified_at",
)


def _error(code: str, path: str, message: str) -> Dict[str, str]:
    return {"code": code, "path": path, "message": message}


def _missing_fields(
    value: Dict[str, Any], fields: tuple[str, ...], path: str
) -> List[Dict[str, str]]:
    errors = []
    for field in fields:
        field_value = value.get(field)
        if field not in value or (
            field not in {"api_id", "openrouter_id"}
            and isinstance(field_value, str)
            and not field_value.strip()
        ):
            field_path = f"{path}.{field}" if path else field
            errors.append(_error("required_field", field_path, f"{field} is required"))
    return errors


def _is_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    return isinstance(value, float) and isfinite(value)


def _validate_required_strings(
    value: Dict[str, Any], fields: tuple[str, ...], path: str
) -> List[Dict[str, str]]:
    errors = []
    for field in fields:
        if field not in value:
            continue
        field_value = value[field]
        if isinstance(field_value, str):
            continue
        field_path = f"{path}.{field}" if path else field
        errors.append(_error("invalid_string", field_path, f"{field} must be a string"))
    return errors


def _validate_optional_string(
    value: Dict[str, Any], field: str, path: str, errors: List[Dict[str, str]]
) -> None:
    field_value = value.get(field)
    if field not in value or field_value is None:
        return
    if not isinstance(field_value, str) or not field_value.strip():
        errors.append(
            _error(
                "invalid_string",
                f"{path}.{field}",
                f"{field} must be a non-empty string or null",
            )
        )


def _is_http_url(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _is_zoned_datetime(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _validate_tiers(
    model: Dict[str, Any], model_path: str, errors: List[Dict[str, str]]
) -> None:
    pricing = model.get("pricing")
    if not isinstance(pricing, dict):
        if "pricing" in model:
            errors.append(
                _error("invalid_pricing", f"{model_path}.pricing", "pricing must be an object")
            )
        return

    if "tiers" not in pricing:
        errors.append(
            _error("required_field", f"{model_path}.pricing.tiers", "tiers is required")
        )
        return

    tiers = pricing["tiers"]
    if not isinstance(tiers, list):
        errors.append(
            _error("invalid_pricing", f"{model_path}.pricing.tiers", "tiers must be a list")
        )
        return

    availability = model.get("availability")
    if (
        model.get("pricing_kind") == "paid"
        and isinstance(availability, str)
        and availability in RENDERABLE
        and not tiers
    ):
        errors.append(
            _error(
                "paid_price_required",
                f"{model_path}.pricing.tiers",
                "renderable paid pricing requires at least one tier",
            )
        )

    for tier_index, tier in enumerate(tiers):
        tier_path = f"{model_path}.pricing.tiers[{tier_index}]"
        if not isinstance(tier, dict):
            errors.append(_error("invalid_pricing", tier_path, "tier must be an object"))
            continue

        condition = tier.get("condition")
        if "condition" not in tier or (isinstance(condition, str) and not condition.strip()):
            errors.append(
                _error("required_field", f"{tier_path}.condition", "condition is required")
            )
        elif not isinstance(condition, str):
            errors.append(
                _error(
                    "invalid_string",
                    f"{tier_path}.condition",
                    "condition must be a string",
                )
            )

        missing_price = False
        invalid_required_price = False
        for field in ("input_price", "output_price"):
            if field not in tier or tier[field] is None:
                if model.get("pricing_kind") == "paid":
                    missing_price = True
                continue
            if not _is_number(tier[field]) or tier[field] < 0:
                invalid_required_price = True

        if model.get("pricing_kind") == "paid":
            if missing_price or (
                not invalid_required_price
                and tier.get("input_price") == 0
                and tier.get("output_price") == 0
            ):
                errors.append(
                    _error(
                        "paid_price_required",
                        tier_path,
                        "paid tier requires input_price and output_price with at least one above zero",
                    )
                )

        if any(not isinstance(field, str) for field in tier):
            errors.append(
                _error(
                    "invalid_pricing",
                    tier_path,
                    "tier field names must be strings",
                )
            )

        for field, value in tier.items():
            if isinstance(field, str) and field.endswith("_price"):
                if not _is_number(value) or value < 0:
                    errors.append(
                        _error(
                            "invalid_price",
                            f"{tier_path}.{field}",
                            f"{field} must be a non-negative number",
                        )
                    )


def _is_claude_vendor(vendor: Dict[str, Any]) -> bool:
    return vendor.get("source_id") == "anthropic" or "claude" in str(
        vendor.get("name", "")
    ).lower()


def _validate_model(
    model: Any,
    vendor: Dict[str, Any],
    model_path: str,
    errors: List[Dict[str, str]],
) -> None:
    if not isinstance(model, dict):
        errors.append(_error("invalid_model", model_path, "model must be an object"))
        return

    errors.extend(_missing_fields(model, _MODEL_FIELDS, model_path))
    errors.extend(
        _validate_required_strings(
            model,
            (
                "canonical",
                "display_name",
                "role",
                "currency",
                "unit",
                "source_url",
                "verified_at",
            ),
            model_path,
        )
    )
    _validate_optional_string(model, "api_id", model_path, errors)
    _validate_optional_string(model, "openrouter_id", model_path, errors)

    availability = model.get("availability")
    if (
        "availability" in model
        and not (isinstance(availability, str) and not availability.strip())
        and (not isinstance(availability, str) or availability not in AVAILABILITY)
    ):
        errors.append(
            _error(
                "invalid_availability",
                f"{model_path}.availability",
                "availability must be one of: invite_only, official, preview, tracking",
            )
        )

    modality = model.get("modality")
    if (
        "modality" in model
        and not (isinstance(modality, str) and not modality.strip())
        and (not isinstance(modality, str) or modality not in MODALITIES)
    ):
        errors.append(
            _error(
                "invalid_modality",
                f"{model_path}.modality",
                "modality must be one of: image, text, video",
            )
        )

    unit = model.get("unit")
    if (
        modality == "text"
        and "unit" in model
        and isinstance(unit, str)
        and unit.strip()
        and unit != TEXT_UNIT
    ):
        errors.append(
            _error(
                "text_unit_required",
                f"{model_path}.unit",
                "text models must use per_million_tokens",
            )
        )
    elif (
        isinstance(modality, str)
        and modality in {"image", "video"}
        and unit == TEXT_UNIT
    ):
        errors.append(
            _error(
                "token_unit_for_non_text",
                f"{model_path}.unit",
                "non-text models cannot use per_million_tokens",
            )
        )

    if availability == "official" and modality == "text":
        context = model.get("context_tokens")
        if not isinstance(context, int) or isinstance(context, bool) or context <= 0:
            errors.append(
                _error(
                    "official_text_context_required",
                    f"{model_path}.context_tokens",
                    "official text context_tokens must be a positive integer",
                )
            )

    context = model.get("context_tokens")
    if (
        "context_tokens" in model
        and context is not None
        and (not isinstance(context, int) or isinstance(context, bool) or context <= 0)
        and not (availability == "official" and modality == "text")
    ):
        errors.append(
            _error(
                "invalid_context_tokens",
                f"{model_path}.context_tokens",
                "context_tokens must be a positive integer or null",
            )
        )

    pricing_kind = model.get("pricing_kind")
    if (
        "pricing_kind" in model
        and not (isinstance(pricing_kind, str) and not pricing_kind.strip())
        and (not isinstance(pricing_kind, str) or pricing_kind not in PRICING_KINDS)
    ):
        errors.append(
            _error(
                "invalid_pricing_kind",
                f"{model_path}.pricing_kind",
                "pricing_kind must be one of: free, paid",
            )
        )
    if "pricing" in model:
        _validate_tiers(model, model_path, errors)

    source_url = model.get("source_url")
    if (
        "source_url" in model
        and isinstance(source_url, str)
        and source_url.strip()
        and not _is_http_url(source_url)
    ):
        errors.append(
            _error(
                "invalid_source_url",
                f"{model_path}.source_url",
                "source_url must be a non-empty HTTP(S) URL",
            )
        )

    verified_at = model.get("verified_at")
    if (
        "verified_at" in model
        and isinstance(verified_at, str)
        and verified_at.strip()
        and not _is_zoned_datetime(verified_at)
    ):
        errors.append(
            _error(
                "invalid_verified_at",
                f"{model_path}.verified_at",
                "verified_at must be an ISO 8601 datetime with timezone",
            )
        )

    canonical = model.get("canonical")
    if (
        availability == "official"
        and _is_claude_vendor(vendor)
        and isinstance(canonical, str)
    ):
        expected = _CLAUDE_OFFICIAL.get(canonical)
        if expected is None or (
            model.get("display_name"), model.get("api_id")
        ) != expected:
            errors.append(
                _error(
                    "invalid_claude_official",
                    model_path,
                    "official Claude model must use an approved canonical, display_name, and exact api_id",
                )
            )


def validate_catalog(catalog: Dict[str, Any]) -> List[Dict[str, str]]:
    errors: List[Dict[str, str]] = []
    if not isinstance(catalog, dict):
        return [_error("invalid_catalog", "", "catalog must be an object")]

    errors.extend(_missing_fields(catalog, _CATALOG_FIELDS, ""))
    errors.extend(_validate_required_strings(catalog, ("updated_at",), ""))
    sections = catalog.get("sections")
    if not isinstance(sections, dict):
        if "sections" in catalog:
            errors.append(_error("invalid_sections", "sections", "sections must be an object"))
        return errors

    for section_id, section in sections.items():
        section_path = f"sections.{section_id}"
        if not isinstance(section, dict):
            errors.append(_error("invalid_section", section_path, "section must be an object"))
            continue

        errors.extend(_missing_fields(section, _SECTION_FIELDS, section_path))
        errors.extend(_validate_required_strings(section, ("title",), section_path))
        vendors = section.get("vendors")
        if not isinstance(vendors, list):
            if "vendors" in section:
                errors.append(
                    _error("invalid_vendors", f"{section_path}.vendors", "vendors must be a list")
                )
            continue

        seen_canons: Dict[str, str] = {}
        for vendor_index, vendor in enumerate(vendors):
            vendor_path = f"{section_path}.vendors[{vendor_index}]"
            if not isinstance(vendor, dict):
                errors.append(_error("invalid_vendor", vendor_path, "vendor must be an object"))
                continue

            errors.extend(_missing_fields(vendor, _VENDOR_FIELDS, vendor_path))
            errors.extend(
                _validate_required_strings(vendor, ("id", "name", "source_id"), vendor_path)
            )
            models = vendor.get("models")
            if not isinstance(models, list):
                if "models" in vendor:
                    errors.append(
                        _error("invalid_models", f"{vendor_path}.models", "models must be a list")
                    )
                continue

            for model_index, model in enumerate(models):
                model_path = f"{vendor_path}.models[{model_index}]"
                _validate_model(model, vendor, model_path, errors)
                if not isinstance(model, dict):
                    continue
                canonical = model.get("canonical")
                if not isinstance(canonical, str) or not canonical.strip():
                    continue
                canonical_path = f"{model_path}.canonical"
                if canonical in seen_canons:
                    errors.append(
                        _error(
                            "duplicate_canonical",
                            canonical_path,
                            f"canonical duplicates {seen_canons[canonical]}",
                        )
                    )
                else:
                    seen_canons[canonical] = canonical_path

    return errors


def load_catalog(path: str) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    errors = validate_catalog(data)
    if errors:
        detail = "; ".join(f"{item['code']}: {item['message']}" for item in errors)
        raise ValueError(f"mainstream catalog invalid: {detail}")
    return data


def renderable_sections(
    catalog: Dict[str, Any],
) -> Dict[str, List[Dict[str, Any]]]:
    rendered: Dict[str, List[Dict[str, Any]]] = {}
    sections = catalog.get("sections", {}) if isinstance(catalog, dict) else {}
    if not isinstance(sections, dict):
        return rendered

    for section_id, section in sections.items():
        vendors = section.get("vendors", []) if isinstance(section, dict) else []
        rendered_vendors = []
        if isinstance(vendors, list):
            for vendor in vendors:
                if not isinstance(vendor, dict):
                    continue
                models = vendor.get("models", [])
                filtered_models = []
                if isinstance(models, list):
                    filtered_models = [
                        deepcopy(model)
                        for model in models
                        if isinstance(model, dict)
                        and model.get("availability") in RENDERABLE
                        and model.get("modality") == "text"
                    ]
                rendered_vendor = deepcopy(vendor)
                rendered_vendor["models"] = filtered_models
                rendered_vendors.append(rendered_vendor)
        rendered[section_id] = rendered_vendors
    return rendered


def catalog_canons(
    catalog: Dict[str, Any], section: Optional[str] = None
) -> List[str]:
    sections = catalog.get("sections", {}) if isinstance(catalog, dict) else {}
    if not isinstance(sections, dict):
        return []

    selected = [(section, sections.get(section))] if section is not None else sections.items()
    canons = []
    seen = set()
    for _, section_data in selected:
        if not isinstance(section_data, dict):
            continue
        vendors = section_data.get("vendors", [])
        if not isinstance(vendors, list):
            continue
        for vendor in vendors:
            models = vendor.get("models", []) if isinstance(vendor, dict) else []
            if not isinstance(models, list):
                continue
            for model in models:
                canonical = model.get("canonical") if isinstance(model, dict) else None
                if isinstance(canonical, str) and canonical and canonical not in seen:
                    seen.add(canonical)
                    canons.append(canonical)
    return canons
