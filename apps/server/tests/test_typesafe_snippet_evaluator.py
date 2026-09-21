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


def test_jev_scores_replace_llm_scores_and_low_confidence_keeps_playbook(monkeypatch):
    async def fake_enrich(feedback, **_kwargs):
        feedback["scores"] = {"record_completeness": {"score": 15, "max_score": 15}}
        feedback["total_score"] = 15
        feedback["jev"] = {"playbook_auto_apply": False}
        feedback["playbook_update_markdown"] = None
        return feedback

    monkeypatch.setattr(flow, "enrich_feedback_with_jev", fake_enrich)
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
