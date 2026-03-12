import json
import os
from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class Location(BaseModel):
    address: Optional[str] = "2111 Richmond Hwy"
    city: Optional[str] = "Arlington"
    state: Optional[str] = "VA"
    country: str = "USA"
    zip: Optional[str] = "22202"

class Links(BaseModel):
    linkedin: Optional[str] = "https://www.linkedin.com/in/-kushal-dave/"
    github: Optional[str] = "https://github.com/kushaldave002"
    portfolio: Optional[str] = ""

class WorkAuth(BaseModel):
    authorized_to_work_in_us: bool = True
    requires_sponsorship: bool = False

class Experience(BaseModel):
    company: str
    role: str
    location: str
    start_date: str
    end_date: Optional[str] = "Present"
    description: List[str] = []

class Education(BaseModel):
    institution: str
    degree: str
    graduation_date: str
    gpa: Optional[str] = ""

class Skills(BaseModel):
    languages: List[str] = []
    frameworks: List[str] = []
    tools: List[str] = []
    domains: List[str] = []

class Preferences(BaseModel):
    job_titles: List[str] = []
    locations: List[str] = []
    salary_min: Optional[int] = 0
    remote_only: bool = True

class Profile(BaseModel):
    personal_info: Dict
    professional_summary: str
    experience: List[Experience]
    education: List[Education]
    skills: Skills
    preferences: Preferences
    resume_paths: Dict

class ProfileManager:
    def __init__(self, file_path: str = "profile/profile.json"):
        self.file_path = file_path
        self.profile_data = self.load()

    def load(self) -> Profile:
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Profile file not found at {self.file_path}")
        with open(self.file_path, "r") as f:
            data = json.load(f)
            return Profile(**data)

    def save(self, profile: Profile):
        with open(self.file_path, "w") as f:
            json.dump(profile.dict(), f, indent=2)

if __name__ == "__main__":
    pm = ProfileManager()
    print(f"Loaded profile for: {pm.profile_data.personal_info['first_name']} {pm.profile_data.personal_info['last_name']}")
    print(f"Target Roles: {', '.join(pm.profile_data.preferences.job_titles)}")
