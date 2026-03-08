/**
 * API Service for Diogenes Backend
 */

import type {
  ResearchRequest,
  ResearchResponse,
  SSEStatusEvent,
  SSESourceEvent,
  SSESynthesisEvent,
  SSECompleteEvent,
  SSEErrorEvent,
  SSEProfileEvent,
  SSEEventType,
  Source,
  SystemSettings,
  LLMModelInfo,
  LLMSettings,
  SearchSettings,
  AgentSettings,
  UserPreferences,
  AllServicesStatus,
  ServiceStatus
} from './api-types';

// Type for Vite env
interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export class DiogenesAPIService {
  private baseUrl: string;

  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl || API_BASE_URL;
  }

  /**
   * Start research query (blocking)
   */
  async research(request: ResearchRequest): Promise<ResearchResponse> {
    const response = await fetch(`${this.baseUrl}/v1/research/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: request.query,
        mode: request.mode,
      }),
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return await response.json();
  }

  /**
   * Start research with streaming (SSE)
   */
  async* researchStream(
    request: ResearchRequest,
    onProgress?: (event: SSEStatusEvent) => void,
    onSource?: (source: SSESourceEvent) => void,
    onProfile?: (profile: SSEProfileEvent) => void
  ): AsyncGenerator<{
    type: 'status' | 'source' | 'synthesis' | 'complete' | 'error' | 'profile';
    data: any;
  }> {
    const url = `${this.baseUrl}/v1/research/stream`;

    // Create AbortController with 5 minute timeout for long research sessions
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 300000); // 5 minutes

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
        },
        body: JSON.stringify({
          query: request.query,
          mode: request.mode,
          profile: request.profile,
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }

      const decoder = new TextDecoder();
      let buffer = '';
      let currentEventType = '';

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (!line.trim() || line.startsWith(':')) continue;

            // Capture event type from event: line
            if (line.startsWith('event:')) {
              currentEventType = line.substring(6).trim();
              continue;
            }

            if (line.startsWith('data:')) {
              try {
                const data = JSON.parse(line.substring(5).trim());
                
                // Use the event type from the event: line if available, otherwise infer from data
                let eventType: 'status' | 'source' | 'synthesis' | 'complete' | 'error' | 'profile';
                
                if (currentEventType === 'status' || data.phase !== undefined) {
                  eventType = 'status';
                  if (onProgress) onProgress(data as SSEStatusEvent);
                } else if (currentEventType === 'sources' || (data.url !== undefined && data.title !== undefined && !data.answer)) {
                  eventType = 'source';
                  if (onSource) onSource(data as SSESourceEvent);
                } else if (currentEventType === 'synthesis' || currentEventType === 'answer_chunk' || (data.content !== undefined && data.answer === undefined)) {
                  eventType = 'synthesis';
                } else if (currentEventType === 'complete' || data.answer !== undefined) {
                  eventType = 'complete';
                } else if (currentEventType === 'error' || data.error !== undefined) {
                  eventType = 'error';
                } else if (data.profile !== undefined && data.name !== undefined) {
                  eventType = 'profile';
                  if (onProfile) onProfile(data as SSEProfileEvent);
                } else {
                  // Log unknown events for debugging
                  console.debug('Unknown SSE event:', currentEventType, data);
                  currentEventType = '';
                  continue;
                }

                yield { type: eventType, data };
                currentEventType = ''; // Reset for next event
              } catch (e) {
                console.warn('Malformed SSE event, skipping:', line);
                currentEventType = '';
                continue;
              }
            }
          }
        }
      } catch (streamError) {
        console.error('SSE stream error:', streamError);
        throw new Error(`Stream connection lost: ${streamError}`);
      } finally {
        reader.releaseLock();
      }
    } finally {
      clearTimeout(timeoutId);
    }
  }

  /**
   * Health check
   */
  async health(): Promise<{ status: string; version: string }> {
    // Health endpoint — derive base from API URL
    const base = this.baseUrl.replace(/\/api\/?$/, '');
    const response = await fetch(`${base}/health/`);
    if (!response.ok) {
      throw new Error(`Health check failed: ${response.statusText}`);
    }
    return await response.json();
  }

  // =============================================================================
  // SETTINGS API
  // =============================================================================

  /**
   * Get all system settings
   */
  async getSettings(): Promise<SystemSettings> {
    const response = await fetch(`${this.baseUrl}/v1/settings/`);
    if (!response.ok) {
      throw new Error(`Failed to get settings: ${response.statusText}`);
    }
    return await response.json();
  }

  /**
   * Get available LLM models from Ollama
   */
  async getAvailableModels(): Promise<LLMModelInfo[]> {
    const response = await fetch(`${this.baseUrl}/v1/settings/llm/models`);
    if (!response.ok) {
      throw new Error(`Failed to get models: ${response.statusText}`);
    }
    return await response.json();
  }

  /**
   * Update LLM settings
   */
  async updateLLMSettings(settings: Partial<LLMSettings>): Promise<void> {
    const response = await fetch(`${this.baseUrl}/v1/settings/llm`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
    });
    if (!response.ok) {
      throw new Error(`Failed to update LLM settings: ${response.statusText}`);
    }
  }

  /**
   * Update search settings
   */
  async updateSearchSettings(settings: Partial<SearchSettings>): Promise<void> {
    const response = await fetch(`${this.baseUrl}/v1/settings/search`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
    });
    if (!response.ok) {
      throw new Error(`Failed to update search settings: ${response.statusText}`);
    }
  }

  /**
   * Update agent settings
   */
  async updateAgentSettings(settings: Partial<AgentSettings>): Promise<void> {
    const response = await fetch(`${this.baseUrl}/v1/settings/agent`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
    });
    if (!response.ok) {
      throw new Error(`Failed to update agent settings: ${response.statusText}`);
    }
  }

  /**
   * Update user preferences
   */
  async updateUserPreferences(preferences: Partial<UserPreferences>): Promise<void> {
    const response = await fetch(`${this.baseUrl}/v1/settings/user`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(preferences),
    });
    if (!response.ok) {
      throw new Error(`Failed to update user preferences: ${response.statusText}`);
    }
  }

  /**
   * Get status of all services (Ollama, SearXNG)
   */
  async getServicesStatus(): Promise<AllServicesStatus> {
    const response = await fetch(`${this.baseUrl}/v1/settings/status`);
    if (!response.ok) {
      throw new Error(`Failed to get services status: ${response.statusText}`);
    }
    return await response.json();
  }

  /**
   * Test connection to a service
   */
  async testServiceConnection(service: 'ollama' | 'searxng', url?: string): Promise<ServiceStatus> {
    const params = new URLSearchParams({ service });
    if (url) params.append('url', url);
    
    const response = await fetch(`${this.baseUrl}/v1/settings/test-connection?${params}`, {
      method: 'POST',
    });
    if (!response.ok) {
      throw new Error(`Failed to test connection: ${response.statusText}`);
    }
    return await response.json();
  }

  /**
   * Reset settings to defaults
   */
  async resetSettings(section?: 'llm' | 'search' | 'agent' | 'user'): Promise<void> {
    const params = section ? `?section=${section}` : '';
    const response = await fetch(`${this.baseUrl}/v1/settings/reset${params}`, {
      method: 'POST',
    });
    if (!response.ok) {
      throw new Error(`Failed to reset settings: ${response.statusText}`);
    }
  }
}

// Default instance
export const apiService = new DiogenesAPIService();
