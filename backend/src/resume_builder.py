import os
import subprocess
import jinja2
import logging
import json
from datetime import datetime
from typing import List, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from dotenv import load_dotenv
from src.prompts import RESUME_OPTIMIZER_PROMPT_TEMPLATE

load_dotenv()

logger = logging.getLogger(__name__)

class ResumeBuilder:
    """
    Handles the creation of tailored resume PDFs.

    It uses an LLM to identify key skills from a job description and then
    uses Jinja2 to render a LaTeX template with those skills, finally
    compiling it with pdflatex.
    """
    def __init__(self, base_template_path="data/resumes/templates/resume_base.tex", output_dir="data/generated_resumes"):
        """
        Initializes the resume builder with template and output paths.

        Args:
            base_template_path (str): Path to the .tex template file.
            output_dir (str): Directory where generated resumes will be stored.
        """
        self.base_template_path = base_template_path
        self.output_dir = output_dir
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Ensure template directory exists
        template_dir = os.path.dirname(base_template_path)
        if template_dir and not os.path.exists(template_dir):
            os.makedirs(template_dir)

        # Configure Jinja2 for LaTeX
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
            loader=jinja2.FileSystemLoader(os.path.dirname(base_template_path))
        )

        self.llm = ChatOpenAI(
            model="meta-llama/llama-3.3-70b-instruct:free", # or appropriate model on OpenRouter
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1"
        )

    def generate_resume_content(self, job_description, current_resume_info):
        """
        Uses an LLM to extract relevant keywords from a job description.
        (Legacy method for skills_list injection)
        """
        prompt = ChatPromptTemplate.from_template(RESUME_OPTIMIZER_PROMPT_TEMPLATE)
        chain = prompt | self.llm | JsonOutputParser()
        return chain.invoke({"job_description": job_description})

    def tailor_latex(self, latex_template: str, job_description: str, user_profile_text: str, custom_prompt: str = None, ats_context: dict = None):
        """
        Tailors the LaTeX template using structured output with full ATS context.
        ats_context should contain: missing_keywords, matched_keywords, score, justification
        """
        from pydantic import BaseModel, Field
        from typing import List

        # New output schema as requested
        class TailoredResumeOutput(BaseModel):
            final_score: int = Field(description="Simulated ATS score between 0 and 100")
            new_latex_code: str = Field(description="The FULL optimized LaTeX resume code")
            summary: List[str] = Field(description="List of changes made, e.g. added skills, modified bullets")

        if not custom_prompt:
            from src.config import ConfigManager
            config_manager = ConfigManager()
            prompts = config_manager.get_ats_prompts()
            custom_prompt = prompts.get("tailor_resume")

        # Prepare context variables
        missing_keywords = ats_context.get("missing_keywords", []) if ats_context else []
        matched_keywords = ats_context.get("matched_keywords", []) if ats_context else []
        initial_score = ats_context.get("score", 0) if ats_context else 0
        justification = ats_context.get("justification", "") if ats_context else ""

        missing_str = ", ".join(missing_keywords) if missing_keywords else "None"
        matched_str = ", ".join(matched_keywords) if matched_keywords else "None"

        # Replace placeholders
        formatted_prompt = custom_prompt.replace("{{job_description}}", job_description)\
                                        .replace("{{old_resume_code}}", latex_template)\
                                        .replace("{{resume_text}}", latex_template)\
                                        .replace("{{missing_keywords}}", missing_str)\
                                        .replace("{{matched_keywords}}", matched_str)\
                                        .replace("{{initial_ats_score}}", str(initial_score))\
                                        .replace("{{justification}}", justification)
        
        # Add user profile context if needed (though new prompt might not need it explicitly if strict)
        if "{{user_profile}}" in custom_prompt:
             formatted_prompt = formatted_prompt.replace("{{user_profile}}", user_profile_text)
        elif "User Profile" not in formatted_prompt:
             formatted_prompt += f"\n\n--- ADDITIONAL CONTEXT: USER PROFILE ---\n{user_profile_text}"

        try:
             if hasattr(self.llm, "with_structured_output"):
                chain = self.llm.with_structured_output(TailoredResumeOutput)
                result = chain.invoke(formatted_prompt)
                return {
                    "latex": result.new_latex_code,
                    "final_score": result.final_score,
                    "keywords": missing_str,
                    "summary": "; ".join(result.summary)
                }
             else:
                from langchain_core.output_parsers import JsonOutputParser
                parser = JsonOutputParser(pydantic_object=TailoredResumeOutput)
                format_instructions = parser.get_format_instructions()
                
                chain = self.llm | parser
                result = chain.invoke(f"{formatted_prompt}\n\n{format_instructions}")
                return {
                    "latex": result.get("new_latex_code", latex_template),
                    "final_score": result.get("final_score", 0),
                    "keywords": missing_str,
                    "summary": "; ".join(result.get("summary", []))
                }
        except Exception as e:
            print(f"Error tailoring resume: {e}")
            return {"latex": latex_template, "keywords": "", "summary": f"Error: {e}"}

    def render_tex(self, context, filename, template_path=None, raw_latex=None):
        """
        Renders the Jinja2 LaTeX template OR saves raw LaTeX output.
        """
        tex_path = os.path.join(self.output_dir, f"{filename}.tex")
        
        if raw_latex:
            with open(tex_path, 'w', encoding='utf-8') as f:
                f.write(raw_latex)
            return tex_path

        if template_path and os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
            template = self.env.from_string(template_content)
        else:
            template_name = os.path.basename(self.base_template_path)
            template = self.env.get_template(template_name)
        
        # Convert skills_list to a comma-separated string if it's a list
        if isinstance(context.get('skills_list'), list):
            context['skills_list'] = ', '.join(context['skills_list'])
        
        rendered = template.render(**context)
        
        with open(tex_path, 'w', encoding='utf-8') as f:
            f.write(rendered)
        
        return tex_path

    def compile_pdf(self, tex_path):
        # ... (same as before)
        # Check if pdflatex is available
        try:
            subprocess.run(["pdflatex", "--version"], check=True, 
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            raise RuntimeError("pdflatex is not available. Please install a TeX distribution.") from e
        
        try:
            # Run pdflatex
            tex_dir = os.path.abspath(os.path.dirname(tex_path))
            tex_filename = os.path.basename(tex_path)
            
            result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-output-directory", tex_dir, tex_filename],
            cwd=tex_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"pdflatex compilation failed: {e.stderr.decode('utf-8')}")
        
        try:
            # Check for compilation errors
            pdf_path = os.path.join(tex_dir, tex_filename.replace('.tex', '.pdf'))
            log_path = os.path.join(tex_dir, tex_filename.replace('.tex', '.log'))
            
            if not os.path.exists(pdf_path):
                log_content = "No log file found."
                if os.path.exists(log_path):
                    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                        log_content = f.read()[-2000:]
                else:
                    raise RuntimeError(f"LaTeX compilation failed (no PDF). Log excerpt:\n{log_content}")
            
            # Clean up auxiliary files
            for ext in ['.aux', '.log', '.out']:
                aux_file = os.path.join(tex_dir, tex_filename.replace('.tex', ext))
                if os.path.exists(aux_file):
                    os.remove(aux_file)
            
            return pdf_path
        except Exception as e:
            print(f"pdflatex module compilation error: {e}")
            raise

    def calculate_ats_score(self, job_description: str, resume_text: str):
        """
        Calculates an ATS score using structured output.
        """
        from src.config import ConfigManager
        from pydantic import BaseModel, Field
        from typing import List
        import json

        class JustificationDetail(BaseModel):
            keyword_match: str = Field(description="Analysis of matched and missing keywords")
            skill_depth: str = Field(description="Evaluation of skill proficiency and relevance")
            role_fit: str = Field(description="Assessment of overall fit for the specific role")
            experience_relevance: str = Field(description="How well past experience aligns with requirements")
            education_fit: str = Field(description="Alignment of education and certifications")
            parsing_quality: str = Field(description="Quality of content structure and readability")

        class ATSScoreOutput(BaseModel):
            missing_keywords: List[str] = Field(description="List of keywords present in the job description but missing from the resume")
            matched_keywords: List[str] = Field(description="List of keywords present in both the job description and the resume")
            score: int = Field(description="ATS score from 0 to 100")
            justification: JustificationDetail = Field(description="Detailed breakdown of the score justification")

        config_manager = ConfigManager()
        prompts = config_manager.get_ats_prompts()
        score_prompt = prompts.get("calculate_score")

        # Replace placeholders
        formatted_prompt = score_prompt.replace("{{job_description}}", job_description)\
                                       .replace("{{resume_text}}", resume_text)

        try:
            # Try structured output if available (requires tool calling model)
            if hasattr(self.llm, "with_structured_output"):
                logger.info("Using structured output for ATS score calculation")
                chain = self.llm.with_structured_output(ATSScoreOutput)
                result = chain.invoke(formatted_prompt)
                
                # Serialize detailed justification to string for DB storage
                justification_json = result.justification.json()
                
                return {
                    "missing_keywords": result.missing_keywords,
                    "matched_keywords": result.matched_keywords,
                    "score": result.score,
                    "justification": justification_json # Store as JSON string
                }
            else:
                # Fallback to JSON parsing
                from langchain_core.output_parsers import JsonOutputParser
                parser = JsonOutputParser(pydantic_object=ATSScoreOutput)
                format_instructions = parser.get_format_instructions()
                
                chain = self.llm | parser
                result = chain.invoke(f"{formatted_prompt}\n\n{format_instructions}")
                
                # Manual fallback serialization if dict returned
                just_data = result.get("justification", {})
                if isinstance(just_data, dict):
                    just_str = json.dumps(just_data)
                else:
                    just_str = str(just_data)

                return {
                    "missing_keywords": result.get("missing_keywords", []),
                    "matched_keywords": result.get("matched_keywords", []),
                    "score": result.get("score", 0),
                    "justification": just_str
                }
                
        except Exception as e:
            print(f"Error calculating ATS score: {e}")
            return {"score": 0, "justification": f"Error: {e}", "missing_keywords": []}

    def build(self, job_description, user_profile_text, job_id, template_path=None, tailoring_prompt=None, version="v1", version_id=None, draft_id=None, draft_manager=None, ats_context=None, job_manager=None, job_url=None):
        """
        Orchestrates the tailoring. If draft_manager and version_id are provided, 
        both tailoring and compilation happen in a separate thread.
        Returns (pdf_path, tex_path, keywords_added, changes_summary)
        """
        # Create versioned directories paths
        gen_dir = os.path.join("data", "generated_resumes", str(job_id), version)
        tex_dir = os.path.join("data", "tex_resumes", str(job_id), version)
        log_dir = os.path.join("data", "logs", str(job_id))
        
        filename = f"Resume_{job_id}_{version}"
        tex_path = os.path.join(tex_dir, f"{filename}.tex")
        pdf_path = os.path.join(gen_dir, f"{filename}.pdf")
        log_path = os.path.join(log_dir, f"{version}.log")
        
        # Use these potentially updated values synchronously
        result_metadata = {"keywords": "", "summary": ""}
        predicted_score = 0
        
        try:
            os.makedirs(log_dir, exist_ok=True)
            os.makedirs(gen_dir, exist_ok=True)
            os.makedirs(tex_dir, exist_ok=True)
            
            with open(log_path, 'a', encoding='utf-8') as log_file:
                def log(msg):
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    formatted_msg = f"[{timestamp}] {msg}"
                    print(formatted_msg)
                    log_file.write(formatted_msg + "\n")
                    log_file.flush()

                log(f"Synchronous Build: Starting process for {filename}...")
                
                try:
                    # 1. Tailor LaTeX
                    if tailoring_prompt:
                        log(f"Synchronous Build: Applying deep LaTeX tailoring for {filename}...")
                        target_template = template_path if template_path else self.base_template_path
                        with open(target_template, 'r', encoding='utf-8') as f:
                            template_content = f.read()
                        
                        tailored_data = self.tailor_latex(template_content, job_description, user_profile_text, custom_prompt=tailoring_prompt, ats_context=ats_context)
                        tailored_latex = tailored_data["latex"]
                        result_metadata["keywords"] = tailored_data["keywords"]
                        result_metadata["summary"] = tailored_data["summary"]
                        # Capture the predicted final score if available
                        predicted_score = tailored_data.get("final_score", 0)
                        
                        with open(tex_path, 'w', encoding='utf-8') as f:
                            f.write(tailored_latex)
                    else:
                        # Fallback to legacy
                        log(f"Synchronous Build: Extracting keywords for {filename}...")
                        extracted_data = self.generate_resume_content(job_description, user_profile_text)
                        context = {
                            "skills_list": extracted_data.get("skills_list", []),
                            "summary": "Tailored Professional",
                            "experience": "Detailed Experience",
                            "education": "University Degree"
                        }
                        target_template = template_path if template_path else self.base_template_path
                        with open(target_template, 'r', encoding='utf-8') as f:
                            template_content = f.read()
                        template = self.env.from_string(template_content)
                        rendered = template.render(**context)
                        
                        with open(tex_path, 'w', encoding='utf-8') as f:
                            f.write(rendered)

                    # 2. Compile PDF
                    log(f"Synchronous Build: Compiling PDF for {filename}...")
                    try:
                        temp_pdf = self.compile_pdf(tex_path)
                        
                        if os.path.exists(temp_pdf) and os.path.abspath(temp_pdf) != os.path.abspath(pdf_path):
                            import shutil
                            shutil.move(temp_pdf, pdf_path)
                        log(f"Synchronous Build: PDF compiled successfully: {pdf_path}")
                    except Exception as compile_err:
                        log(f"Synchronous Build: LaTeX compilation failed: {compile_err}")
                        raise

                    # 3. Update Database
                    if draft_manager and version_id:
                        update_kwargs = {
                            "status": "COMPLETED",
                            "pdf_path": pdf_path,
                            "keywords_added": result_metadata["keywords"],
                            "changes_summary": result_metadata["summary"]
                        }
                        if predicted_score > 0:
                            update_kwargs["ats_score"] = predicted_score
                            
                        draft_manager.update_resume_version(version_id, **update_kwargs)
                        log(f"Synchronous Build: PDF for {filename} COMPLETED")
                    
                    return pdf_path, tex_path, result_metadata["keywords"], result_metadata["summary"]

                except Exception as e:
                    import traceback
                    err_traceback = traceback.format_exc()
                    log(f"Synchronous Build: PDF for {filename} FAILED: {e}")
                    log(f"Traceback:\n{err_traceback}")
                    
                    if draft_manager and version_id:
                        draft_manager.update_resume_version(version_id, status="FAILED")
                    if job_manager and job_url:
                        job_manager.update_job(job_url, status="Draft Failed", error_message=str(e))
                    if draft_manager and draft_id:
                            from api.schemas.form_state import DraftStatus
                            draft_manager.update_status(draft_id, DraftStatus.FAILED)
                    raise e
        except Exception as outer_e:
            print(f"CRITICAL: Synchronous build failed: {outer_e}")
            if job_manager and job_url:
                job_manager.update_job(job_url, status="Critical Error", error_message=str(outer_e))
            raise outer_e


if __name__ == "__main__":
    # Test stub
    builder = ResumeBuilder()
    # Base data
    try:
        # Check if pdflatex exists
        subprocess.run(["pdflatex", "--version"], check=True, stdout=subprocess.PIPE)
        print("pdflatex found.")
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("pdflatex NOT found. Please install TeX distribution.")
