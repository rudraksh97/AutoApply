"""
Resume building and ATS optimization for the AutoApply application.

This module handles:
- LaTeX template rendering with Jinja2
- LLM-based resume tailoring for ATS optimization
- PDF compilation via pdflatex
"""

import json
import logging
import os
import shutil
import subprocess
import traceback
from datetime import datetime
from typing import List, Optional, Tuple
from pydantic import BaseModel

import jinja2
from src.prompts import RESUME_OPTIMIZER_PROMPT_TEMPLATE
from src.schemas import (
    ATSScoreOutput,
    TailoredResumeOutput,
    JustificationDetail
)

logger = logging.getLogger(__name__)


# =============================================================================
# Resume Builder
# =============================================================================

class ResumeBuilder:
    """Handles creation of tailored resume PDFs."""

    def __init__(
        self,
        base_template_path: str = "data/resumes/templates/resume_base.tex",
        output_dir: str = "data/generated_resumes",
        user_email: str = None,
        user_id: str = None,
    ):
        self.user_id = user_id
        # Per-user directory: data/{user_email}/...
        if user_email:
            self.base_user_data = os.path.join("data", user_email)
            self.output_dir = os.path.join(self.base_user_data, "generated_resumes")
            self.base_template_path = base_template_path
        else:
            self.base_user_data = "data"
            self.output_dir = output_dir
            self.base_template_path = base_template_path

        self._ensure_directories()
        self._setup_jinja_env()

    def _ensure_directories(self):
        """Create required directories."""
        os.makedirs(self.output_dir, exist_ok=True)
        template_dir = os.path.dirname(self.base_template_path)
        if template_dir:
            os.makedirs(template_dir, exist_ok=True)

    def _setup_jinja_env(self):
        """Configure Jinja2 environment for LaTeX templates."""
        self.env = jinja2.Environment(
            block_start_string='\\VAR{BLOCK',
            block_end_string='\\VAR{ENDBLOCK}',
            variable_start_string='\\VAR{',
            variable_end_string='}',
            comment_start_string='\\VAR{COMMENT',
            comment_end_string='\\VAR{ENDCOMMENT}',
            line_statement_prefix='%%JINJA_VAR%%',
            line_comment_prefix='%%JINJA_COMMENT%%',
            trim_blocks=True,
            autoescape=False,
            loader=jinja2.FileSystemLoader(os.path.dirname(self.base_template_path))
        )

    # -------------------------------------------------------------------------
    # ATS Score Calculation
    # -------------------------------------------------------------------------

    async def calculate_ats_score(self, job_description: str, resume_text: str, user_id: Optional[str] = None) -> dict:
        """Calculate ATS compatibility score using structured LLM output."""
        from src.config import ConfigManager
        
        config = ConfigManager()
        score_prompt = config.get_ats_prompts().get("calculate_score")

        formatted_prompt = score_prompt.replace("{{job_description}}", job_description)\
                                        .replace("{{resume_text}}", resume_text)

        try:
            from src.llm_factory import LLMFactory
            from src.token_manager import TokenManager

            llm = LLMFactory.get_llm_for_step("step_ats_scoring", user_id=user_id)
            
            # Deduct credits
            config_id = getattr(llm, "config_id", None)

            if config_id:
                TokenManager().deduct_credits(config_id, len(formatted_prompt) * 2)

            return await self._invoke_ats_score(llm, formatted_prompt)
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"Error calculating ATS score: {e}\nStack trace:\n{tb}")
            return {"score": 0, "justification": f"Error: {e}", "missing_keywords": []}

    async def _invoke_ats_score(self, llm, prompt: str) -> dict:
        """Invoke LLM for ATS score with structured output."""
        logger.info("Using structured output for ATS score")
        chain = llm.with_structured_output(ATSScoreOutput)
        result = await chain.ainvoke(prompt)

        # Handle both Pydantic model and dict
        if hasattr(result, "model_dump"):
            data = result.model_dump()
        else:
            data = result

        justification = data.get("justification", {})
        just_str = json.dumps(justification) if isinstance(justification, dict) else str(justification)

        return {
            "missing_keywords": data.get("missing_keywords", []),
            "matched_keywords": data.get("matched_keywords", []),
            "score": data.get("score", 0),
            "justification": just_str
        }

    # -------------------------------------------------------------------------
    # LaTeX Tailoring
    # -------------------------------------------------------------------------

    async def get_formatted_prompt(
        self,
        latex_template: str,
        job_description: str,
        user_profile_text: str,
        custom_prompt: str = None,
        ats_context: dict = None
    ) -> str:
        """
        Returns the formatted prompt that would be sent to the LLM.
        """
        return self._build_tailoring_prompt(
            latex_template, job_description, user_profile_text, custom_prompt, ats_context
        )

    async def tailor_latex(
        self,
        latex_template: str,
        job_description: str,
        user_profile_text: str,
        custom_prompt: str = None,
        ats_context: dict = None,
        user_id: Optional[str] = None
    ) -> dict:
        """Tailor LaTeX template using LLM with ATS context."""
        prompt = self._build_tailoring_prompt(
            latex_template, job_description, user_profile_text, custom_prompt, ats_context
        )
        missing_str = self._format_keywords(ats_context, "missing_keywords")

        try:
            from src.llm_factory import LLMFactory
            from src.token_manager import TokenManager

            llm = LLMFactory.get_llm_for_step("step_resume_tailoring", user_id=user_id)
            
            # Deduct credits
            config_id = getattr(llm, "config_id", None)

            if config_id:
                TokenManager().deduct_credits(config_id, len(prompt) * 2)

            return await self._invoke_tailoring(llm, prompt, latex_template, missing_str)
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"Error tailoring resume: {e}\nStack trace:\n{tb}")
            return {"latex": latex_template, "keywords": "", "summary": f"Error: {e}"}

    def _build_tailoring_prompt(
        self,
        latex_template: str,
        job_description: str,
        user_profile_text: str,
        custom_prompt: str,
        ats_context: dict
    ) -> str:
        """Build the prompt for resume tailoring."""
        if not custom_prompt:
            from src.config import ConfigManager
            custom_prompt = ConfigManager().get_ats_prompts().get("tailor_resume")

        missing_str = self._format_keywords(ats_context, "missing_keywords")
        matched_str = self._format_keywords(ats_context, "matched_keywords")
        initial_score = ats_context.get("score", 0) if ats_context else 0
        justification = ats_context.get("justification", "") if ats_context else ""

        prompt = custom_prompt.replace("{{job_description}}", job_description)\
                              .replace("{{old_resume_code}}", latex_template)\
                              .replace("{{resume_text}}", latex_template)\
                              .replace("{{missing_keywords}}", missing_str)\
                              .replace("{{matched_keywords}}", matched_str)\
                              .replace("{{initial_ats_score}}", str(initial_score))\
                              .replace("{{justification}}", justification)

        if "{{user_profile}}" in custom_prompt:
            prompt = prompt.replace("{{user_profile}}", user_profile_text)
        elif "User Profile" not in prompt:
            prompt += f"\n\n--- USER PROFILE ---\n{user_profile_text}"

        return prompt

    def _format_keywords(self, ats_context: dict, key: str) -> str:
        """Format keywords list as comma-separated string."""
        if not ats_context:
            return "None"
        keywords = ats_context.get(key, [])
        return ", ".join(keywords) if keywords else "None"

    async def _invoke_tailoring(self, llm, prompt: str, fallback_latex: str, missing_str: str) -> dict:
        """Invoke LLM for resume tailoring."""
        logger.info("Using structured output for resume tailoring")
        chain = llm.with_structured_output(TailoredResumeOutput)
        result = await chain.ainvoke(prompt)

        if hasattr(result, "model_dump"):
            data = result.model_dump()
        else:
            data = result

        return {
            "latex": data.get("new_latex_code", fallback_latex),
            "final_score": data.get("final_score", 0),
            "keywords": missing_str,
            "summary": "; ".join(data.get("summary", []))
        }

    # -------------------------------------------------------------------------
    # Legacy Content Generation
    # -------------------------------------------------------------------------

    async def generate_resume_content(self, job_description: str, _current_resume_info: str) -> dict:
        """Extract keywords from job description (legacy method)."""
        from src.llm_factory import LLMFactory
        llm = LLMFactory.get_llm_for_step("step_resume_tailoring") # Reuse tailoring step
        
        # Define a temporary schema for this legacy call to use with_structured_output
        class SkillsList(BaseModel):
            skills_list: List[str]

        structured_llm = llm.with_structured_output(SkillsList)
        result = await structured_llm.ainvoke(RESUME_OPTIMIZER_PROMPT_TEMPLATE.format(job_description=job_description))
        
        if hasattr(result, "model_dump"):
            return result.model_dump()
        return result

    # -------------------------------------------------------------------------
    # LaTeX Rendering
    # -------------------------------------------------------------------------

    def render_tex(
        self,
        context: dict,
        filename: str,
        template_path: str = None,
        raw_latex: str = None
    ) -> str:
        """Render Jinja2 LaTeX template or save raw LaTeX. Returns tex path."""
        tex_path = os.path.join(self.output_dir, f"{filename}.tex")

        if raw_latex:
            with open(tex_path, 'w', encoding='utf-8') as f:
                f.write(raw_latex)
            return tex_path

        template = self._load_template(template_path)

        if isinstance(context.get('skills_list'), list):
            context['skills_list'] = ', '.join(context['skills_list'])

        rendered = template.render(**context)

        with open(tex_path, 'w', encoding='utf-8') as f:
            f.write(rendered)

        return tex_path

    def _load_template(self, template_path: str = None) -> jinja2.Template:
        """Load Jinja2 template from path or default."""
        if template_path and os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                return self.env.from_string(f.read())

        template_name = os.path.basename(self.base_template_path)
        return self.env.get_template(template_name)

    # -------------------------------------------------------------------------
    # PDF Compilation
    # -------------------------------------------------------------------------

    async def compile_pdf(self, tex_path: str) -> str:
        """Compile LaTeX to PDF using pdflatex. Returns PDF path."""
        import asyncio

        await self._check_pdflatex()

        tex_dir = os.path.abspath(os.path.dirname(tex_path))
        tex_filename = os.path.basename(tex_path)

        await asyncio.to_thread(
            subprocess.run,
            ["pdflatex", "-interaction=nonstopmode", "-output-directory", tex_dir, tex_filename],
            cwd=tex_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        pdf_path = os.path.join(tex_dir, tex_filename.replace('.tex', '.pdf'))
        self._verify_pdf_created(pdf_path, tex_dir, tex_filename)
        self._cleanup_aux_files(tex_dir, tex_filename)

        return pdf_path

    async def _check_pdflatex(self):
        """Verify pdflatex is available."""
        import asyncio
        try:
            await asyncio.to_thread(
                subprocess.run,
                ["pdflatex", "--version"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            raise RuntimeError("pdflatex not available. Install a TeX distribution.") from e

    def _verify_pdf_created(self, pdf_path: str, tex_dir: str, tex_filename: str):
        """Verify PDF was created, raise with log excerpt if not."""
        if os.path.exists(pdf_path):
            return

        log_path = os.path.join(tex_dir, tex_filename.replace('.tex', '.log'))
        log_content = "No log file found."

        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                log_content = f.read()[-2000:]

        raise RuntimeError(f"LaTeX compilation failed. Log excerpt:\n{log_content}")

    def _cleanup_aux_files(self, tex_dir: str, tex_filename: str):
        """Remove auxiliary LaTeX files."""
        for ext in ['.aux', '.log', '.out']:
            aux_path = os.path.join(tex_dir, tex_filename.replace('.tex', ext))
            if os.path.exists(aux_path):
                os.remove(aux_path)

    # -------------------------------------------------------------------------
    # Main Build Orchestration
    # -------------------------------------------------------------------------

    async def build(
        self,
        job_description: str,
        user_profile_text: str,
        job_id: str,
        template_path: str = None,
        tailoring_prompt: str = None,
        version: str = "v1",
        version_id: str = None,
        draft_id: str = None,
        draft_manager=None,
        ats_context: dict = None,
        job_manager=None,
        job_url: str = None,
        raw_latex: str = None,
        user_id: str = None
    ) -> Tuple[str, str, str, str]:
        """
        Orchestrate resume tailoring and PDF generation.

        Returns:
            Tuple of (pdf_path, tex_path, keywords_added, changes_summary)
        """
        paths = self._setup_build_paths(job_id, version)

        try:
            with open(paths["log"], 'a', encoding='utf-8') as log_file:
                log = self._create_logger(log_file)

                log(f"Starting build for {paths['filename']}...")

                # Tailor and compile
                metadata = await self._tailor_resume(
                    paths, job_description, user_profile_text,
                    template_path, tailoring_prompt, ats_context, log,
                    raw_latex=raw_latex,
                    user_id=user_id or self.user_id
                )

                await self._compile_resume(paths, log)

                # Update database
                self._update_build_status(
                    draft_manager, version_id, paths["pdf"],
                    metadata, log
                )

                return paths["pdf"], paths["tex"], metadata["keywords"], metadata["summary"]

        except Exception as e:
            self._handle_build_failure(
                e, draft_manager, version_id, draft_id, job_manager, job_url
            )
            raise

    def _setup_build_paths(self, job_id: str, version: str) -> dict:
        """Setup and create directories for build artifacts."""
        gen_dir = os.path.join(self.output_dir, str(job_id), version)
        tex_dir = os.path.join(self.base_user_data, "tex_resumes", str(job_id), version)
        log_dir = os.path.join(self.base_user_data, "logs", str(job_id))

        for d in [gen_dir, tex_dir, log_dir]:
            os.makedirs(d, exist_ok=True)

        filename = f"Resume_{job_id}_{version}"

        return {
            "gen_dir": gen_dir,
            "tex_dir": tex_dir,
            "log_dir": log_dir,
            "filename": filename,
            "tex": os.path.join(tex_dir, f"{filename}.tex"),
            "pdf": os.path.join(gen_dir, f"{filename}.pdf"),
            "log": os.path.join(log_dir, f"{version}.log")
        }

    def _create_logger(self, log_file):
        """Create a logging function that writes to both console and file."""
        def log(msg: str):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            formatted = f"[{timestamp}] {msg}"
            print(formatted)
            log_file.write(formatted + "\n")
            log_file.flush()
        return log

    async def _tailor_resume(
        self,
        paths: dict,
        job_description: str,
        user_profile_text: str,
        template_path: str,
        tailoring_prompt: str,
        ats_context: dict,
        log,
        raw_latex: str = None,
        user_id: str = None
    ) -> dict:
        """Tailor resume content and write to tex file."""
        metadata = {"keywords": "", "summary": "", "score": 0}

        target_template = template_path or self.base_template_path

        with open(target_template, 'r', encoding='utf-8') as f:
            template_content = f.read()

        if raw_latex:
            log("Using provided raw LaTeX content...")
            latex_content = raw_latex
            metadata["keywords"] = "Manual Edit"
            metadata["summary"] = "User provided LaTeX manually"
            metadata["score"] = ats_context.get("score", 0) if ats_context else 0

        elif tailoring_prompt:
            log("Applying LLM-based LaTeX tailoring...")
            result = await self.tailor_latex(
                template_content, job_description, user_profile_text,
                custom_prompt=tailoring_prompt, ats_context=ats_context,
                user_id=user_id
            )
            latex_content = result["latex"]
            metadata["keywords"] = result["keywords"]
            metadata["summary"] = result["summary"]
            metadata["score"] = result.get("final_score", 0)
        else:
            log("Using legacy keyword extraction...")
            extracted = await self.generate_resume_content(job_description, user_profile_text)
            context = {
                "skills_list": extracted.get("skills_list", []),
                "summary": "Tailored Professional",
                "experience": "Detailed Experience",
                "education": "University Degree"
            }
            template = self.env.from_string(template_content)
            latex_content = template.render(**context)

        with open(paths["tex"], 'w', encoding='utf-8') as f:
            f.write(latex_content)

        return metadata

    async def _compile_resume(self, paths: dict, log):
        """Compile LaTeX to PDF and move to final location."""
        log("Compiling PDF...")

        temp_pdf = await self.compile_pdf(paths["tex"])

        if os.path.exists(temp_pdf) and os.path.abspath(temp_pdf) != os.path.abspath(paths["pdf"]):
            shutil.move(temp_pdf, paths["pdf"])

        log(f"PDF compiled: {paths['pdf']}")

    def _update_build_status(
        self,
        draft_manager,
        version_id: str,
        pdf_path: str,
        metadata: dict,
        log
    ):
        """Update draft manager with build results."""
        if not draft_manager or not version_id:
            return

        update_kwargs = {
            "status": "COMPLETED",
            "pdf_path": pdf_path,
            "keywords_added": metadata["keywords"],
            "changes_summary": metadata["summary"]
        }

        if metadata.get("score", 0) > 0:
            update_kwargs["ats_score"] = metadata["score"]

        draft_manager.update_resume_version(version_id, **update_kwargs)
        log("Build COMPLETED")

    def _handle_build_failure(
        self,
        error: Exception,
        draft_manager,
        version_id: str,
        draft_id: str,
        job_manager,
        job_url: str
    ):
        """Handle build failure by updating statuses."""
        logger.error(f"Build failed: {error}\n{traceback.format_exc()}")

        if draft_manager and version_id:
            draft_manager.update_resume_version(version_id, status="FAILED")

        if draft_manager and draft_id:
            from api.schemas.form_state import DraftStatus
            draft_manager.update_status(draft_id, DraftStatus.FAILED)

        if job_manager and job_url:
            job_manager.update_job(job_url, status="Draft Failed", error_message=str(error))


if __name__ == "__main__":
    try:
        subprocess.run(["pdflatex", "--version"], check=True, stdout=subprocess.PIPE)
        print("pdflatex found.")
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("pdflatex NOT found. Install a TeX distribution.")
