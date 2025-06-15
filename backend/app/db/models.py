import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, BigInteger, DateTime, Boolean, func, UniqueConstraint, text, JSON, Text, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Team(Base):
    """
    Central teams table that connects all integrations
    """
    __tablename__ = "teams"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    team_id = Column(
        String,
        nullable=False,
        unique=True,
        index=True,
        doc="Slack team ID (primary identifier)"
    )
    team_name = Column(
        String,
        nullable=True,
        doc="Human-readable team name from Slack"
    )
    domain = Column(
        String,
        nullable=True,
        doc="Team domain (e.g., company.slack.com)"
    )
    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        doc="Whether this team is active"
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    slack_installation = relationship("SlackInstallation", back_populates="team", uselist=False)
    zoho_installation = relationship("ZohoInstallation", back_populates="team", uselist=False)
    gmail_installation = relationship("GmailInstallation", back_populates="team", uselist=False)
    event_logs = relationship("EventLog", back_populates="team")
    leads = relationship("Lead", back_populates="team")

    __table_args__ = (
        UniqueConstraint('team_id', name='uq_teams_team_id'),
    )

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    property_type = Column(String(100), nullable=True)
    min_bedrooms = Column(Integer, nullable=True)
    max_bedrooms = Column(Integer, nullable=True)
    min_price = Column(BigInteger, nullable=True)
    max_price = Column(BigInteger, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=True
    )

class Lead(Base):
    __tablename__ = "leads"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    team_id = Column(
        String,
        ForeignKey('teams.team_id'),
        nullable=False,
        index=True,
        doc="Reference to the team that owns this lead"
    )
    name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    location = Column(String, nullable=True)
    property_type = Column(String, nullable=True)
    bedrooms = Column(Integer, nullable=True)
    budget = Column(Integer, nullable=True)
    matched_project_ids = Column(
        ARRAY(UUID(as_uuid=True)),
        nullable=True
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    team = relationship("Team", back_populates="leads")

class SlackInstallation(Base):
    __tablename__ = "slack_installations"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    team_id = Column(
        String,
        ForeignKey('teams.team_id'),
        nullable=False,
        unique=True,
        index=True,
        doc="Reference to the team this installation belongs to"
    )
    bot_user_id = Column(String, nullable=True)
    access_token = Column(String, nullable=False)
    installed = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    team = relationship("Team", back_populates="slack_installation")

    __table_args__ = (
        UniqueConstraint('team_id', name='uq_slack_installations_team_id'),
    )

class ZohoInstallation(Base):
    """
    Stores OAuth credentials and metadata for a Zoho CRM integration per Slack team.
    """
    __tablename__ = "zoho_installations"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False
    )
    team_id = Column(
        String,
        ForeignKey('teams.team_id'),
        nullable=False,
        unique=True,
        index=True,
        doc="Reference to the team this installation belongs to"
    )
    access_token = Column(
        String,
        nullable=False,
        doc="Current Zoho OAuth access token"
    )
    refresh_token = Column(
        String,
        nullable=True,
        doc="Refresh token to obtain new access tokens"
    )
    api_domain = Column(
        String,
        nullable=False,
        default="https://www.zohoapis.com",
        doc="Base domain for Zoho API endpoints"
    )
    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        doc="UTC timestamp when the access token expires"
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="UTC timestamp when this record was created"
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="UTC timestamp when this record was last updated"
    )

    # Relationships
    team = relationship("Team", back_populates="zoho_installation")

    __table_args__ = (
        UniqueConstraint('team_id', name='uq_zoho_installations_team_id'),
    )

class GmailInstallation(Base):
    """
    Stores OAuth credentials and metadata for Gmail integration per Slack team.
    """
    __tablename__ = "gmail_installations"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False
    )
    team_id = Column(
        String,
        ForeignKey('teams.team_id'),
        nullable=False,
        unique=True,
        index=True,
        doc="Reference to the team this installation belongs to"
    )
    access_token = Column(
        String,
        nullable=False,
        doc="Current Gmail OAuth access token"
    )
    refresh_token = Column(
        String,
        nullable=True,
        doc="Refresh token to obtain new access tokens"
    )
    user_email = Column(
        String,
        nullable=True,
        doc="Gmail user email address"
    )
    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
        doc="UTC timestamp when the access token expires"
    )
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="UTC timestamp when this record was created"
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="UTC timestamp when this record was last updated"
    )

    # Relationships
    team = relationship("Team", back_populates="gmail_installation")

    __table_args__ = (
        UniqueConstraint('team_id', name='uq_gmail_installations_team_id'),
    )

class EventLog(Base):
    __tablename__ = "event_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(
        String,
        ForeignKey('teams.team_id'),
        nullable=True,
        index=True,
        doc="Reference to the team this event belongs to"
    )
    event_type = Column(String, nullable=False)  # lead_processed, crm_insertion, email_notification, etc.
    event_data = Column(JSON, nullable=True)  # Store the actual event data
    status = Column(String, nullable=False, default="processing")  # processing, success, error
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    team = relationship("Team", back_populates="event_logs")
