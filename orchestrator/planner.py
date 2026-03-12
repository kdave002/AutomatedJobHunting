import os
import json
import requests
from typing import Optional
from pydantic import BaseModel

class JobDetails(BaseModel):
    title: str
    company: str
    location: Optional[str] = "Unknown"
    salary: Optional[str] = "N/A"
    required_skills: list[str] = []
    description_summary: str
    application_url: str

class JobExtractor:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GOOGLE_GENERATIVE_AI_API_KEY")
        self.model = "gemini-2.5-flash"

    def extract_from_url(self, url: str, html_content: str) -> Optional[JobDetails]:
        """
        Extract job details from raw HTML content using Gemini.
        """
        prompt = f"""
        Extract structured job information from the following HTML content of a job posting.
        URL: {url}

        HTML:
        {html_content[:15000]}

        Return ONLY a valid JSON object (no markdown, no explanation) with these fields:
        - title
        - company
        - location
        - salary
        - required_skills (list of strings)
        - description_summary
        - application_url
        """

        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0}
        }

        try:
            response = requests.post(endpoint, json=payload, timeout=30)
            response.raise_for_status()
            text = response.json()["candidates"][0]["content"]["parts"][0]["text"]

            # Strip markdown code fences if present
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            return JobDetails(**json.loads(text))
        except Exception as e:
            print(f"Error extracting job details: {e}")
            return None

if __name__ == "__main__":
    print("Job Extractor (Gemini) ready.")
