import os
import requests
from typing import Dict, Optional
from pydantic import BaseModel
from anthropic import Anthropic

class JobDetails(BaseModel):
    title: str
    company: str
    location: Optional[str] = "Unknown"
    salary: Optional[str] = "N/A"
    required_skills: list[str] = []
    description_summary: str
    application_url: str

class JobExtractor:
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)

    def extract_from_url(self, url: str, html_content: str) -> JobDetails:
        """
        Extract job details from raw HTML content using LLM.
        """
        prompt = f"""
        Extract structured job information from the following HTML content of a job posting.
        URL: {url}

        HTML:
        {html_content[:15000]} # Truncate to avoid context window issues

        Return a JSON object with:
        - title
        - company
        - location
        - salary
        - required_skills (list)
        - description_summary
        - application_url
        """

        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            temperature=0,
            system="You are an expert job market analyst. Extract job details into clean JSON format.",
            messages=[{"role": "user", "content": prompt}]
        )
        
        # In a real implementation, we would use tool-calling or a robust JSON parser here.
        # This is the architectural pattern for Step 2.
        import json
        try:
            # Simple extraction for demo purposes
            json_text = response.content[0].text
            if "```json" in json_text:
                json_text = json_text.split("```json")[1].split("```")[0].strip()
            return JobDetails(**json.loads(json_text))
        except Exception as e:
            print(f"Error parsing JSON: {e}")
            return None

if __name__ == "__main__":
    # This will be called by the orchestrator after Playwright fetches the HTML
    print("Job Extractor ready.")
