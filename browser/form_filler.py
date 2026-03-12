import os
import asyncio
from typing import Dict, Optional, List
from playwright.async_api import async_playwright
from profile.profile_manager import ProfileManager

class FormFiller:
    def __init__(self, profile_manager: ProfileManager):
        self.pm = profile_manager
        self.profile = self.pm.profile_data

    async def fill_greenhouse(self, page, job_url: str):
        """
        Specialized logic for Greenhouse forms (very common for tech).
        """
        await page.goto(job_url)
        
        # Fill Basic Info
        await page.fill("#first_name", self.profile.personal_info["first_name"])
        await page.fill("#last_name", self.profile.personal_info["last_name"])
        await page.fill("#email", self.profile.personal_info["email"])
        await page.fill("#phone", self.profile.personal_info["phone"])
        
        # Upload Resume
        resume_path = os.path.abspath(self.profile.resume_paths["base"])
        await page.set_input_files("input[type='file'][name='resume']", resume_path)
        
        # Social links
        if self.profile.personal_info["links"]["linkedin"]:
            await page.fill("input[label*='LinkedIn']", self.profile.personal_info["links"]["linkedin"])
        if self.profile.personal_info["links"]["github"]:
            await page.fill("input[label*='GitHub']", self.profile.personal_info["links"]["github"])

        print(f"Form filled for {job_url}. Awaiting manual submission or further AI logic.")

    async def fill_generic_with_ai(self, page, job_url: str):
        """
        Uses Stagehand/AI-vision style logic to detect and fill any form.
        (Placeholder for the actual Stagehand integration)
        """
        await page.goto(job_url)
        print("Using AI-driven field detection...")
        # In the real build, we'd call stagehand.act("Fill the form using the profile data") here.
        pass

if __name__ == "__main__":
    # Test script entry point
    print("Form Filler Logic Initialized.")
