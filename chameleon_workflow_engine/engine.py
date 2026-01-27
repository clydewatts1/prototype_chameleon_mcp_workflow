"""
Chameleon Workflow Engine Core Controller

This module implements the Transport Layer Abstraction (Interface & MCP Specs, Section 3.1)
that powers both the REST API and the MCP Server. It provides the core business logic
for workflow instantiation, work checkout, submission, and failure handling.

References:
- Interface & MCP Specs: docs/architecture/Interface & MCP Specs.md
- UOW Lifecycle Specs: docs/architecture/UOW Lifecycle Specs.md
- Workflow Constitution: docs/architecture/Workflow_Constitution.md
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from dateutil.parser import isoparse

from database.manager import DatabaseManager
from database.models_template import (
    Template_Workflows,
    Template_Roles,
    Template_Interactions,
    Template_Components,
    Template_Guardians,
)
from database.models_instance import (
    Instance_Context,
    Local_Workflows,
    Local_Roles,
    Local_Interactions,
    Local_Components,
    Local_Guardians,
    UnitsOfWork,
    UOW_Attributes,
    Local_Role_Attributes,
)
from database.enums import (
    RoleType,
    UOWStatus,
    ComponentDirection,
    GuardianType,
)

# Well-known system actor ID for automated operations
# This ensures consistent identity across all system-initiated operations
SYSTEM_ACTOR_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

# Logger for the engine
logger = logging.getLogger(__name__)


class ChameleonEngine:
    """
    Core Engine Controller for the Chameleon Workflow System.

    This class serves as the Transport Layer Abstraction (Spec 3.1) and implements
    the core business logic for:
    - Workflow instantiation from templates (Article I: Isolation)
    - Work checkout with transactional locking
    - Work submission with atomic versioning (Article XVII)
    - Failure handling and Ate Path routing (Article XI)

    The engine enforces Article XXI (Infrastructure Independence) by being
    decoupled from any specific transport protocol.
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize the Chameleon Engine.

        Args:
            db_manager: DatabaseManager instance with initialized template and instance engines.
        """
        self.db_manager = db_manager

    def instantiate_workflow(
        self,
        template_id: uuid.UUID,
        initial_context: Dict[str, Any],
        instance_name: Optional[str] = None,
        instance_description: Optional[str] = None,
    ) -> uuid.UUID:
        """
        Instantiate a new workflow from a template.

        Implements Interface & MCP Specs Section 2.1: POST /workflow/instantiate
        Enforces Article I (Total Isolation) and Article XV (Master-Child Federation).

        Process:
        1. Start a transaction using DatabaseManager
        2. Clone all Roles, Interactions, Guardians, and Components from Template to Instance
        3. Create the "Alpha UOW" (Status: INITIALIZED) with initial_context
        4. Inject the Alpha UOW into the Interaction connected to the Alpha Role
        5. Return the new workflow_instance_id

        Args:
            template_id: UUID of the workflow template to instantiate
            initial_context: Initial data payload for the Alpha UOW
            instance_name: Optional name for the instance
            instance_description: Optional description for the instance

        Returns:
            UUID of the newly created workflow instance (instance_id)

        Raises:
            ValueError: If template not found or invalid
            RuntimeError: If instantiation fails
        """
        with self.db_manager.get_template_session() as template_session:
            with self.db_manager.get_instance_session() as instance_session:
                try:
                    # Step 1: Fetch the template workflow
                    template_workflow = (
                        template_session.query(Template_Workflows)
                        .filter(Template_Workflows.workflow_id == template_id)
                        .first()
                    )

                    if not template_workflow:
                        raise ValueError(f"Template workflow {template_id} not found")

                    # Step 2: Create Instance Context (The World)
                    instance_id = uuid.uuid4()
                    instance_context = Instance_Context(
                        instance_id=instance_id,
                        name=instance_name or f"Instance_{template_workflow.name}",
                        description=instance_description
                        or f"Instantiated from {template_workflow.name}",
                        status="ACTIVE",
                    )
                    instance_session.add(instance_context)
                    instance_session.flush()

                    # Step 3: Clone the workflow
                    local_workflow = Local_Workflows(
                        local_workflow_id=uuid.uuid4(),
                        instance_id=instance_id,
                        original_workflow_id=template_workflow.workflow_id,
                        name=template_workflow.name,
                        description=template_workflow.description,
                        ai_context=template_workflow.ai_context,
                        version=template_workflow.version,
                        is_active=True,
                        is_master=True,
                    )
                    instance_session.add(local_workflow)
                    instance_session.flush()

                    # Step 4: Clone Roles (maintaining mapping for later steps)
                    role_mapping = {}  # template_role_id -> local_role_id
                    template_roles = (
                        template_session.query(Template_Roles)
                        .filter(Template_Roles.workflow_id == template_id)
                        .all()
                    )

                    alpha_role_id = None
                    for template_role in template_roles:
                        local_role_id = uuid.uuid4()
                        local_role = Local_Roles(
                            role_id=local_role_id,
                            local_workflow_id=local_workflow.local_workflow_id,
                            name=template_role.name,
                            description=template_role.description,
                            ai_context=template_role.ai_context,
                            role_type=template_role.role_type,
                            decomposition_strategy=template_role.strategy,  # Template uses 'strategy', Instance uses 'decomposition_strategy'
                            is_recursive_gateway=template_role.child_workflow_id
                            is not None,  # Derive from child_workflow_id presence
                            linked_local_workflow_id=None,  # KNOWN LIMITATION: Recursive workflows not yet implemented
                        )
                        instance_session.add(local_role)
                        role_mapping[template_role.role_id] = local_role_id

                        # KNOWN LIMITATION: If template_role.child_workflow_id is set, this indicates
                        # a recursive gateway, but we don't currently clone and link the child workflow.
                        # This would require recursive instantiation logic to be added.
                        if template_role.child_workflow_id:
                            # TODO: Implement recursive workflow instantiation
                            # This should:
                            # 1. Recursively instantiate the child workflow
                            # 2. Set linked_local_workflow_id to the child's local_workflow_id
                            # 3. Handle Hermes (entry) and Iris (exit) interactions
                            pass

                        # Track the Alpha role for later
                        if template_role.role_type == RoleType.ALPHA.value:
                            alpha_role_id = local_role_id

                    instance_session.flush()

                    if not alpha_role_id:
                        raise ValueError(f"Template workflow {template_id} has no Alpha role")

                    # Step 5: Clone Interactions (maintaining mapping)
                    interaction_mapping = {}  # template_interaction_id -> local_interaction_id
                    template_interactions = (
                        template_session.query(Template_Interactions)
                        .filter(Template_Interactions.workflow_id == template_id)
                        .all()
                    )

                    for template_interaction in template_interactions:
                        local_interaction_id = uuid.uuid4()
                        local_interaction = Local_Interactions(
                            interaction_id=local_interaction_id,
                            local_workflow_id=local_workflow.local_workflow_id,
                            name=template_interaction.name,
                            description=template_interaction.description,
                            ai_context=template_interaction.ai_context,
                            stale_token_limit_seconds=None,  # Template doesn't have this field, set to None
                        )
                        instance_session.add(local_interaction)
                        interaction_mapping[template_interaction.interaction_id] = (
                            local_interaction_id
                        )

                    instance_session.flush()

                    # Step 6: Clone Components (creating connections)
                    template_components = (
                        template_session.query(Template_Components)
                        .filter(Template_Components.workflow_id == template_id)
                        .all()
                    )

                    alpha_outbound_interaction_id = None
                    for template_component in template_components:
                        local_component = Local_Components(
                            component_id=uuid.uuid4(),
                            local_workflow_id=local_workflow.local_workflow_id,
                            interaction_id=interaction_mapping[template_component.interaction_id],
                            role_id=role_mapping[template_component.role_id],
                            direction=template_component.direction,
                            name=template_component.name,
                            description=template_component.description,
                            ai_context=template_component.ai_context,
                        )
                        instance_session.add(local_component)

                        # Find the outbound interaction from Alpha role
                        if (
                            role_mapping[template_component.role_id] == alpha_role_id
                            and template_component.direction == ComponentDirection.OUTBOUND.value
                        ):
                            alpha_outbound_interaction_id = interaction_mapping[
                                template_component.interaction_id
                            ]

                    instance_session.flush()

                    if not alpha_outbound_interaction_id:
                        raise ValueError("No outbound interaction found for Alpha role")

                    # Step 7: Clone Guardians
                    template_guardians = (
                        template_session.query(Template_Guardians)
                        .filter(Template_Guardians.workflow_id == template_id)
                        .all()
                    )

                    component_mapping = {}  # template_component_id -> local_component_id
                    # We need to rebuild the component mapping with IDs
                    for template_component in template_components:
                        # Find the corresponding local component
                        local_component = (
                            instance_session.query(Local_Components)
                            .filter(
                                and_(
                                    Local_Components.local_workflow_id
                                    == local_workflow.local_workflow_id,
                                    Local_Components.interaction_id
                                    == interaction_mapping[template_component.interaction_id],
                                    Local_Components.role_id
                                    == role_mapping[template_component.role_id],
                                    Local_Components.direction == template_component.direction,
                                )
                            )
                            .first()
                        )
                        if local_component:
                            component_mapping[template_component.component_id] = (
                                local_component.component_id
                            )

                    for template_guardian in template_guardians:
                        if template_guardian.component_id in component_mapping:
                            local_guardian = Local_Guardians(
                                guardian_id=uuid.uuid4(),
                                local_workflow_id=local_workflow.local_workflow_id,
                                component_id=component_mapping[template_guardian.component_id],
                                name=template_guardian.name,
                                description=template_guardian.description,
                                ai_context=template_guardian.ai_context,
                                type=template_guardian.type,
                                attributes=template_guardian.config,  # Template uses 'config', Instance uses 'attributes'
                            )
                            instance_session.add(local_guardian)

                    instance_session.flush()

                    # Step 8: Create the Alpha UOW with INITIALIZED status
                    # Note: The spec says INITIALIZED, but the enum only has PENDING, ACTIVE, COMPLETED, FAILED
                    # We'll use PENDING as the initial state based on the available enum values
                    alpha_uow = UnitsOfWork(
                        uow_id=uuid.uuid4(),
                        instance_id=instance_id,
                        local_workflow_id=local_workflow.local_workflow_id,
                        parent_id=None,  # This is the root UOW
                        current_interaction_id=alpha_outbound_interaction_id,
                        status=UOWStatus.PENDING.value,  # Using PENDING as closest to INITIALIZED
                        child_count=0,
                        finished_child_count=0,
                        last_heartbeat=None,
                    )
                    instance_session.add(alpha_uow)
                    instance_session.flush()

                    # Step 9: Create initial UOW attributes from initial_context
                    # Store each key-value pair from initial_context as a separate attribute
                    for key, value in initial_context.items():
                        uow_attr = UOW_Attributes(
                            attribute_id=uuid.uuid4(),
                            uow_id=alpha_uow.uow_id,
                            instance_id=instance_id,
                            key=key,
                            value=value,
                            version=1,
                            actor_id=SYSTEM_ACTOR_ID,  # Use well-known system actor ID
                            reasoning="Initial workflow context",
                        )
                        instance_session.add(uow_attr)

                    instance_session.flush()

                    # Commit the transaction
                    instance_session.commit()

                    return instance_id

                except Exception as e:
                    instance_session.rollback()
                    raise RuntimeError(f"Failed to instantiate workflow: {str(e)}") from e

    def _create_temp_guard(
        self, parent_guard: Local_Guardians, step_config: Dict[str, Any]
    ) -> Local_Guardians:
        """
        Create a temporary guard object for COMPOSITE step evaluation.

        This is a lightweight helper to avoid duplicating guard object creation logic.

        Args:
            parent_guard: The parent COMPOSITE guard
            step_config: The step configuration containing type and config

        Returns:
            A temporary Local_Guardians object for evaluation
        """
        return Local_Guardians(
            guardian_id=uuid.uuid4(),
            local_workflow_id=parent_guard.local_workflow_id,
            component_id=parent_guard.component_id,
            name=f"{parent_guard.name}_step",
            type=step_config.get("type"),
            attributes=step_config.get("config", {}),
        )

    def _evaluate_guard(
        self,
        guard: Local_Guardians,
        uow: UnitsOfWork,
        uow_attributes: Dict[str, Any],
        session: Session,
    ) -> bool:
        """
        Evaluate a guard against a Unit of Work.

        Implements Guard Behavior Specifications for all guard types:
        - PASS_THRU: Always returns True
        - CRITERIA_GATE: Evaluate UOW attributes against operator and threshold
        - TTL_CHECK: Check age of UOW against max_age
        - COMPOSITE: Chain multiple guard checks with AND/OR logic
        - DIRECTIONAL_FILTER: Check routing key (not blocking, just routing)

        Args:
            guard: The guard configuration
            uow: The Unit of Work being evaluated
            uow_attributes: Dictionary of UOW attributes (key -> value)
            session: Database session for any lookups

        Returns:
            True if the guard passes, False if it rejects the UOW

        Raises:
            ValueError: If guard type is unknown or configuration is invalid
        """
        guard_type = guard.type
        config = guard.attributes or {}

        # PASS_THRU: Always allow passage
        if guard_type == GuardianType.PASS_THRU.value:
            return True

        # CRITERIA_GATE: Evaluate field against operator and threshold
        elif guard_type == GuardianType.CRITERIA_GATE.value:
            field = config.get("field")
            operator = config.get("operator")
            threshold = config.get("threshold")

            if not field or not operator:
                # Missing configuration - default to reject for safety
                return False

            # Get the field value from UOW attributes
            field_value = uow_attributes.get(field)

            if field_value is None:
                # Missing attribute - reject
                return False

            # Evaluate based on operator
            if operator == "GT":
                return field_value > threshold
            elif operator == "LT":
                return field_value < threshold
            elif operator == "EQ":
                return field_value == threshold
            elif operator == "IN":
                # threshold should be a list/array
                if not isinstance(threshold, (list, tuple)):
                    return False
                return field_value in threshold
            else:
                # Unknown operator - reject
                return False

        # TTL_CHECK: Check age against max_age_seconds
        elif guard_type == GuardianType.TTL_CHECK.value:
            reference_field = config.get("reference_field")
            max_age_seconds = config.get("max_age_seconds")

            if not reference_field or max_age_seconds is None:
                # Missing configuration - reject
                return False

            # Get the timestamp field
            timestamp_value = uow_attributes.get(reference_field)

            if timestamp_value is None:
                # Missing timestamp - reject
                return False

            # Parse timestamp (handle ISO strings or datetime objects)
            try:
                if isinstance(timestamp_value, str):
                    # Parse ISO 8601 string
                    reference_time = isoparse(timestamp_value)
                elif isinstance(timestamp_value, datetime):
                    reference_time = timestamp_value
                else:
                    # Unknown format - reject
                    return False

                # Ensure timezone awareness
                if reference_time.tzinfo is None:
                    reference_time = reference_time.replace(tzinfo=timezone.utc)

                # Calculate age
                now = datetime.now(timezone.utc)
                age_seconds = (now - reference_time).total_seconds()

                # Check if within TTL
                return age_seconds <= max_age_seconds

            except Exception:
                # Parse error - reject
                return False

        # COMPOSITE: Chain multiple checks with AND/OR logic
        elif guard_type == GuardianType.COMPOSITE.value:
            logic = config.get("logic", "AND").upper()
            steps = config.get("steps", [])

            if not steps:
                # No steps - default to reject
                return False

            # Create temporary guard objects for each step
            if logic == "AND":
                # All steps must pass
                for step in steps:
                    step_guard = self._create_temp_guard(guard, step)

                    # Recursively evaluate the step
                    if not self._evaluate_guard(step_guard, uow, uow_attributes, session):
                        # One step failed - entire composite fails
                        return False

                # All steps passed
                return True

            elif logic == "OR":
                # At least one step must pass
                for step in steps:
                    step_guard = self._create_temp_guard(guard, step)

                    # Recursively evaluate the step
                    if self._evaluate_guard(step_guard, uow, uow_attributes, session):
                        # One step passed - entire composite passes
                        return True

                # All steps failed
                return False

            else:
                # Unknown logic type - reject
                return False

        # DIRECTIONAL_FILTER: Check routing (not blocking in guard evaluation)
        # This type is for routing, not for blocking, so it always passes
        # The routing decision is made elsewhere in the flow
        elif guard_type == GuardianType.DIRECTIONAL_FILTER.value:
            # DIRECTIONAL_FILTER doesn't block - it routes
            # For now, we'll pass it through and let routing logic handle it
            return True

        # CERBERUS: Complex synchronization logic for parent-child sets
        # This is typically evaluated at Omega, not during checkout
        # For now, we'll pass it through as it has special handling requirements
        elif guard_type == GuardianType.CERBERUS.value:
            # CERBERUS requires special handling for parent-child synchronization
            # It's not evaluated during checkout but at Omega reconciliation
            return True

        # Unknown guard type
        else:
            raise ValueError(f"Unknown guard type: {guard_type}")

    def _harvest_experience(
        self,
        session: Session,
        uow: UnitsOfWork,
        actor_id: uuid.UUID,
        role_id: uuid.UUID,
        result_attributes: Dict[str, Any],
    ) -> None:
        """
        Harvest learning from completed work (Experience Extraction).
        
        Implements Memory & Learning Specs Section 2.1: Experience Extraction (The Harvest).
        
        This is a prototype implementation using a rule-based harvester.
        In production, this would be replaced with AI-powered pattern analysis.
        
        Rule-Based Harvester Logic:
        - Look for a reserved key `_learned_rule` in result_attributes
        - Structure: {"_learned_rule": {"key": "rule_name", "value": rule_value}}
        - If found, create or update a record in Local_Role_Attributes
        - Context: ACTOR-specific (Personal Playbook)
        - Confidence: 1.0 (user explicitly taught this)
        
        Args:
            session: Database session
            uow: The Unit of Work being completed
            actor_id: The actor who completed the work
            role_id: The role context for this work
            result_attributes: The submitted work attributes (may contain _learned_rule)
        """
        # Check if result_attributes contains the learning key
        learned_rule = result_attributes.get("_learned_rule")
        
        if not learned_rule:
            # No learning to harvest
            return
        
        # Validate the learned_rule structure
        if not isinstance(learned_rule, dict):
            logger.warning("Invalid _learned_rule format: not a dictionary")
            return
        
        rule_key = learned_rule.get("key")
        rule_value = learned_rule.get("value")
        
        if not rule_key:
            logger.warning("Invalid _learned_rule format: missing 'key' field")
            return
        
        # Create context_id from actor_id (string representation with hyphens)
        context_id = str(actor_id)
        
        # Check if a memory attribute already exists for this actor+role+key
        existing_memory = session.query(Local_Role_Attributes).filter(
            and_(
                Local_Role_Attributes.role_id == role_id,
                Local_Role_Attributes.context_type == "ACTOR",
                Local_Role_Attributes.context_id == context_id,
                Local_Role_Attributes.key == rule_key,
            )
        ).first()
        
        if existing_memory:
            # Update existing memory
            existing_memory.value = rule_value
            existing_memory.confidence_score = 100  # User-taught, 100% confidence (0-100 scale)
            existing_memory.last_accessed_at = datetime.now(timezone.utc)
            logger.info(f"Updated memory for actor {actor_id}, role {role_id}, key '{rule_key}'")
        else:
            # Create new memory attribute
            memory_attr = Local_Role_Attributes(
                memory_id=uuid.uuid4(),
                instance_id=uow.instance_id,
                role_id=role_id,
                context_type="ACTOR",
                context_id=context_id,
                actor_id=actor_id,
                key=rule_key,
                value=rule_value,
                confidence_score=100,  # User-taught, 100% confidence (0-100 scale)
                is_toxic=False,
                created_at=datetime.now(timezone.utc),
                last_accessed_at=datetime.now(timezone.utc),
            )
            session.add(memory_attr)
            logger.info(f"Created new memory for actor {actor_id}, role {role_id}, key '{rule_key}'")
        
        session.flush()

    def _build_memory_context(
        self, session: Session, role_id: uuid.UUID, actor_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Build the memory context for an actor checking out work in a specific role.

        Implements Memory & Learning Specs Section 5: Interface for Actors (The Access Pattern).
        
        This method:
        1. Fetches Global Blueprints (context_type='GLOBAL') for the role
        2. Fetches Personal Playbook (context_type='ACTOR', context_id=actor_id) for the role
        3. Filters out toxic memories (is_toxic=True)
        4. Merges them with Actor-specific keys overriding Global keys
        5. Updates last_accessed_at timestamp for all fetched memories

        Args:
            session: Database session for queries
            role_id: The role being assumed
            actor_id: The actor checking out work

        Returns:
            Dictionary of merged memory context (key -> value)
        """
        # Step 1: Query Global Blueprints for this role
        global_memories = (
            session.query(Local_Role_Attributes)
            .filter(
                and_(
                    Local_Role_Attributes.role_id == role_id,
                    Local_Role_Attributes.context_type == "GLOBAL",
                    Local_Role_Attributes.is_toxic.is_not(True),  # Filter out toxic memories
                )
            )
            .all()
        )

        # Step 2: Query Personal Playbook for this actor + role
        actor_id_str = str(actor_id)
        personal_memories = (
            session.query(Local_Role_Attributes)
            .filter(
                and_(
                    Local_Role_Attributes.role_id == role_id,
                    Local_Role_Attributes.context_type == "ACTOR",
                    Local_Role_Attributes.context_id == actor_id_str,
                    Local_Role_Attributes.is_toxic.is_not(True),  # Filter out toxic memories
                )
            )
            .all()
        )

        # Step 3: Build merged context (Global first, then Actor overrides)
        context = {}
        
        # Add Global Blueprints
        for memory in global_memories:
            context[memory.key] = memory.value

        # Add/Override with Personal Playbook (Actor-specific overrides Global)
        for memory in personal_memories:
            context[memory.key] = memory.value

        # Step 4: Update last_accessed_at timestamps for all fetched memories
        now = datetime.now(timezone.utc)
        all_memories = global_memories + personal_memories
        
        for memory in all_memories:
            memory.last_accessed_at = now

        # Commit timestamp updates
        session.flush()

        return context

    def checkout_work(
        self, actor_id: uuid.UUID, role_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Acquire a Unit of Work from a specific Role's queue with transactional locking.

        Implements Interface & MCP Specs Section 1.1: Tool checkout_work
        Enforces UOW Lifecycle Specs Section 2.2: Valid Transition Matrix (PENDING → IN_PROGRESS)
        Implements Memory & Learning Specs Section 5: Context injection during checkout

        LOCKING MECHANISM NOTE:
        The current implementation uses status (PENDING → ACTIVE) and last_heartbeat timestamp
        as the locking mechanism. The schema does not currently have dedicated locked_by/locked_at
        fields. In production, these fields should be added to provide explicit lock ownership
        tracking and enable better debugging and lock timeout handling.

        Process:
        1. Query Instance_Interactions to find PENDING UOWs for this role_id
        2. Join with Instance_Components and Instance_Guardians to verify path exists
        3. Execute Transactional Lock:
           - Select a candidate UOW
           - Update status to IN_PROGRESS (ACTIVE in current enum)
           - Set last_heartbeat = NOW (as lock timestamp)
        4. Build memory context for the actor + role
        5. Return the uow_id, attributes, and context

        Args:
            actor_id: The Actor's unique identity
            role_id: The Role the Actor is assuming

        Returns:
            Dict with keys: 'uow_id', 'attributes', 'context' if work found, None if no work available

        Raises:
            ValueError: If role not found or invalid
        """
        with self.db_manager.get_instance_session() as session:
            try:
                # Step 1: Find the role and verify it exists
                role = session.query(Local_Roles).filter(Local_Roles.role_id == role_id).first()

                if not role:
                    raise ValueError(f"Role {role_id} not found")

                # Step 2: Find INBOUND components for this role
                # These represent interactions that feed work into this role
                inbound_components = (
                    session.query(Local_Components)
                    .filter(
                        and_(
                            Local_Components.role_id == role_id,
                            Local_Components.direction == ComponentDirection.INBOUND.value,
                        )
                    )
                    .all()
                )

                if not inbound_components:
                    # No inbound paths, no work can arrive
                    return None

                # Extract the interaction IDs that feed this role
                inbound_interaction_ids = [comp.interaction_id for comp in inbound_components]

                # Step 3: Find ALL PENDING UOWs in these interactions
                # We need to iterate through candidates to evaluate guards
                candidate_uows = (
                    session.query(UnitsOfWork)
                    .filter(
                        and_(
                            UnitsOfWork.current_interaction_id.in_(inbound_interaction_ids),
                            UnitsOfWork.status == UOWStatus.PENDING.value,
                        )
                    )
                    .all()
                )

                if not candidate_uows:
                    # No work available
                    return None

                # Step 4: Evaluate guards for each candidate
                for candidate_uow in candidate_uows:
                    # Find the component connecting this interaction to the role
                    component = None
                    for comp in inbound_components:
                        if comp.interaction_id == candidate_uow.current_interaction_id:
                            component = comp
                            break

                    if not component:
                        # Should not happen, but skip if no component found
                        continue

                    # Find the guard associated with this component
                    guard = (
                        session.query(Local_Guardians)
                        .filter(Local_Guardians.component_id == component.component_id)
                        .first()
                    )

                    # Retrieve UOW attributes for guard evaluation
                    uow_attributes_raw = (
                        session.query(UOW_Attributes)
                        .filter(UOW_Attributes.uow_id == candidate_uow.uow_id)
                        .all()
                    )

                    # Build attributes dictionary from the latest version of each key
                    attributes_dict = {}
                    for attr in uow_attributes_raw:
                        # If multiple versions exist, we want the latest
                        if (
                            attr.key not in attributes_dict
                            or attr.version > attributes_dict[attr.key]["version"]
                        ):
                            attributes_dict[attr.key] = {
                                "value": attr.value,
                                "version": attr.version,
                            }

                    # Simplify to just key-value pairs
                    uow_attributes = {key: data["value"] for key, data in attributes_dict.items()}

                    # Evaluate guard (if one exists)
                    guard_passed = True
                    if guard:
                        try:
                            guard_passed = self._evaluate_guard(
                                guard, candidate_uow, uow_attributes, session
                            )
                        except Exception as e:
                            # Guard evaluation error - treat as rejection
                            guard_passed = False
                            # Log the error for debugging
                            logger.warning(
                                "Guard evaluation error for UOW %s: %s",
                                candidate_uow.uow_id,
                                str(e),
                            )

                    if not guard_passed:
                        # Guard rejected the UOW - route to Ate Path (Epsilon)
                        # Find the Epsilon role
                        epsilon_role = (
                            session.query(Local_Roles)
                            .filter(
                                and_(
                                    Local_Roles.local_workflow_id
                                    == candidate_uow.local_workflow_id,
                                    Local_Roles.role_type == RoleType.EPSILON.value,
                                )
                            )
                            .first()
                        )

                        if epsilon_role:
                            # Find the INBOUND component for Epsilon role (the Ate interaction)
                            ate_component = (
                                session.query(Local_Components)
                                .filter(
                                    and_(
                                        Local_Components.role_id == epsilon_role.role_id,
                                        Local_Components.direction
                                        == ComponentDirection.INBOUND.value,
                                    )
                                )
                                .first()
                            )

                            if ate_component:
                                # Route UOW to Ate interaction
                                candidate_uow.status = UOWStatus.FAILED.value
                                candidate_uow.current_interaction_id = ate_component.interaction_id

                                # Log the guard rejection in UOW attributes
                                timestamp = datetime.now(timezone.utc)
                                error_attr = UOW_Attributes(
                                    attribute_id=uuid.uuid4(),
                                    uow_id=candidate_uow.uow_id,
                                    instance_id=candidate_uow.instance_id,
                                    key="_guard_rejection",
                                    value={
                                        "error_code": "GUARD_REJECTION",
                                        "details": f"Criteria failed for guard: {guard.name if guard else 'unknown'}",
                                        "timestamp": timestamp.isoformat(),
                                        "actor_id": str(SYSTEM_ACTOR_ID),
                                        "guard_name": guard.name if guard else None,
                                        "guard_type": guard.type if guard else None,
                                    },
                                    version=1,
                                    actor_id=SYSTEM_ACTOR_ID,
                                    reasoning="Guard criteria not met",
                                )
                                session.add(error_attr)
                                session.flush()

                        # Continue to next candidate
                        continue

                    # Guard passed (or no guard) - this UOW is valid
                    # Step 5: Execute Transactional Lock
                    # Transition PENDING → IN_PROGRESS (using ACTIVE status)
                    candidate_uow.status = UOWStatus.ACTIVE.value
                    candidate_uow.last_heartbeat = datetime.now(timezone.utc)
                    # Note: locked_by and locked_at fields need to be added to the model
                    # For now, we're using status change and last_heartbeat as the lock mechanism

                    session.flush()

                    # TODO: Interaction logging disabled due to SQLite BigInteger autoincrement issue
                    # This needs to be addressed in the schema for production use
                    # Log the interaction
                    # log_entry = Interaction_Logs(
                    #     instance_id=candidate_uow.instance_id,
                    #     uow_id=candidate_uow.uow_id,
                    #     actor_id=actor_id,
                    #     role_id=role_id,
                    #     interaction_id=candidate_uow.current_interaction_id,
                    #     timestamp=datetime.now(timezone.utc)
                    # )
                    # session.add(log_entry)

                    # Step 6: Build memory context for this actor + role
                    memory_context = self._build_memory_context(session, role_id, actor_id)

                    session.commit()

                    return {
                        "uow_id": candidate_uow.uow_id,
                        "attributes": uow_attributes,
                        "context": memory_context,
                    }

                # If we get here, all candidates were rejected by guards
                # Commit the rejections and return None
                session.commit()
                return None

            except Exception as e:
                session.rollback()
                raise RuntimeError(f"Failed to checkout work: {str(e)}") from e

    def submit_work(
        self,
        uow_id: uuid.UUID,
        actor_id: uuid.UUID,
        result_attributes: Dict[str, Any],
        reasoning: Optional[str] = None,
    ) -> bool:
        """
        Submit the results of a completed task, unlocking the UOW and moving it to next stage.

        Implements Interface & MCP Specs Section 1.2: Tool submit_work
        Enforces UOW Lifecycle Specs Section 3: Atomic Versioning (The Data Physics)
        Enforces Article XVII: Historical Lineage and Attribution

        LOCK VERIFICATION NOTE:
        Lock ownership is verified via status check (must be ACTIVE). Full lock verification
        would check a dedicated locked_by field against actor_id, but the current schema
        doesn't have this field. For production use, locked_by/locked_at fields should be
        added to the UnitsOfWork table.

        Process:
        1. Verify that uow_id is locked by actor_id (Security Check via status)
        2. Implement Atomic Versioning (Spec 3.2):
           - Calculate diff between old attributes and result_attributes
           - Insert records into UOW_Attributes (versioned history)
        3. Update Status to COMPLETED
        4. Release the lock (clear last_heartbeat)

        Args:
            uow_id: The token being processed
            actor_id: The Actor's identity (should match lock holder)
            result_attributes: JSON blob of new or modified data
            reasoning: Optional text explanation for the decision (for Traceability)

        Returns:
            True if successful

        Raises:
            ValueError: If UOW not found or not locked by this actor
            RuntimeError: If submission fails
        """
        with self.db_manager.get_instance_session() as session:
            try:
                # Step 1: Verify lock ownership
                uow = session.query(UnitsOfWork).filter(UnitsOfWork.uow_id == uow_id).first()

                if not uow:
                    raise ValueError(f"UOW {uow_id} not found")

                if uow.status != UOWStatus.ACTIVE.value:
                    raise ValueError(
                        f"UOW {uow_id} is not in progress (status: {uow.status}). "
                        "Cannot submit work that isn't checked out."
                    )

                # Note: Full lock verification would check locked_by field
                # For now, we verify via status and trust the actor_id

                # Step 2: Retrieve current attributes to calculate diff
                current_attrs = (
                    session.query(UOW_Attributes).filter(UOW_Attributes.uow_id == uow_id).all()
                )

                # Build current state (latest version of each key)
                current_state = {}
                version_map = {}
                for attr in current_attrs:
                    if attr.key not in current_state or attr.version > version_map[attr.key]:
                        current_state[attr.key] = attr.value
                        version_map[attr.key] = attr.version

                # Step 3: Atomic Versioning - Create new attribute records for changes
                # Filter out reserved learning key - it should not be saved to UOW attributes
                for key, new_value in result_attributes.items():
                    # Skip the reserved learning key - it's processed by the learning loop
                    if key == "_learned_rule":
                        continue
                    
                    # Check if this is a new key or modified value
                    if key not in current_state or current_state[key] != new_value:
                        new_version = version_map.get(key, 0) + 1

                        uow_attr = UOW_Attributes(
                            attribute_id=uuid.uuid4(),
                            uow_id=uow_id,
                            instance_id=uow.instance_id,
                            key=key,
                            value=new_value,
                            version=new_version,
                            actor_id=actor_id,
                            reasoning=reasoning or f"Work submitted by actor {actor_id}",
                        )
                        session.add(uow_attr)

                session.flush()

                # Step 3.5: Trigger Learning Loop (Experience Extraction)
                # This must happen BEFORE status update but AFTER attributes are saved
                # Learning failures should not rollback work submission
                try:
                    # We need to get the role_id from the UOW's current context
                    # The UOW is in an interaction that the role reads from (INBOUND to the role)
                    # Find the role that has an INBOUND component from this interaction
                    role_id_for_learning = None
                    
                    # Query for INBOUND components only (optimization)
                    inbound_component = session.query(Local_Components).filter(
                        and_(
                            Local_Components.interaction_id == uow.current_interaction_id,
                            Local_Components.direction == ComponentDirection.INBOUND.value
                        )
                    ).first()
                    
                    if inbound_component:
                        role_id_for_learning = inbound_component.role_id
                    
                    # If we found a role, harvest the experience
                    if role_id_for_learning:
                        self._harvest_experience(
                            session=session,
                            uow=uow,
                            actor_id=actor_id,
                            role_id=role_id_for_learning,
                            result_attributes=result_attributes
                        )
                    else:
                        logger.debug(f"No role found for learning at interaction {uow.current_interaction_id}")
                except Exception as learning_error:
                    # Log the error but don't fail the submission
                    logger.warning(f"Learning loop failed for UOW {uow_id}: {learning_error}")

                # Step 4: Update UOW Status to COMPLETED
                uow.status = UOWStatus.COMPLETED.value
                uow.last_heartbeat = None  # Release heartbeat

                # TODO: Interaction logging disabled due to SQLite BigInteger autoincrement issue
                # Log the interaction
                # log_entry = Interaction_Logs(
                #     instance_id=uow.instance_id,
                #     uow_id=uow.uow_id,
                #     actor_id=actor_id,
                #     role_id=None,  # TODO: Should track which role completed it
                #     interaction_id=uow.current_interaction_id,
                #     timestamp=timestamp
                # )
                # session.add(log_entry)

                session.commit()

                return True

            except Exception as e:
                session.rollback()
                raise RuntimeError(f"Failed to submit work: {str(e)}") from e

    def report_failure(
        self, uow_id: uuid.UUID, actor_id: uuid.UUID, error_code: str, details: Optional[str] = None
    ) -> bool:
        """
        Explicitly flag a UOW as failed/invalid, triggering the Ate Path (Epsilon).

        Implements Interface & MCP Specs Section 1.3: Tool report_failure
        Enforces Article XI: The Ate Path (Explicit Data Error)
        Enforces UOW Lifecycle Specs Section 2.2: Valid Transition (IN_PROGRESS → FAILED)

        Process:
        1. Verify that uow_id is locked by actor_id
        2. Update UOW Status to FAILED
        3. Log the error in history (UOW_Attributes)
        4. Move the token to the Ate Interaction (connected to Epsilon Role)
        5. Release the lock

        Args:
            uow_id: The token ID
            actor_id: The Actor's identity (must match lock holder)
            error_code: Standardized error string
            details: Descriptive text about the failure

        Returns:
            True if successful

        Raises:
            ValueError: If UOW not found or not locked by this actor
            RuntimeError: If failure reporting fails
        """
        with self.db_manager.get_instance_session() as session:
            try:
                # Step 1: Verify lock ownership
                uow = session.query(UnitsOfWork).filter(UnitsOfWork.uow_id == uow_id).first()

                if not uow:
                    raise ValueError(f"UOW {uow_id} not found")

                if uow.status != UOWStatus.ACTIVE.value:
                    raise ValueError(
                        f"UOW {uow_id} is not in progress (status: {uow.status}). "
                        "Cannot report failure for work that isn't checked out."
                    )

                # Note: Full lock verification would check locked_by field

                # Step 2: Find the Epsilon (Ate) interaction
                # Query the workflow to find the Epsilon role
                epsilon_role = (
                    session.query(Local_Roles)
                    .filter(
                        and_(
                            Local_Roles.local_workflow_id == uow.local_workflow_id,
                            Local_Roles.role_type == RoleType.EPSILON.value,
                        )
                    )
                    .first()
                )

                ate_interaction_id = None
                if epsilon_role:
                    # Find the INBOUND component for Epsilon role (the Ate interaction)
                    ate_component = (
                        session.query(Local_Components)
                        .filter(
                            and_(
                                Local_Components.role_id == epsilon_role.role_id,
                                Local_Components.direction == ComponentDirection.INBOUND.value,
                            )
                        )
                        .first()
                    )

                    if ate_component:
                        ate_interaction_id = ate_component.interaction_id

                # Step 3: Log the error in UOW attributes history
                timestamp = datetime.now(timezone.utc)
                error_attr = UOW_Attributes(
                    attribute_id=uuid.uuid4(),
                    uow_id=uow_id,
                    instance_id=uow.instance_id,
                    key="_error",
                    value={
                        "error_code": error_code,
                        "details": details,
                        "timestamp": timestamp.isoformat(),
                        "actor_id": str(actor_id),
                    },
                    version=1,  # Error records start at version 1
                    actor_id=actor_id,
                    reasoning=f"Failure reported: {error_code}",
                )
                session.add(error_attr)

                # Step 4: Update UOW Status to FAILED
                uow.status = UOWStatus.FAILED.value
                uow.last_heartbeat = None  # Release heartbeat

                # Step 5: Move to Ate interaction if found
                if ate_interaction_id:
                    uow.current_interaction_id = ate_interaction_id

                # TODO: Interaction logging disabled due to SQLite BigInteger autoincrement issue
                # Log the interaction
                # log_entry = Interaction_Logs(
                #     instance_id=uow.instance_id,
                #     uow_id=uow.uow_id,
                #     actor_id=actor_id,
                #     role_id=epsilon_role.role_id if epsilon_role else None,
                #     interaction_id=uow.current_interaction_id,
                #     timestamp=timestamp
                # )
                # session.add(log_entry)

                session.flush()
                session.commit()

                return True

            except Exception as e:
                session.rollback()
                raise RuntimeError(f"Failed to report failure: {str(e)}") from e

    def get_memory(
        self,
        actor_id: uuid.UUID,
        role_id: uuid.UUID,
        query: Optional[str] = None,
    ) -> list[Dict[str, Any]]:
        """
        Retrieve memory attributes for a specific actor and role context.
        
        Implements Memory & Learning Specs Section 5: Interface for Actors (Read Access).
        
        This method allows actors to query their accumulated knowledge:
        - Global Blueprints (shared institutional knowledge)
        - Personal Playbook (actor-specific learned patterns)
        
        Args:
            actor_id: The actor requesting memory access
            role_id: The role context to query
            query: Optional search string to filter keys (case-insensitive substring match)
        
        Returns:
            List of memory records, each containing:
            - memory_id: UUID of the memory record
            - key: The memory key
            - value: The stored value/rule
            - context_type: 'GLOBAL' or 'ACTOR'
            - confidence_score: Confidence level (0-100)
            - created_at: When the memory was created
            - last_accessed_at: When last accessed
        
        Raises:
            RuntimeError: If query fails
        """
        with self.db_manager.get_instance_session() as session:
            try:
                # Build the base query
                # Include both GLOBAL memories and actor-specific memories
                actor_id_str = str(actor_id)
                
                base_query = session.query(Local_Role_Attributes).filter(
                    and_(
                        Local_Role_Attributes.role_id == role_id,
                        Local_Role_Attributes.is_toxic.is_not(True),  # Exclude toxic memories
                    )
                )
                
                # Filter by context: GLOBAL or ACTOR-specific
                context_filter = or_(
                    Local_Role_Attributes.context_type == "GLOBAL",
                    and_(
                        Local_Role_Attributes.context_type == "ACTOR",
                        Local_Role_Attributes.context_id == actor_id_str,
                    )
                )
                
                base_query = base_query.filter(context_filter)
                
                # Apply search query if provided (simple substring match on key)
                if query:
                    base_query = base_query.filter(
                        Local_Role_Attributes.key.ilike(f"%{query}%")
                    )
                
                # Execute query
                memories = base_query.all()
                
                # Convert to dictionary list
                results = []
                for memory in memories:
                    results.append({
                        "memory_id": str(memory.memory_id),
                        "key": memory.key,
                        "value": memory.value,
                        "context_type": memory.context_type,
                        "confidence_score": memory.confidence_score,
                        "created_at": memory.created_at.isoformat() if memory.created_at else None,
                        "last_accessed_at": memory.last_accessed_at.isoformat() if memory.last_accessed_at else None,
                    })
                
                return results
                
            except Exception as e:
                raise RuntimeError(f"Failed to retrieve memory: {str(e)}") from e
