"""
JAAA — Job Application Automation Agent
Entry point. Run with: python run.py [job_url]

Example:
    python run.py https://boards.greenhouse.io/some-company/jobs/12345
"""
import asyncio
import sys
from dotenv import load_dotenv

load_dotenv()

from orchestrator.agent import JobAgent

async def main():
    agent = JobAgent()

    if len(sys.argv) > 1:
        job_url = sys.argv[1]
        print(f"Running agent for: {job_url}")
        await agent.run(job_url)
    else:
        print("Main Agent Loop Ready.")
        print("Usage: python run.py <job_url>")
        print("Example: python run.py https://boards.greenhouse.io/company/jobs/12345")

if __name__ == "__main__":
    asyncio.run(main())
