from __future__ import annotations

from app import (
    crud_achievements,
    crud_comments,
    crud_leaderboards,
    crud_notifications,
    crud_snippets,
    crud_teams,
    crud_terms,
    crud_tokens,
    crud_users,
)


create_daily_snippet = crud_snippets.create_daily_snippet
upsert_daily_snippet = crud_snippets.upsert_daily_snippet
get_daily_snippet_by_id = crud_snippets.get_daily_snippet_by_id
get_daily_snippet_by_user_and_date = crud_snippets.get_daily_snippet_by_user_and_date
update_daily_snippet = crud_snippets.update_daily_snippet
delete_daily_snippet = crud_snippets.delete_daily_snippet
list_daily_snippets = crud_snippets.list_daily_snippets
list_daily_snippets_for_student = crud_snippets.list_daily_snippets_for_student


create_api_token = crud_tokens.create_api_token
list_api_tokens = crud_tokens.list_api_tokens
get_api_token_by_raw_token = crud_tokens.get_api_token_by_raw_token
touch_api_token_last_used_at = crud_tokens.touch_api_token_last_used_at
delete_api_token = crud_tokens.delete_api_token


create_weekly_snippet = crud_snippets.create_weekly_snippet
upsert_weekly_snippet = crud_snippets.upsert_weekly_snippet
get_weekly_snippet_by_id = crud_snippets.get_weekly_snippet_by_id
get_weekly_snippet_by_user_and_week = crud_snippets.get_weekly_snippet_by_user_and_week
update_weekly_snippet = crud_snippets.update_weekly_snippet
delete_weekly_snippet = crud_snippets.delete_weekly_snippet
list_weekly_snippets_for_student = crud_snippets.list_weekly_snippets_for_student


get_user_by_email = crud_users.get_user_by_email
get_user_by_email_basic = crud_users.get_user_by_email_basic
create_or_update_user = crud_users.create_or_update_user
get_user_by_id = crud_users.get_user_by_id
set_user_team = crud_users.set_user_team
update_user_league_type = crud_users.update_user_league_type
search_students = crud_users.search_students
list_students = crud_users.list_students


get_active_terms = crud_terms.get_active_terms
get_term_by_id = crud_terms.get_term_by_id
get_consent = crud_terms.get_consent
create_consent = crud_terms.create_consent


generate_invite_code = crud_teams.generate_invite_code
create_team = crud_teams.create_team
list_teams = crud_teams.list_teams
get_team_by_id = crud_teams.get_team_by_id
get_team_with_members = crud_teams.get_team_with_members
get_team_by_invite_code = crud_teams.get_team_by_invite_code
count_team_members = crud_teams.count_team_members
update_team = crud_teams.update_team
delete_team = crud_teams.delete_team


_parse_total_score = crud_leaderboards._parse_total_score
apply_competition_ranks = crud_leaderboards.apply_competition_ranks
build_individual_leaderboard = crud_leaderboards.build_individual_leaderboard
build_team_leaderboard = crud_leaderboards.build_team_leaderboard


list_weekly_snippets = crud_snippets.list_weekly_snippets


get_achievement_definitions_by_codes = crud_achievements.get_achievement_definitions_by_codes
upsert_achievement_definitions = crud_achievements.upsert_achievement_definitions


list_daily_snippets_for_date = crud_snippets.list_daily_snippets_for_date
list_daily_snippets_in_range = crud_snippets.list_daily_snippets_in_range
list_weekly_snippets_for_week = crud_snippets.list_weekly_snippets_for_week


list_achievement_grant_histories_for_rule_codes = crud_achievements.list_achievement_grant_histories_for_rule_codes
delete_achievement_grants_for_external_prefix = crud_achievements.delete_achievement_grants_for_external_prefix
bulk_create_achievement_grants = crud_achievements.bulk_create_achievement_grants
list_recent_public_achievement_grants = crud_achievements.list_recent_public_achievement_grants
list_my_achievement_groups = crud_achievements.list_my_achievement_groups


# -------------------------
# Comment CRUD
# -------------------------

create_comment = crud_comments.create_comment
list_comments = crud_comments.list_comments
get_comment_by_id = crud_comments.get_comment_by_id
update_comment = crud_comments.update_comment
delete_comment = crud_comments.delete_comment


# -------------------------
# Notification CRUD
# -------------------------

list_notifications = crud_notifications.list_notifications
get_notification_by_id_for_user = crud_notifications.get_notification_by_id_for_user
mark_notification_as_read = crud_notifications.mark_notification_as_read
mark_all_notifications_as_read = crud_notifications.mark_all_notifications_as_read
count_unread_notifications = crud_notifications.count_unread_notifications
get_notification_setting = crud_notifications.get_notification_setting
get_or_create_notification_setting = crud_notifications.get_or_create_notification_setting
update_notification_setting = crud_notifications.update_notification_setting

