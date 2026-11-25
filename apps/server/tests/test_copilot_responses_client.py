import pytest

from app.core.config import Settings, settings
from app.lib.copilot_client import CopilotClient


def test_responses_payload_moves_system_message_to_instructions():
    payload = CopilotClient._responses_payload(
        [
            {"role": "system", "content": "Follow these rules."},
            {"role": "user", "content": "Hello"},
        ],
        model="gpt-6-luna",
        stream=False,
        max_tokens=128,
        temperature=0,
    )

    assert payload == {
        "model": "gpt-6-luna",
        "input": [{"role": "user", "content": "Hello"}],
        "instructions": "Follow these rules.",
        "stream": False,
        "max_output_tokens": 128,
    }


@pytest.mark.parametrize("stream", [False, True])
def test_default_generation_uses_sol_with_low_reasoning(monkeypatch, stream):
    default_model = Settings.model_fields["OPENAI_GENERATION_MODEL"].default
    monkeypatch.setattr(settings, "OPENAI_GENERATION_MODEL", default_model)

    payload = CopilotClient._responses_payload(
        [{"role": "user", "content": "Hello"}],
        model=CopilotClient._model(None),
        stream=stream,
        max_tokens=None,
    )

    assert payload["model"] == "gpt-6.2-sol"
    assert payload["reasoning"] == {"effort": "low"}


def test_response_is_normalized_for_existing_chat_callers():
    response = CopilotClient._as_chat_completion(
        {
            "id": "resp_123",
            "model": "gpt-6-luna",
            "output": [
                {
                    "content": [
                        {"type": "output_text", "text": "Hello "},
                        {"type": "output_text", "text": "world"},
                    ]
                }
            ],
            "usage": {"total_tokens": 12},
        }
    )

    assert response["choices"][0]["message"] == {"role": "assistant", "content": "Hello world"}
    assert response["model"] == "gpt-6-luna"
