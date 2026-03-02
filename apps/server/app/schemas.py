from datetime import date, datetime
from enum import Enum
from typing import List, Optional

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
    feedback: Optional[str] = None


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
    feedback: Optional[str] = None


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


class RiskBand(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class RiskReason(BaseModel):
    layer: str
    risk_factor: str
    prompt_items: List[str]
    severity: str
    impact: float
    evidence: str
    why_it_matters: str


class RiskConfidence(BaseModel):
    score: float
    data_coverage: float
    signal_agreement: float
    history_depth: float


class RiskTonePolicy(BaseModel):
    primary: str
    secondary: List[str] = []
    suppressed: List[str] = []
    trigger_patterns: List[str] = []
    policy_confidence: float


class StudentRiskSnapshotResponse(BaseModel):
    user_id: int
    evaluated_at: datetime
    l1: float
    l2: float
    l3: float
    risk_score: float
    risk_band: RiskBand
    daily_subscores: dict = {}
    weekly_subscores: dict = {}
    trend_subscores: dict = {}
    confidence: RiskConfidence
    reasons: List[RiskReason] = []
    tone_policy: RiskTonePolicy
    needs_professor_review: bool


class ProfessorOverviewResponse(BaseModel):
    high_or_critical_count: int
    high_count: int
    critical_count: int
    medium_count: int
    low_count: int


class ProfessorRiskQueueItem(BaseModel):
    user_id: int
    user_name: str
    user_email: str
    risk_score: float
    risk_band: RiskBand
    evaluated_at: datetime
    confidence: float
    reasons: List[RiskReason] = []
    tone_policy: Optional[RiskTonePolicy] = None
    latest_daily_snippet_id: Optional[int] = None
    latest_weekly_snippet_id: Optional[int] = None


class ProfessorRiskQueueResponse(BaseModel):
    items: List[ProfessorRiskQueueItem] = []
    total: int


class ProfessorRiskHistoryResponse(BaseModel):
    items: List[StudentRiskSnapshotResponse] = []
    total: int


class ProfessorRiskEvaluateResponse(BaseModel):
    snapshot: StudentRiskSnapshotResponse


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
