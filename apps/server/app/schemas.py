from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, field_validator


class UserRole(str, Enum):
    USER = "user"


class LeagueType(str, Enum):
    UNDERGRAD = "undergrad"
    SEMESTER = "semester"
    NONE = "none"


class User(BaseModel):
    name: str
    email: str
    picture: str
    email_verified: bool
    roles: List[str] = ["user"]
    league_type: LeagueType = LeagueType.NONE

    model_config = ConfigDict(extra="allow")


class TermBase(BaseModel):
    type: str
    version: str
    content: str
    is_required: bool = False
    is_active: bool = False

class TermCreate(TermBase):
    pass

class TermUpdate(BaseModel):
    content: Optional[str] = None
    is_required: Optional[bool] = None
    is_active: Optional[bool] = None

class TermResponse(TermBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConsentCreate(BaseModel):
    term_id: int
    agreed: bool


class ConsentResponse(BaseModel):
    term_id: int
    agreed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserResponse(User):
    consents: List[ConsentResponse] = []

class UserAdminResponse(BaseModel):
    id: int
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None
    roles: List[str]
    created_at: datetime
    consents: List[ConsentResponse] = []

    model_config = ConfigDict(from_attributes=True)

class UserUpdate(BaseModel):
    name: Optional[str] = None
    picture: Optional[str] = None
    roles: Optional[List[str]] = None

class AuthStatusResponse(BaseModel):
    authenticated: bool
    user: Optional[UserResponse] = None


class MeLeagueResponse(BaseModel):
    league_type: LeagueType
    can_update: bool
    managed_by_team: bool


class StudentSearchItem(BaseModel):
    student_user_id: int
    student_name: str
    student_email: str
    team_name: Optional[str] = None


class StudentSearchResponse(BaseModel):
    items: List[StudentSearchItem] = []
    total: int


class StudentListResponse(BaseModel):
    items: List[StudentSearchItem] = []
    total: int
    limit: int
    offset: int


class LeaderboardWindow(BaseModel):
    label: str
    key: date


class LeaderboardItem(BaseModel):
    rank: int
    score: float
    participant_type: str
    participant_id: int
    participant_name: str
    member_count: Optional[int] = None
    submitted_count: Optional[int] = None


class LeaderboardResponse(BaseModel):
    period: str
    window: LeaderboardWindow
    league_type: LeagueType
    excluded_by_league: bool = False
    items: List[LeaderboardItem] = []
    total: int


class AchievementDefinitionResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str
    badge_image_url: str
    rarity: str
    is_public_announceable: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AchievementGrantEventResponse(BaseModel):
    id: int
    user_id: int
    achievement_definition_id: int
    granted_at: datetime
    publish_start_at: datetime
    publish_end_at: Optional[datetime] = None
    external_grant_id: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MyAchievementGroupItem(BaseModel):
    achievement_definition_id: int
    code: str
    name: str
    description: str
    badge_image_url: str
    rarity: str
    grant_count: int
    last_granted_at: datetime


class MyAchievementGroupsResponse(BaseModel):
    items: List[MyAchievementGroupItem] = []
    total: int


class RecentAchievementGrantItem(BaseModel):
    grant_id: int
    user_id: int
    user_name: str
    achievement_definition_id: int
    achievement_code: str
    achievement_name: str
    achievement_description: str
    badge_image_url: str
    rarity: str
    granted_at: datetime
    publish_start_at: datetime
    publish_end_at: Optional[datetime] = None


class RecentAchievementGrantsResponse(BaseModel):
    items: List[RecentAchievementGrantItem] = []
    total: int
    limit: int


class MessageResponse(BaseModel):
    message: str

class ErrorResponse(BaseModel):
    error: str

class RoutePermissionBase(BaseModel):
    path: str
    method: str
    is_public: bool = False
    roles: List[str] = []

class RoutePermissionCreate(RoutePermissionBase):
    pass

class RoutePermissionUpdate(BaseModel):
    is_public: Optional[bool] = None
    roles: Optional[List[str]] = None

class RoutePermissionResponse(RoutePermissionBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class RuleType(str, Enum):
    EMAIL_PATTERN = "email_pattern"
    EMAIL_LIST = "email_list"

class RoleAssignmentRuleBase(BaseModel):
    rule_type: RuleType
    rule_value: dict  # {"pattern": "..."} or {"emails": [...]}
    assigned_role: str
    priority: int = 100
    is_active: bool = True

class RoleAssignmentRuleCreate(RoleAssignmentRuleBase):
    pass

class RoleAssignmentRuleUpdate(BaseModel):
    rule_value: Optional[dict] = None
    assigned_role: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None

class RoleAssignmentRuleResponse(RoleAssignmentRuleBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TeamCreate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Team name is required")
        if len(normalized) > 100:
            raise ValueError("Team name must be 100 characters or less")
        return normalized

class TeamJoin(BaseModel):
    invite_code: str

    @field_validator("invite_code")
    @classmethod
    def validate_invite_code(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("Invite code is required")
        return normalized

class TeamUpdate(BaseModel):
    name: Optional[str] = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("Team name is required")
        if len(normalized) > 100:
            raise ValueError("Team name must be 100 characters or less")
        return normalized


class LeagueUpdate(BaseModel):
    league_type: LeagueType

class TeamMemberSummary(BaseModel):
    id: int
    name: str
    email: str
    picture: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class TeamResponse(BaseModel):
    id: int
    name: str
    invite_code: Optional[str] = None
    league_type: LeagueType = LeagueType.NONE
    created_at: datetime
    members: List[TeamMemberSummary] = []

    model_config = ConfigDict(from_attributes=True)

class TeamMeResponse(BaseModel):
    team: Optional[TeamResponse] = None


class TeamListResponse(BaseModel):
    items: List[TeamResponse] = []
    total: int
    limit: int
    offset: int


class TeamMemberResponse(BaseModel):
    user_id: int
    team_id: Optional[int] = None

class DailySnippetCreate(BaseModel):
    content: str

class DailySnippetUpdate(BaseModel):
    content: str

class DailySnippetResponse(BaseModel):
    id: int
    user_id: int
    user: Optional[TeamMemberSummary] = None
    date: date
    content: str
    feedback: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    comments_count: int = 0
    editable: bool = False

    model_config = ConfigDict(from_attributes=True)


class DailySnippetOrganizeRequest(BaseModel):
    content: str


class DailySnippetOrganizeResponse(BaseModel):
    date: date
    organized_content: str


class DailySnippetFeedbackResponse(BaseModel):
    date: date
    feedback: Optional[str] = None


class DailySnippetListResponse(BaseModel):
    items: List[DailySnippetResponse]
    total: int
    limit: int
    offset: int


class DailySnippetPageDataResponse(BaseModel):
    snippet: Optional[DailySnippetResponse] = None
    read_only: bool
    prev_id: Optional[int] = None
    next_id: Optional[int] = None


class WeeklySnippetCreate(BaseModel):
    content: str

class WeeklySnippetUpdate(BaseModel):
    content: str

class WeeklySnippetResponse(BaseModel):
    id: int
    user_id: int
    user: Optional[TeamMemberSummary] = None
    week: date
    content: str
    feedback: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    editable: bool = False

    model_config = ConfigDict(from_attributes=True)

class WeeklySnippetListResponse(BaseModel):
    items: List[WeeklySnippetResponse]
    total: int
    limit: int
    offset: int


class WeeklySnippetPageDataResponse(BaseModel):
    snippet: Optional[WeeklySnippetResponse] = None
    read_only: bool
    prev_id: Optional[int] = None
    next_id: Optional[int] = None


class WeeklySnippetOrganizeRequest(BaseModel):
    content: str


class WeeklySnippetOrganizeResponse(BaseModel):
    week: date
    organized_content: str


class WeeklySnippetFeedbackResponse(BaseModel):
    week: date
    feedback: Optional[str] = None


class ApiTokenCreate(BaseModel):
    description: str

class ApiTokenResponse(BaseModel):
    id: int
    description: Optional[str] = None
    created_at: datetime
    last_used_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class NewApiTokenResponse(ApiTokenResponse):
    token: Optional[str] = None


class CommentType(str, Enum):
    PEER = "peer"
    PROFESSOR = "professor"


class CommentCreate(BaseModel):
    content: str
    daily_snippet_id: Optional[int] = None
    weekly_snippet_id: Optional[int] = None
    comment_type: CommentType = CommentType.PEER


class CommentUpdate(BaseModel):
    content: str


class CommentResponse(BaseModel):
    id: int
    user_id: int
    user: Optional[TeamMemberSummary] = None
    daily_snippet_id: Optional[int] = None
    weekly_snippet_id: Optional[int] = None
    comment_type: CommentType = CommentType.PEER
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MentionableUserResponse(BaseModel):
    id: int
    name: str
    picture: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class NotificationType(str, Enum):
    COMMENT_ON_MY_SNIPPET = "comment_on_my_snippet"
    MENTION_IN_COMMENT = "mention_in_comment"
    COMMENT_ON_PARTICIPATED_SNIPPET = "comment_on_participated_snippet"


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    actor_user_id: int
    actor_user: Optional[TeamMemberSummary] = None
    type: NotificationType
    daily_snippet_id: Optional[int] = None
    weekly_snippet_id: Optional[int] = None
    comment_id: Optional[int] = None
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListResponse(BaseModel):
    items: List[NotificationResponse] = []
    total: int
    limit: int
    offset: int


class NotificationReadAllResponse(BaseModel):
    updated_count: int


class NotificationUnreadCountResponse(BaseModel):
    unread_count: int


class NotificationSettingResponse(BaseModel):
    user_id: int
    notify_post_author: bool
    notify_mentions: bool
    notify_participants: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationSettingUpdate(BaseModel):
    notify_post_author: Optional[bool] = None
    notify_mentions: Optional[bool] = None
    notify_participants: Optional[bool] = None


class PeerReviewSessionCreate(BaseModel):
    title: str

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Session title is required")
        if len(normalized) > 200:
            raise ValueError("Session title must be 200 characters or less")
        return normalized


class PeerReviewSessionUpdateRequest(BaseModel):
    title: str

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Session title is required")
        if len(normalized) > 200:
            raise ValueError("Session title must be 200 characters or less")
        return normalized


class PeerReviewSessionMemberItem(BaseModel):
    student_user_id: int
    student_name: str
    student_email: str
    team_label: str


class PeerReviewSessionResponse(BaseModel):
    id: int
    title: str
    raw_text: Optional[str] = None
    professor_user_id: int
    is_open: bool
    access_token: str
    form_url: str
    created_at: datetime
    updated_at: datetime
    members: List[PeerReviewSessionMemberItem] = []


class PeerReviewSessionListItem(BaseModel):
    id: int
    title: str
    is_open: bool
    created_at: datetime
    updated_at: datetime
    member_count: int
    submitted_evaluators: int


class PeerReviewSessionListResponse(BaseModel):
    items: List[PeerReviewSessionListItem]
    total: int


class PeerReviewParseCandidateItem(BaseModel):
    student_user_id: int
    student_name: str
    student_email: str


class PeerReviewParseUnresolvedItem(BaseModel):
    team_label: str
    raw_name: str
    reason: str
    candidates: List[PeerReviewParseCandidateItem] = []


class PeerReviewParsePreviewMember(BaseModel):
    team_label: str
    raw_name: str
    student_user_id: int
    student_name: str
    student_email: str


class PeerReviewSessionMembersParseRequest(BaseModel):
    raw_text: str

    @field_validator("raw_text")
    @classmethod
    def validate_raw_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Team composition text is required")
        if len(normalized) > 20000:
            raise ValueError("Team composition text must be 20000 characters or less")
        return normalized


class PeerReviewSessionMembersParseResponse(BaseModel):
    teams: Dict[str, List[PeerReviewParsePreviewMember]]
    unresolved_members: List[PeerReviewParseUnresolvedItem] = []


class PeerReviewSessionMembersConfirmRequest(BaseModel):
    members: List[PeerReviewParsePreviewMember]
    unresolved_members: List[PeerReviewParseUnresolvedItem] = []


class PeerReviewSessionMembersConfirmResponse(BaseModel):
    session_id: int
    members: List[PeerReviewSessionMemberItem] = []


class PeerReviewSessionStatusUpdateRequest(BaseModel):
    is_open: bool


class PeerReviewSessionProgressItem(BaseModel):
    evaluator_user_id: int
    evaluator_name: str
    evaluator_email: str
    team_label: str
    has_submitted: bool


class PeerReviewSessionProgressResponse(BaseModel):
    session_id: int
    is_open: bool
    evaluator_statuses: List[PeerReviewSessionProgressItem]


class PeerReviewSubmissionEntry(BaseModel):
    evaluatee_user_id: int
    contribution_percent: int
    fit_yes_no: bool


class PeerReviewFormSubmitRequest(BaseModel):
    entries: List[PeerReviewSubmissionEntry]


class PeerReviewEvaluatorStatusItem(BaseModel):
    evaluator_user_id: int
    evaluator_name: str
    has_submitted: bool


class PeerReviewFormSessionInfo(BaseModel):
    session_id: int
    title: str
    is_open: bool


class PeerReviewFormResponse(BaseModel):
    session: PeerReviewFormSessionInfo
    me: TeamMemberSummary
    team_members: List[TeamMemberSummary]
    evaluator_statuses: List[PeerReviewEvaluatorStatusItem]
    has_submitted: bool


class PeerReviewSubmissionRow(BaseModel):
    evaluator_user_id: int
    evaluator_name: str
    evaluatee_user_id: int
    evaluatee_name: str
    contribution_percent: int
    fit_yes_no: bool
    updated_at: datetime


class PeerReviewAggregatedStatItem(BaseModel):
    user_id: int
    name: str
    value: Optional[float] = None


class PeerReviewSessionResultsResponse(BaseModel):
    session_id: int
    total_evaluators_submitted: int
    total_rows: int
    rows: List[PeerReviewSubmissionRow]
    contribution_avg_by_evaluatee: List[PeerReviewAggregatedStatItem]
    fit_yes_ratio_by_evaluatee: List[PeerReviewAggregatedStatItem]
    fit_yes_ratio_by_evaluator: List[PeerReviewAggregatedStatItem]


class PeerReviewMySummaryResponse(BaseModel):
    session_id: int
    my_received_contribution_avg: float
    my_given_contribution_avg: float
    my_fit_yes_ratio_received: float
    my_fit_yes_ratio_given: float


class MeetingRoomResponse(BaseModel):
    id: int
    name: str
    location: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MeetingRoomReservationResponse(BaseModel):
    id: int
    meeting_room_id: int
    reserved_by_user_id: int
    reserved_by_name: Optional[str] = None
    start_at: datetime
    end_at: datetime
    purpose: Optional[str] = None
    can_cancel: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MeetingRoomReservationCreate(BaseModel):
    start_at: datetime
    end_at: datetime
    purpose: Optional[str] = None


class TournamentTeamMemberItem(BaseModel):
    student_user_id: int
    student_name: str
    student_email: str
    can_attend_vote: bool = True


class TournamentTeamItem(BaseModel):
    team_name: str
    members: List[TournamentTeamMemberItem] = []


class TournamentSessionCreate(BaseModel):
    title: str
    allow_self_vote: bool = True

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Session title is required")
        if len(normalized) > 200:
            raise ValueError("Session title must be 200 characters or less")
        return normalized


class TournamentSessionUpdateRequest(BaseModel):
    title: str
    allow_self_vote: Optional[bool] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Session title is required")
        if len(normalized) > 200:
            raise ValueError("Session title must be 200 characters or less")
        return normalized


class TournamentSessionStatusUpdateRequest(BaseModel):
    is_open: bool


class TournamentSessionResponse(BaseModel):
    id: int
    title: str
    professor_user_id: int
    is_open: bool
    allow_self_vote: bool = True
    format_text: Optional[str] = None
    format_json: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    teams: List[TournamentTeamItem] = []


class TournamentSessionListItem(BaseModel):
    id: int
    title: str
    is_open: bool
    created_at: datetime
    updated_at: datetime
    team_count: int
    match_count: int


class TournamentSessionListResponse(BaseModel):
    items: List[TournamentSessionListItem]
    total: int


class TournamentParseCandidateItem(BaseModel):
    student_user_id: int
    student_name: str
    student_email: str


class TournamentParseUnresolvedItem(BaseModel):
    team_name: str
    raw_name: str
    reason: str
    candidates: List[TournamentParseCandidateItem] = []


class TournamentParsePreviewMember(BaseModel):
    team_name: str
    raw_name: str
    student_user_id: int
    student_name: str
    student_email: str
    can_attend_vote: bool = True


class TournamentTeamsParseRequest(BaseModel):
    raw_text: str

    @field_validator("raw_text")
    @classmethod
    def validate_raw_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Team composition text is required")
        if len(normalized) > 20000:
            raise ValueError("Team composition text must be 20000 characters or less")
        return normalized


class TournamentTeamsParseResponse(BaseModel):
    teams: Dict[str, List[TournamentParsePreviewMember]]
    unresolved_members: List[TournamentParseUnresolvedItem] = []


class TournamentTeamsConfirmRequest(BaseModel):
    members: List[TournamentParsePreviewMember]
    unresolved_members: List[TournamentParseUnresolvedItem] = []


class TournamentTeamsConfirmResponse(BaseModel):
    session_id: int
    teams: List[TournamentTeamItem] = []


class TournamentFormatParseRequest(BaseModel):
    format_text: str

    @field_validator("format_text")
    @classmethod
    def validate_format_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Tournament format text is required")
        if len(normalized) > 2000:
            raise ValueError("Tournament format text must be 2000 characters or less")
        return normalized


class TournamentFormatParseResponse(BaseModel):
    format_text: str
    format_json: Dict[str, Any]


class TournamentMatchItem(BaseModel):
    id: int
    session_id: int
    bracket_type: str
    round_no: int
    match_no: int
    status: str
    is_bye: bool
    session_is_open: Optional[bool] = None
    team1_id: Optional[int] = None
    team1_name: Optional[str] = None
    team2_id: Optional[int] = None
    team2_name: Optional[str] = None
    winner_team_id: Optional[int] = None
    winner_team_name: Optional[str] = None
    next_match_id: Optional[int] = None
    loser_next_match_id: Optional[int] = None
    vote_count_team1: Optional[int] = None
    vote_count_team2: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class TournamentBracketRound(BaseModel):
    bracket_type: str
    round_no: int
    matches: List[TournamentMatchItem] = []


class TournamentBracketResponse(BaseModel):
    session_id: int
    title: str = ""
    rounds: List[TournamentBracketRound] = []


class TournamentMatchStatusUpdateRequest(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"pending", "open", "closed"}:
            raise ValueError("Match status must be one of pending/open/closed")
        return normalized


class TournamentMatchWinnerUpdateRequest(BaseModel):
    winner_team_id: Optional[int] = None


class TournamentVoteSubmitRequest(BaseModel):
    selected_team_id: int


class TournamentMatchVoterStatusItem(BaseModel):
    voter_user_id: int
    voter_name: str
    has_submitted: bool


class TournamentMatchProgressResponse(BaseModel):
    match: TournamentMatchItem
    vote_url: str
    session_is_open: bool
    allow_self_vote: bool = True
    voter_statuses: List[TournamentMatchVoterStatusItem] = []
    submitted_count: int
    total_count: int


class TournamentVoteResponse(BaseModel):
    message: str
    match: TournamentMatchItem


class TournamentMyScoreResponse(BaseModel):
    session_id: int
    my_score: int
    total_matches: int
    my_rank: int
    total_voters: int
    cumulative_response_seconds: float


class TournamentStudentSessionItem(BaseModel):
    id: int
    title: str
    is_open: bool
    created_at: datetime
    updated_at: datetime


class TournamentStudentSessionListResponse(BaseModel):
    items: List[TournamentStudentSessionItem]
    total: int
