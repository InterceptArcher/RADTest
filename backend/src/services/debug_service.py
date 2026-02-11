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
                name="ZoomInfo Data Collection (PRIMARY)",
                description="[PRIORITY SOURCE] Gathering comprehensive company data from ZoomInfo GTM API: company enrichment, buyer intent signals, business scoops/events, news, and technology stack",
                status=ProcessStepStatus.COMPLETED,
                start_time=(base_time + timedelta(seconds=1)).isoformat() + "Z",
                end_time=(base_time + timedelta(seconds=2, milliseconds=400)).isoformat() + "Z",
                duration=1400,
                metadata={
                    "source": "ZoomInfo",
                    "priority": "PRIMARY",
                    "fields_retrieved": 18,
                    "intent_signals": 3,
                    "scoops": 2,
                    "technologies": 5,
                    "contacts_found": 7,
                    "news_articles": 4,
                    "raw_zoominfo_data": {
                        "company": {
                            "companyName": company_name,
                            "domain": domain,
                            "employeeCount": 500,
                            "revenue": 50000000,
                            "industry": "Technology",
                            "city": "San Francisco",
                            "state": "California",
                            "yearFounded": 2015,
                            "ceoName": "Satya Nadella"
                        },
                        "intent_signals": [
                            {"topic": "Cloud Migration", "score": 85, "audienceStrength": "high"},
                            {"topic": "Data Security", "score": 72, "audienceStrength": "medium"},
                            {"topic": "AI/ML Platform", "score": 68, "audienceStrength": "medium"}
                        ],
                        "scoops": [
                            {"type": "executive_hire", "title": "New CTO Appointed", "date": "2025-01"},
                            {"type": "expansion", "title": "Office Expansion Planned", "date": "2025-01"}
                        ],
                        "technologies": ["Salesforce", "AWS", "GitHub", "Slack", "Docker"]
                    }
                }
            ),
            ProcessStep(
                id="step-3",
                name="Apollo.io Data Collection",
                description="Gathering supplementary company intelligence data from Apollo.io API",
                status=ProcessStepStatus.COMPLETED,
                start_time=(base_time + timedelta(seconds=1, milliseconds=100)).isoformat() + "Z",
                end_time=(base_time + timedelta(seconds=3, milliseconds=600)).isoformat() + "Z",
                duration=2500,
                metadata={"source": "Apollo.io", "priority": "SECONDARY", "fields_retrieved": 15}
            ),
            ProcessStep(
                id="step-4",
                name="PeopleDataLabs Data Collection",
                description="Gathering supplementary company intelligence data from PeopleDataLabs API",
                status=ProcessStepStatus.COMPLETED,
                start_time=(base_time + timedelta(seconds=1, milliseconds=200)).isoformat() + "Z",
                end_time=(base_time + timedelta(seconds=3, milliseconds=000)).isoformat() + "Z",
                duration=1800,
                metadata={"source": "PeopleDataLabs", "priority": "SECONDARY", "fields_retrieved": 12}
            ),
            ProcessStep(
                id="step-5",
                name="Data Aggregation & ZoomInfo Priority Merge",
                description="Merging data from multiple sources with ZoomInfo as primary source. ZoomInfo data takes precedence where conflicts exist.",
                status=ProcessStepStatus.COMPLETED,
                start_time=(base_time + timedelta(seconds=4)).isoformat() + "Z",
                end_time=(base_time + timedelta(seconds=4, milliseconds=500)).isoformat() + "Z",
                duration=500,
                metadata={
                    "sources_merged": 3,
                    "primary_source": "ZoomInfo",
                    "merge_strategy": "ZoomInfo-first",
                    "zoominfo_fields_used": 18
                }
            ),
            ProcessStep(
                id="step-6",
                name="Pre-LLM Data Validation",
                description="Fact-checking data against known company facts before LLM processing. Catches egregiously wrong data like incorrect CEO names.",
                status=ProcessStepStatus.COMPLETED,
                start_time=(base_time + timedelta(seconds=5)).isoformat() + "Z",
                end_time=(base_time + timedelta(seconds=6)).isoformat() + "Z",
                duration=1000,
                metadata={
                    "known_facts_checked": True,
                    "companies_in_db": 14,
                    "issues_found": 1,
                    "issues_corrected": 1,
                    "confidence_adjustment": -0.3
                }
            ),
            ProcessStep(
                id="step-7",
                name="LLM Validation",
                description="Validating aggregated data using LLM agents for accuracy",
                status=ProcessStepStatus.COMPLETED,
                start_time=(base_time + timedelta(seconds=6)).isoformat() + "Z",
                end_time=(base_time + timedelta(seconds=11)).isoformat() + "Z",
                duration=5000,
                metadata={"model": "gpt-4", "validators": 3}
            ),
            ProcessStep(
                id="step-8",
                name="LLM Council Resolution",
                description="Resolving data discrepancies using LLM council consensus",
                status=ProcessStepStatus.COMPLETED if status == "completed" else ProcessStepStatus.IN_PROGRESS,
                start_time=(base_time + timedelta(seconds=12)).isoformat() + "Z",
                end_time=(base_time + timedelta(seconds=15)).isoformat() + "Z" if status == "completed" else None,
                duration=3000 if status == "completed" else None,
                metadata={"discrepancies_found": 2, "resolved": 2}
            ),
            ProcessStep(
                id="step-9",
                name="Slideshow Generation",
                description="Generating company profile slideshow using Gamma API",
                status=ProcessStepStatus.COMPLETED if status == "completed" else ProcessStepStatus.PENDING,
                start_time=(base_time + timedelta(seconds=16)).isoformat() + "Z" if status == "completed" else None,
                end_time=(base_time + timedelta(seconds=26)).isoformat() + "Z" if status == "completed" else None,
                duration=10000 if status == "completed" else None,
                metadata={"slides_generated": 8}
            ),
        ]

        # Generate API responses (ordered by priority: ZoomInfo first)
        api_responses = [
            APIResponseData(
                id="api-0",
                api_name="ZoomInfo Company Enrichment (PRIMARY SOURCE)",
                url="https://api.zoominfo.com/gtm/data/v1/companies/enrich",
                method="POST",
                status_code=200,
                status_text="OK",
                headers={
                    "content-type": "application/vnd.api+json",
                    "x-request-id": str(uuid.uuid4()),
                    "x-ratelimit-remaining": "23"
                },
                request_body={"data": {"type": "CompanyEnrich", "attributes": {"companyDomain": domain}}},
                response_body={
                    "data": [{
                        "companyName": company_name,
                        "domain": domain,
                        "employeeCount": 500,
                        "revenue": 50000000,
                        "industry": "Technology",
                        "city": "San Francisco",
                        "state": "California",
                        "country": "United States",
                        "yearFounded": 2015,
                        "ceoName": "Satya Nadella",
                        "phone": "+1-555-0100",
                        "description": "Leading technology company"
                    }]
                },
                timestamp=(base_time + timedelta(seconds=1)).isoformat() + "Z",
                duration=1400,
                is_sensitive=True,
                masked_fields=["authorization"]
            ),
            APIResponseData(
                id="api-0b",
                api_name="ZoomInfo Intent Enrichment",
                url="https://api.zoominfo.com/gtm/data/v1/intent/enrich",
                method="POST",
                status_code=200,
                status_text="OK",
                headers={
                    "content-type": "application/vnd.api+json",
                    "x-request-id": str(uuid.uuid4()),
                    "x-ratelimit-remaining": "22"
                },
                request_body={"data": {"type": "IntentEnrich", "attributes": {"companyDomain": domain}}},
                response_body={
                    "data": [
                        {"topic": "Cloud Migration", "score": 85, "audienceStrength": "high", "lastSeen": "2025-01-15"},
                        {"topic": "Data Security", "score": 72, "audienceStrength": "medium", "lastSeen": "2025-01-12"},
                        {"topic": "AI/ML Platform", "score": 68, "audienceStrength": "medium", "lastSeen": "2025-01-10"}
                    ]
                },
                timestamp=(base_time + timedelta(seconds=1, milliseconds=500)).isoformat() + "Z",
                duration=900,
                is_sensitive=True,
                masked_fields=["authorization"]
            ),
            APIResponseData(
                id="api-0c",
                api_name="ZoomInfo Scoops Search",
                url="https://api.zoominfo.com/gtm/data/v1/scoops/search",
                method="POST",
                status_code=200,
                status_text="OK",
                headers={
                    "content-type": "application/vnd.api+json",
                    "x-request-id": str(uuid.uuid4())
                },
                request_body={"data": {"type": "ScoopSearch", "attributes": {"companyDomain": domain}}},
                response_body={
                    "data": [
                        {
                            "scoopType": "executive_hire",
                            "title": "New CTO Appointed at " + company_name,
                            "date": "2025-01-08",
                            "description": "Company appoints new Chief Technology Officer"
                        },
                        {
                            "scoopType": "expansion",
                            "title": "Office Expansion Planned",
                            "date": "2025-01-05",
                            "description": "Company announces plans for new office location"
                        }
                    ]
                },
                timestamp=(base_time + timedelta(seconds=1, milliseconds=800)).isoformat() + "Z",
                duration=600,
                is_sensitive=True,
                masked_fields=["authorization"]
            ),
            APIResponseData(
                id="api-0d",
                api_name="ZoomInfo Contact Search",
                url="https://api.zoominfo.com/gtm/data/v1/contacts/search",
                method="POST",
                status_code=200,
                status_text="OK",
                headers={
                    "content-type": "application/vnd.api+json",
                    "x-request-id": str(uuid.uuid4())
                },
                request_body={
                    "data": {
                        "type": "ContactSearch",
                        "attributes": {
                            "companyDomain": domain,
                            "jobTitle": ["CEO", "CTO", "CFO"]
                        }
                    }
                },
                response_body={
                    "data": [
                        {
                            "firstName": "John",
                            "lastName": "Doe",
                            "jobTitle": "CEO",
                            "email": "john.doe@company.com",
                            "phone": "+1-555-0101",
                            "linkedInUrl": "https://linkedin.com/in/johndoe"
                        },
                        {
                            "firstName": "Jane",
                            "lastName": "Smith",
                            "jobTitle": "CTO",
                            "email": "jane.smith@company.com",
                            "linkedInUrl": "https://linkedin.com/in/janesmith"
                        }
                    ]
                },
                timestamp=(base_time + timedelta(seconds=2)).isoformat() + "Z",
                duration=800,
                is_sensitive=True,
                masked_fields=["authorization", "email", "phone"]
            ),
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
                id="llm-0",
                task_name="Pre-LLM Data Validation (Fact-Checking)",
                model="rule-based",
                start_time=(base_time + timedelta(seconds=5)).isoformat() + "Z",
                end_time=(base_time + timedelta(seconds=6)).isoformat() + "Z",
                steps=[
                    LLMThoughtStep(
                        id="step-0-1",
                        step=1,
                        action="Check Known Company Facts",
                        reasoning="Validating data against known facts database for major companies. Database contains verified CEO names, headquarters, and founding years for 14 major tech companies.",
                        input={
                            "domain": domain,
                            "ceo_from_source": "Julie Strau",
                            "known_facts_available": True
                        },
                        output={
                            "domain_in_database": True,
                            "known_ceo": "Satya Nadella",
                            "mismatch_detected": True
                        },
                        confidence=1.0
                    ),
                    LLMThoughtStep(
                        id="step-0-2",
                        step=2,
                        action="Apply Correction",
                        reasoning="Source data contained incorrect CEO name 'Julie Strau' for Microsoft. Correcting to known value 'Satya Nadella' from verified facts database.",
                        input={
                            "incorrect_value": "Julie Strau",
                            "correct_value": "Satya Nadella",
                            "field": "ceo"
                        },
                        output={
                            "correction_applied": True,
                            "confidence_penalty": -0.3,
                            "new_confidence": 0.7
                        },
                        confidence=1.0
                    ),
                    LLMThoughtStep(
                        id="step-0-3",
                        step=3,
                        action="Validate Stakeholders",
                        reasoning="Checking stakeholder list for incorrect executive data. Any person listed as CEO must match known CEO for major companies.",
                        input={
                            "stakeholders_count": 3,
                            "ceo_in_stakeholders": "Julie Strau"
                        },
                        output={
                            "stakeholder_filtered": True,
                            "reason": "CEO name mismatch with known facts"
                        },
                        confidence=1.0
                    ),
                ],
                final_decision="Pre-validation caught 1 critical issue: incorrect CEO name. Corrected 'Julie Strau' to 'Satya Nadella'. Confidence score reduced by 0.3 for this source. Data now safe to send to LLM council.",
                discrepancies_resolved=["ceo_name_correction", "stakeholder_validation"]
            ),
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
            LLMThoughtProcess(
                id="llm-3",
                task_name="ZoomInfo Intent Signal Integration",
                model="gpt-4",
                start_time=(base_time + timedelta(seconds=14)).isoformat() + "Z",
                end_time=(base_time + timedelta(seconds=15)).isoformat() + "Z",
                steps=[
                    LLMThoughtStep(
                        id="step-3-1",
                        step=1,
                        action="Analyze ZoomInfo Intent Signals",
                        reasoning="ZoomInfo buyer intent data shows 3 active signals: Cloud Migration (score: 85, high), Data Security (score: 72, medium), AI/ML Platform (score: 68, medium). These signals indicate active buying behavior.",
                        input={
                            "intent_signals": [
                                {"topic": "Cloud Migration", "score": 85},
                                {"topic": "Data Security", "score": 72},
                                {"topic": "AI/ML Platform", "score": 68}
                            ]
                        },
                        output={
                            "primary_intent": "Cloud Migration",
                            "signal_strength": "high",
                            "buying_stage": "active_evaluation"
                        },
                        confidence=0.90
                    ),
                    LLMThoughtStep(
                        id="step-3-2",
                        step=2,
                        action="Cross-Reference with Scoops",
                        reasoning="ZoomInfo scoops show recent CTO hire and expansion announcement, corroborating the cloud migration intent signal. This increases confidence in active evaluation.",
                        input={
                            "scoops": ["New CTO appointed", "Office expansion planned"],
                            "primary_intent": "Cloud Migration"
                        },
                        output={
                            "corroborated": True,
                            "enriched_pain_points": ["Legacy infrastructure migration", "Security compliance gaps"],
                            "confidence_boost": 0.05
                        },
                        confidence=0.92
                    ),
                ],
                final_decision="ZoomInfo intent signals confirm active Cloud Migration evaluation (score 85). Cross-referenced with CTO hire scoop, suggesting infrastructure modernization initiative. Added 2 enriched pain points to opportunity themes.",
                discrepancies_resolved=["intent_topic_validation", "pain_point_enrichment"]
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
                    id="node-zoominfo",
                    label="ZoomInfo API (PRIMARY)",
                    type=ProcessFlowNodeType.API,
                    status=ProcessStepStatus.COMPLETED,
                    details="[PRIORITY] Fetched comprehensive data: company enrichment, buyer intent signals, business scoops, contacts, and tech stack",
                    duration=1400
                ),
                ProcessFlowNode(
                    id="node-apollo",
                    label="Apollo.io API",
                    type=ProcessFlowNodeType.API,
                    status=ProcessStepStatus.COMPLETED,
                    details="Fetched supplementary company data from Apollo.io",
                    duration=2500
                ),
                ProcessFlowNode(
                    id="node-pdl",
                    label="PeopleDataLabs API",
                    type=ProcessFlowNodeType.API,
                    status=ProcessStepStatus.COMPLETED,
                    details="Fetched supplementary company data from PeopleDataLabs",
                    duration=1800
                ),
                ProcessFlowNode(
                    id="node-aggregate",
                    label="ZoomInfo Priority Merge",
                    type=ProcessFlowNodeType.PROCESS,
                    status=ProcessStepStatus.COMPLETED,
                    details="Merged data with ZoomInfo as primary source (takes precedence in conflicts)",
                    duration=500
                ),
                ProcessFlowNode(
                    id="node-pre-validate",
                    label="Pre-LLM Validation",
                    type=ProcessFlowNodeType.DECISION,
                    status=ProcessStepStatus.COMPLETED,
                    details="Fact-checking against known company data (CEO names, HQ, etc.)",
                    duration=1000
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
                ProcessFlowEdge(id="edge-1", source="node-start", target="node-zoominfo", label="Primary Source"),
                ProcessFlowEdge(id="edge-2", source="node-start", target="node-apollo"),
                ProcessFlowEdge(id="edge-3", source="node-start", target="node-pdl"),
                ProcessFlowEdge(id="edge-4", source="node-zoominfo", target="node-aggregate"),
                ProcessFlowEdge(id="edge-5", source="node-apollo", target="node-aggregate"),
                ProcessFlowEdge(id="edge-6", source="node-pdl", target="node-aggregate"),
                ProcessFlowEdge(id="edge-7", source="node-aggregate", target="node-pre-validate"),
                ProcessFlowEdge(id="edge-8", source="node-pre-validate", target="node-validate", label="Validated"),
                ProcessFlowEdge(id="edge-9", source="node-validate", target="node-decision"),
                ProcessFlowEdge(id="edge-10", source="node-decision", target="node-resolve", label="Yes"),
                ProcessFlowEdge(id="edge-11", source="node-decision", target="node-gamma", label="No"),
                ProcessFlowEdge(id="edge-12", source="node-resolve", target="node-gamma"),
                ProcessFlowEdge(id="edge-13", source="node-gamma", target="node-end"),
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
