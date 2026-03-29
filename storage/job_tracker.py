from datetime import datetime
from storage.storage_manager import StorageManager
from logs.logger import log_info, log_error, log_success

class JobTracker:
    """High-level abstraction for job application tracking logic."""
    def __init__(self):
        self.applied_jobs = StorageManager.load_applied_jobs()
        self.failed_jobs = StorageManager.load_failed_jobs()
        self.session = StorageManager.load_session()
        self._update_session_time()

    def _update_session_time(self):
        today = datetime.utcnow().date().isoformat()
        if self.session.get("last_run_date") != today:
            self.session["last_run_date"] = today
            self.session["daily_applied"] = 0
            
        self.session["last_run_time"] = datetime.utcnow().isoformat()
        StorageManager.save_session(self.session)

    def reached_daily_limit(self, limit: int) -> bool:
        """Determines if the application run queue exceeds the daily global cap."""
        return self.session.get("daily_applied", 0) >= limit

    def is_job_applied(self, job_link: str) -> bool:
        """Check if job is already applied strictly matching job_link."""
        return any(job.get("job_link") == job_link for job in self.applied_jobs)

    def load_applied_jobs(self) -> list:
        return self.applied_jobs

    def save_applied_job(self, company: str, role: str, location: str, job_link: str, notes: str = ""):
        if self.is_job_applied(job_link):
            log_info(f"[SKIP] Joblink already recorded internally: {job_link}")
            return
            
        job_data = {
            "company": company,
            "role": role,
            "location": location,
            "job_link": job_link,
            "applied_date": datetime.utcnow().isoformat(),
            "status": "APPLIED",
            "notes": notes
        }
        self.applied_jobs.append(job_data)
        StorageManager.save_applied_jobs(self.applied_jobs)
        
        self.session["daily_applied"] = self.session.get("daily_applied", 0) + 1
        self.session["total_applied"] = self.session.get("total_applied", 0) + 1
        StorageManager.save_session(self.session)
        log_success(f"Application recorded successfully: {company} | {role}")
        
    def save_failed_job(self, company: str, role: str, job_link: str, error: str):
        job_data = {
            "company": company,
            "role": role,
            "job_link": job_link,
            "error": str(error),
            "timestamp": datetime.utcnow().isoformat()
        }
        self.failed_jobs.append(job_data)
        StorageManager.save_failed_jobs(self.failed_jobs)
        
        self.session["total_failed"] = self.session.get("total_failed", 0) + 1
        StorageManager.save_session(self.session)
        log_error(f"Failed to complete job apply flow: {company} | {role}. Extracted Reason: {error}")
