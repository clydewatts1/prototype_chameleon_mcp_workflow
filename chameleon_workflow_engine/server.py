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
from fastapi import FastAPI, HTTPException, Depends, Response
from pydantic import BaseModel
from loguru import logger
import os
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from database import DatabaseManager, UnitsOfWork
from chameleon_workflow_engine.engine import ChameleonEngine

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Chameleon Workflow Engine",
    description="MCP workflow orchestration engine for AI agents",
    version="0.1.0",
)

# Initialize database manager (will be configured on startup)
db_manager: Optional[DatabaseManager] = None

# Background task handle
zombie_sweeper_task: Optional[asyncio.Task] = None


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


# In-memory storage (replace with database in production)
workflows: Dict[str, dict] = {}


def get_db_session():
    """Dependency to get database session"""
    if db_manager is None or db_manager.instance_engine is None:
        raise HTTPException(status_code=503, detail="Database not initialized")

    with db_manager.get_instance_session() as session:
        yield session


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


@app.on_event("startup")
async def startup_event():
    """Initialize database and start background tasks on startup"""
    global db_manager, zombie_sweeper_task

    # Initialize database manager with both template and instance databases
    # Template DB for workflow templates, Instance DB for runtime state
    template_db_url = os.getenv("TEMPLATE_DB_URL", "sqlite:///template.db")
    instance_db_url = os.getenv("INSTANCE_DB_URL", "sqlite:///instance.db")
    db_manager = DatabaseManager(template_url=template_db_url, instance_url=instance_db_url)

    try:
        # Create schemas if they don't exist
        db_manager.create_template_schema()
        db_manager.create_instance_schema()
        logger.info(
            f"Databases initialized - Template: {template_db_url}, Instance: {instance_db_url}"
        )
    except Exception as e:
        logger.warning(f"Database schema already exists or error: {e}")

    # Start zombie sweeper background task
    zombie_sweeper_task = asyncio.create_task(run_tau_zombie_sweeper())
    logger.info("Zombie Actor Sweeper task started")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up background tasks on shutdown"""
    global zombie_sweeper_task

    if zombie_sweeper_task:
        zombie_sweeper_task.cancel()
        try:
            await zombie_sweeper_task
        except asyncio.CancelledError:
            pass
        logger.info("Zombie Actor Sweeper task stopped")


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


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("WORKFLOW_ENGINE_HOST", "0.0.0.0")
    port = int(os.getenv("WORKFLOW_ENGINE_PORT", 8000))

    logger.info(f"Starting Chameleon Workflow Engine on {host}:{port}")

    uvicorn.run("chameleon_workflow_engine.server:app", host=host, port=port, reload=True)
