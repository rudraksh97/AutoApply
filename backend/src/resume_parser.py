
import os
import json
import logging
import pypdf
from langchain_core.messages import SystemMessage, HumanMessage
from browser_use.llm.openrouter.chat import ChatOpenRouter

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
        return await self._parse_text_with_llm(text)

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

        llm = ChatOpenRouter(model="meta-llama/llama-3.3-70b-instruct:free", api_key=self.api_key)
        
        system_prompt = """You are an expert resume parser. Extract structured data from the resume text into JSON format matching this schema:
        {
            "basics": {
                "first_name": "", "last_name": "", "email": "", "phone": "", "location": ""
            },
            "urls": {
                "linkedin": "", "github": "", "portfolio": ""
            },
             "education": [
                {"degree": "BS Computer Science", "university": "University Name", "field_of_study": "CS", "graduation_year": "2020"}
             ],
            "experience": [
                {"company": "Corp", "role": "Dev", "start_date": "01/2020", "end_date": "Present", "description": "built things"}
            ]
        }
        Return ONLY valid JSON."""
        
        response = await llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Resume Text:\n{text[:10000]}") # Truncate to avoid context limits
        ])
        
        # Clean response
        content = response.content.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            raise RuntimeError(f"LLM returned invalid JSON: {content[:100]}...")
