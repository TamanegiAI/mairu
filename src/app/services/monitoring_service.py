from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
import logging
from typing import Optional, Dict, Any

from src.app.models.schemas import MonitoringConfigRequest
from src.app.services.drive import DriveService
from src.app.services.auth import GoogleAuth # For type hinting, actual auth passed during methods
from src.app.services.instagram import InstagramService

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

MONITORING_JOB_ID_PREFIX = "folder_monitoring_job_"

class FolderMonitoringService:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_jobstore(MemoryJobStore(), 'default')
        self.scheduler.start()
        self.current_config: Optional[MonitoringConfigRequest] = None
        self.current_auth_details: Optional[Dict[str, Any]] = None # To store token_info for the job
        self.last_check_timestamp: Optional[datetime] = None
        self.last_processed_image_name: Optional[str] = None
        self.last_processed_image_status: Optional[str] = None
        self.last_processed_timestamp: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self.is_monitoring_active: bool = False
        self.active_job_id: Optional[str] = None

    def _generate_job_id(self, user_identifier: str = "default_user") -> str:
        """Generates a unique job ID for monitoring."""
        # In a multi-user system, user_identifier would be crucial.
        # For now, we assume a single active monitoring configuration.
        return f"{MONITORING_JOB_ID_PREFIX}{user_identifier}"

    async def update_configuration(self, config: MonitoringConfigRequest, auth_service: GoogleAuth, token_info: Dict[str, Any]):
        logger.info(f"Updating monitoring configuration: {config.enabled}, Freq: {config.monitoring_frequency_minutes} min")
        self.current_config = config
        self.current_auth_details = token_info # Store the full token_info
        self.active_job_id = self._generate_job_id()

        # Remove existing job if any
        try:
            if self.scheduler.get_job(self.active_job_id):
                self.scheduler.remove_job(self.active_job_id)
                logger.info(f"Removed existing monitoring job: {self.active_job_id}")
        except Exception as e:
            logger.error(f"Error removing existing job: {e}")

        if config.enabled:
            if not config.trigger_folder_id:
                self.is_monitoring_active = False
                self.error_message = "Trigger folder ID is not set. Monitoring cannot start."
                logger.error(self.error_message)
                return {"success": False, "message": self.error_message}
            
            self.scheduler.add_job(
                self._check_trigger_folder_job_wrapper, # Wrapper to pass necessary context
                trigger=IntervalTrigger(minutes=config.monitoring_frequency_minutes),
                id=self.active_job_id,
                name=f"Folder Monitoring for {config.trigger_folder_id}",
                replace_existing=True,
                misfire_grace_time=60 # 60 seconds
            )
            self.is_monitoring_active = True
            self.error_message = None
            logger.info(f"Scheduled folder monitoring job: {self.active_job_id} every {config.monitoring_frequency_minutes} minutes.")
            return {"success": True, "message": "Monitoring enabled.", "job_id": self.active_job_id}
        else:
            self.is_monitoring_active = False
            logger.info("Monitoring disabled.")
            return {"success": True, "message": "Monitoring disabled."}

    async def _check_trigger_folder_job_wrapper(self):
        """Wrapper to call the async _check_trigger_folder with stored auth."""
        if not self.current_config or not self.current_auth_details:
            logger.error("Monitoring job called without configuration or auth details.")
            return
        
        # Create a temporary GoogleAuth instance or pass token_info directly to DriveService
        # For simplicity, assuming DriveService can be initialized with token_info
        try:
            # Here, you might need to refresh the token if it's about to expire.
            # The GoogleAuth service has validate_and_refresh_token, but it's async and needs a db session.
            # For a background job, this interaction needs careful design.
            # For now, we'll assume the token is valid or DriveService handles it.
            drive_service = DriveService(token_info=self.current_auth_details)
            await self._check_trigger_folder(drive_service)
        except Exception as e:
            logger.error(f"Error in _check_trigger_folder_job_wrapper: {e}")
            self.error_message = f"Error during folder check: {e}"

    async def _check_trigger_folder(self, drive_service: DriveService):
        if not self.current_config or not self.is_monitoring_active:
            logger.info("Skipping folder check as monitoring is not active or configured.")
            return

        logger.info(f"Checking trigger folder: {self.current_config.trigger_folder_id}")
        self.last_check_timestamp = datetime.utcnow()
        self.error_message = None # Clear previous error on new check

        try:
            # List files in the trigger folder, looking for images
            # Mime types for common images: 'image/jpeg', 'image/png', 'image/gif'
            # Query: f"'{self.current_config.trigger_folder_id}' in parents and (mimeType='image/jpeg' or mimeType='image/png') and trashed=false"
            query = f"'{self.current_config.trigger_folder_id}' in parents and trashed=false"
            files = drive_service.search_files(query=query, fields="files(id, name, mimeType, createdTime)")

            if not files:
                logger.info("No files found in the trigger folder.")
                # Potentially update status: "No new images found"
                self.last_processed_image_name = None # Clear last processed if folder is empty
                return

            # For now, process only one image at a time as per requirements
            # Requirement: "Process one image at a time (ensure the folder has at most one image at any time)"
            # We'll take the first one found. If multiple, user should manage this.
            image_file = files[0]
            logger.info(f"Found image: {image_file['name']} (ID: {image_file['id']}) in trigger folder.")
            
            self.last_processed_image_name = image_file['name']
            self.last_processed_image_status = "Detected"
            self.last_processed_timestamp = datetime.utcnow()

            # Instantiate InstagramService
            try:
                instagram_service = InstagramService(token_info_or_token=self.current_auth_details)
            except Exception as e:
                logger.error(f"Failed to instantiate InstagramService: {e}")
                self.error_message = f"Error instantiating InstagramService: {e}"
                self.last_processed_image_status = "Error (InstagramService Init)"
                return

            # Prepare arguments for generate_posts
            # TODO: These placeholder values need to be made configurable in MonitoringConfigRequest
            # and through the frontend UI and backend API.
            config_sheet_name = getattr(self.current_config, 'sheet_name', 'Sheet1') # Placeholder
            config_slides_template_id = getattr(self.current_config, 'slides_template_id', 'DEFAULT_SLIDE_TEMPLATE_ID') # Placeholder
            config_recipient_email = getattr(self.current_config, 'recipient_email', 'user@example.com') # Placeholder
            config_column_mappings = getattr(self.current_config, 'column_mappings', None) # Placeholder
            config_process_flag_column = getattr(self.current_config, 'process_flag_column', None) # Placeholder
            config_process_flag_value = getattr(self.current_config, 'process_flag_value', 'yes') # Placeholder

            logger.info(f"Attempting to generate post for image: {image_file['name']}")
            try:
                post_generation_result = instagram_service.generate_posts(
                    spreadsheet_id=self.current_config.spreadsheet_id,
                    sheet_name=config_sheet_name, 
                    slides_template_id=config_slides_template_id,
                    drive_folder_id=None, # Output folder for generate_posts, may not be needed if image_url is direct
                    recipient_email=config_recipient_email,
                    column_mappings=config_column_mappings,
                    process_flag_column=config_process_flag_column,
                    process_flag_value=config_process_flag_value,
                    image_url=image_file['id'], # Pass Drive file ID as image_url
                    update_status_column=self.current_config.status_column_name
                )

                if post_generation_result and post_generation_result.get("success"):
                    logger.info(f"Successfully generated post for {image_file['name']}. Result: {post_generation_result.get('message')}")
                    self.last_processed_image_status = "Processed and Emailed"
                    
                    # Move to backup folder if backup_folder_id is configured
                    if self.current_config.backup_folder_id:
                        logger.info(f"Moving {image_file['name']} to backup folder {self.current_config.backup_folder_id}")
                        try:
                            drive_service.move_file(file_id=image_file['id'], new_parent_id=self.current_config.backup_folder_id)
                            logger.info(f"Successfully moved {image_file['name']} to backup folder.")
                            self.last_processed_image_status = "Processed and Moved"
                        except Exception as move_error:
                            logger.error(f"Failed to move {image_file['name']} to backup folder: {move_error}")
                            self.error_message = f"Post generated, but failed to move file: {move_error}"
                            self.last_processed_image_status = "Processing OK, Move Failed"
                    else:
                        logger.warning(f"No backup folder configured. File {image_file['name']} will not be moved.")
                        self.last_processed_image_status = "Processed (No Backup Folder)"
                else:
                    error_detail = post_generation_result.get('message', 'Unknown error during post generation.')
                    logger.error(f"Failed to generate post for {image_file['name']}: {error_detail}")
                    self.error_message = f"Post generation failed: {error_detail}"
                    self.last_processed_image_status = "Processing Failed"

            except Exception as e:
                logger.error(f"Exception during post generation for {image_file['name']}: {e}")
                self.error_message = f"Exception during post generation: {e}"
                self.last_processed_image_status = "Processing Exception"

        except Exception as e:
            logger.error(f"Error checking trigger folder: {e}")
            self.error_message = f"Error during folder check: {e}"
            self.last_processed_image_status = "Error during check"

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_monitoring_active": self.is_monitoring_active,
            "status_message": f"Monitoring {'active' if self.is_monitoring_active else 'inactive'}. Job ID: {self.active_job_id if self.is_monitoring_active else 'N/A'}",
            "last_check_timestamp": self.last_check_timestamp,
            "last_processed_image_name": self.last_processed_image_name,
            "last_processed_image_status": self.last_processed_image_status,
            "last_processed_timestamp": self.last_processed_timestamp,
            "error_message": self.error_message,
            "current_config": self.current_config.dict() if self.current_config else None
        }

    def shutdown(self):
        logger.info("Shutting down folder monitoring scheduler.")
        self.scheduler.shutdown()

# Global instance of the monitoring service
# This approach is simple for a single-process app.
# For multi-process (e.g., Gunicorn workers), a shared job store (like Redis/DB) and 
# a single scheduler instance or a more robust inter-process communication would be needed.
folder_monitoring_service = FolderMonitoringService()
