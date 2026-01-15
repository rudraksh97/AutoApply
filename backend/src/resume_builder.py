import os
import subprocess
import jinja2
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from dotenv import load_dotenv

load_dotenv()

"""
Tailored resume generation using LaTeX and LLMs.

This module provides the `ResumeBuilder` class, which extracts relevant 
keywords from job descriptions, injects them into a Jinja2-enabled 
LaTeX template, and compiles the result into a PDF.
"""

import os
import subprocess
import jinja2
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from dotenv import load_dotenv
from src.prompts import RESUME_OPTIMIZER_PROMPT_TEMPLATE

load_dotenv()

class ResumeBuilder:
    """
    Handles the creation of tailored resume PDFs.

    It uses an LLM to identify key skills from a job description and then
    uses Jinja2 to render a LaTeX template with those skills, finally
    compiling it with pdflatex.
    """
    def __init__(self, base_template_path="data/tex_resumes/resume_base.tex", output_dir="data/generated_resumes"):
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

    def tailor_latex(self, latex_template: str, job_description: str, user_profile_text: str, custom_prompt: str = None):
        """
        Tailors the entire LaTeX template using an LLM.
        This follows the 'ATS folder flow' logic.
        """
        if not custom_prompt:
            # Fallback to a default if not passed (though services.py should pass it)
            custom_prompt = (
                "You are a professional career assistant and LaTeX expert. "
                "Rewrite the provided LaTeX template COMPLETELY to be optimized for the Job Description. "
                "Keep the EXACT LaTeX structure and packages. Return ONLY raw LaTeX code."
            )

        system_prompt = f"""
{custom_prompt}

--- User Profile ---
{user_profile_text}
"""
        user_prompt = f"""
Optimize this LaTeX template for the following Job Description:

--- JOB DESCRIPTION ---
{job_description}

--- LATEX TEMPLATE ---
{latex_template}
"""
        from langchain_core.messages import SystemMessage, HumanMessage
        from langchain_core.output_parsers import StrOutputParser
        
        # Use StrOutputParser for raw LaTeX
        chain = self.llm | StrOutputParser()
        
        response = chain.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        
        # Strip potential markdown code blocks if the LLM ignored instructions
        if "```latex" in response:
            response = response.split("```latex")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()
            
        return response.strip()

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
        
        # Run pdflatex
        tex_dir = os.path.abspath(os.path.dirname(tex_path))
        tex_filename = os.path.basename(tex_path)
        
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-output-directory", tex_dir, tex_filename],
            cwd=tex_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Check for compilation errors
        pdf_path = os.path.join(tex_dir, tex_filename.replace('.tex', '.pdf'))
        log_path = os.path.join(tex_dir, tex_filename.replace('.tex', '.log'))
        
        if not os.path.exists(pdf_path):
            log_content = "No log file found."
            if os.path.exists(log_path):
                with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    log_content = f.read()[-2000:]
            raise RuntimeError(f"LaTeX compilation failed (no PDF). Log excerpt:\n{log_content}")
            
        # Clean up auxiliary files ONLY if it succeeded
        for ext in ['.aux', '.log', '.out']:
            aux_file = os.path.join(tex_dir, tex_filename.replace('.tex', ext))
            if os.path.exists(aux_file):
                os.remove(aux_file)
        
        return pdf_path

    def build(self, job_description, user_profile_text, job_id, template_path=None, tailoring_prompt=None):
        """
        Orchestrates the tailoring and compilation of a resume.
        """
        filename = f"Resume_{job_id}"
        
        # Use deep tailoring if prompt provided
        if tailoring_prompt:
            print(f"Applying deep LaTeX tailoring for Job {job_id}...")
            # Load template content
            target_template = template_path if template_path else self.base_template_path
            with open(target_template, 'r', encoding='utf-8') as f:
                template_content = f.read()
            
            tailored_latex = self.tailor_latex(template_content, job_description, user_profile_text, custom_prompt=tailoring_prompt)
            tex_path = self.render_tex({}, filename, raw_latex=tailored_latex)
        else:
            # Fallback to legacy skills_list injection
            print(f"Extracting keywords for Job {job_id}...")
            extracted_data = self.generate_resume_content(job_description, user_profile_text)
            context = {
                "skills_list": extracted_data.get("skills_list", []),
                "summary": "Tailored Professional",
                "experience": "Detailed Experience",
                "education": "University Degree"
            }
            tex_path = self.render_tex(context, filename, template_path=template_path)
        
        print(f"Compiling PDF...")
        pdf_path = self.compile_pdf(tex_path)
        
        return pdf_path


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
