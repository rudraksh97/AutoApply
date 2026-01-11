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
    def __init__(self, base_template_path="data/resume_base.tex", output_dir="data/generated_resumes"):
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

        # Configure Jinja2 for LaTeX
        self.env = jinja2.Environment(
            block_start_string='\\VAR{BLOCK',
            block_end_string='\\VAR{ENDBLOCK}',
            variable_start_string='\\VAR{',
            variable_end_string='}',
            comment_start_string='\\VAR{COMMENT',
            comment_end_string='\\VAR{ENDCOMMENT}',
            line_statement_prefix='%%',
            line_comment_prefix='%#',
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

        Args:
            job_description (str): The text of the target job posting.
            current_resume_info (str): The user's base resume information.

        Returns:
            dict: A dictionary containing 'skills_list' extracted by the LLM.
        """
        prompt = ChatPromptTemplate.from_template(RESUME_OPTIMIZER_PROMPT_TEMPLATE)
        
        chain = prompt | self.llm | JsonOutputParser()
        
        response = chain.invoke({
            "job_description": job_description
        })
        
        return response

    def render_tex(self, context, filename):
        """
        Renders the Jinja2 LaTeX template with the provided context.
        
        Args:
            context (dict): Template variables (skills_list, summary, etc.)
            filename (str): Base filename for the output (without extension)
            
        Returns:
            str: The absolute path to the rendered .tex file.
        """
        template_name = os.path.basename(self.base_template_path)
        template = self.env.get_template(template_name)
        
        # Convert skills_list to a comma-separated string if it's a list
        if isinstance(context.get('skills_list'), list):
            context['skills_list'] = ', '.join(context['skills_list'])
        
        rendered = template.render(**context)
        
        tex_path = os.path.join(self.output_dir, f"{filename}.tex")
        with open(tex_path, 'w') as f:
            f.write(rendered)
        
        return tex_path

    def compile_pdf(self, tex_path):
        """
        Compiles a .tex file to PDF using pdflatex.
        
        Args:
            tex_path (str): Full path to the .tex file.
            
        Returns:
            str: Full path to the generated PDF file.
            
        Raises:
            RuntimeError: If pdflatex is not available or compilation fails.
        """
        # Check if pdflatex is available
        try:
            subprocess.run(["pdflatex", "--version"], check=True, 
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            raise RuntimeError("pdflatex is not available. Please install a TeX distribution.") from e
        
        # Run pdflatex
        tex_dir = os.path.dirname(tex_path)
        tex_filename = os.path.basename(tex_path)
        
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-output-directory", tex_dir, tex_filename],
            cwd=tex_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Check for compilation errors
        pdf_path = tex_path.replace('.tex', '.pdf')
        if not os.path.exists(pdf_path):
            log_path = tex_path.replace('.tex', '.log')
            log_content = ""
            if os.path.exists(log_path):
                with open(log_path, 'r') as f:
                    log_content = f.read()[-2000:]  # Last 2000 chars of log
            raise RuntimeError(f"LaTeX compilation failed. Log excerpt:\n{log_content}")
        
        # Clean up auxiliary files
        for ext in ['.aux', '.log', '.out']:
            aux_file = tex_path.replace('.tex', ext)
            if os.path.exists(aux_file):
                os.remove(aux_file)
        
        return pdf_path

    def build(self, job_description, current_resume_info, job_id):
        """
        Orchestrates the extraction, rendering, and compilation of a resume.

        Args:
            job_description (str): The target job's details.
            current_resume_info (str): The base profile info (currently placeholder-heavy).
            job_id (int): Unique ID to distinguish generated files.

        Returns:
            str: Path to the final PDF file.
        """
        print(f"Extracting keywords for Job {job_id}...")
        extracted_data = self.generate_resume_content(job_description, current_resume_info)
        
        # Fill in the rest with placeholders or static content for now.
        context = {
            "summary": "Experienced Software Engineer with a focus on delivering scalable solutions.",
            "experience": "See attached (Static Experience for now)",
            "education": "BS Computer Science",
            "skills_list": extracted_data.get("skills_list", [])
        }
        
        filename = f"Resume_{job_id}"
        print(f"Rendering TeX template...")
        tex_path = self.render_tex(context, filename)
        
        print(f"Compiling PDF...")
        pdf_path = self.compile_pdf(tex_path)
        
        return pdf_path


if __name__ == "__main__":
    # Test stub
    builder = ResumeBuilder()
    # Dummy data
    try:
        # Check if pdflatex exists
        subprocess.run(["pdflatex", "--version"], check=True, stdout=subprocess.PIPE)
        print("pdflatex found.")
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("pdflatex NOT found. Please install TeX distribution.")
