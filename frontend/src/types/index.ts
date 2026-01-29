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
  // New expanded intelligence sections
  executive_snapshot?: ExecutiveSnapshot;
  buying_signals?: BuyingSignals;
  stakeholder_map?: StakeholderMap;
  sales_program?: SalesProgram;
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

/**
 * Dashboard Types
 */

/**
 * Job with metadata for dashboard display.
 */
export interface JobWithMetadata {
  jobId: string;
  companyName: string;
  domain: string;
  industry?: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  currentStep: string;
  result?: ProfileResult;
  createdAt: string;
  completedAt?: string;
}

/**
 * Saved company from Supabase.
 */
export interface SavedCompany {
  id: string;
  jobId: string;
  companyName: string;
  domain: string;
  validatedData: CompanyData;
  confidenceScore: number;
  slideshowUrl?: string;
  savedAt: string;
}

/**
 * Extended company data with all fields from LLM Council.
 */
export interface ExtendedCompanyData {
  company_name: string;
  domain: string;
  industry?: string;
  sub_industry?: string;
  employee_count?: number | string;
  revenue?: string;
  annual_revenue?: string;
  headquarters?: string;
  founded_year?: number | string;
  ceo?: string;
  technology?: string[];
  technologies?: string[];
  target_market?: string;
  geographic_reach?: string | string[];
  founders?: string[];
  customer_segments?: string[];
  products?: string[];
  competitors?: string[];
  company_type?: string;
  linkedin_url?: string;
  contacts?: {
    website?: string;
    linkedin?: string;
    email?: string;
  };
  // New expanded intelligence sections
  executive_snapshot?: ExecutiveSnapshot;
  buying_signals?: BuyingSignals;
  stakeholder_map?: StakeholderMap;
  sales_program?: SalesProgram;
}

/**
 * Intelligence Expansion Types - Executive Snapshot, Buying Signals, Stakeholder Map, Sales Program
 */

/**
 * Technology stack item with category and last seen date.
 */
export interface TechnologyItem {
  name: string;
  category: string;
  lastSeen?: string;
}

/**
 * Executive Snapshot - Company overview and classification.
 */
export interface ExecutiveSnapshot {
  companyOverview: string;
  companyClassification: 'Public' | 'Private' | 'Government' | 'Unknown';
  estimatedITSpend?: string;
  technologyStack: TechnologyItem[];
}

/**
 * Scoop/Trigger event (executive hires, funding, M&A, expansions).
 */
export interface Scoop {
  type: 'executive_hire' | 'funding' | 'expansion' | 'merger_acquisition' | 'product_launch' | 'other';
  title: string;
  date?: string;
  details: string;
}

/**
 * Opportunity theme mapping challenge to solution.
 */
export interface OpportunityTheme {
  challenge: string;
  solutionCategory: string;
}

/**
 * Buying Signals - Intent topics and scoops.
 */
export interface BuyingSignals {
  intentTopics: string[];
  signalStrength: 'low' | 'medium' | 'high' | 'very_high';
  scoops: Scoop[];
  opportunityThemes: OpportunityTheme[];
}

/**
 * Stakeholder contact information.
 */
export interface StakeholderContact {
  email?: string;
  phone?: string;
  linkedinUrl?: string;
}

/**
 * C-suite role type.
 */
export type StakeholderRoleType = 'CIO' | 'CTO' | 'CISO' | 'COO' | 'CFO' | 'CPO' | 'Unknown';

/**
 * Individual stakeholder profile.
 */
export interface Stakeholder {
  name: string;
  title: string;
  roleType: StakeholderRoleType;
  bio?: string;
  isNewHire: boolean;
  hireDate?: string;
  contact: StakeholderContact;
  strategicPriorities: string[];
  communicationPreference?: string;
  recommendedPlay?: string;
}

/**
 * Stakeholder Map - Collection of executive profiles.
 */
export interface StakeholderMap {
  stakeholders: Stakeholder[];
  lastUpdated?: string;
}

/**
 * Intent level for sales program.
 */
export type IntentLevel = 'Low' | 'Medium' | 'High' | 'Very High';

/**
 * Sales Program - Intent-based strategy.
 */
export interface SalesProgram {
  intentLevel: IntentLevel;
  intentScore: number;
  strategyText: string;
}

/**
 * Generated outreach content for a stakeholder.
 */
export interface OutreachContent {
  roleType: StakeholderRoleType;
  stakeholderName?: string;
  email: {
    subject: string;
    body: string;
  };
  linkedin: {
    connectionRequest: string;
    followupMessage: string;
  };
  callScript: {
    opening: string;
    valueProposition: string;
    questions: string[];
    closingCTA: string;
  };
  generatedAt: string;
}

/**
 * Request payload for generating outreach content.
 */
export interface OutreachRequest {
  stakeholderName?: string;
  customContext?: string;
}

/**
 * Response from outreach generation endpoint.
 */
export interface OutreachResponse {
  success: boolean;
  content?: OutreachContent;
  error?: string;
}
