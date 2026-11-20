import asyncio
import json
import logging

from app.routers import snippet_flow_helpers as flow


class DummyDB:
    def __init__(self):
        self.committed = False

    async def commit(self):
        self.committed = True

    async def refresh(self, _snippet):
        return None


class Snippet:
    feedback = None
    playbook = "기존 Playbook"


def _feedback() -> str:
    return json.dumps(
        {
            "total_score": 1,
            "scores": {},
            "playbook_update_markdown": "## 새 Playbook\n- 근거 있는 다음 행동",
        }
    )


def test_openai_scores_replace_generation_scores_and_keep_playbook(monkeypatch):
    async def fake_enrich(feedback, **_kwargs):
        feedback["scores"] = {"record_completeness": {"score": 15, "max_score": 15}}
        feedback["total_score"] = 15
        feedback["openai_evaluation"] = {"model": "test"}
        feedback["playbook_update_markdown"] = None
        return feedback

    monkeypatch.setattr(flow, "enrich_feedback_with_openai", fake_enrich)
    result = asyncio.run(
        flow.finalize_feedback_json_or_none(
            _feedback(),
            parse_feedback_json=lambda value: json.loads(value),
            logger=logging.getLogger(__name__),
            snippet_content="오늘 결과를 측정했다.",
            playbook_content="기존 Playbook",
            snippet_kind="daily",
        )
    )

    parsed = json.loads(result)
    assert parsed["total_score"] == 15
    assert parsed["playbook_update_markdown"] is None


def test_high_confidence_jev_playbook_update_is_persisted(monkeypatch):
    async def no_cache_invalidation(_redis_url):
        return None

    monkeypatch.setattr(flow, "invalidate_all_leaderboards_cache", no_cache_invalidation)
    snippet = Snippet()
    feedback = json.dumps(
        {
            "jev": {"playbook_auto_apply": True},
            "playbook_update_markdown": "## 갱신된 Playbook\n- 측정한 다음 행동",
        }
    )

    db = DummyDB()
    asyncio.run(flow.persist_snippet_feedback(db, snippet, feedback))

    assert db.committed is True
    assert snippet.feedback == feedback
    assert snippet.playbook == "## 갱신된 Playbook\n- 측정한 다음 행동"


def test_decisions_scores_and_refusal_fallback(monkeypatch):
    from types import SimpleNamespace

    import httpx
    from openai import AsyncOpenAI

    from app.lib import openai_snippet_evaluator as evaluator

    monkeypatch.setattr(evaluator.settings, "OPENAI_API_KEY", "test")
    monkeypatch.setattr(evaluator.settings, "ENVIRONMENT", "development")
    refuse = False
    probability = 0.95

    def handle(request):
        assert request.url.path == "/v1/decisions"
        body = json.loads(request.content)
        questions = body["questions"]
        assert [item["type"] for item in questions] == ["score"] * 5 + ["choice", "predicate"]
        answers = [
            {"type": "score", "name": item["name"], "score": 2.5, "confidence": 0.7}
            for item in questions[:5]
        ]
        answers.extend([
            {"type": "choice", "name": questions[5]["name"], "choice": "extend", "confidence": 0.9},
            {"type": "predicate", "name": questions[6]["name"], "probability": probability},
        ])
        if refuse:
            answers[0] = {"type": "refusal", "name": questions[0]["name"]}
        return httpx.Response(200, json={"model": "gpt-6-luna", "answers": answers})

    async def run():
        nonlocal refuse, probability
        async with AsyncOpenAI(
            api_key="test",
            base_url="https://api.openai.com/v1",
            http_client=httpx.AsyncClient(transport=httpx.MockTransport(handle)),
        ) as sdk:
            draft = json.loads(_feedback())
            inputs = {
                "client": SimpleNamespace(sdk=sdk),
                "snippet_content": "실험 기록",
                "playbook_content": "기존 Playbook",
                "snippet_kind": "daily",
            }
            result = await evaluator.enrich_feedback_with_openai(draft, **inputs)
            assert result["total_score"] == 50
            assert result["scores"]["record_completeness"]["confidence"] == 0.7
            assert result["playbook_relation"] == "extend"
            assert result["openai_evaluation"]["playbook_evidence"] == 0.95
            assert result["playbook_update_markdown"] == draft["playbook_update_markdown"]
            assert result["openai_evaluation"]["playbook_auto_apply"] is True

            async def no_cache_invalidation(_redis_url):
                return None

            monkeypatch.setattr(flow, "invalidate_all_leaderboards_cache", no_cache_invalidation)
            snippet = Snippet()
            await flow.persist_snippet_feedback(DummyDB(), snippet, json.dumps(result))
            assert snippet.playbook == draft["playbook_update_markdown"]

            probability = 0.79
            rejected = await evaluator.enrich_feedback_with_openai(draft, **inputs)
            assert rejected["playbook_update_markdown"] is None
            await flow.persist_snippet_feedback(DummyDB(), snippet, json.dumps(rejected))
            assert snippet.playbook == draft["playbook_update_markdown"]

            refuse = True
            assert await evaluator.enrich_feedback_with_openai(draft, **inputs) == draft

    asyncio.run(run())
