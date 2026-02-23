from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, JSON, Text, ARRAY
from sqlalchemy.orm import relationship
from .db import Base
from datetime import datetime
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    # Roles: 'customer', 'basic', 'admin'
    # using JSON for SQLite compatibility + Postgres flexibility
    roles = Column(JSON, default=lambda: ["customer"])  
    created_at = Column(DateTime, default=datetime.utcnow)

    profiles = relationship("Profile", back_populates="user", cascade="all, delete-orphan")
    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="user", cascade="all, delete-orphan")
    feeds = relationship("Feed", back_populates="user", cascade="all, delete-orphan")
    settings = relationship("Settings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    workflow_links = relationship("WorkflowLLMLink", back_populates="user", cascade="all, delete-orphan")
    user_profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    llm_configs = relationship("LLMConfig", back_populates="user", cascade="all, delete-orphan")

class Profile(Base):
    __tablename__ = "profiles"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"))
    
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    location = Column(String, nullable=True)
    linkedin = Column(String, nullable=True)
    github = Column(String, nullable=True)
    portfolio = Column(String, nullable=True)
    skills = Column(Text, nullable=True) # Comma separated or JSON
    experience = Column(JSON, nullable=True)
    education = Column(JSON, nullable=True)
    
    # Extended profile fields
    demographics = Column(JSON, nullable=True)
    work_auth = Column(JSON, nullable=True)
    great_fit_pitch = Column(Text, nullable=True)
    cover_letter_template = Column(Text, nullable=True)
    why_us = Column(Text, nullable=True)
    challenging_project = Column(Text, nullable=True)
    resume_generation_mode = Column(String, nullable=True, default="ats_generated")
    use_uploaded_resume = Column(Boolean, nullable=True, default=False)
    current_pdf_resume_id = Column(String, nullable=True)
    current_text_resume_id = Column(String, nullable=True)
    
    user = relationship("User", back_populates="profiles")

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"))
    
    filename = Column(String, nullable=False)
    path = Column(String, nullable=False)
    type = Column(String, nullable=False) # PDF, TXT
    content = Column(Text, nullable=True) # For parsed text
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="resumes")

class Feed(Base):
    __tablename__ = "feeds"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"))
    
    url = Column(String, nullable=False)
    name = Column(String, nullable=False)
    is_global = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="feeds")
    jobs = relationship("Job", back_populates="feed")

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"))
    feed_id = Column(String, ForeignKey("feeds.id"), nullable=True)
    
    role = Column(String, nullable=False)
    status = Column(String, default="APPLIED") # APPLIED, PENDING, FAILED
    url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Legacy/Feature parity fields
    pdf_path = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    sent = Column(Boolean, default=False)
    retry_count = Column(Integer, default=0)
    apply_link = Column(String, nullable=True)
    
    user = relationship("User", back_populates="jobs")
    feed = relationship("Feed", back_populates="jobs")

class Settings(Base):
    __tablename__ = "settings"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"))
    
    config_data = Column(JSON, nullable=True)
    include_global_feeds = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="settings")

class SystemState(Base):
    """Global system-level key-value state store (replaces JSON state files)."""
    __tablename__ = "system_state"

    key = Column(String, primary_key=True)
    value = Column(JSON, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WorkflowStep(Base):
    """
    Global catalogue of workflow step definitions (seeded from workflows.json).
    Treated as read-only after initial seed. Versioned via the 'id' field.
    """
    __tablename__ = "workflow_steps"

    id = Column(String, primary_key=True)  # Stable string IDs, e.g. 'step_ats_scoring'
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    required_capabilities = Column(JSON, nullable=True, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to user assignments
    llm_links = relationship("WorkflowLLMLink", back_populates="workflow_step", cascade="all, delete-orphan")


class WorkflowLLMLink(Base):
    """
    Per-user mapping: which LLM config is assigned to which workflow step.
    A user can assign exactly one LLM config per workflow step (upsert semantics).
    The llm_config_id references configs stored in the Settings.config_data JSON blob.
    """
    __tablename__ = "workflow_llm_links"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_id = Column(String, ForeignKey("workflow_steps.id", ondelete="CASCADE"), nullable=False)
    llm_config_id = Column(String, nullable=False)  # References entry in Settings.config_data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="workflow_links")
    workflow_step = relationship("WorkflowStep", back_populates="llm_links")


class LLMConfig(Base):
    """
    Per-user LLM API key configuration.
    Replaces the user_llm_configs section of data/config.json.
    user_id is nullable only during one-time migration from the legacy JSON file.
    After migration, all rows will have a valid user_id.
    """
    __tablename__ = "llm_configs"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    sdk_id = Column(String, nullable=False)          # e.g. 'openai', 'mistral'
    name = Column(String, nullable=False)             # User-facing label
    api_key = Column(Text, nullable=False)            # Stored as plaintext (same as legacy JSON)
    plan_type = Column(String, nullable=True, default="free")
    daily_token_limit = Column(Integer, nullable=True, default=0)  # 0 = no limit
    tokens_used_today = Column(Integer, nullable=True, default=0)
    last_used_at = Column(DateTime, nullable=True)
    reset_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="llm_configs")


class UserProfile(Base):
    """
    Unified per-user profile document stored as JSON.
    Replaces the flat-column Profile table and the UserKnowledgeBase table.
    The 'data' column holds the full profile document, matching profile.json schema.
    The knowledge_base sub-key contains [{id, question, answer}] pairs.
    One row per user; user_id is the primary key.
    """
    __tablename__ = "user_profiles"

    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    data = Column(JSON, nullable=False, default=dict)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="user_profile")
