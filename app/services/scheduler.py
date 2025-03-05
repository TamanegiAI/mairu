from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from datetime import datetime
from app.services.gmail import GmailService
from typing import Dict, Optional
import pytz
from sqlalchemy.orm import Session
from app.services.database import DatabaseService

class EmailScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_jobstore('memory')
        self.scheduler.start()
        self.jobs: Dict[str, str] = {}  # Store job_id -> email_id mapping

    def schedule_email(
        self,
        db: Session,
        access_token: str,
        to: str,
        subject: str,
        body: str,
        scheduled_time: datetime,
        cc: Optional[str] = None,
        document_id: Optional[str] = None
    ) -> dict:
        """Schedule an email to be sent at a specific time."""
        
        def send_scheduled_email(job_id: str):
            try:
                gmail_service = GmailService(access_token)
                result = gmail_service.send_email(
                    to=to,
                    subject=subject,
                    body=body,
                    cc=cc,
                    document_id=document_id
                )
                DatabaseService.update_scheduled_email_status(db, job_id, "sent")
                return result
            except Exception as e:
                DatabaseService.update_scheduled_email_status(db, job_id, "failed")
                raise e

        job = self.scheduler.add_job(
            send_scheduled_email,
            'date',
            run_date=scheduled_time,
            misfire_grace_time=3600
        )

        # Save to database
        DatabaseService.save_scheduled_email(
            db,
            job_id=job.id,
            to_email=to,
            subject=subject,
            body=body,
            scheduled_time=scheduled_time,
            cc=cc,
            document_id=document_id
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
    
    def convert_to_utc(jst_time_str):
        """Convert JST time to UTC before scheduling"""
        jst = pytz.timezone("Asia/Tokyo")
        utc = pytz.utc
        local_time = jst.localize(datetime.strptime(jst_time_str, "%Y-%m-%dT%H:%M:%S"))
        return local_time.astimezone(utc).isoformat()

# Create a global scheduler instance
email_scheduler = EmailScheduler()
