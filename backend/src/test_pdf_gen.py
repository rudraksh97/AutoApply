import os
import sys

# Add app root to path
sys.path.append("/app")

from src.resume_builder import ResumeBuilder

def test_custom_template_generation():
    print("Testing Custom Template PDF Generation...")
    
    try:
        builder = ResumeBuilder()
        
        # Path to custom template (using the one we know exists)
        custom_template = "/app/data/tex_resumes/resume_base.tex"
        
        # Mock data
        job_description = "Software Engineer with Python and Docker skills."
        current_resume_info = "Experienced Python Developer."
        
        # Test build with custom template
        print(f"Running build with custom template: {custom_template}")
        pdf_path = builder.build(
            job_description, 
            current_resume_info, 
            job_id=888, 
            template_path=custom_template
        )
        
        print(f"SUCCESS: PDF generated at {pdf_path}")
        
        # Verify file exists
        if os.path.exists(pdf_path):
             print("Verified: PDF file exists on disk.")
        else:
             print("Error: PDF file path returned but file missing.")

    except Exception as e:
        print(f"FAILURE: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_custom_template_generation()
