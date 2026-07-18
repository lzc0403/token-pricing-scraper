from __future__ import annotations

import copy
import os
import sys

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.mainstream_catalog import (  # noqa: E402
    catalog_canons,
    load_catalog,
    renderable_sections,
    validate_catalog,
)


def _valid_catalog():
    return {
        "updated_at": "2026-07-18",
        "sections": {
            "overseas": {
                "title": "海外主流大模型",
                "vendors": [
                    {
                        "id": "anthropic",
                        "name": "Anthropic Claude",
                        "source_id": "anthropic",
                        "models": [
                            {
                                "canonical": "Claude Fable 5",
                                "display_name": "Fable 5",
                                "api_id": "claude-fable-5",
                                "openrouter_id": None,
                                "role": "旗舰代理",
                                "availability": "official",
                                "modality": "text",
                                "context_tokens": 1_000_000,
                                "pricing_kind": "paid",
                                "pricing": {
                                    "tiers": [
                                        {
                                            "condition": "default",
                                            "input_price": 10.0,
                                            "output_price": 50.0,
                                        }
                                    ]
                                },
                                "currency": "USD",
                                "unit": "per_million_tokens",
                                "source_url": "https://platform.claude.com/docs/zh-TW/about-claude/models/overview",
                                "verified_at": "2026-07-18T23:00:00+08:00",
                            }
                        ],
                    }
                ],
            }
        },
    }


def _model(data):
    return data["sections"]["overseas"]["vendors"][0]["models"][0]


def _non_claude_catalog():
    data = _valid_catalog()
    vendor = data["sections"]["overseas"]["vendors"][0]
    vendor.update(id="example", name="Example", source_id="example")
    _model(data).update(
        canonical="Example Model", display_name="Example Model", api_id="example-model"
    )
    return data


def _codes(data):
    return [error["code"] for error in validate_catalog(data)]


def test_valid_catalog_has_no_errors():
    assert validate_catalog(_valid_catalog()) == []


def test_errors_have_stable_shape_path_and_message():
    data = _valid_catalog()
    _model(data)["availability"] = "beta"

    assert validate_catalog(data) == [
        {
            "code": "invalid_availability",
            "path": "sections.overseas.vendors[0].models[0].availability",
            "message": "availability must be one of: invite_only, official, preview, tracking",
        }
    ]


def test_load_catalog_reads_valid_yaml(tmp_path):
    path = tmp_path / "catalog.yml"
    path.write_text(yaml.safe_dump(_valid_catalog(), allow_unicode=True), encoding="utf-8")

    assert load_catalog(str(path)) == _valid_catalog()


def test_load_catalog_rejects_invalid_yaml_catalog(tmp_path):
    data = _valid_catalog()
    _model(data)["unit"] = "per_second"
    path = tmp_path / "catalog.yml"
    path.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")

    with pytest.raises(ValueError, match=r"^mainstream catalog invalid: text_unit_required: "):
        load_catalog(str(path))


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda data: data.pop("updated_at"), "required_field"),
        (lambda data: data.pop("sections"), "required_field"),
        (lambda data: data["sections"]["overseas"].pop("title"), "required_field"),
        (lambda data: data["sections"]["overseas"].pop("vendors"), "required_field"),
        (lambda data: data["sections"]["overseas"]["vendors"][0].pop("id"), "required_field"),
        (lambda data: data["sections"]["overseas"]["vendors"][0].pop("name"), "required_field"),
        (lambda data: data["sections"]["overseas"]["vendors"][0].pop("source_id"), "required_field"),
        (lambda data: data["sections"]["overseas"]["vendors"][0].pop("models"), "required_field"),
        (lambda data: _model(data).pop("canonical"), "required_field"),
        (lambda data: _model(data).pop("display_name"), "required_field"),
        (lambda data: _model(data).pop("api_id"), "required_field"),
        (lambda data: _model(data).pop("openrouter_id"), "required_field"),
        (lambda data: _model(data).pop("role"), "required_field"),
        (lambda data: _model(data).pop("availability"), "required_field"),
        (lambda data: _model(data).pop("modality"), "required_field"),
        (lambda data: _model(data).pop("context_tokens"), "required_field"),
        (lambda data: _model(data).pop("pricing_kind"), "required_field"),
        (lambda data: _model(data).pop("pricing"), "required_field"),
        (lambda data: _model(data).pop("currency"), "required_field"),
        (lambda data: _model(data).pop("unit"), "required_field"),
        (lambda data: _model(data).pop("source_url"), "required_field"),
        (lambda data: _model(data).pop("verified_at"), "required_field"),
    ],
)
def test_missing_formal_fields_are_rejected_instead_of_guessed(mutate, code):
    data = _valid_catalog()
    mutate(data)

    assert code in _codes(data)


@pytest.mark.parametrize(
    ("target", "field"),
    [
        ("section", "title"),
        ("vendor", "id"),
        ("vendor", "name"),
        ("vendor", "source_id"),
        ("model", "canonical"),
        ("model", "display_name"),
        ("model", "role"),
        ("model", "currency"),
        ("model", "unit"),
    ],
)
def test_required_identity_fields_cannot_be_blank(target, field):
    data = _valid_catalog()
    values = {
        "section": data["sections"]["overseas"],
        "vendor": data["sections"]["overseas"]["vendors"][0],
        "model": _model(data),
    }
    values[target][field] = "   "

    assert "required_field" in _codes(data)


@pytest.mark.parametrize(
    ("target", "field"),
    [
        ("section", "title"),
        ("vendor", "id"),
        ("vendor", "name"),
        ("vendor", "source_id"),
        ("model", "canonical"),
        ("model", "display_name"),
        ("model", "role"),
        ("model", "availability"),
        ("model", "modality"),
        ("model", "currency"),
        ("model", "unit"),
        ("model", "source_url"),
        ("model", "verified_at"),
    ],
)
@pytest.mark.parametrize("invalid_value", [None, 123, ["value"]])
def test_required_string_fields_reject_non_strings_without_duplicate_errors(
    target, field, invalid_value
):
    data = _non_claude_catalog()
    values = {
        "section": data["sections"]["overseas"],
        "vendor": data["sections"]["overseas"]["vendors"][0],
        "model": _model(data),
    }
    values[target][field] = invalid_value

    errors = validate_catalog(data)
    field_path = {
        "section": f"sections.overseas.{field}",
        "vendor": f"sections.overseas.vendors[0].{field}",
        "model": f"sections.overseas.vendors[0].models[0].{field}",
    }[target]
    field_errors = [error for error in errors if error["path"] == field_path]

    assert len(field_errors) == 1
    assert field_errors[0]["code"] != "required_field"


@pytest.mark.parametrize("field", ["api_id", "openrouter_id"])
def test_optional_model_ids_allow_none_but_reject_invalid_strings_and_types(field):
    data = _non_claude_catalog()
    _model(data)[field] = None
    assert validate_catalog(data) == []

    for invalid_value in ("", "   ", 123, ["id"]):
        _model(data)[field] = invalid_value
        field_path = f"sections.overseas.vendors[0].models[0].{field}"
        field_errors = [
            error for error in validate_catalog(data) if error["path"] == field_path
        ]
        assert len(field_errors) == 1
        assert field_errors[0]["code"] == "invalid_string"


@pytest.mark.parametrize(
    ("field", "code"),
    [
        ("availability", "required_field"),
        ("modality", "required_field"),
        ("pricing_kind", "required_field"),
        ("unit", "required_field"),
        ("source_url", "required_field"),
        ("verified_at", "required_field"),
    ],
)
def test_blank_model_fields_emit_only_one_error(field, code):
    data = _non_claude_catalog()
    _model(data)[field] = "   "
    field_path = f"sections.overseas.vendors[0].models[0].{field}"

    field_errors = [
        error for error in validate_catalog(data) if error["path"] == field_path
    ]

    assert len(field_errors) == 1
    assert field_errors[0]["code"] == code


def test_non_official_text_context_allows_none_but_rejects_other_invalid_types():
    data = _non_claude_catalog()
    model = _model(data)
    model["availability"] = "tracking"
    model["context_tokens"] = None
    model["pricing"] = {"tiers": []}
    assert validate_catalog(data) == []

    model["context_tokens"] = "1000000"
    assert "invalid_context_tokens" in _codes(data)


def test_duplicate_canonical_in_same_section_is_rejected():
    data = _valid_catalog()
    duplicate = copy.deepcopy(_model(data))
    data["sections"]["overseas"]["vendors"].append(
        {"id": "other", "name": "Other", "source_id": "other", "models": [duplicate]}
    )

    errors = validate_catalog(data)

    assert {
        "code": "duplicate_canonical",
        "path": "sections.overseas.vendors[1].models[0].canonical",
        "message": "canonical duplicates sections.overseas.vendors[0].models[0].canonical",
    } in errors


def test_same_canonical_in_different_sections_is_allowed():
    data = _valid_catalog()
    data["sections"]["domestic"] = copy.deepcopy(data["sections"]["overseas"])

    assert "duplicate_canonical" not in _codes(data)


@pytest.mark.parametrize("availability", ["beta", "deprecated"])
def test_availability_is_closed_enum(availability):
    data = _valid_catalog()
    _model(data)["availability"] = availability

    assert "invalid_availability" in _codes(data)


@pytest.mark.parametrize("modality", ["audio", "multimodal", None])
def test_modality_is_closed_enum(modality):
    data = _valid_catalog()
    _model(data)["modality"] = modality

    assert "invalid_modality" in _codes(data)


def test_text_model_requires_token_unit():
    data = _valid_catalog()
    _model(data)["unit"] = "per_second"

    assert "text_unit_required" in _codes(data)


@pytest.mark.parametrize("modality", ["image", "video"])
def test_non_text_model_cannot_use_token_unit(modality):
    data = _valid_catalog()
    model = _model(data)
    model["availability"] = "tracking"
    model["modality"] = modality

    assert "token_unit_for_non_text" in _codes(data)


@pytest.mark.parametrize("context", [None, 0, -1, 1.5, True, "1000000"])
def test_official_text_context_must_be_positive_integer(context):
    data = _valid_catalog()
    _model(data)["context_tokens"] = context

    assert "official_text_context_required" in _codes(data)


@pytest.mark.parametrize("pricing_kind", ["trial", "unknown", None])
def test_pricing_kind_is_closed_enum(pricing_kind):
    data = _valid_catalog()
    _model(data)["pricing_kind"] = pricing_kind

    assert "invalid_pricing_kind" in _codes(data)


@pytest.mark.parametrize(
    "tiers",
    [
        [],
        [{"condition": "default", "input_price": None, "output_price": 1}],
        [{"condition": "default", "input_price": 1, "output_price": None}],
        [{"condition": "default", "input_price": 0, "output_price": 0}],
    ],
)
def test_paid_model_requires_complete_positive_tier_prices(tiers):
    data = _valid_catalog()
    _model(data)["pricing"] = {"tiers": tiers}

    assert "paid_price_required" in _codes(data)


@pytest.mark.parametrize(
    "tier",
    [
        {"condition": "default", "input_price": -1, "output_price": 1},
        {"condition": "default", "input_price": 1, "output_price": -1},
        {"condition": "default", "input_price": "1", "output_price": 1},
    ],
)
def test_paid_prices_must_be_non_negative_numbers(tier):
    data = _valid_catalog()
    _model(data)["pricing"] = {"tiers": [tier]}

    assert "invalid_price" in _codes(data)


@pytest.mark.parametrize("price", [float("nan"), float("inf"), float("-inf"), True])
def test_prices_must_be_finite_numbers_and_reject_bool(price):
    data = _valid_catalog()
    _model(data)["pricing"] = {
        "tiers": [{"condition": "default", "input_price": price, "output_price": 1}]
    }

    assert "invalid_price" in _codes(data)


@pytest.mark.parametrize("availability", ["tracking", "invite_only"])
def test_non_renderable_paid_model_allows_empty_tiers_for_unknown_official_price(
    availability,
):
    data = _non_claude_catalog()
    model = _model(data)
    model["availability"] = availability
    model["context_tokens"] = None
    model["pricing"] = {"tiers": []}

    assert validate_catalog(data) == []


@pytest.mark.parametrize("availability", ["official", "preview"])
def test_renderable_paid_model_still_requires_non_empty_tiers(availability):
    data = _non_claude_catalog()
    model = _model(data)
    model["availability"] = availability
    model["pricing"] = {"tiers": []}

    assert "paid_price_required" in _codes(data)


@pytest.mark.parametrize("condition", [None, "", "   ", 123, ["default"]])
def test_tier_condition_must_be_non_empty_string(condition):
    data = _valid_catalog()
    _model(data)["pricing"]["tiers"][0]["condition"] = condition

    errors = validate_catalog(data)
    condition_errors = [
        error
        for error in errors
        if error["path"]
        == "sections.overseas.vendors[0].models[0].pricing.tiers[0].condition"
    ]

    assert len(condition_errors) == 1


def test_each_paid_tier_is_validated():
    data = _valid_catalog()
    _model(data)["pricing"]["tiers"].append(
        {"condition": "long context", "input_price": 0, "output_price": 0}
    )

    errors = validate_catalog(data)

    assert any(
        error["code"] == "paid_price_required"
        and error["path"] == "sections.overseas.vendors[0].models[0].pricing.tiers[1]"
        for error in errors
    )


@pytest.mark.parametrize("source_url", [None, "", "not-a-url", "ftp://example.com/pricing"])
def test_source_url_must_be_http_url(source_url):
    data = _valid_catalog()
    _model(data)["source_url"] = source_url

    if source_url == "":
        expected = "required_field"
    elif source_url is None:
        expected = "invalid_string"
    else:
        expected = "invalid_source_url"
    assert expected in _codes(data)


@pytest.mark.parametrize(
    "verified_at",
    [None, "", "2026-07-18", "2026-07-18T23:00:00", "not-a-date"],
)
def test_verified_at_must_be_iso_datetime_with_timezone(verified_at):
    data = _valid_catalog()
    _model(data)["verified_at"] = verified_at

    if verified_at == "":
        expected = "required_field"
    elif verified_at is None:
        expected = "invalid_string"
    else:
        expected = "invalid_verified_at"
    assert expected in _codes(data)


@pytest.mark.parametrize(
    ("canonical", "display_name", "api_id"),
    [
        ("Claude Fable 5", "Fable 5", None),
        ("Claude Fable 5", "Fable 5", "claude-fable-five"),
        ("Claude Fable 5", "Claude Fable Five", "claude-fable-5"),
        ("Claude Rumor 6", "Rumor 6", "claude-rumor-6"),
    ],
)
def test_official_claude_requires_approved_name_and_exact_api_id(
    canonical, display_name, api_id
):
    data = _valid_catalog()
    model = _model(data)
    model["canonical"] = canonical
    model["display_name"] = display_name
    model["api_id"] = api_id

    assert "invalid_claude_official" in _codes(data)


def test_renderable_sections_keeps_vendor_order_and_only_renderable_text_models():
    data = _valid_catalog()
    official = _model(data)
    preview = copy.deepcopy(official)
    preview.update(
        canonical="Preview Text", display_name="Preview Text", api_id=None, availability="preview"
    )
    tracking = copy.deepcopy(official)
    tracking.update(
        canonical="Tracking Text", display_name="Tracking Text", api_id=None, availability="tracking"
    )
    invite_only = copy.deepcopy(official)
    invite_only.update(
        canonical="Invite Text", display_name="Invite Text", api_id=None, availability="invite_only"
    )
    image = copy.deepcopy(official)
    image.update(
        canonical="Official Image",
        display_name="Official Image",
        api_id=None,
        modality="image",
        context_tokens=None,
        unit="per_image",
    )
    data["sections"]["overseas"]["vendors"][0]["models"] = [
        official,
        preview,
        tracking,
        invite_only,
        image,
    ]

    rendered = renderable_sections(data)

    assert [vendor["id"] for vendor in rendered["overseas"]] == ["anthropic"]
    assert [model["canonical"] for model in rendered["overseas"][0]["models"]] == [
        "Claude Fable 5",
        "Preview Text",
    ]
    assert len(data["sections"]["overseas"]["vendors"][0]["models"]) == 5


def test_renderable_sections_returns_deep_copy():
    data = _valid_catalog()

    rendered = renderable_sections(data)
    rendered_vendor = rendered["overseas"][0]
    rendered_vendor["metadata"] = {"nested": []}
    data["sections"]["overseas"]["vendors"][0]["metadata"] = {"nested": []}
    rendered = renderable_sections(data)
    rendered["overseas"][0]["metadata"]["nested"].append("changed")
    rendered["overseas"][0]["models"][0]["pricing"]["tiers"][0]["input_price"] = 999

    vendor = data["sections"]["overseas"]["vendors"][0]
    assert vendor["metadata"] == {"nested": []}
    assert _model(data)["pricing"]["tiers"][0]["input_price"] == 10.0


def test_catalog_canons_deduplicates_in_configuration_order_and_filters_section():
    data = _valid_catalog()
    overseas_models = data["sections"]["overseas"]["vendors"][0]["models"]
    second = copy.deepcopy(overseas_models[0])
    second.update(canonical="Second", display_name="Second", api_id=None, availability="tracking")
    overseas_models.extend([second, copy.deepcopy(overseas_models[0])])
    data["sections"]["domestic"] = {
        "title": "国内主流大模型",
        "vendors": [
            {
                "id": "domestic",
                "name": "Domestic",
                "source_id": "domestic",
                "models": [copy.deepcopy(second)],
            }
        ],
    }

    assert catalog_canons(data) == ["Claude Fable 5", "Second"]
    assert catalog_canons(data, "overseas") == ["Claude Fable 5", "Second"]
    assert catalog_canons(data, "domestic") == ["Second"]
    assert catalog_canons(data, "missing") == []


@pytest.mark.parametrize("catalog", [None, [], {}, {"updated_at": "2026-07-18", "sections": []}])
def test_malformed_catalog_returns_errors_instead_of_crashing(catalog):
    errors = validate_catalog(catalog)

    assert errors
    assert all(set(error) == {"code", "path", "message"} for error in errors)
