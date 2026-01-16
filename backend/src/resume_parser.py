import os
import json
import logging
import pypdf
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from src.config import ConfigManager

class ResumeParser:
    """
    Parses resume files (PDF, TEX, TXT) into structured JSON using an LLM.
    """
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            logging.warning("OPENROUTER_API_KEY not set. Resume parsing will fail.")

    async def parse_file(self, file_path: str) -> dict:
        """
        Reads a file and uses an LLM to extract structured profile data.

        Args:
            file_path: Absolute path to the resume file.

        Returns:
            dict: Structured JSON data matching the profile schema.
        """
        text = self._extract_text(file_path)
             
        data = await self._parse_text_with_llm(text)
        if "skills" not in data:
            data["skills"] = []
        return data

    def _extract_text(self, file_path: str) -> str:
        """Extracts raw text from PDF or text-based files."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Resume file not found: {file_path}")

        try:
            if file_path.endswith(".pdf"):
                reader = pypdf.PdfReader(file_path)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
            elif file_path.endswith((".tex", ".txt")):
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            else:
                raise ValueError("Unsupported file format. Use .pdf, .tex, or .txt")
        except Exception as e:
            raise RuntimeError(f"Failed to read file: {e}")

    async def _parse_text_with_llm(self, text: str) -> dict:
        """Invokes the LLM to parse raw text into JSON."""
        if not self.api_key:
            raise RuntimeError("Missing API Key for LLM")

        config = ConfigManager()
        llm = ChatOpenAI(
            model=config.get_selected_model(),
            api_key=self.api_key,
            base_url="https://openrouter.ai/api/v1"
        )
        
        system_prompt = """You are an expert resume parser. Extract structured data from the resume text into JSON format matching this exact schema:
        {
            "basics": {
                "first_name": "", "last_name": "", "email": "", "phone": "", "location": ""
            },
            "urls": {
                "linkedin": "", "github": "", "portfolio": ""
            },
            "demographics": {
                "gender": "", "race": "", "nationality": "", "veteran": "", "disability": ""
            },
            "work_auth": {
                "authorized_in_us": true/false,
                "requires_sponsorship": true/false
            },
            "skills": ["skill1", "skill2"],
             "education": [
                {"degree": "", "university": "", "field_of_study": "", "graduation_year": ""}
             ],
            "experience": [
                {"company": "", "role": "", "start_date": "", "end_date": "", "description": ""}
            ]
        }
        Return ONLY the raw JSON block. Do not include any conversational text or markdown formatting markers."""
        
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Extract resume data from this text:\n\n{text[:12000]}")
        ])
        
        # Robust JSON extraction using regex
        import re
        content = response.content
        match = re.search(r"(\{.*\})", content, re.DOTALL)
        if not match:
            raise RuntimeError(f"Could not find JSON block in LLM response: {content[:200]}...")
            
        json_str = match.group(1).strip()
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            raise RuntimeError(f"LLM returned invalid JSON structure: {json_str[:200]}...")
