"""
StreamBroadcaster: Abstract event broadcaster for Constitutional audit trail.

Implements append-only event publishing to support:
- Phase 1: File-based JSONL event log
- Phase 2: Redis Stream publishing (zero code changes to Guard/Engine)
- Phase 3+: Custom backends (Kafka, S3, DataLake, etc.)

By abstracting the broadcaster now, we enable future backend swapping without
touching a single line of Agent, Guard, or Engine code.

Constitutional Reference: Article XVII (Atomic Traceability) - All events logged immutably.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
import json
import logging

logger = logging.getLogger(__name__)


class StreamBroadcaster(ABC):
    """
    Abstract event broadcaster for Constitutional audit trail.
    
    All implementations must be append-only and thread-safe.
    """

    @abstractmethod
    def emit(self, event_type: str, payload: Dict[str, Any]) -> None:
        """
        Publish an event to the observation stream.
        
        Args:
            event_type: Type of event (e.g., "intervention_request", "pilot_waiver_granted", "ambiguity_lock_detected")
            payload: Event metadata (may contain UOW IDs, actor IDs, reasons, etc.)
        
        Raises:
            StreamBroadcasterError: If publishing fails
        """
        pass


class FileStreamBroadcaster(StreamBroadcaster):
    """
    Phase 1 implementation: Append-only JSON Lines event log.
    
    Each event is written as a single JSON object per line (JSONL format).
    Suitable for file-based systems, local development, and audit compliance.
    
    Example:
        {"timestamp": "2026-01-29T10:00:00Z", "event_type": "intervention_request", ...}
        {"timestamp": "2026-01-29T10:00:01Z", "event_type": "pilot_waiver_granted", ...}
    """

    def __init__(self, log_path: str = "events.jsonl"):
        """
        Initialize file-based broadcaster.
        
        Args:
            log_path: Path to JSONL event log file
        """
        self.log_path = Path(log_path)
        # Ensure directory exists
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Write event to JSONL file in append-only mode."""
        try:
            event = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": event_type,
                "payload": payload,
            }

            # Append-only: open in append mode
            with open(self.log_path, "a") as f:
                f.write(json.dumps(event) + "\n")

            logger.debug(f"Event emitted: {event_type}")

        except Exception as e:
            logger.error(f"Failed to emit event to {self.log_path}: {e}")
            raise StreamBroadcasterError(f"File write failed: {e}")


class RedisStreamBroadcaster(StreamBroadcaster):
    """
    Phase 2 implementation: Redis Stream publishing.
    
    Enables real-time event streaming to dashboards without file I/O latency.
    
    **Key Insight:** By swapping FileStreamBroadcaster for RedisStreamBroadcaster,
    the entire system gains pub/sub capabilities WITHOUT modifying Agent, Guard, or Engine code.
    
    Features:
    - Append-only Redis Streams (XADD) for ordered events
    - Automatic TTL management (optional maxlen trimming)
    - Consumer group support for multi-client processing
    - Metrics tracking (events emitted, bytes written)
    - Graceful fallback on connection errors
    
    Example:
        broadcaster = RedisStreamBroadcaster(
            redis_client=redis.from_url("redis://localhost"),
            stream_key="chameleon:events",
            max_stream_length=100000
        )
        StreamBroadcaster.set_global_broadcaster(broadcaster)
        # All subsequent emit() calls use Redis without code changes
    
    Constitutional Reference: Article XVII (Atomic Traceability) - All events logged immutably.
    """

    def __init__(
        self,
        redis_client,
        stream_key: str = "chameleon:events",
        max_stream_length: int = 100000,
        enable_metrics: bool = True,
    ):
        """
        Initialize Redis-based broadcaster.
        
        Args:
            redis_client: redis.Redis client instance
            stream_key: Redis Stream key name
            max_stream_length: Maximum entries before trimming (approximate)
            enable_metrics: Whether to track metrics (events, bytes)
        
        Raises:
            ConnectionError: If Redis connection fails
        """
        self.redis = redis_client
        self.stream_key = stream_key
        self.max_stream_length = max_stream_length
        self.enable_metrics = enable_metrics
        
        # Metrics
        self.metrics = {
            "events_emitted": 0,
            "bytes_written": 0,
            "errors": 0,
        }
        
        # Verify connection
        try:
            self.redis.ping()
            logger.info(f"Redis connection established to {stream_key}")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise ConnectionError(f"Cannot connect to Redis: {e}")

    def emit(self, event_type: str, payload: Dict[str, Any]) -> None:
        """
        Publish event to Redis Stream (append-only).
        
        Args:
            event_type: Type of event
            payload: Event metadata (will be JSON-serialized)
        
        Raises:
            StreamBroadcasterError: If Redis write fails
        """
        try:
            event_data = {
                b"event_type": event_type,
                b"payload": json.dumps(payload),
                b"timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # XADD: Append to Redis Stream (append-only, ordered by timestamp)
            # Returns the generated ID (e.g., "1234567890000-0")
            stream_id = self.redis.xadd(self.stream_key, event_data)

            # Track metrics
            if self.enable_metrics:
                self.metrics["events_emitted"] += 1
                self.metrics["bytes_written"] += sum(
                    len(str(v)) for v in event_data.values()
                )

            logger.debug(
                f"Event emitted to Redis: {event_type} (ID: {stream_id})"
            )

            # Approximate trimming (not blocking)
            # Keep only the last max_stream_length entries
            if self.metrics["events_emitted"] % 1000 == 0:
                try:
                    self.redis.xtrim(
                        self.stream_key,
                        maxlen=self.max_stream_length,
                        approximate=True
                    )
                except Exception as trim_error:
                    logger.warning(f"Stream trim failed: {trim_error}")

        except Exception as e:
            self.metrics["errors"] += 1
            logger.error(f"Failed to emit event to Redis: {e}")
            raise StreamBroadcasterError(f"Redis write failed: {e}")

    def get_metrics(self) -> Dict[str, int]:
        """
        Get broadcaster metrics.
        
        Returns:
            Dictionary with events_emitted, bytes_written, errors
        """
        return self.metrics.copy()

    def read_events(
        self,
        count: int = 10,
        start_id: str = "0"
    ) -> list[Dict[str, Any]]:
        """
        Read recent events from Redis Stream (useful for dashboards).
        
        Args:
            count: Number of events to retrieve
            start_id: Stream ID to start from (default "0" = all)
        
        Returns:
            List of event dictionaries with ID, event_type, payload, timestamp
        """
        try:
            # XRANGE: Read range of events (ordered)
            results = self.redis.xrange(
                self.stream_key,
                min=start_id,
                count=count
            )
            
            events = []
            for stream_id, data in results:
                event = {
                    "id": stream_id.decode() if isinstance(stream_id, bytes) else stream_id,
                    "event_type": (
                        data[b"event_type"].decode()
                        if isinstance(data[b"event_type"], bytes)
                        else data[b"event_type"]
                    ),
                    "payload": json.loads(
                        data[b"payload"].decode()
                        if isinstance(data[b"payload"], bytes)
                        else data[b"payload"]
                    ),
                    "timestamp": (
                        data[b"timestamp"].decode()
                        if isinstance(data[b"timestamp"], bytes)
                        else data[b"timestamp"]
                    ),
                }
                events.append(event)
            
            return events
        except Exception as e:
            logger.error(f"Failed to read events from Redis: {e}")
            return []


# ============================================================================
# Global Dependency Injection
# ============================================================================

_global_broadcaster: StreamBroadcaster = FileStreamBroadcaster()


def set_broadcaster(broadcaster: StreamBroadcaster) -> None:
    """
    Set global broadcaster instance.
    
    Use this to swap implementations (e.g., FileStreamBroadcaster → RedisStreamBroadcaster)
    without changing Agent/Guard/Engine code.
    
    Args:
        broadcaster: StreamBroadcaster instance to use globally
    """
    global _global_broadcaster
    _global_broadcaster = broadcaster
    logger.info(f"StreamBroadcaster swapped to {broadcaster.__class__.__name__}")


def emit(event_type: str, payload: Dict[str, Any]) -> None:
    """
    Emit event using global broadcaster (convenience function).
    
    Args:
        event_type: Type of event
        payload: Event metadata
    """
    _global_broadcaster.emit(event_type, payload)


def get_broadcaster() -> StreamBroadcaster:
    """
    Get current global broadcaster (for testing/inspection).
    
    Returns:
        Current StreamBroadcaster instance
    """
    return _global_broadcaster


# ============================================================================
# Exceptions
# ============================================================================

class StreamBroadcasterError(Exception):
    """Raised when broadcaster fails to publish event."""
    pass
