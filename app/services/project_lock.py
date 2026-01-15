"""Redis-based distributed lock for project-level sequential processing.

Provides project-level locking to ensure:
- Same project: Sequential processing (FIFO)
- Different projects: Concurrent processing
"""
import asyncio
from typing import Optional
from contextlib import asynccontextmanager

import structlog
import redis.asyncio as redis_async

from app.config import settings

logger = structlog.get_logger()


class ProjectLockManager:
    """Redis-based distributed lock manager for project-level sequential processing.
    
    Features:
    - Project-specific locks (different projects can process concurrently)
    - FIFO ordering within same project using Redis lists
    - Automatic lock expiry (prevents deadlocks)
    - Graceful fallback if Redis unavailable
    """
    
    LOCK_PREFIX = "stolink:lock:project:"
    QUEUE_PREFIX = "stolink:queue:project:"
    DEFAULT_LOCK_TTL = 600  # 10 minutes (max analysis time)
    ACQUIRE_TIMEOUT = 300   # 5 minutes max wait
    
    def __init__(self):
        self._redis: Optional[redis_async.Redis] = None
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize Redis connection."""
        if self._initialized:
            return True
        
        try:
            self._redis = redis_async.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=5
            )
            await self._redis.ping()
            self._initialized = True
            logger.info("ProjectLockManager initialized", redis_url=settings.redis_url.split("@")[-1])
            return True
        except Exception as e:
            logger.warning("Redis unavailable, falling back to no-lock mode", error=str(e))
            self._redis = None
            return False
    
    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None
            self._initialized = False
    
    @asynccontextmanager
    async def acquire_project_lock(self, project_id: str, job_id: str):
        """Acquire project-level lock with FIFO ordering.
        
        Usage:
            async with lock_manager.acquire_project_lock(project_id, job_id):
                # Process document
        
        Args:
            project_id: Project to lock
            job_id: Unique identifier for this job (for queue ordering)
        """
        if not self._redis:
            # Fallback: No locking (concurrent processing)
            logger.debug("No Redis, skipping lock", project_id=project_id)
            yield
            return
        
        lock_key = f"{self.LOCK_PREFIX}{project_id}"
        queue_key = f"{self.QUEUE_PREFIX}{project_id}"
        acquired = False
        
        try:
            # 1. Add self to project queue (FIFO ordering)
            await self._redis.rpush(queue_key, job_id)
            await self._redis.expire(queue_key, self.DEFAULT_LOCK_TTL * 2)  # Queue TTL
            
            logger.info("Added to project queue", project_id=project_id, job_id=job_id)
            
            # 2. Wait until we're at the front of the queue AND can acquire lock
            start_time = asyncio.get_event_loop().time()
            
            while True:
                # Check if we're first in queue
                first_in_queue = await self._redis.lindex(queue_key, 0)
                
                if first_in_queue == job_id:
                    # Try to acquire the lock
                    acquired = await self._redis.set(
                        lock_key, 
                        job_id, 
                        nx=True,  # Only if not exists
                        ex=self.DEFAULT_LOCK_TTL
                    )
                    
                    if acquired:
                        logger.info("Project lock acquired", project_id=project_id, job_id=job_id)
                        break
                
                # Check timeout
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > self.ACQUIRE_TIMEOUT:
                    logger.warning(
                        "Lock acquisition timeout, proceeding anyway",
                        project_id=project_id,
                        job_id=job_id,
                        elapsed=elapsed
                    )
                    break
                
                # Wait before retry
                await asyncio.sleep(1)
            
            yield
            
        finally:
            # 3. Release lock and remove from queue
            if acquired:
                await self._redis.delete(lock_key)
                logger.info("Project lock released", project_id=project_id, job_id=job_id)
            
            # Remove self from queue (may have already been removed)
            await self._redis.lrem(queue_key, 1, job_id)

    async def acquire_lock(self, project_id: str, job_id: str) -> bool:
        """Manually acquire project lock. Call release_lock when done.
        
        Returns:
            True if lock acquired, False if Redis unavailable
        """
        if not self._redis:
            logger.debug("No Redis, skipping lock", project_id=project_id)
            return False
        
        lock_key = f"{self.LOCK_PREFIX}{project_id}"
        queue_key = f"{self.QUEUE_PREFIX}{project_id}"
        
        # 1. Add self to project queue (FIFO ordering)
        await self._redis.rpush(queue_key, job_id)
        await self._redis.expire(queue_key, self.DEFAULT_LOCK_TTL * 2)
        
        logger.info("Added to project queue", project_id=project_id, job_id=job_id)
        
        # 2. Wait until we're at the front of the queue AND can acquire lock
        start_time = asyncio.get_event_loop().time()
        
        while True:
            first_in_queue = await self._redis.lindex(queue_key, 0)
            
            if first_in_queue == job_id:
                acquired = await self._redis.set(
                    lock_key, 
                    job_id, 
                    nx=True,
                    ex=self.DEFAULT_LOCK_TTL
                )
                
                if acquired:
                    logger.info("Project lock acquired", project_id=project_id, job_id=job_id)
                    return True
            
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > self.ACQUIRE_TIMEOUT:
                logger.warning("Lock acquisition timeout, proceeding anyway", project_id=project_id, job_id=job_id)
                return False
            
            await asyncio.sleep(1)

    async def release_lock(self, project_id: str, job_id: str) -> None:
        """Manually release project lock."""
        if not self._redis:
            return
        
        lock_key = f"{self.LOCK_PREFIX}{project_id}"
        queue_key = f"{self.QUEUE_PREFIX}{project_id}"
        
        # Delete lock
        await self._redis.delete(lock_key)
        logger.info("Project lock released", project_id=project_id, job_id=job_id)
        
        # Remove from queue
        await self._redis.lrem(queue_key, 1, job_id)


# Singleton instance
_lock_manager: Optional[ProjectLockManager] = None


async def get_project_lock_manager() -> ProjectLockManager:
    """Get or create the lock manager singleton."""
    global _lock_manager
    if _lock_manager is None:
        _lock_manager = ProjectLockManager()
        await _lock_manager.initialize()
    return _lock_manager
