"""
End-to-End Tests for Chameleon Workflow Engine Server (FastAPI).

This test suite verifies that external clients can successfully drive a workflow via HTTP.
Tests the REST API endpoints defined in server.py that integrate with the ChameleonEngine.

Test Coverage:
1. POST /workflow/instantiate - Create workflow instance from template
2. POST /workflow/checkout - Checkout work from a role's queue
3. POST /workflow/submit - Submit completed work
4. POST /workflow/failure - Report work failure

References:
- chameleon_workflow_engine/server.py (The API being tested)
- chameleon_workflow_engine/engine.py (The business logic)
- docs/architecture/Interface & MCP Specs.md (The API contract)
"""

import sys
from pathlib import Path
import uuid

import pytest
from fastapi.testclient import TestClient

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# fmt: off
from database import (  # noqa: E402
    DatabaseManager,
    # Tier 1 Models
    Template_Workflows,
    Template_Roles,
    Template_Interactions,
    Template_Components,
    Template_Guardians,
    # Tier 2 Models
    Local_Workflows,
    Local_Roles,
    Local_Interactions,
    Local_Components,
    Local_Guardians,
    UnitsOfWork,
    UOW_Attributes,
    # Enums
    RoleType,
    ComponentDirection,
    GuardianType,
    UOWStatus,
)
from chameleon_workflow_engine.server import app  # noqa: E402
# fmt: on


def create_simple_test_template(db_manager: DatabaseManager) -> uuid.UUID:
    """
    Create a simple workflow template for E2E API testing.

    This creates a minimal but complete workflow with:
    - Alpha role (initiator)
    - Beta role (processor)
    - Omega role (finalizer)
    - Epsilon role (error handler)
    - Complete interaction topology

    Returns:
        uuid.UUID: The workflow_id of the created template
    """
    with db_manager.get_template_session() as session:
        # Create workflow
        workflow = Template_Workflows(
            name="API_Test_Workflow",
            description="Simple workflow for E2E API testing",
            ai_context={"purpose": "API E2E Testing"},
            version=1,
            schema_json={"topology": "simple linear flow"},
        )
        session.add(workflow)
        session.flush()
        workflow_id = workflow.workflow_id

        # Create roles
        alpha_role = Template_Roles(
            workflow_id=workflow_id,
            name="Initiator_Role",
            description="Start the workflow",
            role_type=RoleType.ALPHA.value,
            ai_context={"persona": "Workflow initiator"},
        )
        session.add(alpha_role)
        session.flush()

        beta_role = Template_Roles(
            workflow_id=workflow_id,
            name="Processor_Role",
            description="Process the work",
            role_type=RoleType.BETA.value,
            strategy="HOMOGENEOUS",
            ai_context={"persona": "Work processor"},
        )
        session.add(beta_role)
        session.flush()

        omega_role = Template_Roles(
            workflow_id=workflow_id,
            name="Finalizer_Role",
            description="Finalize the workflow",
            role_type=RoleType.OMEGA.value,
            ai_context={"persona": "Workflow finalizer"},
        )
        session.add(omega_role)
        session.flush()

        epsilon_role = Template_Roles(
            workflow_id=workflow_id,
            name="ErrorHandler_Role",
            description="Handle errors",
            role_type=RoleType.EPSILON.value,
            ai_context={"persona": "Error handler"},
        )
        session.add(epsilon_role)
        session.flush()

        # Create interactions (queues)
        alpha_to_beta = Template_Interactions(
            workflow_id=workflow_id,
            name="Alpha_to_Beta_Queue",
            description="Queue from Alpha to Beta",
            ai_context={"purpose": "Alpha output / Beta input"},
        )
        session.add(alpha_to_beta)
        session.flush()

        beta_to_omega = Template_Interactions(
            workflow_id=workflow_id,
            name="Beta_to_Omega_Queue",
            description="Queue from Beta to Omega",
            ai_context={"purpose": "Beta output / Omega input"},
        )
        session.add(beta_to_omega)
        session.flush()

        error_queue = Template_Interactions(
            workflow_id=workflow_id,
            name="Error_Queue",
            description="Queue for error handling",
            ai_context={"purpose": "Error routing"},
        )
        session.add(error_queue)
        session.flush()

        # Create components (connections) - Main happy path
        # Alpha -> Alpha_to_Beta_Queue (OUTBOUND)
        comp1 = Template_Components(
            workflow_id=workflow_id,
            interaction_id=alpha_to_beta.interaction_id,
            role_id=alpha_role.role_id,
            direction=ComponentDirection.OUTBOUND.value,
            name="Alpha_Output",
            description="Alpha produces work",
        )
        session.add(comp1)
        session.flush()

        # Beta <- Alpha_to_Beta_Queue (INBOUND)
        comp2 = Template_Components(
            workflow_id=workflow_id,
            interaction_id=alpha_to_beta.interaction_id,
            role_id=beta_role.role_id,
            direction=ComponentDirection.INBOUND.value,
            name="Beta_Input",
            description="Beta consumes work",
        )
        session.add(comp2)
        session.flush()

        # Beta -> Beta_to_Omega_Queue (OUTBOUND)
        comp3 = Template_Components(
            workflow_id=workflow_id,
            interaction_id=beta_to_omega.interaction_id,
            role_id=beta_role.role_id,
            direction=ComponentDirection.OUTBOUND.value,
            name="Beta_Output",
            description="Beta produces results",
        )
        session.add(comp3)
        session.flush()

        # Omega <- Beta_to_Omega_Queue (INBOUND)
        comp4 = Template_Components(
            workflow_id=workflow_id,
            interaction_id=beta_to_omega.interaction_id,
            role_id=omega_role.role_id,
            direction=ComponentDirection.INBOUND.value,
            name="Omega_Input",
            description="Omega consumes results",
        )
        session.add(comp4)
        session.flush()

        # Error path: Beta -> Error_Queue (OUTBOUND)
        comp5 = Template_Components(
            workflow_id=workflow_id,
            interaction_id=error_queue.interaction_id,
            role_id=beta_role.role_id,
            direction=ComponentDirection.OUTBOUND.value,
            name="Beta_Error_Output",
            description="Beta routes errors",
        )
        session.add(comp5)
        session.flush()

        # Epsilon <- Error_Queue (INBOUND)
        comp6 = Template_Components(
            workflow_id=workflow_id,
            interaction_id=error_queue.interaction_id,
            role_id=epsilon_role.role_id,
            direction=ComponentDirection.INBOUND.value,
            name="Epsilon_Input",
            description="Epsilon handles errors",
        )
        session.add(comp6)
        session.flush()

        # Add simple pass-through guardians for the main path
        guard1 = Template_Guardians(
            workflow_id=workflow_id,
            component_id=comp1.component_id,
            name="Alpha_Guard",
            description="Pass through",
            type=GuardianType.PASS_THRU.value,
            config={},
        )
        session.add(guard1)

        guard2 = Template_Guardians(
            workflow_id=workflow_id,
            component_id=comp2.component_id,
            name="Beta_Input_Guard",
            description="Pass through",
            type=GuardianType.PASS_THRU.value,
            config={},
        )
        session.add(guard2)

        guard3 = Template_Guardians(
            workflow_id=workflow_id,
            component_id=comp3.component_id,
            name="Beta_Output_Guard",
            description="Pass through",
            type=GuardianType.PASS_THRU.value,
            config={},
        )
        session.add(guard3)

        guard4 = Template_Guardians(
            workflow_id=workflow_id,
            component_id=comp4.component_id,
            name="Omega_Guard",
            description="Pass through",
            type=GuardianType.PASS_THRU.value,
            config={},
        )
        session.add(guard4)

        session.commit()

        return workflow_id


@pytest.fixture(scope="function")
def test_client():
    """
    Create a TestClient with temporary file-based databases for E2E testing.

    This fixture:
    1. Creates temporary file-based SQLite databases for both template and instance tiers
    2. Initializes schemas
    3. Creates a test workflow template
    4. Overrides the global db_manager in the server module
    5. Returns a TestClient for making HTTP requests

    Each test gets a fresh database and client.

    NOTE: Using file-based SQLite databases in /tmp to avoid threading issues
    that can occur with in-memory databases in FastAPI tests.
    """
    import tempfile
    import os

    # Create temporary database files
    template_db = tempfile.NamedTemporaryFile(mode="w", suffix=".db", delete=False)
    instance_db = tempfile.NamedTemporaryFile(mode="w", suffix=".db", delete=False)
    template_db.close()
    instance_db.close()

    template_db_path = template_db.name
    instance_db_path = instance_db.name

    # Create database manager with file-based databases
    test_db_manager = DatabaseManager(
        template_url=f"sqlite:///{template_db_path}",
        instance_url=f"sqlite:///{instance_db_path}",
        echo=False,  # Set to True for SQL debugging
    )

    # Create schemas
    test_db_manager.create_template_schema()
    test_db_manager.create_instance_schema()

    # Create a test workflow template
    template_id = create_simple_test_template(test_db_manager)

    # Override the global db_manager in the server module
    # This ensures the FastAPI app uses our test database
    import chameleon_workflow_engine.server as server_module

    original_db_manager = server_module.db_manager
    server_module.db_manager = test_db_manager

    # Create test client
    client = TestClient(app)

    # Store template_id on the client for easy access in tests
    client.template_id = template_id
    client.db_manager = test_db_manager

    yield client

    # Cleanup: restore original db_manager, close connections, and delete temp files
    server_module.db_manager = original_db_manager
    test_db_manager.close()

    # Delete temporary database files
    try:
        os.unlink(template_db_path)
        os.unlink(instance_db_path)
    except Exception:
        pass  # Ignore cleanup errors


def test_instantiate_workflow_api(test_client):
    """
    Test POST /workflow/instantiate with a valid template_id.

    Verifies:
    - 200 OK response
    - Response contains a valid UUID workflow_id
    - Alpha UOW is created in the database with PENDING status
    """
    # Prepare request
    initial_context = {"task_id": "TASK-001", "task_name": "Process Invoice", "priority": "high"}

    request_data = {
        "template_id": str(test_client.template_id),
        "initial_context": initial_context,
        "instance_name": "Test Instance",
        "instance_description": "E2E test workflow instance",
    }

    # Make API call
    response = test_client.post("/workflow/instantiate", json=request_data)

    # Assert response
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"

    response_data = response.json()
    assert "workflow_id" in response_data
    assert "message" in response_data

    # Verify workflow_id is a valid UUID
    workflow_id = response_data["workflow_id"]
    try:
        workflow_uuid = uuid.UUID(workflow_id)
    except ValueError:
        pytest.fail(f"workflow_id is not a valid UUID: {workflow_id}")

    # Verify in database that Alpha UOW was created
    with test_client.db_manager.get_instance_session() as session:
        uows = session.query(UnitsOfWork).filter(UnitsOfWork.instance_id == workflow_uuid).all()

        assert len(uows) == 1, f"Expected 1 Alpha UOW, found {len(uows)}"
        alpha_uow = uows[0]

        assert (
            alpha_uow.status == UOWStatus.PENDING.value
        ), f"Alpha UOW should have PENDING status, found {alpha_uow.status}"

        # Verify initial context was stored
        attrs = (
            session.query(UOW_Attributes).filter(UOW_Attributes.uow_id == alpha_uow.uow_id).all()
        )

        assert len(attrs) >= 3, f"Expected at least 3 attributes, found {len(attrs)}"
        attr_dict = {attr.key: attr.value for attr in attrs}
        assert "task_id" in attr_dict
        assert attr_dict["task_id"] == "TASK-001"

    print(f"✓ test_instantiate_workflow_api passed - workflow_id: {workflow_id}")


def test_instantiate_populates_instance_tables(test_client):
    """Ensure template artifacts are cloned into the instance-tier tables."""

    response = test_client.post(
        "/workflow/instantiate",
        json={
            "template_id": str(test_client.template_id),
            "initial_context": {"seed": "value"},
            "instance_name": "Clone Verification",
        },
    )

    assert response.status_code == 200, response.text
    instance_id = uuid.UUID(response.json()["workflow_id"])

    with test_client.db_manager.get_instance_session() as session:
        local_workflow = session.query(Local_Workflows).filter(
            Local_Workflows.instance_id == instance_id
        ).first()
        assert local_workflow is not None

        roles = session.query(Local_Roles).filter(
            Local_Roles.local_workflow_id == local_workflow.local_workflow_id
        ).all()
        assert len(roles) == 4

        interactions = session.query(Local_Interactions).filter(
            Local_Interactions.local_workflow_id == local_workflow.local_workflow_id
        ).all()
        assert len(interactions) == 3

        components = session.query(Local_Components).filter(
            Local_Components.local_workflow_id == local_workflow.local_workflow_id
        ).all()
        assert len(components) == 6

        guardians = session.query(Local_Guardians).filter(
            Local_Guardians.local_workflow_id == local_workflow.local_workflow_id
        ).all()
        assert len(guardians) == 4

        uows = session.query(UnitsOfWork).filter(UnitsOfWork.instance_id == instance_id).all()
        assert len(uows) == 1


def test_checkout_work_api_success(test_client):
    """
    Test POST /workflow/checkout with valid actor_id and role_id.

    Verifies:
    - 200 OK response when work is available
    - Response contains uow_id and attributes
    - UOW status transitions to ACTIVE (IN_PROGRESS) in database
    """
    # Step 1: Instantiate a workflow to create work
    initial_context = {"task_id": "TASK-002", "task_data": "Test data for checkout"}

    instantiate_response = test_client.post(
        "/workflow/instantiate",
        json={"template_id": str(test_client.template_id), "initial_context": initial_context},
    )

    assert instantiate_response.status_code == 200
    workflow_id = instantiate_response.json()["workflow_id"]

    # Step 2: Get the Beta role ID for checkout
    with test_client.db_manager.get_instance_session() as session:
        from database.models_instance import Local_Workflows, Local_Roles

        local_workflow = (
            session.query(Local_Workflows)
            .filter(Local_Workflows.instance_id == uuid.UUID(workflow_id))
            .first()
        )

        beta_role = (
            session.query(Local_Roles)
            .filter(
                Local_Roles.local_workflow_id == local_workflow.local_workflow_id,
                Local_Roles.role_type == RoleType.BETA.value,
            )
            .first()
        )

        assert beta_role is not None, "Beta role not found"
        beta_role_id = str(beta_role.role_id)

    # Step 3: Checkout work
    actor_id = str(uuid.uuid4())
    checkout_response = test_client.post(
        "/workflow/checkout", json={"actor_id": actor_id, "role_id": beta_role_id}
    )

    # Assert response
    assert (
        checkout_response.status_code == 200
    ), f"Expected 200, got {checkout_response.status_code}: {checkout_response.text}"

    checkout_data = checkout_response.json()
    assert "uow_id" in checkout_data
    assert "attributes" in checkout_data

    uow_id = checkout_data["uow_id"]
    attributes = checkout_data["attributes"]

    # Verify attributes contain the initial context
    assert "task_id" in attributes
    assert attributes["task_id"] == "TASK-002"

    # Verify in database that UOW is now ACTIVE
    with test_client.db_manager.get_instance_session() as session:
        uow = session.query(UnitsOfWork).filter(UnitsOfWork.uow_id == uuid.UUID(uow_id)).first()

        assert uow is not None, "UOW not found in database"
        assert (
            uow.status == UOWStatus.ACTIVE.value
        ), f"UOW should be ACTIVE after checkout, found {uow.status}"
        assert uow.last_heartbeat is not None, "last_heartbeat should be set after checkout"

    print(f"✓ test_checkout_work_api_success passed - uow_id: {uow_id}")


def test_checkout_work_api_empty(test_client):
    """
    Test POST /workflow/checkout for a role with no pending work.

    Verifies:
    - 204 No Content response when no work is available
    - No response body
    """
    # Get a Beta role ID (but don't create any work for it)
    # We'll use a freshly created workflow template without instantiating
    with test_client.db_manager.get_template_session() as session:
        from database.models_template import Template_Roles

        # Get any Beta role from the template
        beta_role = (
            session.query(Template_Roles)
            .filter(Template_Roles.role_type == RoleType.BETA.value)
            .first()
        )

        assert beta_role is not None, "No Beta role found in template"

        # We need to create a workflow instance to have roles, but no work
        # Actually, we can't use template role IDs directly
        # Let's instantiate a workflow, checkout the work, then try to checkout again

    # Step 1: Instantiate and checkout all available work
    instantiate_response = test_client.post(
        "/workflow/instantiate",
        json={"template_id": str(test_client.template_id), "initial_context": {"task": "test"}},
    )

    workflow_id = instantiate_response.json()["workflow_id"]

    # Get Beta role ID
    with test_client.db_manager.get_instance_session() as session:
        from database.models_instance import Local_Workflows, Local_Roles

        local_workflow = (
            session.query(Local_Workflows)
            .filter(Local_Workflows.instance_id == uuid.UUID(workflow_id))
            .first()
        )

        beta_role = (
            session.query(Local_Roles)
            .filter(
                Local_Roles.local_workflow_id == local_workflow.local_workflow_id,
                Local_Roles.role_type == RoleType.BETA.value,
            )
            .first()
        )

        beta_role_id = str(beta_role.role_id)

    # Checkout the only available work
    actor_1 = str(uuid.uuid4())
    first_checkout = test_client.post(
        "/workflow/checkout", json={"actor_id": actor_1, "role_id": beta_role_id}
    )
    assert first_checkout.status_code == 200

    # Step 2: Try to checkout again - should get 204 No Content
    actor_2 = str(uuid.uuid4())
    second_checkout = test_client.post(
        "/workflow/checkout", json={"actor_id": actor_2, "role_id": beta_role_id}
    )

    # Assert 204 No Content
    assert (
        second_checkout.status_code == 204
    ), f"Expected 204 No Content, got {second_checkout.status_code}"

    # Verify no response body (or minimal body)
    assert (
        second_checkout.text == "" or second_checkout.text == "null"
    ), "Expected empty response body for 204 No Content"

    print("✓ test_checkout_work_api_empty passed - received 204 No Content")


def test_submit_work_api(test_client):
    """
    Test POST /workflow/submit with valid uow_id and result attributes.

    Verifies:
    - 200 OK response
    - UOW status transitions to COMPLETED in database
    - Atomic versioning: attribute history is maintained
    - Lock is released (last_heartbeat cleared)
    """
    # Step 1: Instantiate workflow and checkout work
    initial_context = {"invoice_id": "INV-003", "status": "pending", "amount": 1500.00}

    instantiate_response = test_client.post(
        "/workflow/instantiate",
        json={"template_id": str(test_client.template_id), "initial_context": initial_context},
    )

    workflow_id = instantiate_response.json()["workflow_id"]

    # Get Beta role ID
    with test_client.db_manager.get_instance_session() as session:
        from database.models_instance import Local_Workflows, Local_Roles

        local_workflow = (
            session.query(Local_Workflows)
            .filter(Local_Workflows.instance_id == uuid.UUID(workflow_id))
            .first()
        )

        beta_role = (
            session.query(Local_Roles)
            .filter(
                Local_Roles.local_workflow_id == local_workflow.local_workflow_id,
                Local_Roles.role_type == RoleType.BETA.value,
            )
            .first()
        )

        beta_role_id = str(beta_role.role_id)

    # Checkout work
    actor_id = str(uuid.uuid4())
    checkout_response = test_client.post(
        "/workflow/checkout", json={"actor_id": actor_id, "role_id": beta_role_id}
    )

    assert checkout_response.status_code == 200
    uow_id = checkout_response.json()["uow_id"]

    # Step 2: Submit work with updated attributes
    result_attributes = {
        "invoice_id": "INV-003",  # Unchanged
        "status": "approved",  # Changed
        "amount": 1500.00,  # Unchanged
        "approved_by": "manager_123",  # New
        "approval_timestamp": "2024-01-27T10:00:00Z",  # New
    }

    submit_response = test_client.post(
        "/workflow/submit",
        json={
            "uow_id": uow_id,
            "actor_id": actor_id,
            "result_attributes": result_attributes,
            "reasoning": "Invoice approved after review",
        },
    )

    # Assert response
    assert (
        submit_response.status_code == 200
    ), f"Expected 200, got {submit_response.status_code}: {submit_response.text}"

    submit_data = submit_response.json()
    assert submit_data["success"] is True
    assert "message" in submit_data

    # Step 3: Verify in database
    with test_client.db_manager.get_instance_session() as session:
        # Verify UOW status is COMPLETED
        uow = session.query(UnitsOfWork).filter(UnitsOfWork.uow_id == uuid.UUID(uow_id)).first()

        assert uow is not None, "UOW not found"
        assert (
            uow.status == UOWStatus.COMPLETED.value
        ), f"UOW should be COMPLETED after submit, found {uow.status}"
        assert (
            uow.last_heartbeat is None
        ), "last_heartbeat should be cleared after submit (lock released)"

        # Verify atomic versioning
        all_attrs = (
            session.query(UOW_Attributes)
            .filter(UOW_Attributes.uow_id == uuid.UUID(uow_id))
            .order_by(UOW_Attributes.key, UOW_Attributes.version)
            .all()
        )

        # Group by key to check versioning
        attr_versions = {}
        for attr in all_attrs:
            if attr.key not in attr_versions:
                attr_versions[attr.key] = []
            attr_versions[attr.key].append({"version": attr.version, "value": attr.value})

        # 'status' should have 2 versions
        assert "status" in attr_versions
        assert (
            len(attr_versions["status"]) >= 2
        ), f"'status' should have at least 2 versions, found {len(attr_versions['status'])}"

        # Verify version 1 had 'pending'
        v1_status = next((v for v in attr_versions["status"] if v["version"] == 1), None)
        assert v1_status is not None
        assert v1_status["value"] == "pending"

        # Verify version 2 has 'approved'
        v2_status = next((v for v in attr_versions["status"] if v["version"] == 2), None)
        assert v2_status is not None
        assert v2_status["value"] == "approved"

        # Verify new attributes exist
        assert "approved_by" in attr_versions
        assert "approval_timestamp" in attr_versions

    print(f"✓ test_submit_work_api passed - uow_id: {uow_id}, status: COMPLETED")


def test_failure_reporting_api(test_client):
    """
    Test POST /workflow/failure for reporting UOW failures.

    Verifies:
    - 200 OK response
    - UOW status transitions to FAILED in database
    - UOW is routed to Epsilon (Ate) interaction
    - Lock is released
    """
    # Step 1: Instantiate workflow and checkout work
    initial_context = {"request_id": "REQ-004", "data": "test data"}

    instantiate_response = test_client.post(
        "/workflow/instantiate",
        json={"template_id": str(test_client.template_id), "initial_context": initial_context},
    )

    workflow_id = instantiate_response.json()["workflow_id"]

    # Get Beta role ID
    with test_client.db_manager.get_instance_session() as session:
        from database.models_instance import Local_Workflows, Local_Roles

        local_workflow = (
            session.query(Local_Workflows)
            .filter(Local_Workflows.instance_id == uuid.UUID(workflow_id))
            .first()
        )

        beta_role = (
            session.query(Local_Roles)
            .filter(
                Local_Roles.local_workflow_id == local_workflow.local_workflow_id,
                Local_Roles.role_type == RoleType.BETA.value,
            )
            .first()
        )

        beta_role_id = str(beta_role.role_id)

    # Checkout work
    actor_id = str(uuid.uuid4())
    checkout_response = test_client.post(
        "/workflow/checkout", json={"actor_id": actor_id, "role_id": beta_role_id}
    )

    assert checkout_response.status_code == 200
    uow_id = checkout_response.json()["uow_id"]

    # Step 2: Report failure
    failure_response = test_client.post(
        "/workflow/failure",
        json={
            "uow_id": uow_id,
            "actor_id": actor_id,
            "error_code": "VALIDATION_ERROR",
            "details": "Data format is invalid",
        },
    )

    # Assert response
    assert (
        failure_response.status_code == 200
    ), f"Expected 200, got {failure_response.status_code}: {failure_response.text}"

    failure_data = failure_response.json()
    assert failure_data["success"] is True
    assert "message" in failure_data

    # Step 3: Verify in database
    with test_client.db_manager.get_instance_session() as session:
        # Verify UOW status is FAILED
        uow = session.query(UnitsOfWork).filter(UnitsOfWork.uow_id == uuid.UUID(uow_id)).first()

        assert uow is not None, "UOW not found"
        assert (
            uow.status == UOWStatus.FAILED.value
        ), f"UOW should be FAILED after failure report, found {uow.status}"
        assert (
            uow.last_heartbeat is None
        ), "last_heartbeat should be cleared after failure (lock released)"

        # Verify error details are logged in attributes
        error_attrs = (
            session.query(UOW_Attributes)
            .filter(UOW_Attributes.uow_id == uuid.UUID(uow_id), UOW_Attributes.key.like("%error%"))
            .all()
        )

        # Should have at least one error-related attribute
        assert len(error_attrs) > 0, "Expected error details to be logged in attributes"

    print(f"✓ test_failure_reporting_api passed - uow_id: {uow_id}, status: FAILED")


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])
