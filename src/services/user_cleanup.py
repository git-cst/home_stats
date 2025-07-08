import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from db.repositories.user_repo import UserRepository

logger = logging.getLogger(__name__)

class DataCleanupService:
    def __init__(self, user_repo: UserRepository, grace_period_days: int = 30):
        self.user_repo = user_repo
        self.grace_period_days = grace_period_days
        self.next_cleanup: Optional[datetime] = None
        self.last_cleanup: Optional[datetime] = None
        self.last_cleanup_result: Optional[dict] = None
        self._task: Optional[asyncio.Task] = None
    
    async def start_daily_cleanup(self):
        """Start daily cleanup background task"""
        if self._task and not self._task.done():
            logger.warning("Cleanup task already running")
            return
        
        self._task = asyncio.create_task(self._daily_cleanup_loop())
        logger.info("Daily cleanup task started")
    
    async def stop_cleanup(self):
        """Stop the cleanup task"""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                logger.info("Cleanup task stopped")
    
    async def _daily_cleanup_loop(self):
        """Simple daily cleanup loop"""

        while True:
            try:
                await asyncio.sleep(86400)  # 24 hours         
                # Record when cleanup starts
                cleanup_start = datetime.now()

                deleted_count = await self.cleanup_expired_deletions()       

                self.last_cleanup = cleanup_start
                                
                # Calculate next cleanup and record results
                self.next_cleanup = datetime.now() + timedelta(seconds=86400)
                duration = (datetime.now() - cleanup_start).total_seconds()
                
                self.last_cleanup_result = {
                    "deleted_users": deleted_count,
                    "duration_seconds": duration,
                    "timestamp": cleanup_start.isoformat(),
                    "status": "success"
                }
                
                logger.info(f"Daily cleanup completed. Deleted {deleted_count} expired users.")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Daily cleanup failed: {e}")

                # Record failure but continue running
                self.last_cleanup_result = {
                    "deleted_users": 0,
                    "duration_seconds": 0,
                    "timestamp": datetime.now().isoformat(),
                    "status": "failed",
                    "error": str(e)
                }
            
                # Still set next cleanup time even on failure
                self.next_cleanup = datetime.utcnow() + timedelta(seconds=86400)

    
    async def cleanup_expired_deletions(self) -> int:
        """The actual cleanup logic"""
        cutoff_date = datetime.now() - timedelta(days=self.grace_period_days)
        expired_users = await self.user_repo.get_expired_soft_deleted_users(cutoff_date)
        
        deleted_count = 0
        for user in expired_users:
            try:
                success = await self.user_repo.hard_delete_user(user['id'])
                if success:
                    deleted_count += 1
                    logger.info(f"Deleted expired user: {user['id']}")
            except Exception as e:
                logger.error(f"Failed to delete user {user['id']}: {e}")
        
        return deleted_count
    
    async def manual_cleanup(self) -> dict:
        """Manual cleanup for admin endpoint"""
        start_time = datetime.now()
        deleted_count = await self.cleanup_expired_deletions()
        duration = (datetime.now() - start_time).total_seconds()
        
        return {
            "deleted_users": deleted_count,
            "duration_seconds": duration,
            "timestamp": start_time.isoformat()
        }

# Global instance - only created when needed
cleanup_service: Optional[DataCleanupService] = None