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
  salesperson_name?: string;
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
  // Core company data fields (duplicated at top level for easy access)
  industry?: string;
  sub_industry?: string;
  employee_count?: number | string;
  employees_range?: string;
  annual_revenue?: string;
  revenue?: string;
  revenue_range?: string;
  headquarters?: string;
  geographic_reach?: string[];
  founded_year?: number | string;
  founders?: string[];
  ceo?: string;
  target_market?: string;
  customer_segments?: string[];
  products?: string[];
  technologies?: string[];
  competitors?: string[];
  company_type?: string;
  ownership_type?: string;
  linkedin_url?: string;
  phone?: string;
  ticker?: string;
  parent_company?: string;
  num_locations?: number | string;
  // New expanded intelligence sections
  executive_snapshot?: ExecutiveSnapshot;
  buying_signals?: BuyingSignals;
  opportunity_themes?: OpportunityThemesDetailed;
  stakeholder_map?: StakeholderMap;
  stakeholder_profiles?: StakeholderProfiles;
  supporting_assets?: SupportingAssets;
  sales_program?: SalesProgram;
  news_intelligence?: NewsIntelligence;
}

/**
 * Validated company data.
 */
export interface CompanyData {
  company_name: string;
  domain: string;
  industry?: string;
  sub_industry?: string;
  employee_count?: number | string;
  employees_range?: string;
  annual_revenue?: string;
  revenue?: string;
  revenue_range?: string;
  headquarters?: string;
  founded_year?: number | string;
  founders?: string[];
  ceo?: string;
  technology?: string[];
  technologies?: string[];
  target_market?: string;
  customer_segments?: string[];
  geographic_reach?: string[] | string;
  products?: string[];
  competitors?: string[];
  company_type?: string;
  ownership_type?: string;
  linkedin_url?: string;
  phone?: string;
  ticker?: string;
  parent_company?: string;
  num_locations?: number | string;
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
 * Orchestrator Plan - API routing decisions from the orchestrator LLM.
 */
export interface OrchestratorPlan {
  apis_to_query: string[];
  priority_order: string[];
  data_point_mapping: Record<string, string[]>;
  reasoning: string;
  timestamp: string;
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
  orchestratorPlan?: OrchestratorPlan;
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
  news_intelligence?: NewsIntelligence;
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
 * Installed technology item with last seen date.
 */
export interface InstalledTechnology {
  name: string;
  category: string;
  last_seen?: string;
}

/**
 * Technology stack organized by category.
 */
export interface TechnologyStack {
  crm?: string[];
  marketing_automation?: string[];
  sales_tools?: string[];
  infrastructure?: string[];
  analytics?: string[];
  collaboration?: string[];
  security?: string[];
  other?: string[];
}

/**
 * Executive Snapshot - Company overview and classification.
 */
export interface ExecutiveSnapshot {
  accountName?: string;
  companyOverview: string;
  accountType?: 'Public Sector' | 'Private Sector';
  companyClassification: 'Public' | 'Private' | 'Government' | 'Unknown';
  estimatedITSpend?: string;
  installedTechnologies?: InstalledTechnology[];
  technologyStack?: TechnologyStack | TechnologyItem[];
  oneYearEmployeeGrowth?: string;
  twoYearEmployeeGrowth?: string;
  fundingAmount?: string;
  fortuneRank?: string;
  numLocations?: number | string;
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
  value_proposition?: string;
}

/**
 * Detailed intent topic with full description.
 */
export interface IntentTopicDetailed {
  topic: string;
  description: string;
}

/**
 * Technology interest with score and trend.
 */
export interface TechnologyInterest {
  name: string;
  score: number;
  trend: 'increasing' | 'stable' | 'decreasing';
}

/**
 * Interest over time data.
 */
export interface InterestOverTime {
  technologies: TechnologyInterest[];
  summary: string;
}

/**
 * Key signals from news.
 */
export interface KeySignals {
  news_paragraphs: string[];
  implications: string;
}

/**
 * Buying Signals - Intent topics and scoops.
 */
export interface BuyingSignals {
  intentTopics: string[];
  intentTopicsDetailed?: IntentTopicDetailed[];
  interestOverTime?: InterestOverTime;
  topPartnerMentions?: string[];
  keySignals?: KeySignals;
  signalStrength: 'low' | 'medium' | 'high' | 'very_high';
  intentTrend?: 'increasing' | 'stable' | 'decreasing';
  scoops: Scoop[];
  opportunityThemes: OpportunityTheme[];
}

/**
 * Stakeholder contact information.
 */
export interface StakeholderContact {
  email?: string;
  phone?: string;
  directPhone?: string;
  mobilePhone?: string;
  companyPhone?: string;
  linkedinUrl?: string;
  contactAccuracyScore?: number;
  /** 'zoominfo' when phone data was enriched via ZoomInfo Contact Enrich API */
  phoneSource?: string;
}

/**
 * Response from the /contacts/enrich/{domain} endpoint.
 */
export interface ZoomInfoEnrichedContact {
  name: string;
  title: string;
  roleType: string;
  email?: string;
  phone?: string;
  directPhone?: string;
  mobilePhone?: string;
  companyPhone?: string;
  linkedinUrl?: string;
  contactAccuracyScore?: number;
  department?: string;
  managementLevel?: string;
  personId?: string;
  phoneSource: 'zoominfo';
}

export interface ContactEnrichResponse {
  domain: string;
  total_count: number;
  contacts: ZoomInfoEnrichedContact[];
  source: string;
}

/**
 * Stakeholder role type including C-suite, VP, Director, and Manager.
 */
export type StakeholderRoleType = 'CIO' | 'CTO' | 'CISO' | 'COO' | 'CFO' | 'CPO' | 'CEO' | 'CMO' | 'VP' | 'Director' | 'Manager' | 'Unknown';

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
  strategicPriorities: string[] | StrategicPriority[];
  communicationPreference?: string;
  recommendedPlay?: string;
  conversationStarters?: string;
  recommendedNextSteps?: string[];
  factCheckScore?: number;
  factCheckNotes?: string;
}

/**
 * Strategic priority with description.
 */
export interface StrategicPriority {
  priority: string;
  description: string;
}

/**
 * LLM-generated stakeholder profile for a role.
 */
export interface StakeholderProfile {
  bio: string;
  strategic_priorities: StrategicPriority[];
  communication_preference: string;
  conversation_starters: string;
  recommended_next_steps: string[];
}

/**
 * Map of stakeholder profiles by role.
 */
export interface StakeholderProfiles {
  CIO?: StakeholderProfile;
  CTO?: StakeholderProfile;
  CISO?: StakeholderProfile;
  CFO?: StakeholderProfile;
  COO?: StakeholderProfile;
  CPO?: StakeholderProfile;
  [key: string]: StakeholderProfile | undefined;
}

/**
 * Stakeholder Map - Collection of executive profiles.
 */
export interface StakeholderMap {
  stakeholders: Stakeholder[];
  otherContacts?: Stakeholder[];
  lastUpdated?: string;
  searchPerformed?: boolean;
}

/**
 * Opportunity Themes Detailed - Pain points, sales opportunities, solution areas.
 */
export interface OpportunityThemesDetailed {
  pain_points: string[];
  sales_opportunities: string[];
  recommended_solution_areas: string[];
}

/**
 * Supporting asset for a contact (email template, LinkedIn outreach, call script).
 */
export interface ContactSupportingAsset {
  role: string;
  name: string;
  email_template: string;
  linkedin_outreach: string;
  call_script: string;
}

/**
 * Supporting Assets - Outreach templates per contact.
 */
export interface SupportingAssets {
  contacts: ContactSupportingAsset[];
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
 * News Intelligence - Recent company news and events analyzed by LLM Council.
 */
export interface NewsIntelligence {
  executiveChanges: string;
  funding: string;
  partnerships: string;
  expansions: string;
  keyInsights?: string[];
  salesImplications?: string;
  articlesCount: number;
  dateRange: string;
  lastUpdated?: string;
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
