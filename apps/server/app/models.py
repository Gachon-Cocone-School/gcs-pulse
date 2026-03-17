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
    CheckConstraint,
    JSON,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String)
    picture = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    roles = Column(JSON, default=["user"])
    league_type = Column(String, nullable=False, default="none", server_default="none", index=True)

    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True, index=True)

    consents = relationship("Consent", back_populates="user")
    team = relationship("Team", back_populates="members")
    team_histories = relationship("UserTeamHistory", back_populates="user")
    daily_snippets = relationship("DailySnippet", back_populates="user")
    weekly_snippets = relationship("WeeklySnippet", back_populates="user")
    api_tokens = relationship("ApiToken", back_populates="user")
    comments = relationship("Comment", back_populates="user")
    achievement_grants = relationship("AchievementGrant", back_populates="user")
    notifications = relationship(
        "Notification",
        back_populates="user",
        foreign_keys="Notification.user_id",
    )
    acted_notifications = relationship(
        "Notification",
        back_populates="actor_user",
        foreign_keys="Notification.actor_user_id",
    )
    notification_setting = relationship(
        "NotificationSetting",
        back_populates="user",
        uselist=False,
    )
    meeting_room_reservations = relationship("MeetingRoomReservation", back_populates="reserved_by")


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
    member_histories = relationship("UserTeamHistory", back_populates="team")


class UserTeamHistory(Base):
    __tablename__ = "user_team_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False, index=True)
    joined_at = Column(DateTime(timezone=True), nullable=False)
    left_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="team_histories")
    team = relationship("Team", back_populates="member_histories")


class PeerReviewSession(Base):
    __tablename__ = "peer_review_sessions"
    __table_args__ = (
        Index("ux_peer_review_sessions_access_token", "access_token", unique=True),
    )

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    professor_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    is_open = Column(Boolean, nullable=False, default=False, server_default="false")
    access_token = Column(String(128), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    professor = relationship("User")
    members = relationship(
        "PeerReviewSessionMember",
        back_populates="session",
        cascade="all, delete-orphan",
    )
    submissions = relationship(
        "PeerReviewSubmission",
        back_populates="session",
        cascade="all, delete-orphan",
    )


class PeerReviewSessionMember(Base):
    __tablename__ = "peer_review_session_members"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "student_user_id",
            name="ux_peer_review_session_member_session_student",
        ),
        Index("ix_peer_review_session_members_session_team", "session_id", "team_label"),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("peer_review_sessions.id"), nullable=False, index=True)
    student_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    team_label = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session = relationship("PeerReviewSession", back_populates="members")
    student = relationship("User")


class PeerReviewSubmission(Base):
    __tablename__ = "peer_review_submissions"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "evaluator_user_id",
            "evaluatee_user_id",
            name="ux_peer_review_submission_session_evaluator_evaluatee",
        ),
        CheckConstraint(
            "contribution_percent >= 0 AND contribution_percent <= 100",
            name="ck_peer_review_submission_contribution_range",
        ),
        Index("ix_peer_review_submission_session_evaluator", "session_id", "evaluator_user_id"),
        Index("ix_peer_review_submission_session_evaluatee", "session_id", "evaluatee_user_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("peer_review_sessions.id"), nullable=False, index=True)
    evaluator_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    evaluatee_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    contribution_percent = Column(Integer, nullable=False)
    fit_yes_no = Column(Boolean, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session = relationship("PeerReviewSession", back_populates="submissions")
    evaluator = relationship("User", foreign_keys=[evaluator_user_id])
    evaluatee = relationship("User", foreign_keys=[evaluatee_user_id])


class DailySnippet(Base):
    __tablename__ = "daily_snippets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(Date, nullable=False)
    content = Column(Text, nullable=False)
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
    comment_type = Column(String(16), nullable=False, default="peer", server_default="peer", index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="comments")
    daily_snippet = relationship("DailySnippet", back_populates="comments")
    weekly_snippet = relationship("WeeklySnippet", back_populates="comments")
    notifications = relationship("Notification", back_populates="comment")


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_created_at", "user_id", "created_at"),
        Index("ix_notifications_user_id_is_read_created_at", "user_id", "is_read", "created_at"),
        Index("ix_notifications_type_created_at", "type", "created_at"),
        Index("ix_notifications_daily_snippet_id", "daily_snippet_id"),
        Index("ix_notifications_weekly_snippet_id", "weekly_snippet_id"),
        Index("ix_notifications_comment_id", "comment_id"),
        Index("ix_notifications_actor_user_id", "actor_user_id"),
        UniqueConstraint("dedupe_key", name="ux_notifications_dedupe_key"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String(50), nullable=False)
    daily_snippet_id = Column(Integer, ForeignKey("daily_snippets.id"), nullable=True)
    weekly_snippet_id = Column(Integer, ForeignKey("weekly_snippets.id"), nullable=True)
    comment_id = Column(Integer, ForeignKey("comments.id"), nullable=True)
    is_read = Column(Boolean, nullable=False, default=False, server_default="false")
    read_at = Column(DateTime(timezone=True), nullable=True)
    dedupe_key = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="notifications", foreign_keys=[user_id])
    actor_user = relationship("User", back_populates="acted_notifications", foreign_keys=[actor_user_id])
    daily_snippet = relationship("DailySnippet")
    weekly_snippet = relationship("WeeklySnippet")
    comment = relationship("Comment", back_populates="notifications")


class NotificationSetting(Base):
    __tablename__ = "notification_settings"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    notify_post_author = Column(Boolean, nullable=False, default=True, server_default="true")
    notify_mentions = Column(Boolean, nullable=False, default=True, server_default="true")
    notify_participants = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="notification_setting")


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


class MeetingRoom(Base):
    __tablename__ = "meeting_rooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    location = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    reservations = relationship(
        "MeetingRoomReservation",
        back_populates="meeting_room",
        cascade="all, delete-orphan",
    )


class MeetingRoomReservation(Base):
    __tablename__ = "meeting_room_reservations"
    __table_args__ = (
        Index("ix_meeting_room_reservations_room_start_end", "meeting_room_id", "start_at", "end_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    meeting_room_id = Column(Integer, ForeignKey("meeting_rooms.id"), nullable=False, index=True)
    reserved_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    start_at = Column(DateTime(timezone=True), nullable=False)
    end_at = Column(DateTime(timezone=True), nullable=False)
    purpose = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    meeting_room = relationship("MeetingRoom", back_populates="reservations")
    reserved_by = relationship("User", back_populates="meeting_room_reservations")


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
