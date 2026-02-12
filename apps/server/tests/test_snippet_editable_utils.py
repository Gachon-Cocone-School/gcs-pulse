import pytest
from datetime import datetime, timedelta
from app.routers.snippet_utils import is_snippet_editable


class DummyUser:
    def __init__(self, id, team_id=None):
        self.id = id
        self.team_id = team_id


@pytest.mark.parametrize("delta_days,expected", [
    (0, True),
    (-1, False),
    (1, False),
])
def test_daily_editable_by_owner_today(delta_days, expected):
    owner = DummyUser(1)
    viewer = DummyUser(1)
    now = datetime.now().astimezone() + timedelta(days=delta_days)
    date_target = now.date()

    assert is_snippet_editable(viewer, owner, date_target, "daily", now=now) == expected


def test_daily_not_editable_by_non_owner():
    owner = DummyUser(1)
    viewer = DummyUser(2)
    now = datetime.now().astimezone()
    date_target = now.date()

    assert is_snippet_editable(viewer, owner, date_target, "daily", now=now) is False


def test_weekly_editable_owner_week_start():
    owner = DummyUser(1)
    viewer = DummyUser(1)
    now = datetime.now().astimezone()
    # compute week_start via util to be robust
    from app.utils_time import current_business_week_start

    week_start = current_business_week_start(now)
    assert is_snippet_editable(viewer, owner, week_start, "weekly", now=now) is True


def test_weekly_not_editable_different_week():
    owner = DummyUser(1)
    viewer = DummyUser(1)
    now = datetime.now().astimezone()
    from app.utils_time import current_business_week_start

    week_start = current_business_week_start(now) - timedelta(days=7)
    assert is_snippet_editable(viewer, owner, week_start, "weekly", now=now) is False
