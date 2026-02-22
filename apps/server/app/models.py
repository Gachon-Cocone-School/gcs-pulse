from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    DateTime,
    Date,
    Text,
    UniqueConstraint,
    JSON,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    google_sub = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, nullable=False)
    name = Column(String)
    picture = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    roles = Column(JSON, default=["user"])
    league_type = Column(String, nullable=False, default="none", server_default="none", index=True)

    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True, index=True)

    consents = relationship("Consent", back_populates="user")
    team = relationship("Team", back_populates="members")
    daily_snippets = relationship("DailySnippet", back_populates="user")
    weekly_snippets = relationship("WeeklySnippet", back_populates="user")
    api_tokens = relationship("ApiToken", back_populates="user")
    comments = relationship("Comment", back_populates="user")
    achievement_grants = relationship("AchievementGrant", back_populates="user")


class Term(Base):
    __tablename__ = "terms"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String, nullable=False)  # 'privacy', 'tos'
    version = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    is_required = Column(Boolean, default=False)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("type", "version", name="_type_version_uc"),)


class Consent(Base):
    __tablename__ = "consents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    term_id = Column(Integer, ForeignKey("terms.id"))
    agreed_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="consents")
    term = relationship("Term")

    __table_args__ = (UniqueConstraint("user_id", "term_id", name="_user_term_uc"),)



class RoutePermission(Base):
    __tablename__ = "route_permissions"

    id = Column(Integer, primary_key=True, index=True)
    path = Column(String, nullable=False)
    method = Column(String, nullable=False)
    is_public = Column(Boolean, default=False)
    roles = Column(JSON, default=[])

    __table_args__ = (UniqueConstraint("path", "method", name="_path_method_uc"),)


class RoleAssignmentRule(Base):
    __tablename__ = "role_assignment_rules"

    id = Column(Integer, primary_key=True, index=True)
    rule_type = Column(String, nullable=False)
    rule_value = Column(JSON, nullable=False)
    assigned_role = Column(String, nullable=False)
    priority = Column(Integer, default=100)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (
        Index("ux_teams_invite_code", "invite_code", unique=True),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    invite_code = Column(String, nullable=True)
    league_type = Column(String, nullable=False, default="none", server_default="none", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    members = relationship("User", back_populates="team")


class DailySnippet(Base):
    __tablename__ = "daily_snippets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    content = Column(Text, nullable=False)
    structured = Column(Text, nullable=True)
    playbook = Column(Text, nullable=True)
    feedback = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="daily_snippets")
    comments = relationship("Comment", back_populates="daily_snippet")

    __table_args__ = (UniqueConstraint("user_id", "date", name="_user_date_uc"),)


class WeeklySnippet(Base):
    __tablename__ = "weekly_snippets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    week = Column(Date, nullable=False)
    content = Column(Text, nullable=False)
    structured = Column(Text, nullable=True)
    playbook = Column(Text, nullable=True)
    feedback = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="weekly_snippets")
    comments = relationship("Comment", back_populates="weekly_snippet")

    __table_args__ = (UniqueConstraint("user_id", "week", name="_user_week_uc"),)


class ApiToken(Base):
    __tablename__ = "api_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    idempotency_key = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="api_tokens")

    __table_args__ = (
        UniqueConstraint("user_id", "idempotency_key", name="ux_api_token_user_id_idempotency_key"),
    )


class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    daily_snippet_id = Column(Integer, ForeignKey("daily_snippets.id"), nullable=True, index=True)
    weekly_snippet_id = Column(Integer, ForeignKey("weekly_snippets.id"), nullable=True, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="comments")
    daily_snippet = relationship("DailySnippet", back_populates="comments")
    weekly_snippet = relationship("WeeklySnippet", back_populates="comments")


class AchievementDefinition(Base):
    __tablename__ = "achievement_definitions"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    badge_image_url = Column(String, nullable=False)
    rarity = Column(String(16), nullable=False, default="common", server_default="common")
    is_public_announceable = Column(Boolean, nullable=False, default=False, server_default="false", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    grants = relationship("AchievementGrant", back_populates="achievement_definition")


class AchievementGrant(Base):
    __tablename__ = "achievement_grants"
    __table_args__ = (
        Index("ix_achievement_grants_publish_window", "publish_start_at", "publish_end_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    achievement_definition_id = Column(Integer, ForeignKey("achievement_definitions.id"), nullable=False, index=True)
    granted_at = Column(DateTime(timezone=True), nullable=False, index=True)
    publish_start_at = Column(DateTime(timezone=True), nullable=False, index=True)
    publish_end_at = Column(DateTime(timezone=True), nullable=True, index=True)
    external_grant_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="achievement_grants")
    achievement_definition = relationship("AchievementDefinition", back_populates="grants")
