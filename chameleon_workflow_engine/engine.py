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
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

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
    Interaction_Logs,
)
from database.enums import (
    RoleType,
    UOWStatus,
    ComponentDirection,
)


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
        instance_description: Optional[str] = None
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
                    template_workflow = template_session.query(Template_Workflows).filter(
                        Template_Workflows.workflow_id == template_id
                    ).first()
                    
                    if not template_workflow:
                        raise ValueError(f"Template workflow {template_id} not found")
                    
                    # Step 2: Create Instance Context (The World)
                    instance_id = uuid.uuid4()
                    instance_context = Instance_Context(
                        instance_id=instance_id,
                        name=instance_name or f"Instance_{template_workflow.name}",
                        description=instance_description or f"Instantiated from {template_workflow.name}",
                        status="ACTIVE"
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
                        is_master=True
                    )
                    instance_session.add(local_workflow)
                    instance_session.flush()
                    
                    # Step 4: Clone Roles (maintaining mapping for later steps)
                    role_mapping = {}  # template_role_id -> local_role_id
                    template_roles = template_session.query(Template_Roles).filter(
                        Template_Roles.workflow_id == template_id
                    ).all()
                    
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
                            is_recursive_gateway=template_role.child_workflow_id is not None,  # Derive from child_workflow_id presence
                            linked_local_workflow_id=None  # TODO: Handle recursive workflows
                        )
                        instance_session.add(local_role)
                        role_mapping[template_role.role_id] = local_role_id
                        
                        # Track the Alpha role for later
                        if template_role.role_type == RoleType.ALPHA.value:
                            alpha_role_id = local_role_id
                    
                    instance_session.flush()
                    
                    if not alpha_role_id:
                        raise ValueError(f"Template workflow {template_id} has no Alpha role")
                    
                    # Step 5: Clone Interactions (maintaining mapping)
                    interaction_mapping = {}  # template_interaction_id -> local_interaction_id
                    template_interactions = template_session.query(Template_Interactions).filter(
                        Template_Interactions.workflow_id == template_id
                    ).all()
                    
                    for template_interaction in template_interactions:
                        local_interaction_id = uuid.uuid4()
                        local_interaction = Local_Interactions(
                            interaction_id=local_interaction_id,
                            local_workflow_id=local_workflow.local_workflow_id,
                            name=template_interaction.name,
                            description=template_interaction.description,
                            ai_context=template_interaction.ai_context,
                            stale_token_limit_seconds=None  # Template doesn't have this field, set to None
                        )
                        instance_session.add(local_interaction)
                        interaction_mapping[template_interaction.interaction_id] = local_interaction_id
                    
                    instance_session.flush()
                    
                    # Step 6: Clone Components (creating connections)
                    template_components = template_session.query(Template_Components).filter(
                        Template_Components.workflow_id == template_id
                    ).all()
                    
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
                            ai_context=template_component.ai_context
                        )
                        instance_session.add(local_component)
                        
                        # Find the outbound interaction from Alpha role
                        if (role_mapping[template_component.role_id] == alpha_role_id and 
                            template_component.direction == ComponentDirection.OUTBOUND.value):
                            alpha_outbound_interaction_id = interaction_mapping[template_component.interaction_id]
                    
                    instance_session.flush()
                    
                    if not alpha_outbound_interaction_id:
                        raise ValueError(f"No outbound interaction found for Alpha role")
                    
                    # Step 7: Clone Guardians
                    template_guardians = template_session.query(Template_Guardians).filter(
                        Template_Guardians.workflow_id == template_id
                    ).all()
                    
                    component_mapping = {}  # template_component_id -> local_component_id
                    # We need to rebuild the component mapping with IDs
                    for template_component in template_components:
                        # Find the corresponding local component
                        local_component = instance_session.query(Local_Components).filter(
                            and_(
                                Local_Components.local_workflow_id == local_workflow.local_workflow_id,
                                Local_Components.interaction_id == interaction_mapping[template_component.interaction_id],
                                Local_Components.role_id == role_mapping[template_component.role_id],
                                Local_Components.direction == template_component.direction
                            )
                        ).first()
                        if local_component:
                            component_mapping[template_component.component_id] = local_component.component_id
                    
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
                                attributes=template_guardian.config  # Template uses 'config', Instance uses 'attributes'
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
                        last_heartbeat=None
                    )
                    instance_session.add(alpha_uow)
                    instance_session.flush()
                    
                    # Step 9: Create initial UOW attributes from initial_context
                    # Store each key-value pair from initial_context as a separate attribute
                    system_actor_id = uuid.uuid4()  # TODO: Should use a proper SYSTEM actor
                    for key, value in initial_context.items():
                        uow_attr = UOW_Attributes(
                            attribute_id=uuid.uuid4(),
                            uow_id=alpha_uow.uow_id,
                            instance_id=instance_id,
                            key=key,
                            value=value,
                            version=1,
                            actor_id=system_actor_id,
                            reasoning="Initial workflow context"
                        )
                        instance_session.add(uow_attr)
                    
                    instance_session.flush()
                    
                    # Commit the transaction
                    instance_session.commit()
                    
                    return instance_id
                    
                except Exception as e:
                    instance_session.rollback()
                    raise RuntimeError(f"Failed to instantiate workflow: {str(e)}") from e

    def checkout_work(
        self,
        actor_id: uuid.UUID,
        role_id: uuid.UUID
    ) -> Optional[Tuple[uuid.UUID, Dict[str, Any]]]:
        """
        Acquire a Unit of Work from a specific Role's queue with transactional locking.
        
        Implements Interface & MCP Specs Section 1.1: Tool checkout_work
        Enforces UOW Lifecycle Specs Section 2.2: Valid Transition Matrix (PENDING → IN_PROGRESS)
        
        Process:
        1. Query Instance_Interactions to find PENDING UOWs for this role_id
        2. Join with Instance_Components and Instance_Guardians to verify path exists
        3. Execute Transactional Lock:
           - Select a candidate UOW
           - Update status to IN_PROGRESS (ACTIVE in current enum)
           - Set locked_by = actor_id
           - Set locked_at = NOW
        4. Return the uow_id and its attributes
        
        Args:
            actor_id: The Actor's unique identity
            role_id: The Role the Actor is assuming
            
        Returns:
            Tuple of (uow_id, attributes dict) if work found, None if no work available
            
        Raises:
            ValueError: If role not found or invalid
        """
        with self.db_manager.get_instance_session() as session:
            try:
                # Step 1: Find the role and verify it exists
                role = session.query(Local_Roles).filter(
                    Local_Roles.role_id == role_id
                ).first()
                
                if not role:
                    raise ValueError(f"Role {role_id} not found")
                
                # Step 2: Find INBOUND components for this role
                # These represent interactions that feed work into this role
                inbound_components = session.query(Local_Components).filter(
                    and_(
                        Local_Components.role_id == role_id,
                        Local_Components.direction == ComponentDirection.INBOUND.value
                    )
                ).all()
                
                if not inbound_components:
                    # No inbound paths, no work can arrive
                    return None
                
                # Extract the interaction IDs that feed this role
                inbound_interaction_ids = [comp.interaction_id for comp in inbound_components]
                
                # Step 3: Find PENDING UOWs in these interactions
                # Using PENDING as equivalent to the spec's queue state
                candidate_uow = session.query(UnitsOfWork).filter(
                    and_(
                        UnitsOfWork.current_interaction_id.in_(inbound_interaction_ids),
                        UnitsOfWork.status == UOWStatus.PENDING.value
                    )
                ).first()
                
                if not candidate_uow:
                    # No work available
                    return None
                
                # Step 4: Execute Transactional Lock
                # Transition PENDING → IN_PROGRESS (using ACTIVE status)
                candidate_uow.status = UOWStatus.ACTIVE.value
                candidate_uow.last_heartbeat = datetime.now(timezone.utc)
                # Note: locked_by and locked_at fields need to be added to the model
                # For now, we're using status change and last_heartbeat as the lock mechanism
                
                session.flush()
                
                # Step 5: Retrieve the UOW attributes
                uow_attributes = session.query(UOW_Attributes).filter(
                    UOW_Attributes.uow_id == candidate_uow.uow_id
                ).all()
                
                # Build attributes dictionary from the latest version of each key
                attributes_dict = {}
                for attr in uow_attributes:
                    # If multiple versions exist, we want the latest
                    if attr.key not in attributes_dict or attr.version > attributes_dict[attr.key]['version']:
                        attributes_dict[attr.key] = {
                            'value': attr.value,
                            'version': attr.version
                        }
                
                # Simplify to just key-value pairs
                result_attributes = {key: data['value'] for key, data in attributes_dict.items()}
                
                # Log the interaction
                log_entry = Interaction_Logs(
                    instance_id=candidate_uow.instance_id,
                    uow_id=candidate_uow.uow_id,
                    actor_id=actor_id,
                    role_id=role_id,
                    interaction_id=candidate_uow.current_interaction_id,
                    timestamp=datetime.now(timezone.utc)
                )
                session.add(log_entry)
                
                session.commit()
                
                return (candidate_uow.uow_id, result_attributes)
                
            except Exception as e:
                session.rollback()
                raise RuntimeError(f"Failed to checkout work: {str(e)}") from e

    def submit_work(
        self,
        uow_id: uuid.UUID,
        actor_id: uuid.UUID,
        result_attributes: Dict[str, Any],
        reasoning: Optional[str] = None
    ) -> bool:
        """
        Submit the results of a completed task, unlocking the UOW and moving it to next stage.
        
        Implements Interface & MCP Specs Section 1.2: Tool submit_work
        Enforces UOW Lifecycle Specs Section 3: Atomic Versioning (The Data Physics)
        Enforces Article XVII: Historical Lineage and Attribution
        
        Process:
        1. Verify that uow_id is locked by actor_id (Security Check)
        2. Implement Atomic Versioning (Spec 3.2):
           - Calculate diff between old attributes and result_attributes
           - Insert records into UOW_Attributes (versioned history)
        3. Update Status to COMPLETED
        4. Release the lock (locked_by = NULL)
        
        Args:
            uow_id: The token being processed
            actor_id: The Actor's identity (must match lock holder)
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
                uow = session.query(UnitsOfWork).filter(
                    UnitsOfWork.uow_id == uow_id
                ).first()
                
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
                current_attrs = session.query(UOW_Attributes).filter(
                    UOW_Attributes.uow_id == uow_id
                ).all()
                
                # Build current state (latest version of each key)
                current_state = {}
                version_map = {}
                for attr in current_attrs:
                    if attr.key not in current_state or attr.version > version_map[attr.key]:
                        current_state[attr.key] = attr.value
                        version_map[attr.key] = attr.version
                
                # Step 3: Atomic Versioning - Create new attribute records for changes
                timestamp = datetime.now(timezone.utc)
                for key, new_value in result_attributes.items():
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
                            reasoning=reasoning or f"Work submitted by actor {actor_id}"
                        )
                        session.add(uow_attr)
                
                session.flush()
                
                # Step 4: Update UOW Status to COMPLETED
                uow.status = UOWStatus.COMPLETED.value
                uow.last_heartbeat = None  # Release heartbeat
                
                # Log the interaction
                log_entry = Interaction_Logs(
                    instance_id=uow.instance_id,
                    uow_id=uow.uow_id,
                    actor_id=actor_id,
                    role_id=None,  # TODO: Should track which role completed it
                    interaction_id=uow.current_interaction_id,
                    timestamp=timestamp
                )
                session.add(log_entry)
                
                session.commit()
                
                return True
                
            except Exception as e:
                session.rollback()
                raise RuntimeError(f"Failed to submit work: {str(e)}") from e

    def report_failure(
        self,
        uow_id: uuid.UUID,
        actor_id: uuid.UUID,
        error_code: str,
        details: Optional[str] = None
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
                uow = session.query(UnitsOfWork).filter(
                    UnitsOfWork.uow_id == uow_id
                ).first()
                
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
                epsilon_role = session.query(Local_Roles).filter(
                    and_(
                        Local_Roles.local_workflow_id == uow.local_workflow_id,
                        Local_Roles.role_type == RoleType.EPSILON.value
                    )
                ).first()
                
                ate_interaction_id = None
                if epsilon_role:
                    # Find the INBOUND component for Epsilon role (the Ate interaction)
                    ate_component = session.query(Local_Components).filter(
                        and_(
                            Local_Components.role_id == epsilon_role.role_id,
                            Local_Components.direction == ComponentDirection.INBOUND.value
                        )
                    ).first()
                    
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
                        "actor_id": str(actor_id)
                    },
                    version=1,  # Error records start at version 1
                    actor_id=actor_id,
                    reasoning=f"Failure reported: {error_code}"
                )
                session.add(error_attr)
                
                # Step 4: Update UOW Status to FAILED
                uow.status = UOWStatus.FAILED.value
                uow.last_heartbeat = None  # Release heartbeat
                
                # Step 5: Move to Ate interaction if found
                if ate_interaction_id:
                    uow.current_interaction_id = ate_interaction_id
                
                # Log the interaction
                log_entry = Interaction_Logs(
                    instance_id=uow.instance_id,
                    uow_id=uow.uow_id,
                    actor_id=actor_id,
                    role_id=epsilon_role.role_id if epsilon_role else None,
                    interaction_id=uow.current_interaction_id,
                    timestamp=timestamp
                )
                session.add(log_entry)
                
                session.flush()
                session.commit()
                
                return True
                
            except Exception as e:
                session.rollback()
                raise RuntimeError(f"Failed to report failure: {str(e)}") from e
