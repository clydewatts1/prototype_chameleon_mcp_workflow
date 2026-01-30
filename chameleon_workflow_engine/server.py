"""
Chameleon Workflow Engine Server

Main entry point for the workflow engine server.
This server provides REST API endpoints for workflow management and orchestration.

The workflow engine coordinates multiple AI agents and manages their execution state,
following principles from AL Wolf's workflow architecture.

API Endpoints:
    POST /workflows - Create a new workflow
    GET /workflows/{id} - Get workflow status
    POST /workflows/{id}/execute - Execute a workflow
    DELETE /workflows/{id} - Delete a workflow
    GET /health - Health check endpoint

Technology Stack:
- FastAPI for REST API
- Pydantic for data validation
- Uvicorn as ASGI server

Development Tools:
- GitHub Copilot: AI pair programming assistant
- Claude: Advanced AI for complex reasoning and architecture
- Antigravity: Because every serious project needs a little fun

Example:
    # Start the server
    python -m chameleon_workflow_engine.server

    # Or with uvicorn directly
    uvicorn chameleon_workflow_engine.server:app --reload
"""

from typing import Dict, Optional, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Response, Request
from pydantic import BaseModel
from loguru import logger
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from database import DatabaseManager, UnitsOfWork
from database.models_phase3 import Phase3DatabaseManager
from database.intervention_store_sqlalchemy import InterventionStoreSQLAlchemy
from chameleon_workflow_engine.engine import ChameleonEngine
from chameleon_workflow_engine.pilot_interface import PilotInterface
from chameleon_workflow_engine.interactive_dashboard import (
    initialize_intervention_store, get_intervention_store, InterventionStatus
)
from chameleon_workflow_engine.jwt_utils import (
    JWTValidator, JWTConfig, PilotToken, InvalidTokenError, MissingTokenError
)
from chameleon_workflow_engine.rbac import PilotAuthContext, InsufficientPermissionsError
from common.config import TEMPLATE_DB_URL, INSTANCE_DB_URL, PHASE3_DB_URL

# Initialize database managers (will be configured on startup)
db_manager: Optional[DatabaseManager] = None
phase3_db_manager: Optional[Phase3DatabaseManager] = None

# Background task handle
zombie_sweeper_task: Optional[asyncio.Task] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    global db_manager, phase3_db_manager, zombie_sweeper_task

    # Startup: Initialize databases and start background tasks
    logger.info(f"Connecting to Template DB: {TEMPLATE_DB_URL}")
    logger.info(f"Connecting to Instance DB: {INSTANCE_DB_URL}")
    logger.info(f"Connecting to Phase 3 DB: {PHASE3_DB_URL}")
    
    # Initialize Tier 1/2 databases (workflow engine)
    db_manager = DatabaseManager(template_url=TEMPLATE_DB_URL, instance_url=INSTANCE_DB_URL)

    try:
        # Create schemas if they don't exist
        db_manager.create_template_schema()
        db_manager.create_instance_schema()
        logger.info(
            f"Databases initialized - Template: {TEMPLATE_DB_URL}, Instance: {INSTANCE_DB_URL}"
        )
    except Exception as e:
        logger.warning(f"Database schema already exists or error: {e}")

    # Initialize Phase 3 database (intervention persistence)
    phase3_db_manager = Phase3DatabaseManager(database_url=PHASE3_DB_URL)
    try:
        phase3_db_manager.create_schema()
        logger.info(f"Phase 3 database initialized: {PHASE3_DB_URL}")
    except Exception as e:
        logger.warning(f"Phase 3 database schema already exists or error: {e}")

    # Initialize intervention store with SQLAlchemy backend
    session = phase3_db_manager.get_session()
    intervention_store = InterventionStoreSQLAlchemy(session)
    initialize_intervention_store(intervention_store)
    logger.info("Intervention store initialized with SQLAlchemy backend")

    # Start zombie sweeper background task
    zombie_sweeper_task = asyncio.create_task(run_tau_zombie_sweeper())
    logger.info("Zombie Actor Sweeper task started")

    yield

    # Shutdown: Clean up background tasks
    if zombie_sweeper_task:
        zombie_sweeper_task.cancel()
        try:
            await zombie_sweeper_task
        except asyncio.CancelledError:
            pass
        logger.info("Zombie Actor Sweeper task stopped")

    # Close database sessions
    if session:
        session.close()
        logger.info("Phase 3 database session closed")


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Chameleon Workflow Engine",
    description="MCP workflow orchestration engine for AI agents",
    version="0.1.0",
    lifespan=lifespan,
)


# Data Models
class WorkflowCreate(BaseModel):
    """Model for creating a new workflow"""

    name: str
    description: Optional[str] = None
    steps: list = []


class WorkflowResponse(BaseModel):
    """Model for workflow response"""

    id: str
    name: str
    status: str
    description: Optional[str] = None


class HeartbeatRequest(BaseModel):
    """Model for heartbeat request"""

    actor_id: str


class HeartbeatResponse(BaseModel):
    """Model for heartbeat response"""

    success: bool
    message: str
    timestamp: datetime


# Workflow Engine API Models
class InstantiateWorkflowRequest(BaseModel):
    """Model for instantiating a workflow from a template"""

    template_id: str
    initial_context: Dict[str, Any]
    instance_name: Optional[str] = None
    instance_description: Optional[str] = None


class InstantiateWorkflowResponse(BaseModel):
    """Model for workflow instantiation response"""

    workflow_id: str
    message: str


class CheckoutWorkRequest(BaseModel):
    """Model for checking out work"""

    actor_id: str
    role_id: str


class CheckoutWorkResponse(BaseModel):
    """Model for checkout work response"""

    uow_id: str
    attributes: Dict[str, Any]
    context: Dict[str, Any]


class SubmitWorkRequest(BaseModel):
    """Model for submitting work"""

    uow_id: str
    actor_id: str
    result_attributes: Dict[str, Any]
    reasoning: Optional[str] = None


class SubmitWorkResponse(BaseModel):
    """Model for submit work response"""

    success: bool
    message: str


class ReportFailureRequest(BaseModel):
    """Model for reporting failure"""

    uow_id: str
    actor_id: str
    error_code: str
    details: Optional[str] = None


class ReportFailureResponse(BaseModel):
    """Model for failure report response"""

    success: bool
    message: str


class RunZombieProtocolRequest(BaseModel):
    """Model for running zombie protocol"""

    timeout_seconds: Optional[int] = 300


class RunZombieProtocolResponse(BaseModel):
    """Model for zombie protocol response"""

    success: bool
    zombies_reclaimed: int
    message: str


class RunMemoryDecayRequest(BaseModel):
    """Model for running memory decay"""

    retention_days: Optional[int] = 90


class RunMemoryDecayResponse(BaseModel):
    """Model for memory decay response"""

    success: bool
    memories_deleted: int
    message: str


class MarkMemoryToxicRequest(BaseModel):
    """Model for marking memory as toxic"""

    memory_id: str
    reason: str


class MarkMemoryToxicResponse(BaseModel):
    """Model for mark memory toxic response"""

    success: bool
    message: str


# ===== Pilot Interface Models (Article XV - Pilot Sovereignty) =====


class PilotKillSwitchRequest(BaseModel):
    """Model for Pilot kill switch intervention"""

    instance_id: str
    reason: str


class PilotKillSwitchResponse(BaseModel):
    """Response for kill switch - all UOWs paused"""

    success: bool
    message: str
    paused_uow_count: int


class PilotClarificationRequest(BaseModel):
    """Model for Pilot clarification submission (break ambiguity lock)"""

    text: str


class PilotClarificationResponse(BaseModel):
    """Response for clarification - UOW resumed from ZOMBIED_SOFT"""

    success: bool
    message: str
    new_status: str


class PilotWaiverRequest(BaseModel):
    """Model for Pilot waiver of Constitutional rule violation"""

    reason: str


class PilotWaiverResponse(BaseModel):
    """Response for waiver - UOW resumed from PAUSED"""

    success: bool
    message: str
    waiver_logged: bool


class PilotResumeResponse(BaseModel):
    """Response for Pilot approval of high-risk transition"""

    success: bool
    message: str
    new_status: str


class PilotCancelRequest(BaseModel):
    """Model for Pilot cancellation of pending UOW"""

    reason: str


class PilotCancelResponse(BaseModel):
    """Response for Pilot cancellation"""

    success: bool
    message: str
    new_status: str


# In-memory storage (replace with database in production)
workflows: Dict[str, dict] = {}


def get_db_session():
    """Dependency to get database session"""
    if db_manager is None or db_manager.instance_engine is None:
        raise HTTPException(status_code=503, detail="Database not initialized")

    with db_manager.get_instance_session() as session:
        yield session


def get_current_pilot(request: Request) -> PilotAuthContext:
    """
    Dependency to extract and validate Pilot identity from JWT token.
    
    Phase 2 implementation: JWT token-based authentication with RBAC.
    
    Expects: Authorization header with format 'Bearer <jwt_token>'
    Claims:
    - sub (str): Pilot ID
    - role (str): Pilot role (ADMIN, OPERATOR, VIEWER)
    - exp (int): Expiration timestamp
    
    Returns:
        PilotAuthContext with pilot_id and role
        
    Raises:
        HTTPException: 401 if token missing/invalid, 403 if role-based access denied
        
    Constitutional Reference: Article XV (Pilot Sovereignty)
    """
    try:
        # Extract Authorization header
        auth_header = request.headers.get("Authorization")
        
        # Initialize JWT validator
        jwt_config = JWTConfig()
        validator = JWTValidator(jwt_config)
        
        # Extract and parse token
        token = validator.extract_bearer_token(auth_header)
        pilot_token: PilotToken = validator.parse_pilot_token(token)
        
        # Create auth context
        auth_context = PilotAuthContext(
            pilot_id=pilot_token.pilot_id,
            role=pilot_token.role,
        )
        
        logger.info(f"Pilot authenticated: {auth_context}")
        
        return auth_context
        
    except MissingTokenError as e:
        logger.warning(f"Missing or invalid Authorization header: {e}")
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header. Expected: 'Authorization: Bearer <token>'"
        )
    except InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {e}")
        raise HTTPException(
            status_code=401,
            detail=f"Invalid token: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Authentication error: {e}", exc_info=True)
        raise HTTPException(
            status_code=401,
            detail="Authentication failed"
        )


def require_pilot_permission(endpoint: str):
    """
    Dependency factory to enforce role-based access control (RBAC).
    
    Usage:
        @app.post("/pilot/kill-switch")
        async def pilot_kill_switch(
            auth: PilotAuthContext = Depends(require_pilot_permission("/pilot/kill-switch")),
        ):
            ...
    
    Args:
        endpoint: Endpoint path for permission check
        
    Returns:
        Dependency function that checks authorization
    """
    async def check_permission_impl(
        auth: PilotAuthContext = Depends(get_current_pilot),
    ) -> PilotAuthContext:
        """Check if Pilot has permission for this endpoint."""
        try:
            auth.require_permission(endpoint)
            logger.debug(f"RBAC: Authorized {auth.pilot_id} for {endpoint}")
            return auth
        except InsufficientPermissionsError as e:
            logger.warning(str(e))
            raise HTTPException(
                status_code=403,
                detail=str(e)
            )
    
    return check_permission_impl


async def run_tau_zombie_sweeper():
    """
    Background task that continuously monitors for zombie actors.

    Runs every 60 seconds and checks for Units of Work with:
    - status == 'ACTIVE'
    - last_heartbeat older than 5 minutes (300 seconds)

    When zombies are detected:
    - Updates status to 'FAILED'
    - Logs warning for reclaiming token
    """
    logger.info("Zombie Actor Sweeper (TAU) starting...")

    while True:
        try:
            await asyncio.sleep(60)  # Run every 60 seconds

            if db_manager is None or db_manager.instance_engine is None:
                logger.debug("Database not initialized, skipping zombie sweep")
                continue

            with db_manager.get_instance_session() as session:
                # Calculate the zombie threshold (5 minutes ago)
                zombie_threshold = datetime.now(timezone.utc) - timedelta(minutes=5)

                # Query for zombie UOWs
                from sqlalchemy import and_

                zombies = (
                    session.query(UnitsOfWork)
                    .filter(
                        and_(
                            UnitsOfWork.status == "ACTIVE",
                            UnitsOfWork.last_heartbeat < zombie_threshold,
                            UnitsOfWork.last_heartbeat.isnot(None),
                        )
                    )
                    .all()
                )

                if zombies:
                    logger.warning(f"Zombie Actor Detected - Found {len(zombies)} stale UOW(s)")

                    for zombie in zombies:
                        logger.warning(
                            f"Zombie Actor Detected - Reclaiming Token: "
                            f"UOW {zombie.uow_id}, last heartbeat: {zombie.last_heartbeat}"
                        )
                        zombie.status = "FAILED"

                    session.commit()
                    logger.info(f"Reclaimed {len(zombies)} zombie tokens")
                else:
                    logger.debug("No zombie actors detected")

        except asyncio.CancelledError:
            logger.info("Zombie Actor Sweeper shutting down...")
            break
        except Exception as e:
            logger.error(f"Unexpected error in zombie sweeper: {e}")
            await asyncio.sleep(60)  # Wait before retrying


@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "name": "Chameleon Workflow Engine",
        "version": "0.1.0",
        "status": "running",
        "message": "Welcome to the Chameleon Workflow Engine API",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# ============================================================================
# Intervention REST API Endpoints (Phase 3)
# ============================================================================


@app.get("/api/interventions/pending")
async def get_pending_interventions(
    limit: int = 50,
    offset: int = 0,
    pilot_id: str | None = None,
):
    """
    Get pending intervention requests.
    
    Args:
        limit: Maximum number of results
        offset: Pagination offset
        pilot_id: Filter by assigned pilot (optional)
    
    Returns:
        List of pending intervention requests
    """
    store = get_intervention_store()
    if not store:
        raise HTTPException(status_code=500, detail="Intervention store not initialized")
    
    requests = store.get_pending_requests(pilot_id=pilot_id, limit=limit)
    # Apply offset manually since store doesn't support it
    return [r.to_dict() for r in requests[offset:]]


@app.get("/api/interventions/metrics")
async def get_metrics():
    """
    Get intervention metrics and analytics.
    
    Returns:
        DashboardMetrics with aggregated statistics
    """
    store = get_intervention_store()
    metrics = store.get_metrics()
    return metrics.to_dict()


@app.get("/api/interventions/{request_id}")
async def get_intervention(request_id: str):
    """
    Get a single intervention request by ID.
    
    Args:
        request_id: The intervention request ID
    
    Returns:
        InterventionRequest object
    """
    store = get_intervention_store()
    request = store.get_request(request_id)
    
    if not request:
        raise HTTPException(status_code=404, detail=f"Intervention {request_id} not found")
    
    return request.to_dict()


@app.post("/api/interventions/{request_id}/approve")
async def approve_intervention(
    request_id: str,
    action_reason: str | None = None,
):
    """
    Approve an intervention request.
    
    Args:
        request_id: The intervention request ID
        action_reason: Optional reason for approval
    
    Returns:
        Updated InterventionRequest
    """
    store = get_intervention_store()
    request = store.update_request(
        request_id=request_id,
        status=InterventionStatus.APPROVED,
        action_reason=action_reason,
    )
    
    if not request:
        raise HTTPException(status_code=404, detail=f"Intervention {request_id} not found")
    
    logger.info(f"Intervention {request_id} approved. Reason: {action_reason}")
    return request.to_dict()


@app.post("/api/interventions/{request_id}/reject")
async def reject_intervention(
    request_id: str,
    action_reason: str | None = None,
):
    """
    Reject an intervention request.
    
    Args:
        request_id: The intervention request ID
        action_reason: Optional reason for rejection
    
    Returns:
        Updated InterventionRequest
    """
    store = get_intervention_store()
    request = store.update_request(
        request_id=request_id,
        status=InterventionStatus.REJECTED,
        action_reason=action_reason,
    )
    
    if not request:
        raise HTTPException(status_code=404, detail=f"Intervention {request_id} not found")
    
    logger.info(f"Intervention {request_id} rejected. Reason: {action_reason}")
    return request.to_dict()


# ============================================================================
# WebSocket Endpoint for Real-Time Updates
# ============================================================================

from fastapi import WebSocket, WebSocketDisconnect


@app.websocket("/ws/interventions")
async def websocket_interventions(websocket: WebSocket):
    """
    WebSocket endpoint for real-time intervention updates.
    
    Message types:
    - subscribe: Subscribe to updates
    - get_pending: Fetch pending requests
    - get_metrics: Fetch metrics
    - request_detail: Get single request details
    
    Sends:
    - pending_requests: List of pending interventions
    - metrics_update: Updated metrics
    - new_request: New intervention created
    - status_changed: Intervention status changed
    """
    await websocket.accept()
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            message_type = data.get("type", "unknown")
            payload = data.get("payload", {})
            
            logger.info(f"WebSocket message received: type={message_type}")
            
            # Route to handler
            if message_type == "subscribe":
                await handle_subscribe(websocket, payload)
            
            elif message_type == "get_pending":
                await handle_get_pending(websocket, payload)
            
            elif message_type == "get_metrics":
                await handle_get_metrics(websocket)
            
            elif message_type == "request_detail":
                await handle_request_detail(websocket, payload)
            
            else:
                await websocket.send_json({
                    "success": False,
                    "error": {"code": "UNKNOWN_MESSAGE", "message": f"Unknown message type: {message_type}"}
                })
    
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "success": False,
                "error": {"code": "SERVER_ERROR", "message": str(e)}
            })
        except:
            pass


async def handle_subscribe(websocket: WebSocket, payload: dict):
    """Handle subscribe message"""
    pilot_id = payload.get("pilot_id")
    await websocket.send_json({
        "success": True,
        "data": {
            "subscribed": True,
            "pilot_id": pilot_id,
            "message": "Subscribed to intervention updates"
        }
    })


async def handle_get_pending(websocket: WebSocket, payload: dict):
    """Handle get_pending message"""
    from chameleon_workflow_engine.interactive_dashboard import WebSocketMessageHandler
    
    handler = WebSocketMessageHandler()
    response = handler.handle_message("get_pending", payload)
    await websocket.send_json(response)


async def handle_get_metrics(websocket: WebSocket):
    """Handle get_metrics message"""
    from chameleon_workflow_engine.interactive_dashboard import WebSocketMessageHandler
    
    handler = WebSocketMessageHandler()
    response = handler.handle_message("get_metrics", {})
    await websocket.send_json(response)


async def handle_request_detail(websocket: WebSocket, payload: dict):
    """Handle request_detail message"""
    from chameleon_workflow_engine.interactive_dashboard import WebSocketMessageHandler
    
    handler = WebSocketMessageHandler()
    response = handler.handle_message("request_detail", payload)
    await websocket.send_json(response)


@app.post("/workflows", response_model=WorkflowResponse)
async def create_workflow(workflow: WorkflowCreate):
    """
    Create a new workflow

    This endpoint creates a new workflow definition that can be executed
    by the workflow engine.
    """
    import uuid

    workflow_id = str(uuid.uuid4())

    workflows[workflow_id] = {
        "id": workflow_id,
        "name": workflow.name,
        "description": workflow.description,
        "steps": workflow.steps,
        "status": "created",
    }

    logger.info(f"Created workflow {workflow_id}: {workflow.name}")

    return WorkflowResponse(
        id=workflow_id, name=workflow.name, status="created", description=workflow.description
    )


@app.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: str):
    """Get workflow details by ID"""
    if workflow_id not in workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")

    wf = workflows[workflow_id]
    return WorkflowResponse(
        id=wf["id"], name=wf["name"], status=wf["status"], description=wf.get("description")
    )


@app.post("/workflows/{workflow_id}/execute")
async def execute_workflow(workflow_id: str):
    """
    Execute a workflow

    This endpoint triggers the execution of a workflow by the engine.
    """
    if workflow_id not in workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Update status to running
    workflows[workflow_id]["status"] = "running"

    logger.info(f"Executing workflow {workflow_id}")

    # TODO: Implement actual workflow execution logic
    # This is where the workflow engine would orchestrate the steps

    return {
        "workflow_id": workflow_id,
        "status": "running",
        "message": "Workflow execution started",
    }


@app.delete("/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str):
    """Delete a workflow"""
    if workflow_id not in workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")

    del workflows[workflow_id]
    logger.info(f"Deleted workflow {workflow_id}")

    return {"message": "Workflow deleted successfully"}


@app.post("/workflow/uow/{uow_id}/heartbeat", response_model=HeartbeatResponse)
async def heartbeat(uow_id: str, request: HeartbeatRequest, db: Session = Depends(get_db_session)):
    """
    Update the heartbeat timestamp for a Unit of Work.

    This endpoint is called by actors to signal they are still processing
    a UOW, preventing it from being marked as a zombie by the TAU sweeper.

    Args:
        uow_id: The unique identifier of the Unit of Work
        request: Contains the actor_id making the heartbeat
        db: Database session (injected)

    Returns:
        HeartbeatResponse with success status and timestamp
    """
    try:
        # Parse UUID
        import uuid

        try:
            uow_uuid = uuid.UUID(uow_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid UOW ID format")

        # Find the UOW
        uow = db.query(UnitsOfWork).filter(UnitsOfWork.uow_id == uow_uuid).first()

        if not uow:
            raise HTTPException(status_code=404, detail="Unit of Work not found")

        # Update the heartbeat timestamp
        timestamp = datetime.now(timezone.utc)
        uow.last_heartbeat = timestamp

        db.commit()

        logger.info(f"Heartbeat received for UOW {uow_id} from actor {request.actor_id}")

        return HeartbeatResponse(
            success=True, message="Heartbeat recorded successfully", timestamp=timestamp
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error processing heartbeat for UOW {uow_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# Workflow Engine API Endpoints


@app.post("/workflow/instantiate", response_model=InstantiateWorkflowResponse)
async def instantiate_workflow(request: InstantiateWorkflowRequest):
    """
    Instantiate a new workflow from a template.

    This endpoint creates a new workflow instance from a template,
    cloning all roles, interactions, components, and guardians,
    and creating the Alpha UOW with the initial context.

    Args:
        request: Contains template_id, initial_context, and optional name/description

    Returns:
        InstantiateWorkflowResponse with the new workflow instance ID
    """
    try:
        if db_manager is None:
            raise HTTPException(status_code=503, detail="Database not initialized")

        # Parse template_id to UUID
        try:
            template_uuid = uuid.UUID(request.template_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid template_id format")

        # Create engine and instantiate workflow
        engine = ChameleonEngine(db_manager)

        instance_id = engine.instantiate_workflow(
            template_id=template_uuid,
            initial_context=request.initial_context,
            instance_name=request.instance_name,
            instance_description=request.instance_description,
        )

        logger.info(
            f"Workflow instantiated: instance_id={instance_id}, template_id={template_uuid}"
        )

        return InstantiateWorkflowResponse(
            workflow_id=str(instance_id), message="Workflow instantiated successfully"
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error instantiating workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/workflow/checkout", response_model=CheckoutWorkResponse)
async def checkout_work(request: CheckoutWorkRequest, response: Response):
    """
    Checkout a Unit of Work from a role's queue.

    This endpoint acquires a UOW from the specified role's inbound interactions,
    locks it for processing, and returns the UOW ID and attributes.

    Args:
        request: Contains actor_id and role_id
        response: FastAPI response object for status code control

    Returns:
        CheckoutWorkResponse with uow_id and attributes, or 204 No Content if no work available
    """
    try:
        if db_manager is None:
            raise HTTPException(status_code=503, detail="Database not initialized")

        # Parse UUIDs
        try:
            actor_uuid = uuid.UUID(request.actor_id)
            role_uuid = uuid.UUID(request.role_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid actor_id or role_id format")

        # Create engine and checkout work
        engine = ChameleonEngine(db_manager)

        result = engine.checkout_work(actor_id=actor_uuid, role_id=role_uuid)

        if result is None:
            # No work available - return 204 No Content
            response.status_code = 204
            return Response(status_code=204)

        # Extract components from the result dict
        uow_id = result["uow_id"]
        attributes = result["attributes"]
        context = result["context"]

        logger.info(
            f"Work checked out: uow_id={uow_id}, actor_id={actor_uuid}, role_id={role_uuid}"
        )

        return CheckoutWorkResponse(
            uow_id=str(uow_id), attributes=attributes, context=context
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error checking out work: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/workflow/submit", response_model=SubmitWorkResponse)
async def submit_work(request: SubmitWorkRequest):
    """
    Submit completed work for a Unit of Work.

    This endpoint submits the results of a completed task, implementing
    atomic versioning and transitioning the UOW to COMPLETED status.

    Args:
        request: Contains uow_id, actor_id, result_attributes, and optional reasoning

    Returns:
        SubmitWorkResponse with success status
    """
    try:
        if db_manager is None:
            raise HTTPException(status_code=503, detail="Database not initialized")

        # Parse UUIDs
        try:
            uow_uuid = uuid.UUID(request.uow_id)
            actor_uuid = uuid.UUID(request.actor_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid uow_id or actor_id format")

        # Create engine and submit work
        engine = ChameleonEngine(db_manager)

        success = engine.submit_work(
            uow_id=uow_uuid,
            actor_id=actor_uuid,
            result_attributes=request.result_attributes,
            reasoning=request.reasoning,
        )

        logger.info(f"Work submitted: uow_id={uow_uuid}, actor_id={actor_uuid}")

        return SubmitWorkResponse(success=success, message="Work submitted successfully")

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error submitting work: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/workflow/failure", response_model=ReportFailureResponse)
async def report_failure(request: ReportFailureRequest):
    """
    Report a failure for a Unit of Work.

    This endpoint flags a UOW as failed, triggering the Ate Path (Epsilon role)
    for error handling.

    Args:
        request: Contains uow_id, actor_id, error_code, and optional details

    Returns:
        ReportFailureResponse with success status
    """
    try:
        if db_manager is None:
            raise HTTPException(status_code=503, detail="Database not initialized")

        # Parse UUIDs
        try:
            uow_uuid = uuid.UUID(request.uow_id)
            actor_uuid = uuid.UUID(request.actor_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid uow_id or actor_id format")

        # Create engine and report failure
        engine = ChameleonEngine(db_manager)

        success = engine.report_failure(
            uow_id=uow_uuid,
            actor_id=actor_uuid,
            error_code=request.error_code,
            details=request.details,
        )

        logger.info(
            f"Failure reported: uow_id={uow_uuid}, actor_id={actor_uuid}, error_code={request.error_code}"
        )

        return ReportFailureResponse(success=success, message="Failure reported successfully")

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error reporting failure: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# Admin Endpoints for Background Services


@app.post("/admin/run-zombie-protocol", response_model=RunZombieProtocolResponse)
async def run_zombie_protocol_endpoint(
    request: RunZombieProtocolRequest, db: Session = Depends(get_db_session)
):
    """
    Manually trigger the Zombie Actor Protocol (Article XI.3).

    This endpoint executes the Tau Role's zombie detection and reclamation logic,
    identifying UOWs that have been locked (ACTIVE) for longer than the timeout
    threshold and resetting/failing them.

    Useful for:
    - Manual testing of the zombie protocol
    - Triggering cleanup on-demand
    - Integration with external cron jobs

    Args:
        request: Contains optional timeout_seconds (default: 300)
        db: Database session (injected)

    Returns:
        RunZombieProtocolResponse with count of zombies reclaimed
    """
    try:
        if db_manager is None:
            raise HTTPException(status_code=503, detail="Database not initialized")

        # Create engine
        engine = ChameleonEngine(db_manager)

        # Run zombie protocol
        zombies_reclaimed = engine.run_zombie_protocol(
            session=db, timeout_seconds=request.timeout_seconds or 300
        )

        logger.info(
            f"Zombie Protocol executed: {zombies_reclaimed} zombie(s) reclaimed "
            f"(timeout: {request.timeout_seconds or 300}s)"
        )

        return RunZombieProtocolResponse(
            success=True,
            zombies_reclaimed=zombies_reclaimed,
            message=f"Zombie protocol completed. Reclaimed {zombies_reclaimed} zombie token(s).",
        )

    except Exception as e:
        logger.error(f"Error running zombie protocol: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/admin/run-memory-decay", response_model=RunMemoryDecayResponse)
async def run_memory_decay_endpoint(
    request: RunMemoryDecayRequest, db: Session = Depends(get_db_session)
):
    """
    Manually trigger Memory Decay / The Janitor (Article XX.3).

    This endpoint executes the memory cleanup logic, removing old/stale memory
    entries that haven't been accessed for longer than the retention period.

    Useful for:
    - Manual testing of the memory decay logic
    - Triggering cleanup on-demand
    - Integration with external cron jobs

    Args:
        request: Contains optional retention_days (default: 90)
        db: Database session (injected)

    Returns:
        RunMemoryDecayResponse with count of memories deleted
    """
    try:
        if db_manager is None:
            raise HTTPException(status_code=503, detail="Database not initialized")

        # Create engine
        engine = ChameleonEngine(db_manager)

        # Run memory decay
        memories_deleted = engine.run_memory_decay(
            session=db, retention_days=request.retention_days or 90
        )

        logger.info(
            f"Memory Decay executed: {memories_deleted} memory entries deleted "
            f"(retention: {request.retention_days or 90} days)"
        )

        return RunMemoryDecayResponse(
            success=True,
            memories_deleted=memories_deleted,
            message=f"Memory decay completed. Deleted {memories_deleted} stale memory entries.",
        )

    except Exception as e:
        logger.error(f"Error running memory decay: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/admin/mark-toxic", response_model=MarkMemoryToxicResponse)
async def mark_memory_toxic_endpoint(request: MarkMemoryToxicRequest):
    """
    Mark a specific memory as "Toxic" (Article XX.1 - The Toxic Knowledge Filter).

    This endpoint flags a memory entry so it is excluded during execution. Used when:
    - A UOW reaches FAILED status and requires Epsilon remediation
    - An Admin identifies a memory that led to incorrect results
    - Post-mortem analysis reveals problematic learned patterns

    Toxic memories are automatically excluded from context during work checkout
    (see the _build_memory_context method in the engine).

    Args:
        request: Contains memory_id and reason for marking toxic

    Returns:
        MarkMemoryToxicResponse with success status
    """
    try:
        if db_manager is None:
            raise HTTPException(status_code=503, detail="Database not initialized")

        # Parse memory_id to UUID
        try:
            memory_uuid = uuid.UUID(request.memory_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid memory_id format")

        # Create engine
        engine = ChameleonEngine(db_manager)

        # Mark memory as toxic
        engine.mark_memory_toxic(memory_id=memory_uuid, reason=request.reason)

        logger.info(f"Memory {memory_uuid} marked as toxic. Reason: {request.reason}")

        return MarkMemoryToxicResponse(
            success=True,
            message=f"Memory {memory_uuid} successfully marked as toxic.",
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error marking memory as toxic: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# ===== Pilot Interface Endpoints (Article XV - Pilot Sovereignty) =====
# All Pilot actions require X-Pilot-ID header for authentication


@app.post("/pilot/kill-switch", response_model=PilotKillSwitchResponse)
async def pilot_kill_switch(
    request: PilotKillSwitchRequest,
    auth: PilotAuthContext = Depends(require_pilot_permission("/pilot/kill-switch")),
    db: Session = Depends(get_db_session),
):
    """
    Emergency halt: Pilot pauses all ACTIVE UOWs in an instance.
    
    Requires: ADMIN role (Article XV - Pilot Sovereignty)
    Authentication: JWT token in 'Authorization: Bearer <token>' header
    
    Args:
        request: Contains instance_id and reason for emergency halt
        auth: Authenticated Pilot context from JWT token
        db: Database session
        
    Returns:
        PilotKillSwitchResponse with count of paused UOWs
        
    Raises:
        HTTPException: 401 if auth token invalid, 403 if insufficient role, 400 if invalid instance_id, 500 on error
    """
    try:
        # Parse instance_id
        try:
            instance_uuid = uuid.UUID(request.instance_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid instance_id format")
        
        if db_manager is None:
            raise HTTPException(status_code=503, detail="Database not initialized")
        
        # Create PilotInterface instance
        pilot_interface = PilotInterface(db_manager)
        
        # Execute kill switch
        paused_count = pilot_interface.kill_switch(
            instance_id=instance_uuid,
            reason=request.reason,
            pilot_id=auth.pilot_id
        )
        
        logger.info(
            f"Pilot {auth.pilot_id} ({auth.role.value}) executed kill_switch on instance {instance_uuid}: "
            f"paused {paused_count} UOWs. Reason: {request.reason}"
        )
        
        return PilotKillSwitchResponse(
            success=True,
            message=f"Kill switch executed: {paused_count} UOWs paused",
            paused_uow_count=paused_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in pilot kill_switch: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/pilot/clarification/{uow_id}", response_model=PilotClarificationResponse)
async def pilot_submit_clarification(
    uow_id: str,
    request: PilotClarificationRequest,
    auth: PilotAuthContext = Depends(require_pilot_permission("/pilot/clarification")),
    db: Session = Depends(get_db_session),
):
    """
    Break ambiguity lock: Pilot provides clarification to resume ZOMBIED_SOFT UOW.
    
    Requires: OPERATOR+ role (Article XV - Pilot Sovereignty)
    Authentication: JWT token in 'Authorization: Bearer <token>' header
    
    Args:
        uow_id: Unit of Work ID in ZOMBIED_SOFT status
        request: Contains clarification text
        auth: Authenticated Pilot context from JWT token
        db: Database session
        
    Returns:
        PilotClarificationResponse with new UOW status
        
    Raises:
        HTTPException: 401 if auth token invalid, 403 if insufficient role, 400 if invalid uow_id, 404 if UOW not found, 500 on error
    """
    try:
        # Parse uow_id
        try:
            uow_uuid = uuid.UUID(uow_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid uow_id format")
        
        if db_manager is None:
            raise HTTPException(status_code=503, detail="Database not initialized")
        
        # Create PilotInterface instance
        pilot_interface = PilotInterface(db_manager)
        
        # Submit clarification
        new_status = pilot_interface.submit_clarification(
            uow_id=uow_uuid,
            text=request.text,
            pilot_id=auth.pilot_id
        )
        
        logger.info(
            f"Pilot {auth.pilot_id} ({auth.role.value}) submitted clarification for UOW {uow_uuid}. "
            f"New status: {new_status}"
        )
        
        return PilotClarificationResponse(
            success=True,
            message=f"Clarification submitted for UOW {uow_id}",
            new_status=new_status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in pilot submit_clarification: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/pilot/waive/{uow_id}/{guard_rule_id}", response_model=PilotWaiverResponse)
async def pilot_waive_violation(
    uow_id: str,
    guard_rule_id: str,
    request: PilotWaiverRequest,
    auth: PilotAuthContext = Depends(require_pilot_permission("/pilot/waive")),
    db: Session = Depends(get_db_session),
):
    """
    Constitutional waiver: Pilot overrides a Constitutional violation with justification.
    
    Requires: ADMIN role only (Article XV - Pilot Sovereignty)
    Authentication: JWT token in 'Authorization: Bearer <token>' header
    
    Args:
        uow_id: Unit of Work ID in PAUSED status
        guard_rule_id: ID of the Guardian rule being waived
        request: Contains mandatory justification reason
        auth: Authenticated Pilot context from JWT token
        db: Database session
        
    Returns:
        PilotWaiverResponse with waiver logged flag
        
    Raises:
        HTTPException: 401 if auth token invalid, 403 if insufficient role, 400 if invalid IDs or empty reason, 404 if UOW not found, 500 on error
    """
    try:
        # Parse IDs
        try:
            uow_uuid = uuid.UUID(uow_id)
            guard_rule_uuid = uuid.UUID(guard_rule_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid uow_id or guard_rule_id format")
        
        # Validate reason is non-empty
        if not request.reason or not request.reason.strip():
            raise HTTPException(status_code=400, detail="Waiver reason cannot be empty")
        
        if db_manager is None:
            raise HTTPException(status_code=503, detail="Database not initialized")
        
        # Create PilotInterface instance
        pilot_interface = PilotInterface(db_manager)
        
        # Execute waiver
        new_status = pilot_interface.waive_violation(
            uow_id=uow_uuid,
            guard_rule_id=guard_rule_uuid,
            reason=request.reason,
            pilot_id=auth.pilot_id
        )
        
        logger.info(
            f"Pilot {auth.pilot_id} ({auth.role.value}) waived guard rule {guard_rule_uuid} for UOW {uow_uuid}. "
            f"Reason: {request.reason}"
        )
        
        return PilotWaiverResponse(
            success=True,
            message=f"Constitutional waiver recorded for UOW {uow_id}",
            waiver_logged=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in pilot waive_violation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/pilot/resume/{uow_id}", response_model=PilotResumeResponse)
async def pilot_resume_uow(
    uow_id: str,
    auth: PilotAuthContext = Depends(require_pilot_permission("/pilot/resume")),
    db: Session = Depends(get_db_session),
):
    """
    Approve high-risk transition: Pilot resumes PENDING_PILOT_APPROVAL UOW.
    
    Requires: OPERATOR+ role (Article XV - Pilot Sovereignty)
    Authentication: JWT token in 'Authorization: Bearer <token>' header
    
    Args:
        uow_id: Unit of Work ID in PENDING_PILOT_APPROVAL status
        auth: Authenticated Pilot context from JWT token
        db: Database session
        
    Returns:
        PilotResumeResponse with new UOW status
        
    Raises:
        HTTPException: 401 if auth token invalid, 403 if insufficient role, 400 if invalid uow_id, 404 if UOW not found, 500 on error
    """
    try:
        # Parse uow_id
        try:
            uow_uuid = uuid.UUID(uow_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid uow_id format")
        
        if db_manager is None:
            raise HTTPException(status_code=503, detail="Database not initialized")
        
        # Create PilotInterface instance
        pilot_interface = PilotInterface(db_manager)
        
        # Resume UOW
        new_status = pilot_interface.resume_uow(
            uow_id=uow_uuid,
            pilot_id=auth.pilot_id
        )
        
        logger.info(f"Pilot {auth.pilot_id} ({auth.role.value}) approved high-risk transition for UOW {uow_uuid}")
        
        return PilotResumeResponse(
            success=True,
            message=f"High-risk transition approved for UOW {uow_id}",
            new_status=new_status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in pilot resume_uow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/pilot/cancel/{uow_id}", response_model=PilotCancelResponse)
async def pilot_cancel_uow(
    uow_id: str,
    request: PilotCancelRequest,
    auth: PilotAuthContext = Depends(require_pilot_permission("/pilot/cancel")),
    db: Session = Depends(get_db_session),
):
    """
    Reject high-risk transition: Pilot cancels PENDING_PILOT_APPROVAL UOW.
    
    Requires: OPERATOR+ role (Article XV - Pilot Sovereignty)
    Authentication: JWT token in 'Authorization: Bearer <token>' header
    
    Args:
        uow_id: Unit of Work ID in PENDING_PILOT_APPROVAL status
        request: Contains reason for cancellation
        auth: Authenticated Pilot context from JWT token
        db: Database session
        
    Returns:
        PilotCancelResponse with new UOW status (FAILED)
        
    Raises:
        HTTPException: 401 if auth token invalid, 403 if insufficient role, 400 if invalid uow_id, 404 if UOW not found, 500 on error
    """
    try:
        # Parse uow_id
        try:
            uow_uuid = uuid.UUID(uow_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid uow_id format")
        
        if db_manager is None:
            raise HTTPException(status_code=503, detail="Database not initialized")
        
        # Create PilotInterface instance
        pilot_interface = PilotInterface(db_manager)
        
        # Cancel UOW
        new_status = pilot_interface.cancel_uow(
            uow_id=uow_uuid,
            pilot_id=auth.pilot_id,
            reason=request.reason
        )
        
        logger.info(
            f"Pilot {auth.pilot_id} ({auth.role.value}) rejected high-risk transition for UOW {uow_uuid}. "
            f"Reason: {request.reason}"
        )
        
        return PilotCancelResponse(
            success=True,
            message=f"High-risk transition rejected for UOW {uow_id}",
            new_status=new_status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in pilot cancel_uow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    import os

    host = os.getenv("WORKFLOW_ENGINE_HOST", "0.0.0.0")
    port = int(os.getenv("WORKFLOW_ENGINE_PORT", 8000))

    logger.info(f"Starting Chameleon Workflow Engine on {host}:{port}")

    uvicorn.run("chameleon_workflow_engine.server:app", host=host, port=port, reload=False)
