# backend/services/background_job_manager.py
import time
import uuid
import logging
import os
import glob
import threading
import subprocess
from typing import Dict, Any, List, Optional
from backend.config import settings

logger = logging.getLogger("vyaparai.services.background_job_manager")

class JobCancelledException(Exception):
    """Exception raised when a video generation job is cancelled by the user."""
    pass

class BackgroundJob:
    def __init__(self, job_id: str, campaign_name: str, product_name: str, product_id: str):
        self.job_id = job_id or str(uuid.uuid4())
        self.campaign_name = campaign_name
        self.product_name = product_name
        self.product_id = product_id
        self.current_stage = "Script Generation"
        self.percentage_complete = 0
        self.started_time = time.time()
        self.last_updated_time = time.time()
        self.estimated_completion_time = self.started_time + 120  # Default 2 minutes
        self.current_status = "Queued"  # Queued, Preparing, Running, Waiting, Rendering, Uploading, Completed, Failed, Cancelled, Stalled, Paused
        self.retry_count = 0
        self.logs: List[str] = []
        self.error_message: Optional[str] = None
        self.completed_stages: List[str] = []
        
        # Cancellation and pause controls
        self.cancel_event = threading.Event()
        self.pause_event = threading.Event()
        self.active_pids: List[int] = []
        self.active_subprocesses: List[subprocess.Popen] = []

        self.agents = {
            "ProductAgent": "Queued",
            "ResearchAgent": "Queued",
            "KeywordAgent": "Queued",
            "ScreenplayAgent": "Queued",
            "ThumbnailAgent": "Queued",
            "ImagePromptAgent": "Queued",
            "TranslationAgent": "Queued",
            "VoiceoverAgent": "Queued",
            "VideoAgent": "Queued"
        }
        self.agent_durations = {}
        self.add_log(f"Job initialized for campaign '{campaign_name}', product '{product_name}'")

    def add_log(self, message: str):
        self.last_updated_time = time.time()
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.logs.append(f"[{timestamp}] {message}")
        logger.info(f"[Job {self.job_id}] {message}")

    def update_progress(self, stage: str, status: str, percentage: int, est_remaining_seconds: int):
        self.last_updated_time = time.time()
        if self.current_stage and self.current_stage != stage and self.current_stage not in self.completed_stages:
            self.completed_stages.append(self.current_stage)
            
        self.current_stage = stage
        self.current_status = status
        self.percentage_complete = percentage
        self.estimated_completion_time = time.time() + est_remaining_seconds
        self.add_log(f"Stage transition: {stage} ({status}) - {percentage}% - Est remaining: {est_remaining_seconds}s")

    def is_cancelled(self) -> bool:
        return self.cancel_event.is_set() or self.current_status == "Cancelled"

    def is_paused(self) -> bool:
        return self.pause_event.is_set() or self.current_status == "Paused"

    def check_cancellation(self):
        """Helper method that raises JobCancelledException if cancellation was requested."""
        if self.is_cancelled():
            raise JobCancelledException(f"Job {self.job_id} was cancelled.")

    def check_stalled(self, threshold_seconds: int = 600) -> bool:
        """
        Detects if a job has been in an active state with no progress updates for longer than threshold_seconds.
        If stalled, updates status to 'Stalled'.
        """
        active_statuses = ["Queued", "Preparing", "Running", "Waiting", "Rendering", "Uploading"]
        if self.current_status in active_statuses:
            inactive_duration = time.time() - self.last_updated_time
            if inactive_duration > threshold_seconds:
                self.current_status = "Stalled"
                self.add_log(f"This generation appears to be stalled. (No progress updates for {int(inactive_duration)} seconds)")
                return True
        return self.current_status == "Stalled"

    def register_subprocess(self, proc: subprocess.Popen):
        """Tracks active subprocess (e.g. ffmpeg) to allow emergency termination on cancellation."""
        if proc:
            self.active_subprocesses.append(proc)
            if hasattr(proc, "pid") and proc.pid:
                self.active_pids.append(proc.pid)

    def unregister_subprocess(self, proc: subprocess.Popen):
        """Removes subprocess once finished."""
        if proc in self.active_subprocesses:
            self.active_subprocesses.remove(proc)
        if hasattr(proc, "pid") and proc.pid in self.active_pids:
            self.active_pids.remove(proc.pid)

    def terminate_active_processes(self):
        """Forcefully kills any registered running subprocesses and PIDs."""
        for proc in list(self.active_subprocesses):
            try:
                proc.kill()
                logger.info(f"[Job {self.job_id}] Terminated active subprocess PID {getattr(proc, 'pid', None)}")
            except Exception as e:
                logger.warning(f"[Job {self.job_id}] Failed to kill subprocess: {e}")
        self.active_subprocesses.clear()

        for pid in list(self.active_pids):
            try:
                if os.name == 'nt':
                    subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
                else:
                    os.kill(pid, 9)
                logger.info(f"[Job {self.job_id}] Terminated PID {pid}")
            except Exception as e:
                logger.warning(f"[Job {self.job_id}] Failed to terminate PID {pid}: {e}")
        self.active_pids.clear()

    def cancel(self):
        """Immediately stops the pipeline, marks job cancelled, and terminates background tasks."""
        self.cancel_event.set()
        self.current_status = "Cancelled"
        self.add_log("Job was CANCELLED by user. Stopping all agent execution and background processes immediately.")
        self.terminate_active_processes()

    def pause(self):
        """Pauses the job."""
        self.pause_event.set()
        self.current_status = "Paused"
        self.add_log("Job PAUSED by user.")

    def resume(self):
        """Resumes a paused or stalled job."""
        self.pause_event.clear()
        self.cancel_event.clear()
        self.current_status = "Running"
        self.last_updated_time = time.time()
        self.add_log("Job RESUMED by user.")

    def retry(self, from_stage: Optional[str] = None):
        """
        Resets flags to allow job retry. Increments retry count and sets status to Running/Queued.
        """
        self.cancel_event.clear()
        self.pause_event.clear()
        self.retry_count += 1
        self.current_status = "Running"
        self.error_message = None
        self.last_updated_time = time.time()
        if from_stage:
            self.current_stage = from_stage
            self.add_log(f"Job RETRY #{self.retry_count} initiated starting from stage '{from_stage}'.")
        else:
            self.add_log(f"Job RETRY #{self.retry_count} initiated.")

    def fail(self, error_msg: str):
        self.current_status = "Failed"
        self.error_message = error_msg
        self.add_log(f"Job FAILED: {error_msg}")
        self.terminate_active_processes()

    def complete(self):
        self.current_status = "Completed"
        self.percentage_complete = 100
        self.current_stage = "Processing Complete"
        self.estimated_completion_time = time.time()
        if "Video Rendering" not in self.completed_stages:
            self.completed_stages.append("Video Rendering")
        self.add_log("Job COMPLETED successfully.")

    def cleanup_files(self):
        """
        Removes temporary image, audio, and intermediate render files associated with this job/product.
        (Note: Completed saved library videos remain intact unless explicitly deleted).
        """
        try:
            media_dir = settings.MEDIA_DIR
            patterns = [
                f"temp_*{self.product_id}*",
                f"temp_no_audio_*{self.product_id}*",
                f"*_temp_{self.product_id}*"
            ]
            cleaned_count = 0
            for pat in patterns:
                for filepath in glob.glob(os.path.join(str(media_dir), pat)):
                    try:
                        if os.path.exists(filepath):
                            os.remove(filepath)
                            cleaned_count += 1
                    except Exception as err:
                        logger.warning(f"Could not remove temp file {filepath}: {err}")
            self.add_log(f"Cleaned up {cleaned_count} temporary intermediate files.")
        except Exception as e:
            logger.error(f"Error during job cleanup_files: {e}")

    def to_dict(self) -> Dict[str, Any]:
        elapsed = int(time.time() - self.started_time)
        remaining = int(max(0, self.estimated_completion_time - time.time()))
        
        # Check stalled state
        is_stalled = self.check_stalled()

        return {
            "job_id": self.job_id,
            "campaign_name": self.campaign_name,
            "product_name": self.product_name,
            "product_id": self.product_id,
            "current_stage": self.current_stage,
            "percentage_complete": self.percentage_complete,
            "started_time": self.started_time,
            "last_updated_time": self.last_updated_time,
            "estimated_completion_time": self.estimated_completion_time,
            "estimated_remaining_time": remaining,
            "elapsed_time": elapsed,
            "current_status": self.current_status,
            "status": self.current_status.lower(),  # Compatibility mapping
            "retry_count": self.retry_count,
            "logs": self.logs,
            "error_message": self.error_message,
            "completed_stages": self.completed_stages,
            "is_stalled": is_stalled,
            "is_cancelled": self.is_cancelled(),
            "is_paused": self.is_paused(),
            "agents": self.agents,
            "agent_durations": self.agent_durations
        }

class BackgroundJobManager:
    def __init__(self):
        self.jobs: Dict[str, BackgroundJob] = {}

    def create_job(self, campaign_name: str, product_name: str, product_id: str, job_id: str = None) -> BackgroundJob:
        if not job_id:
            job_id = str(uuid.uuid4())
        job = BackgroundJob(job_id, campaign_name, product_name, product_id)
        self.jobs[job_id] = job
        # Also store under product_id for compatibility lookups
        self.jobs[product_id] = job
        return job

    def get_job(self, job_id_or_product_id: str) -> Optional[BackgroundJob]:
        if not job_id_or_product_id:
            return None

        job = self.jobs.get(job_id_or_product_id)
        if not job:
            # Automatic restoration from database / mock database
            try:
                from backend.services.supabase_service import supabase_svc
                db_job = supabase_svc.get_video_job(job_id_or_product_id)
                if not db_job:
                    jobs = supabase_svc.get_video_jobs_by_product(job_id_or_product_id)
                    if jobs:
                        db_job = jobs[0]
                
                if db_job:
                    product_id = db_job["product_id"]
                    prod = supabase_svc.get_product(product_id)
                    p_name = prod["name"] if prod else "Product"
                    campaign_name = f"Campaign - {p_name}"
                    
                    job = self.create_job(campaign_name, p_name, product_id, db_job["id"])
                    st = db_job.get("status", "queued")
                    job.current_status = st.capitalize()
                    job.percentage_complete = 100 if st == "completed" else int(db_job.get("progress_step", 0) / 9 * 100)
                    job.current_stage = "Completed" if st == "completed" else (db_job.get("progress_message") or job.current_stage)
                    if db_job.get("error_message"):
                        job.error_message = db_job["error_message"]
            except Exception as err:
                logger.error(f"Failed to auto-restore job from DB: {err}")

        if job:
            job.check_stalled()
        return job

    def cancel_job(self, job_id_or_product_id: str) -> Optional[BackgroundJob]:
        job = self.get_job(job_id_or_product_id)
        if job:
            job.cancel()
        return job

    def delete_job(self, job_id_or_product_id: str) -> bool:
        if not job_id_or_product_id:
            return False

        job = self.jobs.get(job_id_or_product_id)
        product_id = job.product_id if job else job_id_or_product_id

        if job:
            job.cancel()
            job.cleanup_files()
            # Remove all memory references
            keys_to_remove = [k for k, v in self.jobs.items() if v.job_id == job.job_id or v.product_id == job.product_id]
            for k in keys_to_remove:
                self.jobs.pop(k, None)
            
        # Clean up Supabase DB & Mock DB records & physical files unconditionally
        try:
            from backend.services.supabase_service import supabase_svc
            supabase_svc.purge_campaign_data(product_id)
            if job_id_or_product_id != product_id:
                supabase_svc.purge_campaign_data(job_id_or_product_id)
        except Exception as e:
            logger.error(f"Failed to purge video job and campaign records from DB: {e}")
        return True

    def get_active_jobs(self) -> List[BackgroundJob]:
        active_jobs = []
        seen_ids = set()
        active_statuses = ["Queued", "Preparing", "Running", "Waiting", "Rendering", "Uploading"]
        for job in self.jobs.values():
            if job.job_id not in seen_ids:
                seen_ids.add(job.job_id)
                job.check_stalled()
                if job.current_status in active_statuses:
                    active_jobs.append(job)
        return active_jobs

    def list_all_jobs(self, status_filter: Optional[str] = None) -> List[BackgroundJob]:
        seen_ids = set()
        dedup_jobs = []
        for job in self.jobs.values():
            if job.job_id not in seen_ids:
                seen_ids.add(job.job_id)
                job.check_stalled()
                
                if status_filter:
                    sf = status_filter.lower().strip()
                    if sf == "all":
                        dedup_jobs.append(job)
                    elif sf == "running" and job.current_status.lower() in ["running", "preparing", "rendering", "uploading"]:
                        dedup_jobs.append(job)
                    elif sf == job.current_status.lower():
                        dedup_jobs.append(job)
                else:
                    dedup_jobs.append(job)
        return dedup_jobs

job_manager = BackgroundJobManager()
