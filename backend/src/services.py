"""
Core service layer for the AutoApply application.

This module contains the business logic for orchestrating the job application
workflow, coordinating between storage, browser automation, and resume generation.
"""

import logging
from typing import Callable, Optional
from src.interfaces import JobManagerProtocol, BrowserAgentProtocol, ResumeBuilderProtocol
import os

# Preserving the constant from main.py for behavior compatibility
# In a future refactor, this should move to ProfileManager or Config
CURRENT_RESUME_INFO = """
Software Engineer with 5 years of experience in Python, AWS, and Web Development.
Education: BS in Computer Science.
Key Skills: Python, Django, React, Docker, Kubernetes.
"""

class JobApplicationService:
    """
    Orchestrates the lifecycle of a single job application.

    This service coordinates the scraping of job details, the generation of 
    a tailored resume, and the automated submission of the application.
    """
    def __init__(
        self,
        job_manager: JobManagerProtocol,
        browser_agent: BrowserAgentProtocol,
        resume_builder: ResumeBuilderProtocol
    ):
        """
        Initializes the service with required dependencies.

        Args:
            job_manager: Implementation of JobManagerProtocol for status tracking.
            browser_agent: Implementation of BrowserAgentProtocol for web interaction.
            resume_builder: Implementation of ResumeBuilderProtocol for PDF generation.
        """
        self.job_manager = job_manager
        self.browser_agent = browser_agent
        self.resume_builder = resume_builder

    async def process_job(
        self, 
        job_link: str, 
        user_details_text: str, 
        log_callback: Callable[[str], None] = print
    ) -> bool:
        """
        Orchestrates the entire job application process for a given link.

        Workflow:
        1. Scrape original job details from the provided link.
        2. Generate a tailored resume PDF based on the scraped details.
        3. Navigate to the job link and fill out the application form.
        4. Update the job status in the persistent store accordingly.

        Args:
            job_link: The URL of the job posting to process.
            user_details_text: Structured textual representation of the user's profile.
            log_callback: Optional function to handle progress logging.

        Returns:
            True if the application was successfully completed, False otherwise.
        """
        log_callback(f"Processing Job: {job_link}")
        self.job_manager.update_job(job_link, status="Running - Scraping")
        
        try:
            # Step 1: Scrape Job Details
            log_callback("Scraping job details...")
            job_description = await self.browser_agent.scrape_job_details(job_link)
            # Store snippet
            self.job_manager.update_job(job_link, details=job_description[:500] + "...") 
            

            # Step 2: Resume Preparation
            # Check user preference for uploaded resume
            from src.profile_manager import ProfileManager
            profile_manager = ProfileManager()
            profile = profile_manager.get_profile()
            
            use_uploaded = profile.get("use_uploaded_resume", False)
            uploaded_path = profile.get("uploaded_resume_path", "")
            
            pdf_path = None
            
            if use_uploaded and uploaded_path:
                if os.path.exists(uploaded_path):
                    log_callback(f"✅ Using uploaded resume: {uploaded_path}")
                    pdf_path = uploaded_path
                    self.job_manager.update_job(job_link, pdf_path=pdf_path, status="Running - Resume Ready")
                else:
                    log_callback(f"⚠️ Uploaded resume not found at: {uploaded_path}. Falling back to generation.")
                    # Generate a tailored resume
                    log_callback("Generating resume...")
                    self.job_manager.update_job(job_link, status="Running - Generating Resume")
                    
                    job_id = abs(hash(job_link)) 
                    pdf_path = self.resume_builder.build(job_description, CURRENT_RESUME_INFO, job_id=job_id)
                    self.job_manager.update_job(job_link, pdf_path=pdf_path, status="Running - Resume Ready")
            else:
                log_callback(f"Generating resume (Use Uploaded: {use_uploaded}, Path: {uploaded_path})")
                self.job_manager.update_job(job_link, status="Running - Generating Resume")
                
                # Reproducing logic from legacy main.py
                job_id = abs(hash(job_link)) 
                pdf_path = self.resume_builder.build(job_description, CURRENT_RESUME_INFO, job_id=job_id)
                self.job_manager.update_job(job_link, pdf_path=pdf_path, status="Running - Resume Ready")
            
            # Step 3: Apply (Local File)
            log_callback(f"Applying to job with resume: {pdf_path}")
            self.job_manager.update_job(job_link, status="Running - Applying")
            
            application_result = await self.browser_agent.apply_to_job(job_link, pdf_path, user_details_text)
            
            log_callback(f"Application Result: {application_result}")
            self.job_manager.update_job(job_link, status="Completed")
            return True

        except Exception as e:
            log_callback(f"Error processing job {job_link}: {e}")
            self.job_manager.update_job(job_link, status="Failed", error_message=str(e))
            return False

