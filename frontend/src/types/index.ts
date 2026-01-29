/**
 * Type definitions for the RADTest application.
 */

/**
 * Company profile request payload.
 */
export interface CompanyProfileRequest {
  company_name: string;
  domain: string;
  industry?: string;
  requested_by: string;
}

/**
 * Profile request response from backend.
 */
export interface ProfileRequestResponse {
  status: string;
  job_id: string;
  message?: string;
}

/**
 * Error response from backend.
 */
export interface ErrorResponse {
  error: string;
  detail?: string | any;
}

/**
 * Processing status for a job.
 */
export interface JobStatus {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress?: number;
  current_step?: string;
  result?: ProfileResult;
  error?: string;
}

/**
 * Final profile result.
 */
export interface ProfileResult {
  success: boolean;
  company_name: string;
  domain: string;
  slideshow_url?: string;
  confidence_score: number;
  finalize_record_id?: string;
  validated_data?: CompanyData;
}

/**
 * Validated company data.
 */
export interface CompanyData {
  company_name: string;
  domain: string;
  industry?: string;
  employee_count?: number | string;
  revenue?: string;
  headquarters?: string;
  founded_year?: number | string;
  ceo?: string;
  technology?: string[];
  target_market?: string;
  geographic_reach?: string;
  contacts?: {
    website?: string;
    linkedin?: string;
    email?: string;
  };
}

/**
 * Form validation errors.
 */
export interface FormErrors {
  company_name?: string;
  domain?: string;
  industry?: string;
  requested_by?: string;
}

/**
 * Debug Mode Types - Features 018-021
 */

/**
 * Process step status.
 */
export type ProcessStepStatus = 'pending' | 'in_progress' | 'completed' | 'failed';

/**
 * Individual process step in the pipeline.
 */
export interface ProcessStep {
  id: string;
  name: string;
  description: string;
  status: ProcessStepStatus;
  startTime?: string;
  endTime?: string;
  duration?: number;
  metadata?: Record<string, unknown>;
}

/**
 * API response data for debug display.
 */
export interface APIResponseData {
  id: string;
  apiName: string;
  url: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  statusCode: number;
  statusText: string;
  headers: Record<string, string>;
  requestBody?: unknown;
  responseBody: unknown;
  timestamp: string;
  duration: number;
  isSensitive?: boolean;
  maskedFields?: string[];
}

/**
 * LLM thought process step.
 */
export interface LLMThoughtStep {
  id: string;
  step: number;
  action: string;
  reasoning: string;
  input?: unknown;
  output?: unknown;
  confidence?: number;
  timestamp?: string;
}

/**
 * LLM thought process for decision-making.
 */
export interface LLMThoughtProcess {
  id: string;
  taskName: string;
  model: string;
  promptTokens?: number;
  completionTokens?: number;
  totalTokens?: number;
  startTime: string;
  endTime?: string;
  duration?: number;
  steps: LLMThoughtStep[];
  finalDecision: string;
  confidenceScore?: number;
  discrepanciesResolved?: string[];
}

/**
 * Process flow node for visualization.
 */
export interface ProcessFlowNode {
  id: string;
  label: string;
  type: 'start' | 'process' | 'decision' | 'api' | 'llm' | 'end';
  status: ProcessStepStatus;
  details?: string;
  duration?: number;
}

/**
 * Process flow connection.
 */
export interface ProcessFlowEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
}

/**
 * Complete process flow data.
 */
export interface ProcessFlow {
  nodes: ProcessFlowNode[];
  edges: ProcessFlowEdge[];
}

/**
 * Complete debug data for a job.
 */
export interface DebugData {
  jobId: string;
  companyName: string;
  domain: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  processSteps: ProcessStep[];
  apiResponses: APIResponseData[];
  llmThoughtProcesses: LLMThoughtProcess[];
  processFlow: ProcessFlow;
  createdAt: string;
  completedAt?: string;
}
