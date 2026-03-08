/**
 * TypeScript types for Diogenes Backend API
 */

export interface Source {
  index?: number;
  title: string;
  url: string;
  domain: string;
  quality_score?: number;
  favicon_url?: string;
}

export interface ResearchAnswer {
  content: string;
  word_count: number;
  has_citations: boolean;
}

export interface ResearchTiming {
  total_ms: number;
}

export interface ResearchMetadata {
  profile: string;
  mode: string;
  reliability_score: number;
  confidence: number;
  iterations: number;
  verified_claims_count: number;
  contradictions_count: number;
}

export interface ResearchResponse {
  session_id: string;
  query: string;
  status: string;
  answer: ResearchAnswer | null;
  sources: Source[];
  timing: ResearchTiming;
  errors: string[];
  created_at: string;
  metadata: ResearchMetadata;
}

export interface ResearchRequest {
  query: string;
  mode: 'quick' | 'balanced' | 'deep';
  profile?: string;
}

// SSE Event Types
export enum SSEEventType {
  STATUS = 'status',
  SOURCES = 'sources',
  SYNTHESIS = 'synthesis',
  COMPLETE = 'complete',
  ERROR = 'error',
  PROFILE = 'profile'
}

export interface SSEStatusEvent {
  session_id: string;
  phase: string;
  progress?: number;
  sources_found?: number;
  message: string;
}

export interface SSESourceEvent {
  url: string;
  title: string;
}

export interface SSESynthesisEvent {
  content: string;
}

export interface SSECompleteEvent {
  session_id: string;
  answer: string;
  sources_count: number;
  reliability_score: number;
  confidence: number;
  duration_seconds: number;
  metadata: {
    profile: string;
    mode: string;
    iterations: number;
  };
}

export interface SSEErrorEvent {
  session_id: string;
  error: string;
}

export interface SSEProfileEvent {
  profile: string;
  name: string;
  description: string;
}

// =============================================================================
// SETTINGS TYPES
// =============================================================================

export interface LLMModelInfo {
  name: string;
  size?: string;
  modified_at?: string;
  parameter_size?: string;
  quantization?: string;
  family?: string;
}

export interface LLMModelsConfig {
  planner: string;
  extractor: string;
  synthesizer: string;
  reflector: string;
}

export interface LLMSettings {
  provider: string;
  base_url: string;
  temperature: number;
  max_tokens: number;
  timeout: number;
  models: LLMModelsConfig;
}

export interface SearchSettings {
  provider: string;
  base_url: string;
  timeout: number;
  max_results: number;
  categories: string[];
  language: string;
}

export interface CrawlSettings {
  max_concurrent: number;
  timeout: number;
  max_content_length: number;
}

export interface AgentSettings {
  max_iterations: number;
  min_sources: number;
  max_sources: number;
  coverage_threshold: number;
}

export interface UserPreferences {
  username: string;
  user_title: string;
  language: string;
  default_research_mode: string;
  default_profile: string;
  enable_suggestions: boolean;
  enable_verification: boolean;
  theme: string;
}

export interface SystemSettings {
  llm: LLMSettings;
  search: SearchSettings;
  crawl: CrawlSettings;
  agent: AgentSettings;
  user: UserPreferences;
  version: string;
  environment: string;
}

export interface ServiceStatus {
  name: string;
  status: 'online' | 'offline' | 'degraded';
  latency_ms?: number;
  error?: string;
  details?: Record<string, any>;
}

export interface AllServicesStatus {
  ollama: ServiceStatus;
  searxng: ServiceStatus;
  overall: 'healthy' | 'degraded' | 'unhealthy';
}
