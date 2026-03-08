import type { Source } from './api-types';

export interface Message {
  role: 'user' | 'model';
  content: string;
  sources?: Source[];
  thinkContent?: string;
}

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  createdAt: number;
  mode?: string;
  profile?: string;
}

export interface UserSettings {
  username: string;
  userTitle: string;
  language: string;
  defaultResearchMode: string;
  defaultProfile: string;
}

export interface IntelligenceSettings {
  llmProvider: string;
  llmBaseUrl: string;
  llmApiKey: string;
  selectedModel: string;
  temperature: number;
  maxTokens: number;
  searchBaseUrl: string;
  maxSearchResults: number;
  maxSources: number;
  maxIterations: number;
}

export const DEFAULT_SETTINGS: UserSettings = {
  username: "Guest Researcher",
  userTitle: "Pro Plan",
  language: "English",
  defaultResearchMode: "balanced",
  defaultProfile: "general"
};

export const DEFAULT_INTELLIGENCE_SETTINGS: IntelligenceSettings = {
  llmProvider: "ollama",
  llmBaseUrl: "http://localhost:11434",
  llmApiKey: "",
  selectedModel: "llama3.1:8b",
  temperature: 0.0,
  maxTokens: 4096,
  searchBaseUrl: "http://localhost:8080",
  maxSearchResults: 10,
  maxSources: 8,
  maxIterations: 3
};

export const RESEARCH_MODES = [
  { id: 'quick', label: 'Quick', description: 'Concise (30s)' },
  { id: 'balanced', label: 'Balanced', description: 'Standard (1m)' },
  { id: 'deep', label: 'Deep', description: 'Comprehensive (3m)' },
] as const;

export const RESEARCH_PROFILES = [
  { id: 'general', label: 'General' },
  { id: 'academic', label: 'Academic' },
  { id: 'technical', label: 'Technical' },
  { id: 'news', label: 'News' },
  { id: 'medical', label: 'Medical' },
  { id: 'legal', label: 'Legal' },
] as const;

export const LANDING_PLACEHOLDERS = [
  "Why is the sky blue?",
  "Latest developments in fusion energy",
  "Explain string theory like I'm 5",
  "History of the Roman Empire",
  "Best hiking trails in Kyoto",
  "Recipe for authentic Carbonara",
];

export const FOLLOW_UP_PLACEHOLDERS = [
  "Ask a follow up...",
  "More details on...",
  "Explain further...",
  "What about...",
];

export const SHARED_TRANSITION = {
  type: "spring" as const,
  stiffness: 300,
  damping: 30,
  mass: 1
};

export function getSessionGroup(timestamp: number): string {
  const date = new Date(timestamp);
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const sevenDaysAgo = new Date(today);
  sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
  const thirtyDaysAgo = new Date(today);
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

  if (date >= today) return "Today";
  if (date >= yesterday) return "Yesterday";
  if (date >= sevenDaysAgo) return "Previous 7 Days";
  if (date >= thirtyDaysAgo) return "Previous 30 Days";
  return date.toLocaleString('default', { month: 'long', year: 'numeric' });
}

export function getDomain(uri: string): string {
  try {
    return new URL(uri).hostname.replace(/^www\./, '');
  } catch {
    return "source";
  }
}
