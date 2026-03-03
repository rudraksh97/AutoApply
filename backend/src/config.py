"""
Configuration management for the AutoApply application.

Design contract:
  - `get_sdk_definitions()` reads from llms.json (static, read-only bundled catalogue).
  - `get_user_configs()` / LLM CRUD → DB (llm_configs table, per-user).
  - `get_ats_prompts()` / `set_ats_prompts()` → SystemState DB (key='ats_prompts').
  - `get_global_setting()` / `get_api_key()` → configs/development.json (infra-level, not user data).
  - No user data is written to local JSON files.
"""

import os
import json
import uuid
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DATA_DIR = os.path.join(BASE_DIR, "data")
LLMS_FILE = os.path.join(DATA_DIR, "llms.json")
GLOBAL_CONFIG_FILE = os.path.join(BASE_DIR, "configs", "development.json")


class ConfigManager:
    """
    Delegates all user data reads/writes to the database.
    Only static SDK definitions and infrastructure config still read from files.
    """

    def __init__(self):
        self.global_config = self._load_global_config()

    def _load_global_config(self) -> dict:
        if os.path.exists(GLOBAL_CONFIG_FILE):
            with open(GLOBAL_CONFIG_FILE, "r") as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse development.json; using empty config.")
        return {}

    # =========================================================================
    # SDK Definitions (llms.json — static read-only catalogue)
    # =========================================================================

    def get_sdk_definitions(self) -> list:
        """Returns the list of supported LLM SDKs from the bundled llms.json."""
        if not os.path.exists(LLMS_FILE):
            return []
        with open(LLMS_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []

    def get_sdk_definition(self, sdk_id: str) -> Optional[dict]:
        for sdk in self.get_sdk_definitions():
            if sdk.get("id") == sdk_id:
                return sdk
        return None

    # =========================================================================
    # User LLM Configurations → DB
    # =========================================================================

    def get_user_configs(self, user_id: Optional[str] = None) -> list:
        """
        Returns LLM configs from the database.
        If user_id is provided, returns configs for that user only.
        If user_id is None (legacy call sites), returns all configs (admin view).
        """
        from src.db import SessionLocal
        from src.models import LLMConfig
        db = SessionLocal()
        try:
            query = db.query(LLMConfig)
            if user_id:
                query = query.filter(LLMConfig.user_id == user_id)
            configs = query.all()
            return [self._llm_config_to_dict(c) for c in configs]
        finally:
            db.close()

    def add_user_config(
        self,
        sdk_id: str,
        name: str,
        api_key: str,
        plan_type: str = "free",
        daily_limit: Optional[int] = None,
        user_id: Optional[str] = None,
    ) -> dict:
        """Insert a new LLM config into the DB. Returns the created config dict."""
        from src.db import SessionLocal
        from src.models import LLMConfig
        db = SessionLocal()
        try:
            # Fallback to SDK default limit if not provided or set to 0
            if daily_limit is None or daily_limit <= 0:
                sdk = self.get_sdk_definition(sdk_id)
                if sdk:
                    daily_limit = sdk.get("daily_token_limit", 1000000)
                else:
                    daily_limit = 1000000

            new_id = str(uuid.uuid4())
            cfg = LLMConfig(
                id=new_id,
                user_id=user_id,
                sdk_id=sdk_id,
                name=name,
                api_key=api_key,
                plan_type=plan_type,
                daily_token_limit=daily_limit,
                tokens_used_today=0,
            )
            db.add(cfg)
            db.commit()
            db.refresh(cfg)
            return self._llm_config_to_dict(cfg)
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def get_llm_config(self, config_id: str) -> Optional[dict]:
        """Fetch a single LLM config by ID."""
        from src.db import SessionLocal
        from src.models import LLMConfig
        db = SessionLocal()
        try:
            cfg = db.query(LLMConfig).filter(LLMConfig.id == config_id).first()
            return self._llm_config_to_dict(cfg) if cfg else None
        finally:
            db.close()

    def update_user_config(self, config_id: str, updates: dict) -> bool:
        """Update fields on an existing LLM config. Returns True if found and updated."""
        from src.db import SessionLocal
        from src.models import LLMConfig
        db = SessionLocal()
        try:
            cfg = db.query(LLMConfig).filter(LLMConfig.id == config_id).first()
            if not cfg:
                return False
            for key, val in updates.items():
                if hasattr(cfg, key):
                    setattr(cfg, key, val)
            db.commit()
            return True
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def remove_user_config(self, config_id: str) -> bool:
        """Delete an LLM config by ID. Returns True if deleted."""
        from src.db import SessionLocal
        from src.models import LLMConfig
        db = SessionLocal()
        try:
            cfg = db.query(LLMConfig).filter(LLMConfig.id == config_id).first()
            if not cfg:
                return False
            db.delete(cfg)
            db.commit()
            return True
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def _llm_config_to_dict(cfg) -> dict:
        return {
            "id": cfg.id,
            "user_id": cfg.user_id,
            "sdk_id": cfg.sdk_id,
            "name": cfg.name,
            "api_key": cfg.api_key,
            "plan_type": cfg.plan_type,
            "daily_token_limit": cfg.daily_token_limit,
            "tokens_used_today": cfg.tokens_used_today or 0,
            "last_used_at": cfg.last_used_at.isoformat() if cfg.last_used_at else None,
            "reset_at": cfg.reset_at.isoformat() if cfg.reset_at else None,
        }

    # =========================================================================
    # ATS Prompts → SystemState DB
    # =========================================================================

    def get_ats_prompts(self) -> dict:
        """Returns custom ATS prompts from SystemState DB with fallback to defaults."""
        from src.db import SessionLocal
        from src.models import SystemState
        
        defaults = {
            "calculate_score": (
                "You are an Applicant Tracking System (ATS) used by Fortune-500 companies.\n\n"
                "Your task is to score how well a candidate’s resume matches a job description using the same logic "
                "as modern ATS platforms (Workday, Greenhouse, Lever, iCIMS).\n\n"
                "You must analyze the resume exactly like an ATS parser would — keyword matching, semantic matching, "
                "experience relevance, and role fit — not like a human recruiter.\n\n"
                "--------------------------------\n"
                "SCORING METHODOLOGY (must follow strictly)\n\n"
                "Total Score = 100 points\n"
                "A. Keyword Match (70 points)\n"
                "B. Skill Coverage Depth (20 points)\n"
                "C. Job Title & Role Match (2 points)\n"
                "D. Experience Relevance (7 points)\n"
                "E. Education & Domain Fit (1 point)\n\n"
                "--------------------------------\n"
                "OUTPUT FORMAT (STRICT JSON — NO EXTRA TEXT)\n\n"
                "{\n"
                "  \"ats_score\": number between 0 and 100,\n"
                "  \"missing_keywords\": [\n"
                "     list of important skills or phrases in JOB_DESCRIPTION that are missing or weak in the resume. "
                "Focus on Technical Skills Keywords and Soft skills keywords.\n"
                "  ],\n"
                "  \"matched_keywords\": [\n"
                "     list of important skills that were successfully matched\n"
                "  ],\n"
                "  \"justification\": {\n"
                "     \"keyword_match\": \"...\",\n"
                "     \"skill_depth\": \"...\",\n"
                "     \"role_fit\": \"...\",\n"
                "     \"experience_relevance\": \"...\",\n"
                "     \"education_fit\": \"...\",\n"
                "     \"parsing_quality\": \"...\"\n"
                "  }\n"
                "}\n\n"
                "--------------------------------\n"
                "INPUTS\n\n"
                "RESUME_CODE (LaTeX):\n{{resume_text}}\n\n"
                "JOB_DESCRIPTION:\n{{job_description}}"
            ),
            "tailor_resume": (
                "You are an ATS-optimization engine used by Big Tech recruiting platforms.\n\n"
                "Your task is to rewrite a LaTeX resume so that its ATS score becomes at least 90% for a given job "
                "description, while preserving structure, honesty, and formatting.\n\n"
                "--------------------------------\n"
                "STRICT RULES\n"
                "1) DO NOT: change section structure, remove existing sections, or rename headers.\n"
                "2) YOU MUST: Add missing keywords which are Technical in Nature to Technical Skills and Experience. "
                "Do not Touch Projects\n"
                "3) If a technical skill is missing, enhance bullets with relevant frameworks (e.g., Java with Spring Boot, "
                "Python with Django, Flask, FASTAPI).\n"
                "4) If & or % is written in latex code, replace with \\& and \\% as these punctuations throws error in Latex.\n"
                "5) Make sure, You are not making syntactical errors in the latex code.\n"
                "6) Latex tags should have \\tagname instead of \\\\tagname.\n"
                "7) Technical Section should not look like a paragraph. For Subsections of Technical Skills Section, "
                "use \\\\ for line break instead of \\.\n"
                "8) Try to mix Missing Technical Keywords with the Existing Skills, for eg. PostgresSQL is already there, "
                "and one of the Missing Keyword is Relational Database, then don't add Relation Database as a separate skills, "
                "Just Edit PostgresSQL to PostgresSQL Relational Database.\n"
                "9) If a Keyword is a Technical Skill, then only add it in the Technical Skill Section, else try to add that in Experience.\n"
                "10) YOU MUST: If a Missing Keyword is Non-Technical - DO NOT add that in Technical Section. Add those in Experience. "
                "Try to Create another Bullet point in Euler Motors Experience.\n"
                "11) If a Technical Skill is missing from my Resume: Try to add both in Skills and Experience Section of "
                "Euler Motors by adding another Bullet Point at the Start of Euler Motors Section.\n"
                "12) Very Important: Make Sure there is no Compilation Error in the Produced Latex File.\n\n"
                "--------------------------------\n"
                "REQUIRED OUTPUT (JSON — NO EXTRA TEXT)\n"
                "{\n"
                "  \"final_score\": number between 0 and 100,\n"
                "  \"new_latex_code\": \"FULL optimized LaTeX resume\",\n"
                "  \"summary\": [\n"
                "     \"Added 'Next.js' to skills\",\n"
                "     \"Updated project description\"\n"
                "  ]\n"
                "}\n\n"
                "--------------------------------\n"
                "INPUTS\n"
                "initial_ats_score: {{initial_ats_score}}\n"
                "missing_keywords: {{missing_keywords}}\n"
                "matched_keywords: {{matched_keywords}}\n"
                "justification: {{justification}}\n"
                "job_description: {{job_description}}\n"
                "old_resume_code (LaTeX): {{resume_text}}"
            )
        }
        
        db = SessionLocal()
        try:
            row = db.query(SystemState).filter(SystemState.key == "ats_prompts").first()
            prompts = row.value if row and row.value else {}
            # Overlay defaults for any missing keys
            for k, v in defaults.items():
                if k not in prompts or not prompts[k]:
                    prompts[k] = v
            return prompts
        finally:
            db.close()

    def set_ats_prompts(self, prompts: dict) -> None:
        """Persists custom ATS prompts to SystemState DB."""
        from src.db import SessionLocal
        from src.models import SystemState
        from datetime import datetime
        db = SessionLocal()
        try:
            row = db.query(SystemState).filter(SystemState.key == "ats_prompts").first()
            if row:
                row.value = prompts
                row.updated_at = datetime.utcnow()
            else:
                db.add(SystemState(key="ats_prompts", value=prompts))
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    # =========================================================================
    # Workflow Assignments → DB
    # =========================================================================

    def get_workflow_links(self, user_id: Optional[str] = None) -> list:
        """Returns the list of workflow-to-LLM assignments from the DB."""
        from src.db import SessionLocal
        from src.models import WorkflowLLMLink
        db = SessionLocal()
        try:
            query = db.query(WorkflowLLMLink)
            if user_id:
                query = query.filter(WorkflowLLMLink.user_id == user_id)
            links = query.all()
            return [
                {
                    "id": l.id,
                    "user_id": l.user_id,
                    "workflow_id": l.workflow_id,
                    "llm_config_id": l.llm_config_id,
                }
                for l in links
            ]
        finally:
            db.close()

    def set_workflow_link(self, user_id: str, workflow_id: str, llm_config_id: str) -> dict:
        """Assigns an LLM config to a workflow step for a specific user (upsert)."""
        from src.db import SessionLocal
        from src.models import WorkflowLLMLink
        db = SessionLocal()
        try:
            link = (
                db.query(WorkflowLLMLink)
                .filter(WorkflowLLMLink.user_id == user_id, WorkflowLLMLink.workflow_id == workflow_id)
                .first()
            )
            if link:
                link.llm_config_id = llm_config_id
            else:
                link = WorkflowLLMLink(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    workflow_id=workflow_id,
                    llm_config_id=llm_config_id,
                )
                db.add(link)
            db.commit()
            db.refresh(link)
            return {
                "id": link.id,
                "user_id": link.user_id,
                "workflow_id": link.workflow_id,
                "llm_config_id": link.llm_config_id,
            }
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    # =========================================================================
    # Infrastructure Config (development.json — not user data)
    # =========================================================================

    def get_api_key(self, key_name: str) -> Optional[str]:
        """Returns an infrastructure API key from development.json."""
        key = key_name.lower()
        return self.global_config.get(key) or self.global_config.get(key_name)

    def get_global_setting(self, key: str, default: Any = None) -> Any:
        return self.global_config.get(key, default)

    # =========================================================================
    # One-time Migration: config.json → DB
    # =========================================================================

    def migrate_legacy_llm_configs(self, user_id: Optional[str] = None) -> int:
        """
        One-time migration: reads user_llm_configs from data/config.json and
        inserts any not already present in the DB (matched by id).
        Returns the number of rows inserted.
        
        Called from server.py lifespan on startup. Safe to call repeatedly.
        """
        legacy_path = os.path.join(DATA_DIR, "config.json")
        if not os.path.exists(legacy_path):
            return 0

        try:
            with open(legacy_path, "r") as f:
                data = json.load(f)
        except Exception:
            logger.warning("Could not read legacy config.json for migration.")
            return 0

        legacy_configs = data.get("user_llm_configs", [])
        if not legacy_configs:
            return 0

        from src.db import SessionLocal
        from src.models import LLMConfig
        db = SessionLocal()
        try:
            inserted = 0
            for cfg in legacy_configs:
                cfg_id = cfg.get("id")
                if not cfg_id:
                    continue
                if db.query(LLMConfig).filter(LLMConfig.id == cfg_id).first():
                    continue  # Already migrated
                db.add(LLMConfig(
                    id=cfg_id,
                    user_id=user_id,  # May be None for legacy global configs
                    sdk_id=cfg.get("sdk_id", "unknown"),
                    name=cfg.get("name", "Migrated Config"),
                    api_key=cfg.get("api_key", ""),
                    plan_type=cfg.get("plan_type", "free"),
                    daily_token_limit=cfg.get("daily_token_limit") or 0,
                    tokens_used_today=cfg.get("tokens_used_today") or 0,
                ))
                inserted += 1
            if inserted:
                db.commit()
                logger.info(f"Migrated {inserted} legacy LLM config(s) from config.json to DB.")
            return inserted
        except Exception:
            db.rollback()
            logger.exception("Failed to migrate legacy LLM configs.")
            return 0
        finally:
            db.close()
