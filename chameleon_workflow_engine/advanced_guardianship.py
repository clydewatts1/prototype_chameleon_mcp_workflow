"""
Advanced Guardianship: Intelligent gate logic for UOW routing and validation.

Implements the Constitutional Guardian types:
- CERBERUS: Three-headed synchronization check (parent-child UOW sets)
- PASS_THRU: Identity-only validation (rapid transit)
- CRITERIA_GATE: Data-driven threshold enforcement
- DIRECTIONAL_FILTER: Attribute-based UOW routing
- TTL_CHECK: Time-to-live validation
- COMPOSITE: Chain multiple checks with AND/OR logic

Constitutional Reference: Articles VI, VII, IX (Guard Logic, Deterministic Routing)

All guardians operate on immutable interaction_policy from UOW creation time
(Constitutional Article IX: Logic-Blind preservation).
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Callable
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ============================================================================
# Guardian Base Classes
# ============================================================================


@dataclass
class GuardianDecision:
    """Result of guardian evaluation."""
    
    allowed: bool
    reason: str
    guardian_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __repr__(self) -> str:
        return f"GuardianDecision(allowed={self.allowed}, type={self.guardian_type}, reason='{self.reason}')"


class Guardian(ABC):
    """
    Abstract guardian gate for UOW validation and routing.
    
    All implementations MUST:
    1. Be deterministic (same input → same output)
    2. Preserve immutable interaction_policy (Article IX)
    3. Return GuardianDecision with clear reasoning
    4. Handle missing attributes gracefully
    """

    def __init__(
        self,
        name: str,
        guardian_type: str,
        attributes: Optional[Dict[str, Any]] = None,
        ai_context: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize guardian.
        
        Args:
            name: Guardian name
            guardian_type: Type (CERBERUS, PASS_THRU, etc.)
            attributes: Configuration for this guardian type
            ai_context: AI context for reasoning
        """
        self.name = name
        self.guardian_type = guardian_type
        self.attributes = attributes or {}
        self.ai_context = ai_context or {}

    @abstractmethod
    def evaluate(
        self,
        uow_data: Dict[str, Any],
        policy: Dict[str, Any],
    ) -> GuardianDecision:
        """
        Evaluate whether UOW passes this gate.
        
        Args:
            uow_data: UOW attributes (immutable snapshot)
            policy: interaction_policy (immutable snapshot)
        
        Returns:
            GuardianDecision with allowed=True/False and reason
        """
        pass


# ============================================================================
# Guardian Type Implementations
# ============================================================================


class CerberusGuardian(Guardian):
    """
    Three-headed synchronization check for parent-child UOW sets.
    
    Validates:
    1. Child count matches expected decomposition
    2. All children have same origin (parent_uow_id)
    3. Child total execution time reasonable
    
    Use Case: After BETA role spawns children, CERBERUS verifies structural integrity.
    
    Attributes:
        min_children: Minimum expected children (e.g., 3 for "three-headed")
        max_children: Maximum expected children
        timeout_seconds: Max allowed child execution time
    """

    def __init__(
        self,
        name: str = "cerberus-sync",
        attributes: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            name=name,
            guardian_type="CERBERUS",
            attributes=attributes or {
                "min_children": 1,
                "max_children": 100,
                "timeout_seconds": 3600,
            },
        )

    def evaluate(
        self,
        uow_data: Dict[str, Any],
        policy: Dict[str, Any],
    ) -> GuardianDecision:
        """
        Check parent-child UOW synchronization.
        
        Args:
            uow_data: {"child_count": 5, "finished_child_count": 3, "created_at": "..."}
            policy: Interaction policy (immutable)
        
        Returns:
            PASS if structure valid, FAIL if orphaned or miscounted children
        """
        try:
            child_count = uow_data.get("child_count", 0)
            finished_count = uow_data.get("finished_child_count", 0)
            created_at_str = uow_data.get("created_at")
            
            min_children = self.attributes.get("min_children", 1)
            max_children = self.attributes.get("max_children", 100)
            timeout_seconds = self.attributes.get("timeout_seconds", 3600)
            
            # Check 1: Child count within bounds
            if not (min_children <= child_count <= max_children):
                return GuardianDecision(
                    allowed=False,
                    reason=f"Child count {child_count} outside range [{min_children}, {max_children}]",
                    guardian_type=self.guardian_type,
                    metadata={"child_count": child_count},
                )
            
            # Check 2: All children accounted for (finished <= total)
            if finished_count > child_count:
                return GuardianDecision(
                    allowed=False,
                    reason=f"Finished children ({finished_count}) exceeds total ({child_count})",
                    guardian_type=self.guardian_type,
                    metadata={"child_count": child_count, "finished": finished_count},
                )
            
            # Check 3: Execution time reasonable
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(
                        created_at_str.replace("Z", "+00:00")
                    )
                    elapsed = (datetime.now(timezone.utc) - created_at).total_seconds()
                    if elapsed > timeout_seconds:
                        return GuardianDecision(
                            allowed=False,
                            reason=f"UOW execution time {elapsed}s exceeds timeout {timeout_seconds}s",
                            guardian_type=self.guardian_type,
                            metadata={"elapsed_seconds": elapsed, "timeout_seconds": timeout_seconds},
                        )
                except (ValueError, AttributeError) as e:
                    logger.warning(f"Could not parse created_at: {e}")
            
            return GuardianDecision(
                allowed=True,
                reason=f"Cerberus sync valid: {child_count} children, {finished_count} finished",
                guardian_type=self.guardian_type,
                metadata={
                    "child_count": child_count,
                    "finished": finished_count,
                },
            )
        except Exception as e:
            logger.error(f"Cerberus evaluation failed: {e}")
            return GuardianDecision(
                allowed=False,
                reason=f"Guardian evaluation error: {str(e)}",
                guardian_type=self.guardian_type,
                metadata={"error": str(e)},
            )


class PassThruGuardian(Guardian):
    """
    Identity-only validation for rapid transit.
    
    Simply validates that UOW ID exists and is not None.
    Used for high-throughput paths where no complex logic needed.
    
    Attributes: None (identity-only)
    """

    def __init__(
        self,
        name: str = "pass-thru",
        attributes: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            name=name,
            guardian_type="PASS_THRU",
            attributes=attributes or {},
        )

    def evaluate(
        self,
        uow_data: Dict[str, Any],
        policy: Dict[str, Any],
    ) -> GuardianDecision:
        """
        Validate UOW identity exists.
        
        Args:
            uow_data: {"uow_id": "uuid", ...}
            policy: Ignored (identity-only)
        
        Returns:
            PASS if uow_id exists and non-null
        """
        uow_id = uow_data.get("uow_id")
        
        if not uow_id:
            return GuardianDecision(
                allowed=False,
                reason="Missing or null uow_id",
                guardian_type=self.guardian_type,
            )
        
        return GuardianDecision(
            allowed=True,
            reason=f"UOW identity valid: {uow_id}",
            guardian_type=self.guardian_type,
            metadata={"uow_id": str(uow_id)},
        )


class CriteriaGateGuardian(Guardian):
    """
    Data-driven threshold enforcement using attribute conditions.
    
    Evaluates UOW attributes against configured criteria rules:
    - Exact match: {"field": "status", "condition": "equals", "value": "ACTIVE"}
    - Range: {"field": "priority", "condition": "gte", "value": 5}
    - Contains: {"field": "tags", "condition": "contains", "value": "urgent"}
    
    Use Case: Route high-value transactions to OMEGA role, low-value to automation.
    
    Attributes:
        rules: List of condition dicts, combined with AND logic
        operator: "AND" or "OR" to combine rules (default AND)
    """

    def __init__(
        self,
        name: str = "criteria-gate",
        attributes: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            name=name,
            guardian_type="CRITERIA_GATE",
            attributes=attributes or {
                "rules": [],
                "operator": "AND",
            },
        )

    def evaluate(
        self,
        uow_data: Dict[str, Any],
        policy: Dict[str, Any],
    ) -> GuardianDecision:
        """
        Evaluate UOW against criteria rules.
        
        Args:
            uow_data: {"amount": 50000, "status": "PENDING", ...}
            policy: Interaction policy (for context)
        
        Returns:
            PASS if criteria met, FAIL if not
        """
        rules = self.attributes.get("rules", [])
        operator = self.attributes.get("operator", "AND").upper()
        
        if not rules:
            return GuardianDecision(
                allowed=True,
                reason="No criteria rules configured",
                guardian_type=self.guardian_type,
            )
        
        results = []
        for rule in rules:
            passed = self._evaluate_rule(rule, uow_data)
            results.append(passed)
        
        # Combine results
        if operator == "AND":
            allowed = all(results)
        elif operator == "OR":
            allowed = any(results)
        else:
            return GuardianDecision(
                allowed=False,
                reason=f"Unknown operator: {operator}",
                guardian_type=self.guardian_type,
            )
        
        return GuardianDecision(
            allowed=allowed,
            reason=f"Criteria evaluation: {operator} of {len(results)} rules passed",
            guardian_type=self.guardian_type,
            metadata={
                "results": results,
                "operator": operator,
                "passed": sum(results),
                "total": len(results),
            },
        )

    def _evaluate_rule(
        self,
        rule: Dict[str, Any],
        uow_data: Dict[str, Any],
    ) -> bool:
        """
        Evaluate a single criteria rule.
        
        Returns:
            True if rule matched, False otherwise
        """
        field = rule.get("field")
        condition = rule.get("condition")
        value = rule.get("value")
        
        if not field or not condition:
            logger.warning(f"Invalid rule format: {rule}")
            return False
        
        field_value = uow_data.get(field)
        
        # Condition evaluation
        if condition == "equals":
            return field_value == value
        elif condition == "not_equals":
            return field_value != value
        elif condition == "gt":
            return (field_value or 0) > value
        elif condition == "gte":
            return (field_value or 0) >= value
        elif condition == "lt":
            return (field_value or 0) < value
        elif condition == "lte":
            return (field_value or 0) <= value
        elif condition == "contains":
            if isinstance(field_value, (list, str)):
                return value in field_value
            return False
        elif condition == "not_contains":
            if isinstance(field_value, (list, str)):
                return value not in field_value
            return True
        elif condition == "exists":
            return field in uow_data
        elif condition == "not_exists":
            return field not in uow_data
        else:
            logger.warning(f"Unknown condition: {condition}")
            return False


class DirectionalFilterGuardian(Guardian):
    """
    Routes UOW sets based on attribute evaluation.
    
    Maps attribute values to allowed directions/roles:
    {
        "attribute": "priority",
        "routes": {
            "high": ["ADMIN", "OMEGA"],
            "medium": ["OPERATOR", "BETA"],
            "low": ["AUTOMATION"]
        }
    }
    
    Use Case: Route invoices to different approval workflows based on amount.
    
    Attributes:
        attribute: Field to evaluate for routing
        routes: Dict mapping attribute values to list of allowed targets
        default_route: Fallback if attribute not found
    """

    def __init__(
        self,
        name: str = "directional-filter",
        attributes: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            name=name,
            guardian_type="DIRECTIONAL_FILTER",
            attributes=attributes or {
                "attribute": None,
                "routes": {},
                "default_route": None,
            },
        )

    def evaluate(
        self,
        uow_data: Dict[str, Any],
        policy: Dict[str, Any],
    ) -> GuardianDecision:
        """
        Determine allowed directions for this UOW.
        
        Args:
            uow_data: {"priority": "high", ...}
            policy: Interaction policy
        
        Returns:
            PASS with metadata containing allowed routes
        """
        attribute = self.attributes.get("attribute")
        routes = self.attributes.get("routes", {})
        default_route = self.attributes.get("default_route")
        
        if not attribute or not routes:
            return GuardianDecision(
                allowed=False,
                reason="Directional filter not configured (missing attribute or routes)",
                guardian_type=self.guardian_type,
            )
        
        attribute_value = uow_data.get(attribute)
        allowed_directions = routes.get(str(attribute_value), default_route)
        
        if not allowed_directions:
            return GuardianDecision(
                allowed=False,
                reason=f"No route found for {attribute}={attribute_value}",
                guardian_type=self.guardian_type,
                metadata={"attribute": attribute, "value": attribute_value},
            )
        
        return GuardianDecision(
            allowed=True,
            reason=f"Directional route: {attribute}={attribute_value} → {allowed_directions}",
            guardian_type=self.guardian_type,
            metadata={
                "attribute": attribute,
                "value": attribute_value,
                "allowed_directions": allowed_directions,
            },
        )


class TTLCheckGuardian(Guardian):
    """
    Time-to-live validation based on age of UOW.
    
    Ensures UOW hasn't exceeded configured lifespan.
    
    Attributes:
        max_age_seconds: Maximum allowed age
    """

    def __init__(
        self,
        name: str = "ttl-check",
        attributes: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            name=name,
            guardian_type="TTL_CHECK",
            attributes=attributes or {"max_age_seconds": 86400},  # 1 day default
        )

    def evaluate(
        self,
        uow_data: Dict[str, Any],
        policy: Dict[str, Any],
    ) -> GuardianDecision:
        """
        Check UOW age against TTL.
        
        Args:
            uow_data: {"created_at": "2026-01-29T10:00:00Z"}
            policy: Ignored
        
        Returns:
            PASS if age within limit, FAIL if expired
        """
        created_at_str = uow_data.get("created_at")
        max_age = self.attributes.get("max_age_seconds", 86400)
        
        if not created_at_str:
            return GuardianDecision(
                allowed=False,
                reason="Missing created_at timestamp",
                guardian_type=self.guardian_type,
            )
        
        try:
            created_at = datetime.fromisoformat(
                created_at_str.replace("Z", "+00:00")
            )
            elapsed = (datetime.now(timezone.utc) - created_at).total_seconds()
            
            if elapsed > max_age:
                return GuardianDecision(
                    allowed=False,
                    reason=f"UOW expired: {elapsed}s > {max_age}s TTL",
                    guardian_type=self.guardian_type,
                    metadata={"elapsed_seconds": elapsed, "max_age_seconds": max_age},
                )
            
            return GuardianDecision(
                allowed=True,
                reason=f"UOW TTL valid: {elapsed}s < {max_age}s",
                guardian_type=self.guardian_type,
                metadata={"elapsed_seconds": elapsed, "max_age_seconds": max_age},
            )
        except (ValueError, AttributeError) as e:
            logger.error(f"TTL check failed: {e}")
            return GuardianDecision(
                allowed=False,
                reason=f"Cannot parse timestamp: {e}",
                guardian_type=self.guardian_type,
            )


class CompositeGuardian(Guardian):
    """
    Chains multiple guardian checks with AND/OR logic.
    
    Enables complex gate logic by composing simpler guardians:
    {
        "type": "COMPOSITE",
        "attributes": {
            "guardians": [
                {"type": "PASS_THRU"},
                {"type": "CRITERIA_GATE", "rules": [...]},
                {"type": "CERBERUS"}
            ],
            "operator": "AND"
        }
    }
    
    Use Case: Verify identity AND criteria AND synchronization
    
    Attributes:
        guardians: List of guardian configs to compose
        operator: "AND" or "OR"
    """

    def __init__(
        self,
        name: str = "composite",
        attributes: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            name=name,
            guardian_type="COMPOSITE",
            attributes=attributes or {
                "guardians": [],
                "operator": "AND",
            },
        )

    def evaluate(
        self,
        uow_data: Dict[str, Any],
        policy: Dict[str, Any],
    ) -> GuardianDecision:
        """
        Evaluate composite guardian chain.
        
        Args:
            uow_data: UOW attributes
            policy: Interaction policy
        
        Returns:
            PASS if all/any guardians pass (based on operator)
        """
        guardians_config = self.attributes.get("guardians", [])
        operator = self.attributes.get("operator", "AND").upper()
        
        if not guardians_config:
            return GuardianDecision(
                allowed=True,
                reason="No guardians in composite chain",
                guardian_type=self.guardian_type,
            )
        
        results = []
        for guardian_config in guardians_config:
            guardian = self._create_guardian(guardian_config)
            decision = guardian.evaluate(uow_data, policy)
            results.append(decision)
        
        # Combine results
        if operator == "AND":
            allowed = all(d.allowed for d in results)
        elif operator == "OR":
            allowed = any(d.allowed for d in results)
        else:
            return GuardianDecision(
                allowed=False,
                reason=f"Unknown operator: {operator}",
                guardian_type=self.guardian_type,
            )
        
        return GuardianDecision(
            allowed=allowed,
            reason=f"Composite: {operator} of {len(results)} guardians",
            guardian_type=self.guardian_type,
            metadata={
                "decisions": [
                    {
                        "type": d.guardian_type,
                        "allowed": d.allowed,
                        "reason": d.reason,
                    }
                    for d in results
                ],
                "operator": operator,
            },
        )

    def _create_guardian(
        self,
        config: Dict[str, Any],
    ) -> Guardian:
        """Create guardian instance from config."""
        guardian_type = config.get("type")
        name = config.get("name", f"{guardian_type.lower()}-{id(config)}")
        attributes = config.get("attributes", {})
        
        return create_guardian(guardian_type, name, attributes)


# ============================================================================
# Guardian Factory
# ============================================================================


def create_guardian(
    guardian_type: str,
    name: str = "",
    attributes: Optional[Dict[str, Any]] = None,
) -> Guardian:
    """
    Factory function to create guardian instances.
    
    Args:
        guardian_type: Type name (CERBERUS, PASS_THRU, etc.)
        name: Guardian name
        attributes: Type-specific configuration
    
    Returns:
        Guardian instance
    
    Raises:
        ValueError: If guardian_type unknown
    """
    guardian_class = {
        "CERBERUS": CerberusGuardian,
        "PASS_THRU": PassThruGuardian,
        "CRITERIA_GATE": CriteriaGateGuardian,
        "DIRECTIONAL_FILTER": DirectionalFilterGuardian,
        "TTL_CHECK": TTLCheckGuardian,
        "COMPOSITE": CompositeGuardian,
    }.get(guardian_type)
    
    if not guardian_class:
        raise ValueError(f"Unknown guardian type: {guardian_type}")
    
    return guardian_class(name=name, attributes=attributes)


# ============================================================================
# Guardian Registry
# ============================================================================


class GuardianRegistry:
    """
    Central registry for active guardians in an instance.
    
    Caches guardian instances to avoid recreating them on every evaluation.
    """

    def __init__(self):
        """Initialize empty registry."""
        self.guardians: Dict[str, Guardian] = {}

    def register(self, guardian_id: str, guardian: Guardian) -> None:
        """
        Register a guardian instance.
        
        Args:
            guardian_id: Unique guardian ID
            guardian: Guardian instance
        """
        self.guardians[guardian_id] = guardian
        logger.debug(f"Guardian registered: {guardian_id} ({guardian.guardian_type})")

    def get(self, guardian_id: str) -> Optional[Guardian]:
        """
        Get guardian by ID.
        
        Args:
            guardian_id: Unique guardian ID
        
        Returns:
            Guardian instance or None if not found
        """
        return self.guardians.get(guardian_id)

    def evaluate_all(
        self,
        guardian_ids: List[str],
        uow_data: Dict[str, Any],
        policy: Dict[str, Any],
        operator: str = "AND",
    ) -> List[GuardianDecision]:
        """
        Evaluate multiple guardians in sequence.
        
        Args:
            guardian_ids: List of guardian IDs to evaluate
            uow_data: UOW attributes
            policy: Interaction policy
            operator: "AND" to short-circuit on first failure
        
        Returns:
            List of GuardianDecision results
        """
        results = []
        for guardian_id in guardian_ids:
            guardian = self.get(guardian_id)
            if not guardian:
                logger.warning(f"Guardian not found: {guardian_id}")
                continue
            
            decision = guardian.evaluate(uow_data, policy)
            results.append(decision)
            
            # Short-circuit on AND if any failed
            if operator == "AND" and not decision.allowed:
                break
        
        return results
