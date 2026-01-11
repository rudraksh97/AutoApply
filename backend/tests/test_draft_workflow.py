"""
Unit tests for FormState and DraftManager.

Tests the draft-first workflow data models and persistence layer.
"""

import pytest
from datetime import datetime
from unittest.mock import patch
import tempfile
import os

from api.schemas.form_state import (
    FormState, 
    FieldState, 
    FieldType, 
    ApplicationDraft, 
    DraftStatus,
    DraftSummary
)
from src.draft_manager import DraftManager


class TestFormStateModels:
    """Tests for FormState and related Pydantic models."""
    
    def test_field_state_defaults(self):
        """Test FieldState initializes with correct defaults."""
        field = FieldState(field_id="email")
        
        assert field.field_id == "email"
        assert field.field_type == FieldType.TEXT
        assert field.value is None
        assert field.confidence == 0.0
        assert field.user_edited is False
        assert field.required is False
    
    def test_field_state_with_values(self):
        """Test FieldState with explicit values."""
        field = FieldState(
            field_id="first_name",
            field_type=FieldType.TEXT,
            label="First Name",
            value="John",
            confidence=0.95,
            required=True
        )
        
        assert field.field_id == "first_name"
        assert field.value == "John"
        assert field.confidence == 0.95
        assert field.required is True
    
    def test_field_type_enum(self):
        """Test all FieldType enum values."""
        expected_types = ["text", "email", "phone", "select", "checkbox", "radio", "file", "textarea", "hidden"]
        actual_types = [t.value for t in FieldType]
        
        for expected in expected_types:
            assert expected in actual_types
    
    def test_form_state_creation(self):
        """Test FormState creates with fields list."""
        form = FormState(
            job_url="https://example.com/job",
            fields=[
                FieldState(field_id="name", value="John"),
                FieldState(field_id="email", value="john@test.com")
            ]
        )
        
        assert form.version == "1.0"
        assert form.job_url == "https://example.com/job"
        assert form.page_index == 0
        assert len(form.fields) == 2
    
    def test_form_state_get_field(self):
        """Test FormState.get_field retrieves correct field."""
        form = FormState(
            job_url="https://example.com/job",
            fields=[
                FieldState(field_id="name", value="John"),
                FieldState(field_id="email", value="john@test.com")
            ]
        )
        
        email_field = form.get_field("email")
        assert email_field is not None
        assert email_field.value == "john@test.com"
        
        missing = form.get_field("nonexistent")
        assert missing is None
    
    def test_form_state_update_field(self):
        """Test FormState.update_field modifies field value."""
        form = FormState(
            job_url="https://example.com/job",
            fields=[FieldState(field_id="name", value="John")]
        )
        
        original_modified = form.last_modified
        
        success = form.update_field("name", "Jane", user_edited=True)
        assert success is True
        
        field = form.get_field("name")
        assert field.value == "Jane"
        assert field.user_edited is True
        assert form.last_modified >= original_modified
    
    def test_form_state_serialization(self):
        """Test FormState serializes to/from JSON."""
        form = FormState(
            job_url="https://example.com/job",
            fields=[FieldState(field_id="name", value="John")]
        )
        
        json_str = form.model_dump_json()
        restored = FormState.model_validate_json(json_str)
        
        assert restored.job_url == form.job_url
        assert len(restored.fields) == 1
        assert restored.fields[0].value == "John"
    
    def test_draft_status_enum(self):
        """Test DraftStatus lifecycle states."""
        expected = ["job_found", "extracted", "prefilled", "draft_saved", "user_opened"]
        actual = [s.value for s in DraftStatus]
        
        for expected_status in expected:
            assert expected_status in actual
    
    def test_application_draft_creation(self):
        """Test ApplicationDraft initializes correctly."""
        draft = ApplicationDraft(job_url="https://example.com/job")
        
        assert draft.id is not None
        assert len(draft.id) == 36  # UUID format
        assert draft.job_url == "https://example.com/job"
        assert draft.status == DraftStatus.JOB_FOUND
        assert draft.form_state is None
    
    def test_application_draft_can_open(self):
        """Test ApplicationDraft.can_open returns correct values."""
        draft = ApplicationDraft(job_url="https://example.com/job")
        
        # Initial state cannot open
        draft.status = DraftStatus.JOB_FOUND
        assert draft.can_open() is False
        
        draft.status = DraftStatus.EXTRACTED
        assert draft.can_open() is False
        
        # These states can open
        draft.status = DraftStatus.PREFILLED
        assert draft.can_open() is True
        
        draft.status = DraftStatus.DRAFT_SAVED
        assert draft.can_open() is True
        
        draft.status = DraftStatus.USER_OPENED
        assert draft.can_open() is True
    
    def test_application_draft_mark_opened(self):
        """Test ApplicationDraft.mark_opened updates status."""
        draft = ApplicationDraft(
            job_url="https://example.com/job",
            status=DraftStatus.DRAFT_SAVED
        )
        
        draft.mark_opened()
        
        assert draft.status == DraftStatus.USER_OPENED


class TestDraftManager:
    """Tests for DraftManager persistence layer."""
    
    @pytest.fixture
    def temp_db(self, tmp_path):
        """Create temporary database for testing."""
        db_path = tmp_path / "data"
        db_path.mkdir()
        
        with patch('src.database.DB_FILE', str(db_path / "test.db")):
            from src.database import init_db
            init_db()
            yield str(db_path / "test.db")
    
    @pytest.fixture
    def draft_manager(self, temp_db):
        """Create DraftManager with temp database."""
        with patch('src.database.DB_FILE', temp_db):
            manager = DraftManager()
            yield manager
    
    def test_create_draft(self, draft_manager):
        """Test creating a new draft."""
        draft_id = draft_manager.create_draft(
            job_url="https://example.com/job1",
            status=DraftStatus.JOB_FOUND
        )
        
        assert draft_id is not None
        assert len(draft_id) == 36
    
    def test_get_draft(self, draft_manager):
        """Test retrieving a draft by ID."""
        draft_id = draft_manager.create_draft(
            job_url="https://example.com/job2",
            job_details="Software Engineer position"
        )
        
        draft = draft_manager.get_draft(draft_id)
        
        assert draft is not None
        assert draft.id == draft_id
        assert draft.job_url == "https://example.com/job2"
        assert draft.job_details == "Software Engineer position"
    
    def test_get_draft_by_url(self, draft_manager):
        """Test retrieving a draft by job URL."""
        draft_manager.create_draft(job_url="https://example.com/unique-job")
        
        draft = draft_manager.get_draft_by_url("https://example.com/unique-job")
        
        assert draft is not None
        assert draft.job_url == "https://example.com/unique-job"
    
    def test_get_nonexistent_draft(self, draft_manager):
        """Test getting a draft that doesn't exist."""
        draft = draft_manager.get_draft("nonexistent-id")
        
        assert draft is None
    
    def test_update_draft_status(self, draft_manager):
        """Test updating draft status."""
        draft_id = draft_manager.create_draft(job_url="https://example.com/job")
        
        success = draft_manager.update_status(draft_id, DraftStatus.EXTRACTED)
        assert success is True
        
        draft = draft_manager.get_draft(draft_id)
        assert draft.status == DraftStatus.EXTRACTED
    
    def test_update_draft_form_state(self, draft_manager):
        """Test updating draft with FormState."""
        draft_id = draft_manager.create_draft(job_url="https://example.com/job")
        
        form_state = FormState(
            job_url="https://example.com/job",
            fields=[FieldState(field_id="name", value="John")]
        )
        
        success = draft_manager.update_draft(draft_id, form_state=form_state)
        assert success is True
        
        draft = draft_manager.get_draft(draft_id)
        assert draft.form_state is not None
        assert len(draft.form_state.fields) == 1
        assert draft.form_state.fields[0].value == "John"
    
    def test_get_all_drafts(self, draft_manager):
        """Test listing all drafts."""
        draft_manager.create_draft(job_url="https://example.com/job1")
        draft_manager.create_draft(job_url="https://example.com/job2")
        draft_manager.create_draft(job_url="https://example.com/job3")
        
        drafts = draft_manager.get_all_drafts()
        
        assert len(drafts) == 3
    
    def test_delete_draft(self, draft_manager):
        """Test deleting a draft."""
        draft_id = draft_manager.create_draft(job_url="https://example.com/to-delete")
        
        success = draft_manager.delete_draft(draft_id)
        assert success is True
        
        draft = draft_manager.get_draft(draft_id)
        assert draft is None
    
    def test_draft_exists(self, draft_manager):
        """Test checking if draft exists by URL."""
        draft_manager.create_draft(job_url="https://example.com/exists")
        
        assert draft_manager.draft_exists("https://example.com/exists") is True
        assert draft_manager.draft_exists("https://example.com/not-exists") is False
    
    def test_get_all_summaries(self, draft_manager):
        """Test getting lightweight summaries."""
        draft_id = draft_manager.create_draft(
            job_url="https://example.com/job",
            job_details="Test job description"
        )
        
        # Add form state
        form_state = FormState(
            job_url="https://example.com/job",
            fields=[
                FieldState(field_id="name", value="John"),
                FieldState(field_id="email", value=None)
            ]
        )
        draft_manager.update_draft(draft_id, form_state=form_state)
        
        summaries = draft_manager.get_all_summaries()
        
        assert len(summaries) >= 1
        summary = summaries[0]
        assert summary.field_count == 2
        assert summary.filled_field_count == 1
