/**
 * Debug Mode Page.
 * Features 018-021: Debug UI for Process Inspection
 */

'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import {
  DebugPanel,
  APIResponseDisplay,
  LLMThoughtDisplay,
  ProcessFlowVisualization,
} from '@/components/debug';
import LoadingSpinner from '@/components/LoadingSpinner';
import { debugApiClient } from '@/lib/debugApi';
import type { DebugData } from '@/types';

type TabType = 'process' | 'api' | 'llm' | 'flow';

/**
 * Generate demo data for showcasing debug features.
 */
const generateDemoData = (): DebugData => ({
  jobId: 'demo-job-123',
  companyName: 'Microsoft Corporation',
  domain: 'microsoft.com',
  status: 'completed',
  processSteps: [
    {
      id: 'step-1',
      name: 'Initialize Request',
      description: 'Received and validated company profile request',
      status: 'completed',
      startTime: new Date(Date.now() - 300000).toISOString(),
      endTime: new Date(Date.now() - 299500).toISOString(),
      duration: 500,
      metadata: { requestId: 'req-abc-123' },
    },
    {
      id: 'step-2',
      name: 'ZoomInfo Data Collection (PRIMARY)',
      description: '[PRIORITY SOURCE] Gathering comprehensive company data from ZoomInfo GTM API: company enrichment, buyer intent signals, business scoops/events, news, and technology stack',
      status: 'completed',
      startTime: new Date(Date.now() - 299000).toISOString(),
      endTime: new Date(Date.now() - 297600).toISOString(),
      duration: 1400,
      metadata: {
        source: 'ZoomInfo',
        priority: 'PRIMARY',
        fields_retrieved: 18,
        intent_signals: 3,
        scoops: 2,
        technologies: 5,
        contacts_found: 7,
        news_articles: 4,
        raw_zoominfo_data: {
          company: {
            companyName: 'Microsoft Corporation',
            domain: 'microsoft.com',
            employeeCount: 221000,
            revenue: 211900000000,
            industry: 'Technology',
            city: 'Redmond',
            state: 'Washington',
            yearFounded: 1975,
            ceoName: 'Satya Nadella',
          },
          intent_signals: [
            { topic: 'Cloud Migration', score: 85, audienceStrength: 'high' },
            { topic: 'Data Security', score: 72, audienceStrength: 'medium' },
            { topic: 'AI/ML Platform', score: 68, audienceStrength: 'medium' },
          ],
          scoops: [
            { type: 'executive_hire', title: 'New CTO Appointed', date: '2025-01' },
            { type: 'expansion', title: 'Office Expansion Planned', date: '2025-01' },
          ],
          technologies: ['Azure', 'GitHub', 'VS Code', 'Teams', 'Power BI'],
        },
      },
    },
    {
      id: 'step-3',
      name: 'Apollo.io Data Collection',
      description: 'Gathering supplementary company intelligence data from Apollo.io API',
      status: 'completed',
      startTime: new Date(Date.now() - 298900).toISOString(),
      endTime: new Date(Date.now() - 296400).toISOString(),
      duration: 2500,
      metadata: { source: 'Apollo.io', priority: 'SECONDARY', fields_retrieved: 15 },
    },
    {
      id: 'step-4',
      name: 'PeopleDataLabs Data Collection',
      description: 'Gathering supplementary company intelligence data from PeopleDataLabs API',
      status: 'completed',
      startTime: new Date(Date.now() - 298800).toISOString(),
      endTime: new Date(Date.now() - 297000).toISOString(),
      duration: 1800,
      metadata: { source: 'PeopleDataLabs', priority: 'SECONDARY', fields_retrieved: 12 },
    },
    {
      id: 'step-5',
      name: 'Data Aggregation & ZoomInfo Priority Merge',
      description: 'Merging data from multiple sources with ZoomInfo as primary source. ZoomInfo data takes precedence where conflicts exist.',
      status: 'completed',
      startTime: new Date(Date.now() - 296000).toISOString(),
      endTime: new Date(Date.now() - 295500).toISOString(),
      duration: 500,
      metadata: {
        sources_merged: 3,
        primary_source: 'ZoomInfo',
        merge_strategy: 'ZoomInfo-first',
        zoominfo_fields_used: 18,
      },
    },
    {
      id: 'step-6',
      name: '>>> PRE-LLM DATA VALIDATION <<<',
      description: 'CRITICAL: Fact-checking data against verified company database BEFORE sending to LLM. Catches wrong CEO names, fake executives, and placeholder data.',
      status: 'completed',
      startTime: new Date(Date.now() - 295000).toISOString(),
      endTime: new Date(Date.now() - 293000).toISOString(),
      duration: 2000,
      metadata: {
        validation_type: 'PRE-LLM FACT CHECK',
        companies_in_database: 14,
        known_executives_checked: true,
        issues_found: 2,
        issues_corrected: 2,
        rejected_stakeholders: ['Julie Strau (fake CEO)', 'Tom Smith (unverified)'],
        corrected_ceo: 'Satya Nadella',
        confidence_before: 1.0,
        confidence_after: 0.7,
      },
    },
    {
      id: 'step-7',
      name: 'LLM Validation',
      description: 'Validating and resolving remaining data conflicts with GPT-4',
      status: 'completed',
      startTime: new Date(Date.now() - 293000).toISOString(),
      endTime: new Date(Date.now() - 276000).toISOString(),
      duration: 17000,
      metadata: { model: 'gpt-4o-mini', tokensUsed: 1250 },
    },
    {
      id: 'step-8',
      name: 'LLM Council Resolution',
      description: 'Multi-agent consensus for remaining discrepancies',
      status: 'completed',
      startTime: new Date(Date.now() - 276000).toISOString(),
      endTime: new Date(Date.now() - 271000).toISOString(),
      duration: 5000,
      metadata: { discrepancies_found: 2, resolved: 2 },
    },
    {
      id: 'step-9',
      name: 'Store Results',
      description: 'Saving validated data to Supabase',
      status: 'completed',
      startTime: new Date(Date.now() - 271000).toISOString(),
      endTime: new Date(Date.now() - 269000).toISOString(),
      duration: 2000,
      metadata: { tablesUpdated: 2 },
    },
    {
      id: 'step-10',
      name: 'Generate Slideshow',
      description: 'Creating presentation with Gamma API',
      status: 'completed',
      startTime: new Date(Date.now() - 269000).toISOString(),
      endTime: new Date(Date.now() - 240000).toISOString(),
      duration: 29000,
      metadata: { slidesGenerated: 8 },
    },
  ],
  apiResponses: [
    {
      id: 'api-0',
      apiName: 'ZoomInfo Company Enrichment (PRIMARY SOURCE)',
      url: 'https://api.zoominfo.com/gtm/data/v1/companies/enrich',
      method: 'POST',
      statusCode: 200,
      statusText: 'OK',
      headers: {
        'content-type': 'application/vnd.api+json',
        'x-request-id': 'zi-req-001',
        'x-ratelimit-remaining': '23',
      },
      requestBody: {
        data: { type: 'CompanyEnrich', attributes: { companyDomain: 'microsoft.com' } },
      },
      responseBody: {
        data: [{
          companyName: 'Microsoft Corporation',
          domain: 'microsoft.com',
          employeeCount: 221000,
          revenue: 211900000000,
          industry: 'Technology',
          city: 'Redmond',
          state: 'Washington',
          country: 'United States',
          yearFounded: 1975,
          ceoName: 'Satya Nadella',
          phone: '+1-425-882-8080',
          description: 'Global technology corporation',
        }],
      },
      timestamp: new Date(Date.now() - 299000).toISOString(),
      duration: 1400,
      isSensitive: true,
      maskedFields: ['authorization'],
    },
    {
      id: 'api-0b',
      apiName: 'ZoomInfo Intent Enrichment',
      url: 'https://api.zoominfo.com/gtm/data/v1/intent/enrich',
      method: 'POST',
      statusCode: 200,
      statusText: 'OK',
      headers: {
        'content-type': 'application/vnd.api+json',
        'x-request-id': 'zi-req-002',
        'x-ratelimit-remaining': '22',
      },
      requestBody: {
        data: { type: 'IntentEnrich', attributes: { companyDomain: 'microsoft.com' } },
      },
      responseBody: {
        data: [
          { topic: 'Cloud Migration', score: 85, audienceStrength: 'high', lastSeen: '2025-01-15' },
          { topic: 'Data Security', score: 72, audienceStrength: 'medium', lastSeen: '2025-01-12' },
          { topic: 'AI/ML Platform', score: 68, audienceStrength: 'medium', lastSeen: '2025-01-10' },
        ],
      },
      timestamp: new Date(Date.now() - 298500).toISOString(),
      duration: 900,
      isSensitive: true,
      maskedFields: ['authorization'],
    },
    {
      id: 'api-0c',
      apiName: 'ZoomInfo Scoops Search',
      url: 'https://api.zoominfo.com/gtm/data/v1/scoops/search',
      method: 'POST',
      statusCode: 200,
      statusText: 'OK',
      headers: {
        'content-type': 'application/vnd.api+json',
        'x-request-id': 'zi-req-003',
      },
      requestBody: {
        data: { type: 'ScoopSearch', attributes: { companyDomain: 'microsoft.com' } },
      },
      responseBody: {
        data: [
          {
            scoopType: 'executive_hire',
            title: 'New CTO Appointed at Microsoft Corporation',
            date: '2025-01-08',
            description: 'Company appoints new Chief Technology Officer',
          },
          {
            scoopType: 'expansion',
            title: 'Office Expansion Planned',
            date: '2025-01-05',
            description: 'Company announces plans for new office location',
          },
        ],
      },
      timestamp: new Date(Date.now() - 298200).toISOString(),
      duration: 600,
      isSensitive: true,
      maskedFields: ['authorization'],
    },
    {
      id: 'api-0d',
      apiName: 'ZoomInfo Contact Search',
      url: 'https://api.zoominfo.com/gtm/data/v1/contacts/search',
      method: 'POST',
      statusCode: 200,
      statusText: 'OK',
      headers: {
        'content-type': 'application/vnd.api+json',
        'x-request-id': 'zi-req-004',
      },
      requestBody: {
        data: {
          type: 'ContactSearch',
          attributes: {
            companyDomain: 'microsoft.com',
            jobTitle: ['CEO', 'CTO', 'CFO'],
          },
        },
      },
      responseBody: {
        data: [
          {
            firstName: 'Satya',
            lastName: 'Nadella',
            jobTitle: 'CEO',
            email: 'satya.nadella@microsoft.com',
            phone: '+1-425-882-8080',
            linkedInUrl: 'https://linkedin.com/in/satyanadella',
          },
          {
            firstName: 'Amy',
            lastName: 'Hood',
            jobTitle: 'CFO',
            email: 'amy.hood@microsoft.com',
            linkedInUrl: 'https://linkedin.com/in/amyhood',
          },
        ],
      },
      timestamp: new Date(Date.now() - 298000).toISOString(),
      duration: 800,
      isSensitive: true,
      maskedFields: ['authorization', 'email', 'phone'],
    },
    {
      id: 'api-1',
      apiName: 'Apollo.io Company Enrichment',
      url: 'https://api.apollo.io/v1/organizations/enrich',
      method: 'POST',
      statusCode: 200,
      statusText: 'OK',
      headers: {
        'content-type': 'application/json',
        'x-rate-limit-remaining': '95',
      },
      requestBody: {
        domain: 'microsoft.com',
        name: 'Microsoft Corporation',
      },
      responseBody: {
        company: {
          name: 'Microsoft Corporation',
          domain: 'microsoft.com',
          employee_count: 221000,
          industry: 'Technology',
          founded_year: 1975,
          headquarters: 'Redmond, WA',
        },
      },
      timestamp: new Date(Date.now() - 298900).toISOString(),
      duration: 2500,
      isSensitive: true,
      maskedFields: ['api_key'],
    },
    {
      id: 'api-2',
      apiName: 'PeopleDataLabs Company API',
      url: 'https://api.peopledatalabs.com/v5/company/enrich',
      method: 'GET',
      statusCode: 200,
      statusText: 'OK',
      headers: {
        'content-type': 'application/json',
        'x-bl-request-id': 'pdl-req-456',
      },
      responseBody: {
        company: {
          name: 'Microsoft Corporation',
          domain: 'microsoft.com',
          size: '200,000+',
          industry: 'Software Development',
          founded: 1975,
          location: 'Redmond, Washington, USA',
        },
      },
      timestamp: new Date(Date.now() - 298800).toISOString(),
      duration: 1800,
      isSensitive: true,
      maskedFields: ['api_key'],
    },
    {
      id: 'api-3',
      apiName: 'OpenAI Chat Completion',
      url: 'https://api.openai.com/v1/chat/completions',
      method: 'POST',
      statusCode: 200,
      statusText: 'OK',
      headers: {
        'content-type': 'application/json',
        'x-request-id': 'oai-789',
      },
      requestBody: {
        model: 'gpt-4o-mini',
        messages: [{ role: 'user', content: 'Validate company data...' }],
      },
      responseBody: {
        choices: [
          {
            message: {
              content: '{"company_name": "Microsoft Corporation", "confidence": 0.95}',
            },
          },
        ],
        usage: { prompt_tokens: 450, completion_tokens: 800 },
      },
      timestamp: new Date(Date.now() - 293000).toISOString(),
      duration: 5000,
      isSensitive: true,
      maskedFields: ['api_key', 'authorization'],
    },
    {
      id: 'api-4',
      apiName: 'Supabase Insert',
      url: 'https://project.supabase.co/rest/v1/finalize_data',
      method: 'POST',
      statusCode: 201,
      statusText: 'Created',
      headers: {
        'content-type': 'application/json',
      },
      responseBody: {
        id: 'record-123',
        created_at: new Date().toISOString(),
      },
      timestamp: new Date(Date.now() - 271000).toISOString(),
      duration: 120,
      isSensitive: false,
    },
  ],
  llmThoughtProcesses: [
    {
      id: 'llm-0',
      taskName: '>>> PRE-LLM DATA VALIDATION (Fact-Checking) <<<',
      model: 'rule-based-validator',
      promptTokens: 0,
      completionTokens: 0,
      totalTokens: 0,
      startTime: new Date(Date.now() - 279000).toISOString(),
      endTime: new Date(Date.now() - 277000).toISOString(),
      duration: 2000,
      steps: [
        {
          id: 'pre-thought-1',
          step: 1,
          action: 'CHECK KNOWN COMPANY DATABASE',
          reasoning:
            'Checking microsoft.com against verified facts database containing 14 major tech companies with known CEOs, executives, and company data.',
          input: { domain: 'microsoft.com', in_database: true, known_ceo: 'Satya Nadella' },
          output: { database_match: true, verification_enabled: true },
          confidence: 1.0,
          timestamp: new Date(Date.now() - 279000).toISOString(),
        },
        {
          id: 'pre-thought-2',
          step: 2,
          action: 'REJECT FAKE CEO: Julie Strau',
          reasoning:
            'API returned "Julie Strau" as CEO. This is INCORRECT. Verified Microsoft CEO is Satya Nadella. Correcting value and flagging source as unreliable.',
          input: { provided_ceo: 'Julie Strau', verified_ceo: 'Satya Nadella' },
          output: { corrected: true, value: 'Satya Nadella', confidence_penalty: -0.3 },
          confidence: 1.0,
          timestamp: new Date(Date.now() - 278500).toISOString(),
        },
        {
          id: 'pre-thought-3',
          step: 3,
          action: 'REJECT FAKE STAKEHOLDER: Tom Smith',
          reasoning:
            'Stakeholder "Tom Smith" is NOT in verified Microsoft executives list. Known executives include: Satya Nadella, Amy Hood, Brad Smith, Scott Guthrie. Filtering out unverified person.',
          input: {
            provided_name: 'Tom Smith',
            known_executives: ['Satya Nadella', 'Amy Hood', 'Brad Smith', 'Scott Guthrie', 'Kathleen Hogan']
          },
          output: { rejected: true, reason: 'Not in verified executives list' },
          confidence: 1.0,
          timestamp: new Date(Date.now() - 278000).toISOString(),
        },
        {
          id: 'pre-thought-4',
          step: 4,
          action: 'VALIDATION COMPLETE',
          reasoning:
            'Pre-LLM validation caught 2 critical issues BEFORE sending to LLM council. This prevents hallucinated or wrong data from polluting the AI analysis.',
          input: { total_issues: 2, corrected: 2 },
          output: { safe_for_llm: true, confidence_score: 0.7 },
          confidence: 1.0,
          timestamp: new Date(Date.now() - 277000).toISOString(),
        },
      ],
      finalDecision:
        'PRE-LLM VALIDATION COMPLETE: Caught and corrected fake CEO "Julie Strau" -> "Satya Nadella". Rejected unverified stakeholder "Tom Smith". Data is now safe to send to LLM Council.',
      confidenceScore: 1.0,
      discrepanciesResolved: ['ceo_correction', 'stakeholder_filtering', 'fake_data_rejection'],
    },
    {
      id: 'llm-1',
      taskName: 'LLM Council Data Validation',
      model: 'gpt-4o-mini',
      promptTokens: 450,
      completionTokens: 800,
      totalTokens: 1250,
      startTime: new Date(Date.now() - 277000).toISOString(),
      endTime: new Date(Date.now() - 260000).toISOString(),
      duration: 17000,
      steps: [
        {
          id: 'thought-1',
          step: 1,
          action: 'Analyze Employee Count',
          reasoning:
            'Comparing employee count from Apollo (221,000) and PeopleDataLabs (200,000+). Both sources agree Microsoft is a large enterprise.',
          input: { apollo: 221000, pdl: '200,000+' },
          output: { resolved: '221,000', confidence: 0.95 },
          timestamp: new Date(Date.now() - 275000).toISOString(),
        },
        {
          id: 'thought-2',
          step: 2,
          action: 'Verify Headquarters',
          reasoning:
            'Both sources confirm Redmond, Washington headquarters. This matches our verified database.',
          input: { apollo: 'Redmond, WA', pdl: 'Redmond, Washington' },
          output: { resolved: 'Redmond, Washington', confidence: 0.99 },
          timestamp: new Date(Date.now() - 270000).toISOString(),
        },
      ],
      finalDecision:
        'Data validated successfully with pre-validated CEO and filtered stakeholder list. Overall confidence: 0.94.',
      confidenceScore: 0.94,
      discrepanciesResolved: ['employee_count_format'],
    },
    {
      id: 'llm-2',
      taskName: 'ZoomInfo Intent Signal Integration',
      model: 'gpt-4',
      promptTokens: 380,
      completionTokens: 620,
      totalTokens: 1000,
      startTime: new Date(Date.now() - 275000).toISOString(),
      endTime: new Date(Date.now() - 274000).toISOString(),
      duration: 1000,
      steps: [
        {
          id: 'thought-zi-1',
          step: 1,
          action: 'Analyze ZoomInfo Intent Signals',
          reasoning:
            'ZoomInfo buyer intent data shows 3 active signals: Cloud Migration (score: 85, high), Data Security (score: 72, medium), AI/ML Platform (score: 68, medium). These signals indicate active buying behavior.',
          input: {
            intent_signals: [
              { topic: 'Cloud Migration', score: 85 },
              { topic: 'Data Security', score: 72 },
              { topic: 'AI/ML Platform', score: 68 },
            ],
          },
          output: {
            primary_intent: 'Cloud Migration',
            signal_strength: 'high',
            buying_stage: 'active_evaluation',
          },
          confidence: 0.90,
          timestamp: new Date(Date.now() - 275000).toISOString(),
        },
        {
          id: 'thought-zi-2',
          step: 2,
          action: 'Cross-Reference with Scoops',
          reasoning:
            'ZoomInfo scoops show recent CTO hire and expansion announcement, corroborating the cloud migration intent signal. This increases confidence in active evaluation.',
          input: {
            scoops: ['New CTO appointed', 'Office expansion planned'],
            primary_intent: 'Cloud Migration',
          },
          output: {
            corroborated: true,
            enriched_pain_points: ['Legacy infrastructure migration', 'Security compliance gaps'],
            confidence_boost: 0.05,
          },
          confidence: 0.92,
          timestamp: new Date(Date.now() - 274500).toISOString(),
        },
      ],
      finalDecision:
        'ZoomInfo intent signals confirm active Cloud Migration evaluation (score 85). Cross-referenced with CTO hire scoop, suggesting infrastructure modernization initiative. Added 2 enriched pain points to opportunity themes.',
      confidenceScore: 0.92,
      discrepanciesResolved: ['intent_topic_validation', 'pain_point_enrichment'],
    },
    {
      id: 'llm-3',
      taskName: 'Slideshow Content Generation',
      model: 'gpt-4o-mini',
      promptTokens: 320,
      completionTokens: 650,
      totalTokens: 970,
      startTime: new Date(Date.now() - 270000).toISOString(),
      endTime: new Date(Date.now() - 265000).toISOString(),
      duration: 5000,
      steps: [
        {
          id: 'thought-4',
          step: 1,
          action: 'Generate Executive Summary',
          reasoning:
            'Creating concise overview for Microsoft using validated data with correct CEO Satya Nadella.',
          output: { slide: 1, title: 'Executive Summary' },
          timestamp: new Date(Date.now() - 268000).toISOString(),
        },
      ],
      finalDecision:
        'Generated 8-slide presentation with verified executive data.',
      confidenceScore: 0.91,
    },
  ],
  processFlow: {
    nodes: [
      { id: 'start', label: 'Request Received', type: 'start', status: 'completed' },
      { id: 'zoominfo', label: 'ZoomInfo API (PRIMARY)', type: 'api', status: 'completed', details: '[PRIORITY] Fetched comprehensive data: company enrichment, buyer intent signals, business scoops, contacts, and tech stack', duration: 1400 },
      { id: 'apollo', label: 'Apollo.io API', type: 'api', status: 'completed', details: 'Fetched supplementary company data from Apollo.io', duration: 2500 },
      { id: 'pdl', label: 'PeopleDataLabs API', type: 'api', status: 'completed', details: 'Fetched supplementary company data from PeopleDataLabs', duration: 1800 },
      { id: 'merge', label: 'ZoomInfo Priority Merge', type: 'process', status: 'completed', details: 'Merged data with ZoomInfo as primary source (takes precedence in conflicts)', duration: 500 },
      { id: 'pre-validate', label: 'PRE-LLM VALIDATION', type: 'decision', status: 'completed', details: 'Fact-check against known company database' },
      { id: 'llm', label: 'LLM Council', type: 'llm', status: 'completed', details: 'Resolving conflicts with LLM council', duration: 5000 },
      { id: 'store', label: 'Store to Supabase', type: 'process', status: 'completed' },
      { id: 'gamma', label: 'Generate Slideshow', type: 'api', status: 'completed', duration: 29000 },
      { id: 'end', label: 'Complete', type: 'end', status: 'completed' },
    ],
    edges: [
      { id: 'e1', source: 'start', target: 'zoominfo', label: 'Primary Source' },
      { id: 'e2', source: 'start', target: 'apollo' },
      { id: 'e3', source: 'start', target: 'pdl' },
      { id: 'e4', source: 'zoominfo', target: 'merge' },
      { id: 'e5', source: 'apollo', target: 'merge' },
      { id: 'e6', source: 'pdl', target: 'merge' },
      { id: 'e7', source: 'merge', target: 'pre-validate', label: 'Merged Data' },
      { id: 'e8', source: 'pre-validate', target: 'llm', label: 'Validated + Filtered' },
      { id: 'e9', source: 'llm', target: 'store', label: 'Council Approved' },
      { id: 'e10', source: 'store', target: 'gamma', label: 'Generate' },
      { id: 'e11', source: 'gamma', target: 'end', label: 'Slideshow URL' },
    ],
  },
  createdAt: new Date(Date.now() - 300000).toISOString(),
  completedAt: new Date(Date.now() - 240000).toISOString(),
});

/**
 * Tab button component.
 */
const TabButton = ({
  tab,
  activeTab,
  onClick,
  children,
}: {
  tab: TabType;
  activeTab: TabType;
  onClick: (tab: TabType) => void;
  children: React.ReactNode;
}) => (
  <button
    onClick={() => onClick(tab)}
    className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
      activeTab === tab
        ? 'bg-white text-primary-700 border-t border-l border-r border-gray-200'
        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
    }`}
    role="tab"
    aria-selected={activeTab === tab}
    aria-controls={`${tab}-panel`}
  >
    {children}
  </button>
);

/**
 * Debug Mode content component.
 */
function DebugModeContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const jobId = searchParams.get('jobId');

  const [debugData, setDebugData] = useState<DebugData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('process');
  const [isDemo, setIsDemo] = useState(false);

  useEffect(() => {
    // If no jobId, show demo option immediately
    if (!jobId) {
      setError('No job ID provided. Please access Debug Mode from a completed job, or view the demo below.');
      setLoading(false);
      return;
    }

    const fetchDebugData = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await debugApiClient.getDebugData(jobId);
        setDebugData(data);
        setIsDemo(false);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : 'Failed to load debug data. Please try again.'
        );
      } finally {
        setLoading(false);
      }
    };

    fetchDebugData();
  }, [jobId]);

  const handleBack = () => {
    router.back();
  };

  const handleLoadDemo = () => {
    setDebugData(generateDemoData());
    setError(null);
    setIsDemo(true);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <LoadingSpinner message="Loading debug data..." progress={50} />
      </div>
    );
  }

  if (error && !debugData) {
    return (
      <div className="text-center py-12">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-red-100 rounded-full mb-4">
          <svg
            className="w-8 h-8 text-red-600"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Unable to Load Debug Data
        </h2>
        <p className="text-gray-600 mb-6">{error}</p>
        <div className="flex justify-center gap-4">
          <button
            onClick={handleBack}
            className="px-6 py-3 bg-gray-200 text-gray-800 font-medium rounded-lg hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
          >
            Go Back
          </button>
          <button
            onClick={handleLoadDemo}
            className="px-6 py-3 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
          >
            View Demo Data
          </button>
        </div>
      </div>
    );
  }

  if (!debugData) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Demo Banner */}
      {isDemo && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 flex items-center justify-between">
          <div className="flex items-center">
            <svg
              className="w-5 h-5 text-yellow-600 mr-2"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span className="text-yellow-800 font-medium">
              Viewing Demo Data - This is sample data to demonstrate the Debug Mode UI
            </span>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <button
            onClick={handleBack}
            className="flex items-center text-gray-600 hover:text-gray-900 mb-2"
          >
            <svg
              className="w-5 h-5 mr-1"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 19l-7-7 7-7"
              />
            </svg>
            Back to Results
          </button>
          <h1 className="text-3xl font-bold text-gray-900">
            Debug Mode: {debugData.companyName}
          </h1>
          <p className="text-gray-600 mt-1">
            Job ID: {debugData.jobId} | Domain: {debugData.domain}
          </p>
        </div>

        {/* Status Badge */}
        <span
          className={`px-4 py-2 rounded-full text-sm font-medium ${
            debugData.status === 'completed'
              ? 'bg-green-100 text-green-800'
              : debugData.status === 'failed'
                ? 'bg-red-100 text-red-800'
                : 'bg-blue-100 text-blue-800'
          }`}
        >
          {debugData.status.charAt(0).toUpperCase() + debugData.status.slice(1)}
        </span>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-1" role="tablist">
          <TabButton tab="process" activeTab={activeTab} onClick={setActiveTab}>
            Process Steps ({debugData.processSteps.length})
          </TabButton>
          <TabButton tab="api" activeTab={activeTab} onClick={setActiveTab}>
            API Responses ({debugData.apiResponses.length})
          </TabButton>
          <TabButton tab="llm" activeTab={activeTab} onClick={setActiveTab}>
            LLM Insights ({debugData.llmThoughtProcesses.length})
          </TabButton>
          <TabButton tab="flow" activeTab={activeTab} onClick={setActiveTab}>
            Process Flow
          </TabButton>
        </nav>
      </div>

      {/* Tab Panels */}
      <div className="mt-4">
        {activeTab === 'process' && (
          <div id="process-panel" role="tabpanel">
            <DebugPanel steps={debugData.processSteps} />
          </div>
        )}

        {activeTab === 'api' && (
          <div id="api-panel" role="tabpanel">
            <APIResponseDisplay responses={debugData.apiResponses} />
          </div>
        )}

        {activeTab === 'llm' && (
          <div id="llm-panel" role="tabpanel">
            <LLMThoughtDisplay
              thoughtProcesses={debugData.llmThoughtProcesses}
            />
          </div>
        )}

        {activeTab === 'flow' && (
          <div id="flow-panel" role="tabpanel">
            <ProcessFlowVisualization flow={debugData.processFlow} />
          </div>
        )}
      </div>

      {/* Timestamps */}
      <div className="text-sm text-gray-500 text-center pt-4 border-t border-gray-200">
        Created: {new Date(debugData.createdAt).toLocaleString()}
        {debugData.completedAt && (
          <> | Completed: {new Date(debugData.completedAt).toLocaleString()}</>
        )}
      </div>
    </div>
  );
}

/**
 * Debug Mode Page with Suspense boundary.
 */
export default function DebugModePage() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      <div className="container mx-auto px-4 py-8 max-w-6xl">
        <Suspense
          fallback={
            <div className="flex items-center justify-center min-h-[60vh]">
              <LoadingSpinner message="Loading..." progress={0} />
            </div>
          }
        >
          <DebugModeContent />
        </Suspense>
      </div>
    </main>
  );
}
