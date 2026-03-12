import os
import asyncio
from datetime import datetime
from browser.stagehand_filler import StagehandFormFiller
from profile.profile_manager import ProfileManager
from storage.logger import ApplicationLogger
from orchestrator.planner import JobExtractor # Step 2
from dotenv import load_dotenv

load_dotenv()

class JobAgent:
    def __init__(self):
        self.pm = ProfileManager()
        self.logger = ApplicationLogger()
        self.filler = StagehandFormFiller(self.pm, self.logger)
        # Assuming you have ANTHROPIC_API_KEY set in .env
        self.extractor = JobExtractor(os.environ.get("ANTHROPIC_API_KEY"))

    async def run(self, job_url: str):
        # Step 2: Extract
        print(f"--- [Step 2] Extracting job details from {job_url} ---")
        company = "Bio-Rad Laboratories"
        job_title = "IT Intern (AI/ML)"
        
        # Step 3: Apply
        print(f"--- [Step 3] Starting Apply with Playwright + Stagehand ---")
        # Log entry for tracking
        app_id = f"{company.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.logger.log_event(app_id, company, job_title, "init", "success", f"Live test run for {job_url}")
        
        await self.filler.apply(job_url, company, job_title)
        
        print(f"--- [Step 4] Application results logged to data/logs/{app_id}.json ---")

if __name__ == "__main__":
    agent = JobAgent()
    # To run: asyncio.run(agent.run("https://boards.greenhouse.io/test-url"))
    print("Main Agent Loop Ready.")
