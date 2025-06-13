# app/db/models.py
import uuid
from sqlalchemy import Column, String, Integer, TIMESTAMP, text, ARRAY , Boolean , UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Project(Base):
    __tablename__ = "projects"
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        nullable=False,
        server_default=text("gen_random_uuid()")
    )
    name = Column(String, nullable=False)
    location = Column(String, nullable=False)
    min_price = Column(Integer, nullable=False)
    max_price = Column(Integer, nullable=False)
    min_bedrooms = Column(Integer, nullable=False)
    max_bedrooms = Column(Integer, nullable=False)
    property_type = Column(String, nullable=False)
    created_at = Column(TIMESTAMP, server_default=text("NOW()"))

class Lead(Base):
    __tablename__ = "leads"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    location = Column(String, nullable=True)
    property_type = Column(String, nullable=True)
    bedrooms = Column(Integer, nullable=True)
    budget = Column(Integer, nullable=True)
    matched_project_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True)
    created_at = Column(TIMESTAMP, server_default=text("NOW()"))

class SlackInstallation(Base):
    __tablename__ = "slack_installations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(String, nullable=False, unique=True)  # Slack team/workspace ID
    team_name = Column(String, nullable=True)
    bot_user_id = Column(String, nullable=True)
    access_token = Column(String, nullable=False)
    installed = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=text("NOW()"))

    __table_args__ = (
        UniqueConstraint('team_id', name='uq_slack_team_id'),
    )

class ZohoInstallation(Base):
    __tablename__ = "zoho_installations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    team_id = Column(String, nullable=False, unique=True)  # Link to Slack team_id
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=True)
    api_domain = Column(String, nullable=True)
    expires_at = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, server_default=text("NOW()"))

    __table_args__ = (
        UniqueConstraint('team_id', name='uq_zoho_team_id'),
    )