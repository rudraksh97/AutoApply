import os
import subprocess
import jinja2
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from dotenv import load_dotenv

load_dotenv()

class ResumeBuilder:
    def __init__(self, base_template_path="data/resume_base.tex", output_dir="data/generated_resumes"):
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
        Uses LLM to extract relevant keywords from JD and inject into resume.
        """
        prompt = ChatPromptTemplate.from_template("""
            You are an expert ATS optimizer.
            Analyze the Job Description and extract the most important technical keywords, skills, and tools mentioned.
            
            Job Description:
            {job_description}
            
            Return a JSON object with a single key:
            - skills_list: A list of the top 10-15 most relevant keywords/skills found in the description.
            
            Do not manufacture skills that are completely unrelated to software engineering, but prioritize matching the JD hard skills.
        """)
        
        chain = prompt | self.llm | JsonOutputParser()
        
        response = chain.invoke({
            "job_description": job_description
        })
        
        # We also need to ensure the other fields (summary, experience) are present.
        # For now, we reuse the static profile info or just leave them static if the TeX is static.
        # But the template expects 'summary', 'experience', 'education'.
        # Since the user said "impute those keywords", we will merge the dynamic skills with static content.
        
        # NOTE: Ideally these would come from the user profile or be static in the specific base tex.
        # For this iteration, we keep the rest static or passed from 'current_resume_info' if it was a dict, 
        # but current_resume_info is a string in main.py.
        # Let's just return the skills, and the render_tex will need the other keys.
        
        return response

    def build(self, job_description, current_resume_info, job_id):
        """Orchestrates the resume creation process."""
        print(f"Extracting keywords for Job {job_id}...")
        extracted_data = self.generate_resume_content(job_description, current_resume_info)
        
        # Fill in the rest with placeholders or static content for now, 
        # as the user specifically focused on keyword imputation.
        # In a real app, 'current_resume_info' would be parsed or the template would be static text.
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
