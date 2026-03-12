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
        # For the test, we can pass dummy HTML or just extract later
        # For now, let's assume we know the company/title or extraction succeeds
        # In the full loop, this would happen in-browser first
        
        # Step 3: Apply
        print(f"--- [Step 3] Starting Apply with Playwright + Stagehand ---")
        # We'll use dummy company/title for the test run initialization
        company = "GreenhouseTest"
        job_title = "AI Engineer"
        
        await self.filler.apply(job_url, company, job_title)
        
        # Step 4: Store Result
        # (Handled by the internal logger in Step 3 for now)
        print(f"--- [Step 4] Application results logged to data/logs/ ---")

if __name__ == "__main__":
    agent = JobAgent()
    # To run: asyncio.run(agent.run("https://boards.greenhouse.io/test-url"))
    print("Main Agent Loop Ready.")
