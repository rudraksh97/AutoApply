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
        pass

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
        """Invokes the LLM to parse raw text into structured JSON."""
        from src.llm_factory import LLMFactory
        from src.schemas import ResumeParserOutput
        
        try:
            llm = LLMFactory.get_llm_for_step("step_resume_parsing")
            
            system_prompt = "You are an expert resume parser. Extract structured data from the resume text into the required JSON format."
            
            structured_llm = llm.with_structured_output(ResumeParserOutput)
            result = await structured_llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Extract resume data from this text:\n\n{text[:12000]}")
            ])
            # Deduct credits
            from src.token_manager import TokenManager
            config_id = getattr(llm, "config_id", None)
            if config_id:
                TokenManager().deduct_credits(config_id, len(text[:12000]) * 2)

            if hasattr(result, "model_dump"):
                return result.model_dump()
            return result
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            logging.error(f"Resume parsing LLM call failed: {e}\nStack trace:\n{tb}")
            raise RuntimeError(f"Failed to parse resume with AI: {e}")
