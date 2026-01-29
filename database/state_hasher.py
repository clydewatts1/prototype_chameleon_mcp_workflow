"""
StateHasher: Cryptographic state verification for Constitutional Atomic Traceability.

Implements Article XVII (Atomic Traceability) by computing SHA-256 hashes
of UOW attributes in a deterministic, database-agnostic manner.

Constitutional Requirement: The same attributes must produce the same hash
regardless of whether they're stored in SQLite, PostgreSQL, Snowflake, or Databricks.

Strategy:
1. Normalize input (handle None, strings, dicts, lists)
2. Sort keys alphabetically (JSON dict consistency)
3. Serialize to UTF-8 JSON (no whitespace)
4. Compute SHA-256 hash (cryptographic strength)
"""

import hashlib
import json
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class StateHasher:
    """Cryptographic state verification utility."""

    @staticmethod
    def compute_content_hash(attributes: Optional[Dict[str, Any]]) -> str:
        """
        Compute deterministic SHA-256 hash of UOW attributes.
        
        **Normalization Protocol (Constitutional Article XVII):**
        1. Handle None/null → empty dict
        2. Sort keys alphabetically (JSON dict consistency)
        3. Serialize to UTF-8 JSON (no whitespace)
        4. Compute SHA-256 hash
        
        **Result:** Same attributes always produce the same hash,
        regardless of database backend or insertion order.
        
        Args:
            attributes: Dict of UOW attributes (may be None)
        
        Returns:
            SHA-256 hash as hex string (64 characters)
        
        Example:
            >>> hash1 = StateHasher.compute_content_hash({"name": "Alice", "age": 30})
            >>> hash2 = StateHasher.compute_content_hash({"age": 30, "name": "Alice"})
            >>> hash1 == hash2  # True: same attributes, same order
            True
        """
        try:
            # Normalize: None → {}
            if attributes is None:
                attributes = {}

            # Sort keys alphabetically for determinism
            # This ensures {"a": 1, "b": 2} and {"b": 2, "a": 1} produce identical hash
            normalized_json = json.dumps(
                attributes,
                sort_keys=True,
                separators=(',', ':'),  # Remove spaces for consistency
                default=str  # Handle non-JSON-serializable types
            )

            # Encode to UTF-8 bytes
            json_bytes = normalized_json.encode('utf-8')

            # Compute SHA-256 hash
            hash_hex = hashlib.sha256(json_bytes).hexdigest()

            return hash_hex

        except Exception as e:
            logger.error(f"Failed to compute content hash: {e}")
            raise StateHasherError(f"Hash computation failed: {e}")

    @staticmethod
    def verify_state_hash(
        current_attributes: Dict[str, Any],
        recorded_hash: str
    ) -> bool:
        """
        Verify that current attributes match recorded hash.
        
        Constitutional Article XVII: Detect state drift via hash mismatch.
        
        Args:
            current_attributes: Current UOW attributes
            recorded_hash: Previously recorded hash
        
        Returns:
            True if current hash matches recorded hash (state intact)
            False if mismatch (unauthorized modification detected)
        """
        try:
            current_hash = StateHasher.compute_content_hash(current_attributes)
            return current_hash == recorded_hash
        except Exception as e:
            logger.error(f"Failed to verify state hash: {e}")
            return False

    @staticmethod
    def get_hash_diff(
        previous_attributes: Dict[str, Any],
        current_attributes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compute human-readable diff between two attribute sets.
        
        Useful for audit trails and continuous learning.
        
        Args:
            previous_attributes: Prior state
            current_attributes: Current state
        
        Returns:
            Dict with added, removed, and modified keys
        """
        try:
            added = {}
            removed = {}
            modified = {}

            prev_keys = set(previous_attributes.keys() if previous_attributes else {})
            curr_keys = set(current_attributes.keys() if current_attributes else {})

            # Added keys
            for key in curr_keys - prev_keys:
                added[key] = current_attributes[key]

            # Removed keys
            for key in prev_keys - curr_keys:
                removed[key] = previous_attributes[key]

            # Modified keys
            for key in prev_keys & curr_keys:
                if previous_attributes[key] != current_attributes[key]:
                    modified[key] = {
                        "previous": previous_attributes[key],
                        "current": current_attributes[key]
                    }

            return {
                "added": added,
                "removed": removed,
                "modified": modified
            }

        except Exception as e:
            logger.error(f"Failed to compute hash diff: {e}")
            return {}


class StateHasherError(Exception):
    """Raised when state hashing operation fails."""
    pass
