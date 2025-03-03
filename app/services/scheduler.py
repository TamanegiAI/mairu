from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from datetime import datetime
from app.services.gmail import GmailService
from typing import Dict, Optional

class EmailScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_jobstore('memory')
        self.scheduler.start()
        self.jobs: Dict[str, str] = {}  # Store job_id -> email_id mapping

    def schedule_email(
        self,
        access_token: str,
        to: str,
        subject: str,
        body: str,
        scheduled_time: datetime,
        cc: Optional[str] = None,
        document_id: Optional[str] = None
    ) -> dict:
        """Schedule an email to be sent at a specific time."""
        
        def send_scheduled_email():
            gmail_service = GmailService(access_token)
            return gmail_service.send_email(
                to=to,
                subject=subject,
                body=body,
                cc=cc,
                document_id=document_id
            )

        job = self.scheduler.add_job(
            send_scheduled_email,
            'date',
            run_date=scheduled_time,
            misfire_grace_time=3600  # Allow 1 hour grace time for misfires
        )

        return {
            "success": True,
            "job_id": job.id,
            "scheduled_time": scheduled_time.isoformat()
        }

    def cancel_scheduled_email(self, job_id: str) -> dict:
        """Cancel a scheduled email."""
        try:
            self.scheduler.remove_job(job_id)
            return {"success": True, "message": f"Scheduled email {job_id} cancelled"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def list_scheduled_emails(self) -> list:
        """List all scheduled emails."""
        jobs = self.scheduler.get_jobs()
        return [{
            "job_id": job.id,
            "scheduled_time": job.next_run_time.isoformat(),
            "status": "pending"
        } for job in jobs]

# Create a global scheduler instance
email_scheduler = EmailScheduler()
