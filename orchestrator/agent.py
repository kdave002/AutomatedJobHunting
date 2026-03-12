import os
import asyncio
from datetime import datetime
from browser.stagehand_filler import StagehandFormFiller
from profile.profile_manager import ProfileManager
from storage.logger import ApplicationLogger
from orchestrator.planner import JobExtractor
from dotenv import load_dotenv

load_dotenv()

class JobAgent:
    def __init__(self):
        self.pm = ProfileManager()
        self.logger = ApplicationLogger()
        self.filler = StagehandFormFiller(self.pm, self.logger)
        self.extractor = JobExtractor(os.environ.get("GOOGLE_GENERATIVE_AI_API_KEY"))

    async def run(self, job_url: str):
        # Derive a best-guess company name from the URL for logging
        # (planner would normally fetch and parse the page HTML)
        from urllib.parse import urlparse
        domain = urlparse(job_url).netloc.replace("www.", "")
        company = domain.split(".")[0].replace("-", " ").title()
        job_title = "Unknown Role"

        print(f"\n[JAAA] Starting application")
        print(f"[JAAA] URL     : {job_url}")
        print(f"[JAAA] Company : {company}")
        print(f"[JAAA] Email   : {os.environ.get('ACCOUNT_EMAIL', 'not set')}")
        print()

        await self.filler.apply(job_url, company, job_title)

if __name__ == "__main__":
    agent = JobAgent()
    print("Main Agent Loop Ready.")
