"""
Pydantic models for debug data.
Features 018-021: Debug Mode Data Models
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class ProcessStepStatus(str, Enum):
    """Status of a process step."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessStep(BaseModel):
    """Individual process step in the pipeline."""
    id: str = Field(..., description="Unique step identifier")
    name: str = Field(..., description="Step name")
    description: str = Field(..., description="Step description")
    status: ProcessStepStatus = Field(..., description="Step status")
    start_time: Optional[str] = Field(None, description="ISO timestamp when step started")
    end_time: Optional[str] = Field(None, description="ISO timestamp when step ended")
    duration: Optional[int] = Field(None, description="Duration in milliseconds")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

    class Config:
        use_enum_values = True


class APIResponseData(BaseModel):
    """API response data for debug display."""
    id: str = Field(..., description="Unique response identifier")
    api_name: str = Field(..., description="Name of the API")
    url: str = Field(..., description="Request URL")
    method: str = Field(..., description="HTTP method")
    status_code: int = Field(..., description="HTTP status code")
    status_text: str = Field(..., description="HTTP status text")
    headers: Dict[str, str] = Field(..., description="Response headers")
    request_body: Optional[Any] = Field(None, description="Request body")
    response_body: Any = Field(..., description="Response body")
    timestamp: str = Field(..., description="ISO timestamp of the request")
    duration: int = Field(..., description="Duration in milliseconds")
    is_sensitive: Optional[bool] = Field(False, description="Contains sensitive data")
    masked_fields: Optional[List[str]] = Field(None, description="Fields that were masked")


class LLMThoughtStep(BaseModel):
    """Individual step in LLM thought process."""
    id: str = Field(..., description="Step identifier")
    step: int = Field(..., description="Step number")
    action: str = Field(..., description="Action taken")
    reasoning: str = Field(..., description="Reasoning for the action")
    input: Optional[Any] = Field(None, description="Input data")
    output: Optional[Any] = Field(None, description="Output data")
    confidence: Optional[float] = Field(None, ge=0, le=1, description="Confidence score 0-1")


class LLMThoughtProcess(BaseModel):
    """LLM thought process for decision-making."""
    id: str = Field(..., description="Unique process identifier")
    task_name: str = Field(..., description="Name of the task")
    model: str = Field(..., description="LLM model used")
    start_time: str = Field(..., description="ISO timestamp when process started")
    end_time: Optional[str] = Field(None, description="ISO timestamp when process ended")
    steps: List[LLMThoughtStep] = Field(..., description="Thought process steps")
    final_decision: str = Field(..., description="Final decision made")
    discrepancies_resolved: Optional[List[str]] = Field(None, description="List of resolved discrepancies")


class ProcessFlowNodeType(str, Enum):
    """Type of process flow node."""
    START = "start"
    PROCESS = "process"
    DECISION = "decision"
    API = "api"
    LLM = "llm"
    END = "end"


class ProcessFlowNode(BaseModel):
    """Node in the process flow visualization."""
    id: str = Field(..., description="Unique node identifier")
    label: str = Field(..., description="Display label")
    type: ProcessFlowNodeType = Field(..., description="Node type")
    status: ProcessStepStatus = Field(..., description="Node status")
    details: Optional[str] = Field(None, description="Additional details")
    duration: Optional[int] = Field(None, description="Duration in milliseconds")

    class Config:
        use_enum_values = True


class ProcessFlowEdge(BaseModel):
    """Edge connecting nodes in process flow."""
    id: str = Field(..., description="Unique edge identifier")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    label: Optional[str] = Field(None, description="Edge label")


class ProcessFlow(BaseModel):
    """Complete process flow data."""
    nodes: List[ProcessFlowNode] = Field(..., description="Flow nodes")
    edges: List[ProcessFlowEdge] = Field(..., description="Flow edges")


class DebugData(BaseModel):
    """Complete debug data for a job."""
    job_id: str = Field(..., description="Job identifier")
    company_name: str = Field(..., description="Company name")
    domain: str = Field(..., description="Company domain")
    status: str = Field(..., description="Job status")
    process_steps: List[ProcessStep] = Field(..., description="Process steps")
    api_responses: List[APIResponseData] = Field(..., description="API responses")
    llm_thought_processes: List[LLMThoughtProcess] = Field(..., description="LLM thought processes")
    process_flow: ProcessFlow = Field(..., description="Process flow visualization data")
    created_at: str = Field(..., description="ISO timestamp when job was created")
    completed_at: Optional[str] = Field(None, description="ISO timestamp when job completed")

    class Config:
        schema_extra = {
            "example": {
                "job_id": "job-abc-123",
                "company_name": "Acme Corp",
                "domain": "acme.com",
                "status": "completed",
                "process_steps": [],
                "api_responses": [],
                "llm_thought_processes": [],
                "process_flow": {"nodes": [], "edges": []},
                "created_at": "2024-01-15T10:00:00Z",
                "completed_at": "2024-01-15T10:05:00Z"
            }
        }
