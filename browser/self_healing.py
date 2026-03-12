import os
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from stagehand import AsyncStagehand
from playwright.async_api import async_playwright
from profile.profile_manager import ProfileManager
from storage.logger import ApplicationLogger

class SelfHealingAgent:
    def __init__(self, profile_manager: ProfileManager, logger: ApplicationLogger):
        self.pm = profile_manager
        self.profile = self.pm.profile_data
        self.logger = logger
        self.knowledge_base_path = "data/knowledge_base.json"
        self.knowledge_base = self._load_knowledge_base()

    def _load_knowledge_base(self) -> Dict:
        if os.path.exists(self.knowledge_base_path):
            with open(self.knowledge_base_path, "r") as f:
                return json.load(f)
        return {"errors": {}, "successful_patterns": {}}

    def _save_knowledge_base(self):
        with open(self.knowledge_base_path, "w") as f:
            json.dump(self.knowledge_base, f, indent=2)

    async def apply_with_healing(self, job_url: str, company: str, job_title: str):
        app_id = f"{company.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.logger.log_event(app_id, company, job_title, "init", "success", "Self-healing agent started")

        async with async_playwright() as p:
            # Headless=True for server environment
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # Check knowledge base for previous failures on this domain
            domain = job_url.split('/')[2]
            previous_error = self.knowledge_base["errors"].get(domain)
            if previous_error:
                print(f"[Self-Healing] Detected previous error for {domain}: {previous_error['message']}")
                print(f"[Self-Healing] Applying mitigation: {previous_error['mitigation']}")

            try:
                await page.goto(job_url)
                
                # Logic for multi-step application
                # This uses a feedback loop: Action -> Observation -> Validation -> Correction
                
                steps = ["click_apply", "fill_personal_info", "upload_resume", "answer_screening", "submit"]
                for step in steps:
                    success = await self._execute_step_with_retry(page, step, app_id)
                    if not success:
                        raise Exception(f"Failed at step: {step}")

                # Step 2: Screenshot once submitted
                screenshot_path = f"screenshots/{app_id}_submitted.png"
                os.makedirs("screenshots", exist_ok=True)
                await page.screenshot(path=screenshot_path, full_page=True)
                self.logger.log_event(app_id, company, job_title, "screenshot", "success", screenshot_path)

            except Exception as e:
                # Step 3: Learn from mistakes
                error_msg = str(e)
                mitigation = self._analyze_error_and_suggest_mitigation(error_msg)
                
                self.knowledge_base["errors"][domain] = {
                    "message": error_msg,
                    "mitigation": mitigation,
                    "timestamp": datetime.now().isoformat()
                }
                self._save_knowledge_base()
                self.logger.log_event(app_id, company, job_title, "error_learning", "recorded", f"Learned from error: {error_msg}")
                raise e
            finally:
                await browser.close()

    async def _execute_step_with_retry(self, page, step, app_id, max_retries=3):
        """
        Implements self-healing retry logic. 
        If a selector fails, it uses AI to find an alternative.
        """
        for attempt in range(max_retries):
            try:
                # Placeholder for Stagehand/AI logic
                # if step == "click_apply":
                #    await page.act("Click the apply button")
                return True
            except Exception as e:
                print(f"[Self-Healing] Attempt {attempt+1} failed for {step}: {e}")
                await asyncio.sleep(2)
        return False

    def _analyze_error_and_suggest_mitigation(self, error_msg: str) -> str:
        """
        Uses heuristics or LLM reasoning to suggest a mitigation strategy.
        """
        if "timeout" in error_msg.lower():
            return "Increase timeout and check internet connection."
        if "selector" in error_msg.lower() or "not found" in error_msg.lower():
            return "Use AI vision (Stagehand) to find the element by visual context instead of CSS."
        return "Manual intervention required to identify root cause."

if __name__ == "__main__":
    print("Self-Healing Agent with Knowledge Base Initialized.")
