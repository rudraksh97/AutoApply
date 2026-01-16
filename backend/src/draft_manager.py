"""
Draft management and persistence for the AutoApply application.

This module handles CRUD operations for application drafts, implementing
the draft-first workflow where applications are prepared but never submitted.
"""

import json
import os
import shutil
import uuid
from datetime import datetime
from typing import List, Optional

from api.schemas.form_state import (
    ApplicationDraft,
    DraftStatus,
    DraftSummary,
    FormState,
    ResumeVersion,
)
from src.database import get_connection, init_db
from src.url_utils import get_stable_job_id, normalize_job_url


class DraftManager:
    """
    Manages application draft persistence using SQLite.

    Drafts represent prepared job applications that are saved for later
    manual completion by the user. The system never submits applications.
    """

    def __init__(self):
        init_db()

    # -------------------------------------------------------------------------
    # Draft CRUD
    # -------------------------------------------------------------------------

    def create_draft(
        self,
        job_url: str,
        status: DraftStatus = DraftStatus.JOB_FOUND,
        form_state: Optional[FormState] = None,
        resume_path: Optional[str] = None,
        job_details: Optional[str] = None,
        apply_link: Optional[str] = None
    ) -> str:
        """Create a new application draft. Returns the draft ID."""
        job_url = normalize_job_url(job_url)

        existing = self.get_draft_by_url(job_url)
        draft_id = existing.id if existing else str(uuid.uuid4())

        draft = ApplicationDraft(
            id=draft_id,
            job_url=job_url,
            apply_link=apply_link,
            status=status,
            form_state=form_state,
            resume_path=resume_path,
            job_details=job_details
        )

        self._save_draft_to_db(draft, existing)
        return draft.id

    def _save_draft_to_db(self, draft: ApplicationDraft, existing: Optional[ApplicationDraft]):
        """Persist draft to database."""
        now = datetime.utcnow().isoformat()
        form_state_json = draft.form_state.model_dump_json() if draft.form_state else None

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO drafts
                (id, job_url, apply_link, status, form_state_json, resume_path,
                 job_details, initial_ats_score, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                draft.id,
                draft.job_url,
                draft.apply_link,
                draft.status.value,
                form_state_json,
                draft.resume_path,
                draft.job_details,
                existing.initial_ats_score if existing else None,
                existing.created_at.isoformat() if existing else now,
                now
            ))
            conn.commit()

    def get_draft(self, draft_id: str) -> Optional[ApplicationDraft]:
        """Retrieve a draft by its ID."""
        with get_connection() as conn:
            conn.row_factory = self._dict_row_factory
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,))
            row = cursor.fetchone()

        return self._row_to_draft(row) if row else None

    def get_draft_by_url(self, job_url: str) -> Optional[ApplicationDraft]:
        """Retrieve a draft by job URL."""
        job_url = normalize_job_url(job_url)

        with get_connection() as conn:
            conn.row_factory = self._dict_row_factory
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM drafts WHERE job_url = ?", (job_url,))
            row = cursor.fetchone()

        return self._row_to_draft(row) if row else None

    def get_all_drafts(self) -> List[ApplicationDraft]:
        """Retrieve all drafts ordered by most recent first."""
        with get_connection() as conn:
            conn.row_factory = self._dict_row_factory
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM drafts ORDER BY updated_at DESC")
            rows = cursor.fetchall()

        return [self._row_to_draft(row) for row in rows]

    def get_all_summaries(self) -> List[DraftSummary]:
        """Retrieve lightweight summaries of all drafts (efficient for listing)."""
        with get_connection() as conn:
            conn.row_factory = self._dict_row_factory
            cursor = conn.cursor()
            cursor.execute("""
                SELECT d.id, d.job_url, d.apply_link, d.status, d.job_details,
                       d.initial_ats_score, d.created_at, d.updated_at, d.form_state_json,
                       v.ats_score as current_ats_score
                FROM drafts d
                LEFT JOIN resume_versions v ON d.id = v.draft_id AND v.is_current = 1
                ORDER BY d.updated_at DESC
            """)
            rows = cursor.fetchall()

        return [self._row_to_summary(row) for row in rows]

    def _row_to_summary(self, row: dict) -> DraftSummary:
        """Convert a database row to a DraftSummary."""
        field_count, filled_count = self._count_form_fields(row.get('form_state_json'))

        job_details = row.get('job_details')
        if job_details and len(job_details) > 200:
            job_details = job_details[:200] + "..."

        return DraftSummary(
            id=row['id'],
            job_url=row['job_url'],
            apply_link=row.get('apply_link'),
            status=DraftStatus(row['status']),
            job_details=job_details,
            initial_ats_score=row.get('initial_ats_score'),
            current_ats_score=row.get('current_ats_score'),
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            field_count=field_count,
            filled_field_count=filled_count
        )

    def _count_form_fields(self, form_state_json: Optional[str]) -> tuple:
        """Count total and filled fields from form state JSON."""
        if not form_state_json:
            return 0, 0

        try:
            data = json.loads(form_state_json)
            fields = data.get('fields', [])
            return len(fields), sum(1 for f in fields if f.get('value'))
        except json.JSONDecodeError:
            return 0, 0

    # -------------------------------------------------------------------------
    # Draft Updates
    # -------------------------------------------------------------------------

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
        """Update an existing draft. Returns True if found and updated."""
        updates, values = self._build_update_params(
            status, form_state, resume_path, job_details, apply_link, initial_ats_score
        )

        if not updates:
            return True

        updates.append("updated_at = ?")
        values.append(datetime.utcnow().isoformat())
        values.append(draft_id)

        query = f"UPDATE drafts SET {', '.join(updates)} WHERE id = ?"

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
            return cursor.rowcount > 0

    def _build_update_params(
        self,
        status: Optional[DraftStatus],
        form_state: Optional[FormState],
        resume_path: Optional[str],
        job_details: Optional[str],
        apply_link: Optional[str],
        initial_ats_score: Optional[int]
    ) -> tuple:
        """Build SQL update clause and values."""
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

        return updates, values

    def update_status(self, draft_id: str, status: DraftStatus) -> bool:
        """Update only the status of a draft."""
        return self.update_draft(draft_id, status=status)

    # -------------------------------------------------------------------------
    # Draft Deletion
    # -------------------------------------------------------------------------

    def delete_draft(self, draft_id: str) -> bool:
        """Delete a draft by ID including all associated files."""
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT job_url FROM drafts WHERE id = ?", (draft_id,))
            row = cursor.fetchone()

            if row:
                return self.delete_draft_by_url(row[0])

            # Fallback cleanup if draft record already gone
            cursor.execute("DELETE FROM resume_versions WHERE draft_id = ?", (draft_id,))
            cursor.execute("DELETE FROM drafts WHERE id = ?", (draft_id,))
            conn.commit()
            return cursor.rowcount > 0

    def delete_draft_by_url(self, job_url: str) -> bool:
        """Delete a draft by URL including all files and database records."""
        job_url = normalize_job_url(job_url)
        draft = self.get_draft_by_url(job_url)

        if not draft:
            return False

        # Clean up filesystem
        self._delete_draft_files(job_url)

        # Delete from database
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM resume_versions WHERE draft_id = ?", (draft.id,))
            cursor.execute("DELETE FROM drafts WHERE id = ?", (draft.id,))
            conn.commit()
            return cursor.rowcount > 0

    def _delete_draft_files(self, job_url: str):
        """Remove all files associated with a draft."""
        job_id = get_stable_job_id(job_url)

        dirs_to_remove = [
            f"data/generated_resumes/{job_id}",
            f"data/tex_resumes/{job_id}",
            f"data/logs/{job_id}"
        ]

        for directory in dirs_to_remove:
            if os.path.exists(directory):
                try:
                    shutil.rmtree(directory)
                except Exception as e:
                    print(f"Warning: Failed to delete {directory}: {e}")

    def draft_exists(self, job_url: str) -> bool:
        """Check if a draft exists for the given job URL."""
        job_url = normalize_job_url(job_url)

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM drafts WHERE job_url = ?", (job_url,))
            return cursor.fetchone() is not None

    # -------------------------------------------------------------------------
    # Row Conversion
    # -------------------------------------------------------------------------

    @staticmethod
    def _dict_row_factory(cursor, row):
        """SQLite row factory that returns dicts."""
        return dict(zip([col[0] for col in cursor.description], row))

    def _row_to_draft(self, row: dict) -> ApplicationDraft:
        """Convert a database row to an ApplicationDraft."""
        form_state = self._parse_form_state(row.get('form_state_json'))

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

    def _parse_form_state(self, json_str: Optional[str]) -> Optional[FormState]:
        """Parse form state JSON, handling data sanitization."""
        if not json_str:
            return None

        try:
            return FormState.model_validate_json(json_str)
        except Exception:
            pass

        # Try to sanitize non-string field values
        try:
            data = json.loads(json_str)
            for field in data.get('fields', []):
                value = field.get('value')
                if value is not None and not isinstance(value, str):
                    field['value'] = str(value).lower() if isinstance(value, bool) else str(value)
            return FormState.model_validate(data)
        except Exception:
            return None

    # -------------------------------------------------------------------------
    # Resume Version Management
    # -------------------------------------------------------------------------

    def create_resume_version(self, version: ResumeVersion) -> str:
        """Store a new resume version."""
        now = datetime.utcnow().isoformat()

        with get_connection() as conn:
            cursor = conn.cursor()

            if version.is_current:
                cursor.execute(
                    "UPDATE resume_versions SET is_current = 0 WHERE draft_id = ?",
                    (version.draft_id,)
                )

            cursor.execute("""
                INSERT INTO resume_versions
                (id, draft_id, version_number, tex_path, pdf_path, ats_score,
                 justification, keywords_added, changes_summary, status, is_current, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                version.status,
                1 if version.is_current else 0,
                now
            ))

            if version.is_current:
                cursor.execute(
                    "UPDATE drafts SET resume_path = ? WHERE id = ?",
                    (version.pdf_path, version.draft_id)
                )

            conn.commit()

        return version.id

    def get_resume_versions(self, draft_id: str) -> List[ResumeVersion]:
        """Get all resume versions for a draft."""
        with get_connection() as conn:
            conn.row_factory = self._dict_row_factory
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM resume_versions WHERE draft_id = ? ORDER BY version_number DESC",
                (draft_id,)
            )
            rows = cursor.fetchall()

        return [self._row_to_resume_version(row) for row in rows]

    def _row_to_resume_version(self, row: dict) -> ResumeVersion:
        """Convert a database row to a ResumeVersion."""
        return ResumeVersion(
            id=row['id'],
            draft_id=row['draft_id'],
            version_number=row['version_number'],
            tex_path=row['tex_path'],
            pdf_path=row['pdf_path'],
            ats_score=row['ats_score'],
            justification=row.get('justification'),
            keywords_added=row.get('keywords_added'),
            changes_summary=row.get('changes_summary'),
            status=row.get('status', 'COMPLETED'),
            is_current=bool(row['is_current']),
            created_at=datetime.fromisoformat(row['created_at'])
        )

    def update_resume_version(self, version_id: str, **kwargs) -> bool:
        """Update a resume version's fields."""
        if not kwargs:
            return True

        updates = [f"{k} = ?" for k in kwargs.keys()]
        values = list(kwargs.values())
        values.append(version_id)

        query = f"UPDATE resume_versions SET {', '.join(updates)} WHERE id = ?"

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
            return cursor.rowcount > 0

    def set_current_resume_version(self, draft_id: str, version_id: str) -> bool:
        """Set a specific version as current for a draft."""
        with get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                "UPDATE resume_versions SET is_current = 0 WHERE draft_id = ?",
                (draft_id,)
            )

            cursor.execute(
                "UPDATE resume_versions SET is_current = 1 WHERE id = ?",
                (version_id,)
            )

            if cursor.rowcount == 0:
                conn.rollback()
                return False

            cursor.execute(
                "SELECT pdf_path FROM resume_versions WHERE id = ?",
                (version_id,)
            )
            row = cursor.fetchone()

            if row:
                cursor.execute(
                    "UPDATE drafts SET resume_path = ? WHERE id = ?",
                    (row[0], draft_id)
                )

            conn.commit()
            return True
