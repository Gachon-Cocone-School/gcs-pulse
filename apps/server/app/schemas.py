from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class UserRole(str, Enum):
    USER = "user"


class User(BaseModel):
    sub: str
    name: str
    email: str
    picture: str
    email_verified: bool
    roles: List[str] = ["user"]

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
    google_sub: str
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

class TeamUpdate(BaseModel):
    name: Optional[str] = None

class TeamMemberSummary(BaseModel):
    id: int
    name: str
    email: str
    picture: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class TeamResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    members: List[TeamMemberSummary] = []

    model_config = ConfigDict(from_attributes=True)

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
    structured: Optional[str] = None
    feedback: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    comments_count: int = 0

    model_config = ConfigDict(from_attributes=True)

class DailySnippetOrganizeResponse(BaseModel):
    id: int
    date: date
    content: str
    structured: Optional[str] = None
    feedback: Optional[str] = None  # JSON string from DB

    model_config = ConfigDict(from_attributes=True)

class DailySnippetListResponse(BaseModel):
    items: List[DailySnippetResponse]
    total: int
    limit: int
    offset: int

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
    structured: Optional[str] = None
    feedback: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class WeeklySnippetListResponse(BaseModel):
    items: List[WeeklySnippetResponse]
    total: int
    limit: int
    offset: int

class WeeklySnippetOrganizeResponse(BaseModel):
    id: int
    week: date
    content: str
    structured: Optional[str] = None
    feedback: Optional[str] = None  # JSON string from DB

    model_config = ConfigDict(from_attributes=True)

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


class CommentCreate(BaseModel):
    content: str
    daily_snippet_id: Optional[int] = None
    weekly_snippet_id: Optional[int] = None


class CommentUpdate(BaseModel):
    content: str


class CommentResponse(BaseModel):
    id: int
    user_id: int
    user: Optional[TeamMemberSummary] = None
    daily_snippet_id: Optional[int] = None
    weekly_snippet_id: Optional[int] = None
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
