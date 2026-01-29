"""
Debug service for retrieving process inspection data.
Features 018-021: Debug Mode Service

This service handles retrieval of debug data including process steps,
API responses, and LLM thought processes. In production, this would
retrieve data from a persistent store (e.g., Supabase).
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid
import logging

from ..models.debug import (
    ProcessStep,
    ProcessStepStatus,
    APIResponseData,
    LLMThoughtStep,
    LLMThoughtProcess,
    ProcessFlowNode,
    ProcessFlowNodeType,
    ProcessFlowEdge,
    ProcessFlow,
    DebugData,
)

logger = logging.getLogger(__name__)

# In-memory store for demo purposes
# In production, this would be backed by Supabase or another database
_debug_data_store: Dict[str, DebugData] = {}


class DebugServiceError(Exception):
    """Exception raised by debug service operations."""
    pass


class DebugService:
    """Service for managing debug data."""

    @staticmethod
    def generate_debug_data_for_job(
        job_id: str,
        company_name: str,
        domain: str,
        status: str = "completed"
    ) -> DebugData:
        """
        Generate debug data for a job.

        In production, this would retrieve actual logged data from the database.
        For now, it generates sample data to demonstrate the debug UI.
        """
        base_time = datetime.utcnow() - timedelta(minutes=5)

        # Generate process steps
        process_steps = [
            ProcessStep(
                id="step-1",
                name="Request Initialization",
                description="Initializing company profile request and validating input data",
                status=ProcessStepStatus.COMPLETED,
                start_time=(base_time).isoformat() + "Z",
                end_time=(base_time + timedelta(milliseconds=500)).isoformat() + "Z",
                duration=500,
                metadata={"request_id": job_id}
            ),
            ProcessStep(
                id="step-2",
                name="Apollo.io Data Collection",
                description="Gathering company intelligence data from Apollo.io API",
                status=ProcessStepStatus.COMPLETED,
                start_time=(base_time + timedelta(seconds=1)).isoformat() + "Z",
                end_time=(base_time + timedelta(seconds=3, milliseconds=500)).isoformat() + "Z",
                duration=2500,
                metadata={"source": "Apollo.io", "fields_retrieved": 15}
            ),
            ProcessStep(
                id="step-3",
                name="PeopleDataLabs Data Collection",
                description="Gathering company intelligence data from PeopleDataLabs API",
                status=ProcessStepStatus.COMPLETED,
                start_time=(base_time + timedelta(seconds=1)).isoformat() + "Z",
                end_time=(base_time + timedelta(seconds=2, milliseconds=800)).isoformat() + "Z",
                duration=1800,
                metadata={"source": "PeopleDataLabs", "fields_retrieved": 12}
            ),
            ProcessStep(
                id="step-4",
                name="Data Aggregation",
                description="Merging data from multiple sources into unified format",
                status=ProcessStepStatus.COMPLETED,
                start_time=(base_time + timedelta(seconds=4)).isoformat() + "Z",
                end_time=(base_time + timedelta(seconds=4, milliseconds=500)).isoformat() + "Z",
                duration=500,
                metadata={"sources_merged": 2}
            ),
            ProcessStep(
                id="step-5",
                name="LLM Validation",
                description="Validating aggregated data using LLM agents for accuracy",
                status=ProcessStepStatus.COMPLETED,
                start_time=(base_time + timedelta(seconds=5)).isoformat() + "Z",
                end_time=(base_time + timedelta(seconds=10)).isoformat() + "Z",
                duration=5000,
                metadata={"model": "gpt-4", "validators": 3}
            ),
            ProcessStep(
                id="step-6",
                name="Conflict Resolution",
                description="Resolving data discrepancies using LLM council consensus",
                status=ProcessStepStatus.COMPLETED if status == "completed" else ProcessStepStatus.IN_PROGRESS,
                start_time=(base_time + timedelta(seconds=11)).isoformat() + "Z",
                end_time=(base_time + timedelta(seconds=14)).isoformat() + "Z" if status == "completed" else None,
                duration=3000 if status == "completed" else None,
                metadata={"discrepancies_found": 2, "resolved": 2}
            ),
            ProcessStep(
                id="step-7",
                name="Slideshow Generation",
                description="Generating company profile slideshow using Gamma API",
                status=ProcessStepStatus.COMPLETED if status == "completed" else ProcessStepStatus.PENDING,
                start_time=(base_time + timedelta(seconds=15)).isoformat() + "Z" if status == "completed" else None,
                end_time=(base_time + timedelta(seconds=25)).isoformat() + "Z" if status == "completed" else None,
                duration=10000 if status == "completed" else None,
                metadata={"slides_generated": 8}
            ),
        ]

        # Generate API responses
        api_responses = [
            APIResponseData(
                id="api-1",
                api_name="Apollo.io Company Enrichment",
                url="https://api.apollo.io/v1/companies/enrich",
                method="POST",
                status_code=200,
                status_text="OK",
                headers={
                    "content-type": "application/json",
                    "x-request-id": str(uuid.uuid4()),
                    "x-ratelimit-remaining": "95"
                },
                request_body={"domain": domain},
                response_body={
                    "company": {
                        "name": company_name,
                        "domain": domain,
                        "employee_count": 500,
                        "industry": "Technology",
                        "founded_year": 2015,
                        "headquarters": "San Francisco, CA"
                    }
                },
                timestamp=(base_time + timedelta(seconds=1)).isoformat() + "Z",
                duration=2500,
                is_sensitive=True,
                masked_fields=["api_key"]
            ),
            APIResponseData(
                id="api-2",
                api_name="PeopleDataLabs Company API",
                url="https://api.peopledatalabs.com/v5/company/enrich",
                method="GET",
                status_code=200,
                status_text="OK",
                headers={
                    "content-type": "application/json",
                    "x-request-id": str(uuid.uuid4())
                },
                response_body={
                    "company": {
                        "name": company_name,
                        "domain": domain,
                        "size": "201-500",
                        "industry": "Software Development",
                        "founded": 2015,
                        "location": "San Francisco, California, USA"
                    }
                },
                timestamp=(base_time + timedelta(seconds=1, milliseconds=100)).isoformat() + "Z",
                duration=1800,
                is_sensitive=True,
                masked_fields=["api_key"]
            ),
            APIResponseData(
                id="api-3",
                api_name="OpenAI Chat Completion",
                url="https://api.openai.com/v1/chat/completions",
                method="POST",
                status_code=200,
                status_text="OK",
                headers={
                    "content-type": "application/json"
                },
                request_body={
                    "model": "gpt-4",
                    "messages": [{"role": "user", "content": "Validate company data..."}]
                },
                response_body={
                    "choices": [{"message": {"content": "Data validated successfully"}}]
                },
                timestamp=(base_time + timedelta(seconds=5)).isoformat() + "Z",
                duration=5000,
                is_sensitive=True,
                masked_fields=["api_key", "authorization"]
            ),
        ]

        # Generate LLM thought processes
        llm_thought_processes = [
            LLMThoughtProcess(
                id="llm-1",
                task_name="Employee Count Discrepancy Resolution",
                model="gpt-4",
                start_time=(base_time + timedelta(seconds=11)).isoformat() + "Z",
                end_time=(base_time + timedelta(seconds=12, milliseconds=500)).isoformat() + "Z",
                steps=[
                    LLMThoughtStep(
                        id="step-1-1",
                        step=1,
                        action="Compare Data Sources",
                        reasoning="Apollo.io reports 500 employees while PeopleDataLabs reports '201-500'. Need to resolve this discrepancy.",
                        input={
                            "apollo": {"employee_count": 500},
                            "pdl": {"size": "201-500"}
                        },
                        output={
                            "discrepancy_type": "range_vs_exact",
                            "compatible": True
                        },
                        confidence=0.95
                    ),
                    LLMThoughtStep(
                        id="step-1-2",
                        step=2,
                        action="Evaluate Data Compatibility",
                        reasoning="Apollo.io provides exact count (500) which falls within PeopleDataLabs range (201-500). Data sources are compatible.",
                        input={"apollo_exact": 500, "pdl_range": "201-500"},
                        output={"selected_value": 500, "reason": "Exact value within range"},
                        confidence=0.92
                    ),
                ],
                final_decision="Selected employee count of 500 from Apollo.io as it provides more precision and falls within the PeopleDataLabs range.",
                discrepancies_resolved=["employee_count"]
            ),
            LLMThoughtProcess(
                id="llm-2",
                task_name="Industry Classification Reconciliation",
                model="gpt-4",
                start_time=(base_time + timedelta(seconds=13)).isoformat() + "Z",
                end_time=(base_time + timedelta(seconds=14)).isoformat() + "Z",
                steps=[
                    LLMThoughtStep(
                        id="step-2-1",
                        step=1,
                        action="Compare Industry Labels",
                        reasoning="Apollo.io categorizes as 'Technology' while PeopleDataLabs uses 'Software Development'. These are related but not identical.",
                        input={
                            "apollo": "Technology",
                            "pdl": "Software Development"
                        },
                        output={
                            "semantic_similarity": 0.85,
                            "compatible": True
                        },
                        confidence=0.88
                    ),
                    LLMThoughtStep(
                        id="step-2-2",
                        step=2,
                        action="Select Most Specific Label",
                        reasoning="'Software Development' is more specific than 'Technology'. More specific labels are generally more useful for targeting.",
                        output={
                            "selected_value": "Software Development",
                            "parent_category": "Technology"
                        },
                        confidence=0.85
                    ),
                ],
                final_decision="Selected 'Software Development' as primary industry (more specific), with 'Technology' as parent category.",
                discrepancies_resolved=["industry"]
            ),
        ]

        # Generate process flow
        process_flow = ProcessFlow(
            nodes=[
                ProcessFlowNode(
                    id="node-start",
                    label="Request Received",
                    type=ProcessFlowNodeType.START,
                    status=ProcessStepStatus.COMPLETED,
                    details="Profile request initiated",
                    duration=500
                ),
                ProcessFlowNode(
                    id="node-apollo",
                    label="Apollo.io API",
                    type=ProcessFlowNodeType.API,
                    status=ProcessStepStatus.COMPLETED,
                    details="Fetched company data from Apollo.io",
                    duration=2500
                ),
                ProcessFlowNode(
                    id="node-pdl",
                    label="PeopleDataLabs API",
                    type=ProcessFlowNodeType.API,
                    status=ProcessStepStatus.COMPLETED,
                    details="Fetched company data from PeopleDataLabs",
                    duration=1800
                ),
                ProcessFlowNode(
                    id="node-aggregate",
                    label="Data Aggregation",
                    type=ProcessFlowNodeType.PROCESS,
                    status=ProcessStepStatus.COMPLETED,
                    details="Merged data from multiple sources",
                    duration=500
                ),
                ProcessFlowNode(
                    id="node-validate",
                    label="LLM Validation",
                    type=ProcessFlowNodeType.LLM,
                    status=ProcessStepStatus.COMPLETED,
                    details="Data validated by LLM agents",
                    duration=5000
                ),
                ProcessFlowNode(
                    id="node-decision",
                    label="Data Discrepancy?",
                    type=ProcessFlowNodeType.DECISION,
                    status=ProcessStepStatus.COMPLETED,
                    details="Checking for data conflicts"
                ),
                ProcessFlowNode(
                    id="node-resolve",
                    label="LLM Council",
                    type=ProcessFlowNodeType.LLM,
                    status=ProcessStepStatus.COMPLETED if status == "completed" else ProcessStepStatus.IN_PROGRESS,
                    details="Resolving conflicts with LLM council",
                    duration=3000 if status == "completed" else None
                ),
                ProcessFlowNode(
                    id="node-gamma",
                    label="Gamma API",
                    type=ProcessFlowNodeType.API,
                    status=ProcessStepStatus.COMPLETED if status == "completed" else ProcessStepStatus.PENDING,
                    details="Generate slideshow",
                    duration=10000 if status == "completed" else None
                ),
                ProcessFlowNode(
                    id="node-end",
                    label="Complete",
                    type=ProcessFlowNodeType.END,
                    status=ProcessStepStatus.COMPLETED if status == "completed" else ProcessStepStatus.PENDING
                ),
            ],
            edges=[
                ProcessFlowEdge(id="edge-1", source="node-start", target="node-apollo"),
                ProcessFlowEdge(id="edge-2", source="node-start", target="node-pdl"),
                ProcessFlowEdge(id="edge-3", source="node-apollo", target="node-aggregate"),
                ProcessFlowEdge(id="edge-4", source="node-pdl", target="node-aggregate"),
                ProcessFlowEdge(id="edge-5", source="node-aggregate", target="node-validate"),
                ProcessFlowEdge(id="edge-6", source="node-validate", target="node-decision"),
                ProcessFlowEdge(id="edge-7", source="node-decision", target="node-resolve", label="Yes"),
                ProcessFlowEdge(id="edge-8", source="node-decision", target="node-gamma", label="No"),
                ProcessFlowEdge(id="edge-9", source="node-resolve", target="node-gamma"),
                ProcessFlowEdge(id="edge-10", source="node-gamma", target="node-end"),
            ]
        )

        debug_data = DebugData(
            job_id=job_id,
            company_name=company_name,
            domain=domain,
            status=status,
            process_steps=process_steps,
            api_responses=api_responses,
            llm_thought_processes=llm_thought_processes,
            process_flow=process_flow,
            created_at=base_time.isoformat() + "Z",
            completed_at=(base_time + timedelta(seconds=25)).isoformat() + "Z" if status == "completed" else None
        )

        # Store for later retrieval
        _debug_data_store[job_id] = debug_data

        return debug_data

    @staticmethod
    def get_debug_data(job_id: str) -> Optional[DebugData]:
        """
        Retrieve debug data for a job.

        Returns None if job not found.
        """
        # Check in-memory store
        if job_id in _debug_data_store:
            return _debug_data_store[job_id]

        # In production, this would query Supabase
        # For demo, generate sample data for any job ID that starts with 'job-'
        if job_id.startswith('job-'):
            return DebugService.generate_debug_data_for_job(
                job_id=job_id,
                company_name="Demo Company",
                domain="demo.com",
                status="completed"
            )

        return None

    @staticmethod
    def get_process_steps(job_id: str) -> Optional[List[ProcessStep]]:
        """Get process steps for a job."""
        debug_data = DebugService.get_debug_data(job_id)
        if debug_data:
            return debug_data.process_steps
        return None

    @staticmethod
    def get_api_responses(job_id: str, mask_sensitive: bool = True) -> Optional[List[APIResponseData]]:
        """Get API responses for a job with optional sensitive data masking."""
        debug_data = DebugService.get_debug_data(job_id)
        if debug_data:
            responses = debug_data.api_responses
            if mask_sensitive:
                # Apply additional masking if needed
                # (masking is already applied during generation)
                pass
            return responses
        return None

    @staticmethod
    def get_llm_thought_processes(job_id: str) -> Optional[List[LLMThoughtProcess]]:
        """Get LLM thought processes for a job."""
        debug_data = DebugService.get_debug_data(job_id)
        if debug_data:
            return debug_data.llm_thought_processes
        return None

    @staticmethod
    def get_process_flow(job_id: str) -> Optional[ProcessFlow]:
        """Get process flow for a job."""
        debug_data = DebugService.get_debug_data(job_id)
        if debug_data:
            return debug_data.process_flow
        return None

    @staticmethod
    def check_debug_available(job_id: str) -> bool:
        """Check if debug data is available for a job."""
        return DebugService.get_debug_data(job_id) is not None


# Create singleton instance
debug_service = DebugService()
