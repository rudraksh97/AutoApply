"""
Draft management and persistence for the AutoApply application.

This module handles CRUD operations for application drafts, implementing
the draft-first workflow where applications are prepared but never submitted.
"""

import json
from datetime import datetime
from typing import Optional, List

from src.database import init_db, get_connection
from src.url_utils import normalize_job_url
from api.schemas.form_state import (
    ApplicationDraft, 
    FormState, 
    DraftStatus, 
    DraftSummary,
    ResumeVersion
)


class DraftManager:
    """
    Manages application draft persistence using SQLite.
    
    Drafts represent prepared job applications that are saved for later
    manual completion by the user. The system never submits applications.
    """
    
    def __init__(self):
        """Initialize the manager and ensure database schema exists."""
        init_db()
    
    def create_draft(
        self,
        job_url: str,
        status: DraftStatus = DraftStatus.JOB_FOUND,
        form_state: Optional[FormState] = None,
        resume_path: Optional[str] = None,
        job_details: Optional[str] = None,
        apply_link: Optional[str] = None
    ) -> str:
        """
        Create a new application draft.
        
        Args:
            job_url: URL of the job posting (JD page)
            status: Initial lifecycle status
            form_state: Form state if already captured
            resume_path: Path to the resume file
            job_details: Extracted job description
            apply_link: URL of the application form (if different from job_url)
            
        Returns:
            The draft ID (UUID string)
        """
        job_url = normalize_job_url(job_url)

        draft = ApplicationDraft(
            job_url=job_url,
            apply_link=apply_link,
            status=status,
            form_state=form_state,
            resume_path=resume_path,
            job_details=job_details
        )
        
        now = datetime.utcnow().isoformat()
        form_state_json = form_state.model_dump_json() if form_state else None
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO drafts 
                (id, job_url, apply_link, status, form_state_json, resume_path, job_details, initial_ats_score, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                draft.id,
                job_url,
                apply_link,
                status.value,
                form_state_json,
                resume_path,
                job_details,
                None,  # initial_ats_score
                now,
                now
            ))
            conn.commit()
            
        return draft.id
    
    def get_draft(self, draft_id: str) -> Optional[ApplicationDraft]:
        """
        Retrieve a draft by its ID.
        
        Args:
            draft_id: The UUID of the draft
            
        Returns:
            The ApplicationDraft if found, None otherwise
        """
        with get_connection() as conn:
            conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,))
            row = cursor.fetchone()
            
        if not row:
            return None
            
        return self._row_to_draft(row)
    
    def get_draft_by_url(self, job_url: str) -> Optional[ApplicationDraft]:
        """
        Retrieve a draft by job URL.
        
        Args:
            job_url: The URL of the job posting
            
        Returns:
            The ApplicationDraft if found, None otherwise
        """
        job_url = normalize_job_url(job_url)

        with get_connection() as conn:
            conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM drafts WHERE job_url = ?", (job_url,))
            row = cursor.fetchone()
            
        if not row:
            return None
            
        return self._row_to_draft(row)
    
    def get_all_drafts(self) -> List[ApplicationDraft]:
        """
        Retrieve all drafts ordered by most recent first.
        
        Returns:
            List of all ApplicationDraft objects
        """
        with get_connection() as conn:
            conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM drafts ORDER BY updated_at DESC")
            rows = cursor.fetchall()
            
        return [self._row_to_draft(row) for row in rows]
    
    def get_all_summaries(self) -> List[DraftSummary]:
        """
        Retrieve lightweight summaries of all drafts.
        
        This is more efficient for listing endpoints as it doesn't
        deserialize the full FormState.
        
        Returns:
            List of DraftSummary objects
        """
        with get_connection() as conn:
            conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
            cursor = conn.cursor()
            cursor.execute("""
                SELECT d.id, d.job_url, d.apply_link, d.status, d.job_details, d.initial_ats_score, 
                       d.created_at, d.updated_at, d.form_state_json,
                       v.ats_score as current_ats_score
                FROM drafts d
                LEFT JOIN resume_versions v ON d.id = v.draft_id AND v.is_current = 1
                ORDER BY d.updated_at DESC
            """)
            rows = cursor.fetchall()
            
        summaries = []
        for row in rows:
            field_count = 0
            filled_count = 0
            
            if row['form_state_json']:
                try:
                    form_data = json.loads(row['form_state_json'])
                    fields = form_data.get('fields', [])
                    field_count = len(fields)
                    filled_count = sum(1 for f in fields if f.get('value'))
                except json.JSONDecodeError:
                    pass
            
            summaries.append(DraftSummary(
                id=row['id'],
                job_url=row['job_url'],
                apply_link=row.get('apply_link'),
                status=DraftStatus(row['status']),
                job_details=row['job_details'][:200] + "..." if row['job_details'] and len(row['job_details']) > 200 else row['job_details'],
                initial_ats_score=row.get('initial_ats_score'),
                current_ats_score=row.get('current_ats_score'),
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at']),
                field_count=field_count,
                filled_field_count=filled_count
            ))
            
        return summaries
    
    def update_draft(
        self,
        draft_id: str,
        status: Optional[DraftStatus] = None,
        form_state: Optional[FormState] = None,
        resume_path: Optional[str] = None,
        job_details: Optional[str] = None,
        apply_link: Optional[str] = None,
        initial_ats_score: Optional[int] = None
    ) -> bool:
        """
        Update an existing draft.
        
        Args:
            draft_id: The UUID of the draft to update
            status: New status (optional)
            form_state: New form state (optional)
            resume_path: New resume path (optional)
            job_details: New job details (optional)
            apply_link: URL of the application page (optional)
            
        Returns:
            True if the draft was found and updated, False otherwise
        """
        updates = []
        values = []
        
        if status is not None:
            updates.append("status = ?")
            values.append(status.value)
        
        if form_state is not None:
            updates.append("form_state_json = ?")
            values.append(form_state.model_dump_json())
        
        if resume_path is not None:
            updates.append("resume_path = ?")
            values.append(resume_path)
        
        if job_details is not None:
            updates.append("job_details = ?")
            values.append(job_details)
        
        if apply_link is not None:
            updates.append("apply_link = ?")
            values.append(apply_link)
            
        if initial_ats_score is not None:
            updates.append("initial_ats_score = ?")
            values.append(initial_ats_score)
        
        if not updates:
            return True  # Nothing to update
        
        updates.append("updated_at = ?")
        values.append(datetime.utcnow().isoformat())
        values.append(draft_id)
        
        query = f"UPDATE drafts SET {', '.join(updates)} WHERE id = ?"
        
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
            return cursor.rowcount > 0
    
    def update_status(self, draft_id: str, status: DraftStatus) -> bool:
        """
        Update only the status of a draft.
        
        Args:
            draft_id: The UUID of the draft
            status: New lifecycle status
            
        Returns:
            True if updated, False if draft not found
        """
        return self.update_draft(draft_id, status=status)
    
    def delete_draft(self, draft_id: str) -> bool:
        """
        Delete a draft by ID.
        
        Args:
            draft_id: The UUID of the draft to delete
            
        Returns:
            True if deleted, False if not found
        """
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM drafts WHERE id = ?", (draft_id,))
            conn.commit()
            return cursor.rowcount > 0

    def delete_draft_by_url(self, job_url: str) -> bool:
        """
        Delete a draft by job URL.
        
        Args:
            job_url: The URL of the job
            
        Returns:
            True if deleted, False if not found
        """
        job_url = normalize_job_url(job_url)

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM drafts WHERE job_url = ?", (job_url,))
            conn.commit()
            return cursor.rowcount > 0
    
    def draft_exists(self, job_url: str) -> bool:
        """
        Check if a draft exists for the given job URL.
        
        Args:
            job_url: The URL to check
            
        Returns:
            True if a draft exists, False otherwise
        """
        job_url = normalize_job_url(job_url)

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM drafts WHERE job_url = ?", (job_url,))
            return cursor.fetchone() is not None
    
    def _row_to_draft(self, row: dict) -> ApplicationDraft:
        """Convert a database row to an ApplicationDraft object."""
        form_state = None
        if row['form_state_json']:
            try:
                form_state = FormState.model_validate_json(row['form_state_json'])
            except Exception:
                # Try to sanitize the data - convert non-string values to strings
                try:
                    data = json.loads(row['form_state_json'])
                    for field in data.get('fields', []):
                        if field.get('value') is not None and not isinstance(field.get('value'), str):
                            field['value'] = str(field['value']).lower() if isinstance(field['value'], bool) else str(field['value'])
                    form_state = FormState.model_validate(data)
                except Exception:
                    pass
        
        return ApplicationDraft(
            id=row['id'],
            job_url=row['job_url'],
            apply_link=row.get('apply_link'),
            status=DraftStatus(row['status']),
            form_state=form_state,
            resume_path=row.get('resume_path'),
            job_details=row.get('job_details'),
            initial_ats_score=row.get('initial_ats_score'),
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at'])
        )

    def create_resume_version(self, version: ResumeVersion) -> str:
        """Store a new resume version."""
        now = datetime.utcnow().isoformat()
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # If this is set as current, unset others for this draft
            if version.is_current:
                cursor.execute(
                    "UPDATE resume_versions SET is_current = 0 WHERE draft_id = ?",
                    (version.draft_id,)
                )
                
            cursor.execute("""
                INSERT INTO resume_versions 
                (id, draft_id, version_number, tex_path, pdf_path, ats_score, justification, keywords_added, changes_summary, is_current, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                version.id,
                version.draft_id,
                version.version_number,
                version.tex_path,
                version.pdf_path,
                version.ats_score,
                version.justification,
                version.keywords_added,
                version.changes_summary,
                1 if version.is_current else 0,
                now
            ))
            
            # Also update the main draft's current resume path if this is current
            if version.is_current:
                cursor.execute(
                    "UPDATE drafts SET resume_path = ? WHERE id = ?",
                    (version.pdf_path, version.draft_id)
                )
                
            conn.commit()
        return version.id

    def get_resume_versions(self, draft_id: str) -> List[ResumeVersion]:
        """Get all versions for a draft."""
        with get_connection() as conn:
            conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM resume_versions WHERE draft_id = ? ORDER BY version_number DESC",
                (draft_id,)
            )
            rows = cursor.fetchall()
            
        return [
            ResumeVersion(
                id=row['id'],
                draft_id=row['draft_id'],
                version_number=row['version_number'],
                tex_path=row['tex_path'],
                pdf_path=row['pdf_path'],
                ats_score=row['ats_score'],
                justification=row.get('justification'),
                keywords_added=row.get('keywords_added'),
                changes_summary=row.get('changes_summary'),
                is_current=bool(row['is_current']),
                created_at=datetime.fromisoformat(row['created_at'])
            ) for row in rows
        ]

    def set_current_resume_version(self, draft_id: str, version_id: str) -> bool:
        """Set a specific version as current for a draft."""
        with get_connection() as conn:
            cursor = conn.cursor()
            
            # Unset all
            cursor.execute("UPDATE resume_versions SET is_current = 0 WHERE draft_id = ?", (draft_id,))
            
            # Set target
            cursor.execute(
                "UPDATE resume_versions SET is_current = 1 WHERE id = ?",
                (version_id,)
            )
            
            if cursor.rowcount == 0:
                conn.rollback()
                return False
                
            # Get the PDF path to update the main draft
            cursor.execute("SELECT pdf_path FROM resume_versions WHERE id = ?", (version_id,))
            row = cursor.fetchone()
            if row:
                cursor.execute("UPDATE drafts SET resume_path = ? WHERE id = ?", (row[0], draft_id))
            
            conn.commit()
            return True
