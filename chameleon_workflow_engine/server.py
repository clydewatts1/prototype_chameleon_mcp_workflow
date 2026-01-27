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

from typing import Dict, Optional
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from loguru import logger
import os
import asyncio
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from database import DatabaseManager, UnitsOfWork

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Chameleon Workflow Engine",
    description="MCP workflow orchestration engine for AI agents",
    version="0.1.0"
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
                zombies = session.query(UnitsOfWork).filter(
                    and_(
                        UnitsOfWork.status == 'ACTIVE',
                        UnitsOfWork.last_heartbeat < zombie_threshold,
                        UnitsOfWork.last_heartbeat.isnot(None)
                    )
                ).all()
                
                if zombies:
                    logger.warning(f"Zombie Actor Detected - Found {len(zombies)} stale UOW(s)")
                    
                    for zombie in zombies:
                        logger.warning(
                            f"Zombie Actor Detected - Reclaiming Token: "
                            f"UOW {zombie.uow_id}, last heartbeat: {zombie.last_heartbeat}"
                        )
                        zombie.status = 'FAILED'
                    
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
    
    # Initialize database manager with instance database
    instance_db_url = os.getenv("INSTANCE_DB_URL", "sqlite:///instance.db")
    db_manager = DatabaseManager(instance_url=instance_db_url)
    
    try:
        # Create schema if it doesn't exist
        db_manager.create_instance_schema()
        logger.info(f"Database initialized: {instance_db_url}")
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
        "message": "Welcome to the Chameleon Workflow Engine API"
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
        "status": "created"
    }
    
    logger.info(f"Created workflow {workflow_id}: {workflow.name}")
    
    return WorkflowResponse(
        id=workflow_id,
        name=workflow.name,
        status="created",
        description=workflow.description
    )


@app.get("/workflows/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: str):
    """Get workflow details by ID"""
    if workflow_id not in workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    wf = workflows[workflow_id]
    return WorkflowResponse(
        id=wf["id"],
        name=wf["name"],
        status=wf["status"],
        description=wf.get("description")
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
        "message": "Workflow execution started"
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
async def heartbeat(
    uow_id: str, 
    request: HeartbeatRequest,
    db: Session = Depends(get_db_session)
):
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
            success=True,
            message="Heartbeat recorded successfully",
            timestamp=timestamp
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error processing heartbeat for UOW {uow_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("WORKFLOW_ENGINE_HOST", "0.0.0.0")
    port = int(os.getenv("WORKFLOW_ENGINE_PORT", 8000))
    
    logger.info(f"Starting Chameleon Workflow Engine on {host}:{port}")
    
    uvicorn.run(
        "chameleon_workflow_engine.server:app",
        host=host,
        port=port,
        reload=True
    )
