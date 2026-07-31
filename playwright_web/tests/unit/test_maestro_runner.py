from flows.mobile_runner import apply_env_overrides

FLOW = """appId: org.commcare.dalvik
env:
  COUNTRY_CODE: "+7426"
  PHONE_NUMBER: "7426000"
---
- launchApp
- inputText: "${PHONE_NUMBER}"
"""


def test_overrides_existing_env_key():
    result = apply_env_overrides(FLOW, {"PHONE_NUMBER": "7426009"})
    assert 'PHONE_NUMBER: "7426009"' in result
    assert 'COUNTRY_CODE: "+7426"' in result, "untouched keys must survive"


def test_appends_new_env_key():
    result = apply_env_overrides(FLOW, {"OPPORTUNITY": "Demo Opp"})
    assert 'OPPORTUNITY: "Demo Opp"' in result
    assert 'PHONE_NUMBER: "7426000"' in result


def test_quotes_values_containing_colons():
    # Opportunity names carry a timestamp: "Demo Opportunity_30-Jul-2026 : 17:26"
    name = "Demo Opportunity_30-Jul-2026 : 17:26"
    result = apply_env_overrides(FLOW, {"OPPORTUNITY": name})
    assert f'OPPORTUNITY: "{name}"' in result


def test_body_steps_are_untouched():
    result = apply_env_overrides(FLOW, {"PHONE_NUMBER": "7426009"})
    body = result.split("---", 1)[1]
    assert '- inputText: "${PHONE_NUMBER}"' in body
    assert "- launchApp" in body


def test_adds_env_block_when_flow_has_none():
    flow = 'appId: org.commcare.dalvik\n---\n- launchApp\n'
    result = apply_env_overrides(flow, {"OPPORTUNITY": "Demo Opp"})
    assert "env:" in result
    assert 'OPPORTUNITY: "Demo Opp"' in result
    assert result.index("env:") < result.index("---"), "env must stay in the header"


def test_empty_env_returns_flow_unchanged():
    assert apply_env_overrides(FLOW, {}) == FLOW
    assert apply_env_overrides(FLOW, None) == FLOW
