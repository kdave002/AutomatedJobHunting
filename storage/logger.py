import json
import os
from datetime import datetime

class ApplicationLogger:
    def __init__(self, log_dir: str = "data/logs"):
        self.log_dir = log_dir
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def log_event(self, application_id: str, company: str, job_title: str, event: str, status: str, details: Optional[str] = None):
        """
        Logs a specific event (e.g., 'navigating', 'filling_form', 'waiting_for_otp', 'submitted') to a JSON file.
        """
        log_file = os.path.join(self.log_dir, f"{application_id}.json")
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "company": company,
            "job_title": job_title,
            "event": event,
            "status": status,
            "details": details
        }

        # Load existing log if it exists
        if os.path.exists(log_file):
            with open(log_file, "r") as f:
                history = json.load(f)
        else:
            history = []

        history.append(log_entry)

        with open(log_file, "w") as f:
            json.dump(history, f, indent=2)
        
        print(f"[LOG] {event} - {status}: {details if details else ''}")

if __name__ == "__main__":
    logger = ApplicationLogger()
    logger.log_event("test_id", "ReferU.AI", "AI Engineer", "session_start", "success", "Starting application via Playwright.")
