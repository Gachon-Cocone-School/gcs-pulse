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
