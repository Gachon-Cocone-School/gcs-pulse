from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional

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


class PeerEvaluationSessionCreate(BaseModel):
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


class PeerEvaluationSessionUpdateRequest(BaseModel):
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


class PeerEvaluationSessionMemberItem(BaseModel):
    student_user_id: int
    student_name: str
    student_email: str
    team_label: str


class PeerEvaluationSessionResponse(BaseModel):
    id: int
    title: str
    raw_text: Optional[str] = None
    professor_user_id: int
    is_open: bool
    access_token: str
    form_url: str
    created_at: datetime
    updated_at: datetime
    members: List[PeerEvaluationSessionMemberItem] = []


class PeerEvaluationSessionListItem(BaseModel):
    id: int
    title: str
    is_open: bool
    created_at: datetime
    updated_at: datetime
    member_count: int
    submitted_evaluators: int


class PeerEvaluationSessionListResponse(BaseModel):
    items: List[PeerEvaluationSessionListItem]
    total: int


class PeerEvaluationParseCandidateItem(BaseModel):
    student_user_id: int
    student_name: str
    student_email: str


class PeerEvaluationParseUnresolvedItem(BaseModel):
    team_label: str
    raw_name: str
    reason: str
    candidates: List[PeerEvaluationParseCandidateItem] = []


class PeerEvaluationParsePreviewMember(BaseModel):
    team_label: str
    raw_name: str
    student_user_id: int
    student_name: str
    student_email: str


class PeerEvaluationSessionMembersParseRequest(BaseModel):
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


class PeerEvaluationSessionMembersParseResponse(BaseModel):
    teams: Dict[str, List[PeerEvaluationParsePreviewMember]]
    unresolved_members: List[PeerEvaluationParseUnresolvedItem] = []


class PeerEvaluationSessionMembersConfirmRequest(BaseModel):
    members: List[PeerEvaluationParsePreviewMember]
    unresolved_members: List[PeerEvaluationParseUnresolvedItem] = []


class PeerEvaluationSessionMembersConfirmResponse(BaseModel):
    session_id: int
    members: List[PeerEvaluationSessionMemberItem] = []


class PeerEvaluationSessionStatusUpdateRequest(BaseModel):
    is_open: bool


class PeerEvaluationSessionProgressItem(BaseModel):
    evaluator_user_id: int
    evaluator_name: str
    evaluator_email: str
    team_label: str
    has_submitted: bool


class PeerEvaluationSessionProgressResponse(BaseModel):
    session_id: int
    is_open: bool
    evaluator_statuses: List[PeerEvaluationSessionProgressItem]


class PeerEvaluationSubmissionEntry(BaseModel):
    evaluatee_user_id: int
    contribution_percent: int
    fit_yes_no: bool


class PeerEvaluationFormSubmitRequest(BaseModel):
    entries: List[PeerEvaluationSubmissionEntry]


class PeerEvaluationEvaluatorStatusItem(BaseModel):
    evaluator_user_id: int
    evaluator_name: str
    has_submitted: bool


class PeerEvaluationFormSessionInfo(BaseModel):
    session_id: int
    title: str
    is_open: bool


class PeerEvaluationFormResponse(BaseModel):
    session: PeerEvaluationFormSessionInfo
    me: TeamMemberSummary
    team_members: List[TeamMemberSummary]
    evaluator_statuses: List[PeerEvaluationEvaluatorStatusItem]
    has_submitted: bool


class PeerEvaluationSubmissionRow(BaseModel):
    evaluator_user_id: int
    evaluator_name: str
    evaluatee_user_id: int
    evaluatee_name: str
    contribution_percent: int
    fit_yes_no: bool
    updated_at: datetime


class PeerEvaluationSessionResultsResponse(BaseModel):
    session_id: int
    total_evaluators_submitted: int
    total_rows: int
    rows: List[PeerEvaluationSubmissionRow]
    contribution_avg_by_evaluatee: Dict[str, Optional[float]]
    fit_yes_ratio_by_evaluatee: Dict[str, Optional[float]]
    fit_yes_ratio_by_evaluator: Dict[str, Optional[float]]


class PeerEvaluationMySummaryResponse(BaseModel):
    session_id: int
    my_received_contribution_avg: float
    my_given_contribution_avg: float
    my_fit_yes_ratio_received: float
    my_fit_yes_ratio_given: float
