import os
import json
from abc import ABC, abstractmethod

class BaseResumeParser(ABC):
    @abstractmethod
    def parse_pdf(self, file_path: str) -> dict:
        """Parse PDF and return structured profile JSON."""
        pass

class JSONResumeParser(BaseResumeParser):
    def parse_pdf(self, file_path: str) -> dict:
        # Placeholder for AI/PDF extraction logic (LandingAI/PyPDF2)
        # Will extract Name, Skills, Experience, Education, etc.
        return {
            "name": "Kushal",
            "skills": [],
            "experience": [],
            "education": []
        }
