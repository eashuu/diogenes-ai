
"use client";

import React, { useState, useEffect, useRef, useMemo } from 'react';
import WarpShaderHero from "./components/ui/wrap-shader";
import { 
  Plus, 
  PanelLeftClose, 
  PanelLeftOpen, 
  Globe,
  ArrowRight,
  Search,
  BookOpen,
  Share2,
  Moon,
  Sun,
  Flame,
  Settings,
  Trash2,
  Github,
  ChevronUp,
  X,
  User,
  Cpu,
  Palette,
  Database,
  Save,
  Download,
  Check,
  MoreHorizontal,
  Zap,
  Scale,
  Microscope,
  GraduationCap,
  Terminal,
  Activity,
  Gavel,
  Newspaper,
  LayoutTemplate,
  BrainCircuit,
  Eye,
  Briefcase,
  Copy,
  RefreshCw,
  ThumbsUp,
  ThumbsDown,
  Layers,
  Loader2
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { PlaceholdersAndVanishInput } from "./components/ui/placeholders-and-vanish-input";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from "./lib/utils";
import { useTheme } from "./lib/theme-provider";
import { apiService } from "./lib/api-service";
import type { Source, SystemSettings, LLMModelInfo, AllServicesStatus } from "./lib/api-types";

// --- Types ---

interface Message {
  role: 'user' | 'model';
  content: string;
  sources?: Source[];
}

interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  createdAt: number;
  mode?: string;
  profile?: string;
}

interface UserSettings {
  username: string;
  userTitle: string;
  language: string;
  defaultResearchMode: string;
  defaultProfile: string;
}

interface IntelligenceSettings {
  llmProvider: string;
  llmBaseUrl: string;
  selectedModel: string;
  temperature: number;
  maxTokens: number;
  searchBaseUrl: string;
  maxSearchResults: number;
  maxSources: number;
  maxIterations: number;
}

// --- Constants ---

const DEFAULT_SETTINGS: UserSettings = {
  username: "Guest Researcher",
  userTitle: "Pro Plan",
  language: "English",
  defaultResearchMode: "balanced",
  defaultProfile: "general"
};

const DEFAULT_INTELLIGENCE_SETTINGS: IntelligenceSettings = {
  llmProvider: "ollama",
  llmBaseUrl: "http://localhost:11434",
  selectedModel: "llama3.1:8b",
  temperature: 0.0,
  maxTokens: 4096,
  searchBaseUrl: "http://localhost:8080",
  maxSearchResults: 10,
  maxSources: 8,
  maxIterations: 3
};

const LANDING_PLACEHOLDERS = [
  "Why is the sky blue?",
  "Latest developments in fusion energy",
  "Explain string theory like I'm 5",
  "History of the Roman Empire",
  "Best hiking trails in Kyoto",
  "Recipe for authentic Carbonara",
];

const FOLLOW_UP_PLACEHOLDERS = [
  "Ask a follow up...",
  "More details on...",
  "Explain further...",
  "What about...",
];

const RESEARCH_MODES = [
  { id: 'quick', label: 'Quick', icon: Zap, description: 'Concise (30s)' },
  { id: 'balanced', label: 'Balanced', icon: Scale, description: 'Standard (1m)' },
  { id: 'deep', label: 'Deep', icon: Microscope, description: 'Comprehensive (3m)' },
];

const RESEARCH_PROFILES = [
  { id: 'general', label: 'General', icon: Globe },
  { id: 'academic', label: 'Academic', icon: GraduationCap },
  { id: 'technical', label: 'Technical', icon: Terminal },
  { id: 'news', label: 'News', icon: Newspaper },
  { id: 'medical', label: 'Medical', icon: Activity },
  { id: 'legal', label: 'Legal', icon: Gavel },
];

const SIDEBAR_WIDTH = 260;

const SHARED_TRANSITION = {
  type: "spring" as const,
  stiffness: 300,
  damping: 30,
  mass: 1
};

// --- Helper Functions ---

function getSessionGroup(timestamp: number): string {
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

function getDomain(uri: string): string {
  try {
    return new URL(uri).hostname.replace(/^www\./, '');
  } catch (e) {
    return "source";
  }
}

// --- Components ---

const SidebarSourceCard: React.FC<{ source: Source; index: number }> = ({ source, index }) => {
  const domain = source.domain || getDomain(source.url);

  return (
    <a 
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex flex-col gap-1 p-3 rounded-lg hover:bg-foreground/5 transition-colors group no-underline border border-transparent hover:border-foreground/5"
    >
      <div className="flex items-center gap-2">
         <div className="w-4 h-4 rounded-full bg-foreground/10 flex items-center justify-center shrink-0 overflow-hidden">
            <img 
               src={`https://www.google.com/s2/favicons?domain=${domain}&sz=64`} 
               alt="" 
               className="w-full h-full object-cover opacity-70 group-hover:opacity-100 transition-opacity"
               onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
             />
         </div>
         <span className="text-xs font-medium text-foreground truncate">{domain}</span>
         <span className="text-[10px] text-foreground/80 ml-auto">#{index + 1}</span>
      </div>
      <div className="text-sm font-semibold text-foreground leading-tight line-clamp-2 group-hover:text-accent transition-colors">
        {source.title}
      </div>
      <div className="text-xs text-foreground/80 line-clamp-2 mt-1">
        {source.url}
      </div>
    </a>
  );
};

const CitationChip = ({ index, source }: { index: number; source?: Source }) => {
  const domain = source ? (source.domain || getDomain(source.url)) : 'source';
  
  return (
    <a 
      href={source?.url || '#'}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1.5 px-2 py-0.5 mx-1 -translate-y-0.5 rounded-full bg-accent/10 hover:bg-accent/20 text-[10px] font-medium text-accent hover:text-accent/80 no-underline transition-all select-none border border-accent/20 align-middle whitespace-nowrap"
      title={source?.title || `Source ${index}`}
      onClick={(e) => e.stopPropagation()}
    >
      <span className="opacity-70 text-[9px] font-bold">[{index}]</span>
      <div className="flex items-center gap-1 max-w-[120px]">
        {source?.url && (
          <img 
            src={`https://www.google.com/s2/favicons?domain=${domain}&sz=64`} 
            alt=""
            className="w-2.5 h-2.5 rounded-full opacity-80"
            onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
          />
        )}
        <span className="truncate">{domain}</span>
      </div>
    </a>
  );
};

// --- Main Application ---

export default function DiogenesResearch() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isStreaming, setIsStreaming] = useState(false);
  const [input, setInput] = useState("");
  
  // Research State
  const [researchMode, setResearchMode] = useState<string>('balanced');
  const [researchProfile, setResearchProfile] = useState<string>('general');
  const [researchPhase, setResearchPhase] = useState<string | null>(null);
  const [isInputMenuOpen, setIsInputMenuOpen] = useState(false);
  
  // Sources Panel State
  const [viewSourcesFor, setViewSourcesFor] = useState<Source[] | null>(null);

  // UI States for actions
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Settings State
  const [settings, setSettings] = useState<UserSettings>(DEFAULT_SETTINGS);
  const [intelligenceSettings, setIntelligenceSettings] = useState<IntelligenceSettings>(DEFAULT_INTELLIGENCE_SETTINGS);
  const [availableModels, setAvailableModels] = useState<LLMModelInfo[]>([]);
  const [servicesStatus, setServicesStatus] = useState<AllServicesStatus | null>(null);
  const [isLoadingSettings, setIsLoadingSettings] = useState(false);
  const [settingsSaveStatus, setSettingsSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [activeSettingsTab, setActiveSettingsTab] = useState<'general' | 'intelligence' | 'appearance' | 'data'>('general');

  const { theme, setTheme } = useTheme();
  
  const scrollRef = useRef<HTMLDivElement>(null);
  const activeSession = sessions.find(s => s.id === activeChatId);

  // Load/Save sessions and settings
  useEffect(() => {
    const savedSessions = localStorage.getItem('diogenes_sessions_v2');
    if (savedSessions) {
      setSessions(JSON.parse(savedSessions));
    }
    
    const savedSettings = localStorage.getItem('diogenes_settings');
    if (savedSettings) {
      setSettings({ ...DEFAULT_SETTINGS, ...JSON.parse(savedSettings) });
    }
  }, []);

  useEffect(() => {
    if (sessions.length > 0) {
      localStorage.setItem('diogenes_sessions_v2', JSON.stringify(sessions));
    }
  }, [sessions]);

  useEffect(() => {
    localStorage.setItem('diogenes_settings', JSON.stringify(settings));
  }, [settings]);

  // Load settings from backend when settings modal opens
  useEffect(() => {
    if (showSettingsModal) {
      const loadBackendSettings = async () => {
        setIsLoadingSettings(true);
        try {
          // Load system settings
          const systemSettings = await apiService.getSettings();
          setIntelligenceSettings({
            llmProvider: systemSettings.llm.provider,
            llmBaseUrl: systemSettings.llm.base_url,
            // Use the synthesizer model as the "main" model in the UI
            selectedModel: systemSettings.llm.models.synthesizer,
            temperature: systemSettings.llm.temperature,
            maxTokens: systemSettings.llm.max_tokens,
            searchBaseUrl: systemSettings.search.base_url,
            maxSearchResults: systemSettings.search.max_results,
            maxSources: systemSettings.agent.max_sources,
            maxIterations: systemSettings.agent.max_iterations
          });
          
          // Load available models
          const models = await apiService.getAvailableModels();
          setAvailableModels(models);
          
          // Load services status
          const status = await apiService.getServicesStatus();
          setServicesStatus(status);
        } catch (error) {
          console.error('Failed to load backend settings:', error);
        } finally {
          setIsLoadingSettings(false);
        }
      };
      loadBackendSettings();
    }
  }, [showSettingsModal]);

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current) {
      const { scrollHeight, clientHeight, scrollTop } = scrollRef.current;
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
      if (isNearBottom || isStreaming) {
         scrollRef.current.scrollTo({
          top: scrollHeight,
          behavior: isStreaming ? 'auto' : 'smooth'
        });
      }
    }
  }, [activeSession?.messages, isStreaming, researchPhase]);

  const createNewChat = () => {
    setActiveChatId(null);
    setResearchMode('balanced');
    setResearchProfile('general');
    setViewSourcesFor(null);
  };

  const handleSidebarSelect = (id: string) => {
    setActiveChatId(id);
    setViewSourcesFor(null);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInput(e.target.value);
  };

  const handleClearHistory = () => {
    if (confirm("Are you sure you want to delete all local history? This cannot be undone.")) {
      setSessions([]);
      localStorage.removeItem('diogenes_sessions_v2');
      setActiveChatId(null);
      setShowSettingsModal(false);
    }
  };

  const handleExportData = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify({ settings, sessions }, null, 2));
    const downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href", dataStr);
    downloadAnchorNode.setAttribute("download", "diogenes_backup.json");
    document.body.appendChild(downloadAnchorNode);
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
  };

  const handleSaveIntelligenceSettings = async () => {
    setSettingsSaveStatus('saving');
    try {
      // Update LLM settings - set all model roles to the selected model
      await apiService.updateLLMSettings({
        provider: intelligenceSettings.llmProvider,
        base_url: intelligenceSettings.llmBaseUrl,
        temperature: intelligenceSettings.temperature,
        max_tokens: intelligenceSettings.maxTokens,
        models: {
          planner: intelligenceSettings.selectedModel,
          extractor: intelligenceSettings.selectedModel,
          synthesizer: intelligenceSettings.selectedModel,
          reflector: intelligenceSettings.selectedModel
        }
      });

      // Update search settings
      await apiService.updateSearchSettings({
        base_url: intelligenceSettings.searchBaseUrl,
        max_results: intelligenceSettings.maxSearchResults
      });

      // Update agent settings
      await apiService.updateAgentSettings({
        max_sources: intelligenceSettings.maxSources,
        max_iterations: intelligenceSettings.maxIterations
      });

      setSettingsSaveStatus('saved');
      setTimeout(() => setSettingsSaveStatus('idle'), 2000);
    } catch (error) {
      console.error('Failed to save intelligence settings:', error);
      setSettingsSaveStatus('error');
      setTimeout(() => setSettingsSaveStatus('idle'), 3000);
    }
  };

  const handleTestConnection = async (service: 'ollama' | 'searxng') => {
    const url = service === 'ollama' ? intelligenceSettings.llmBaseUrl : intelligenceSettings.searchBaseUrl;
    try {
      const result = await apiService.testServiceConnection(service, url);
      if (result.status === 'online') {
        alert(`${service === 'ollama' ? 'Ollama' : 'SearXNG'} connection successful!`);
      } else {
        alert(`Connection failed: ${result.error || 'Service unavailable'}`);
      }
      // Refresh services status
      const status = await apiService.getServicesStatus();
      setServicesStatus(status);
    } catch (error) {
      alert(`Connection test failed: ${error}`);
    }
  };

  const handleCopy = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    const id = `${activeChatId}-${index}`;
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Reusable function to run research via Diogenes API
  const runDiogenesResearch = async (
    sessionId: string, 
    prompt: string
  ) => {
    setIsStreaming(true);
    setViewSourcesFor(null);

    // Set initial phase based on mode
    if (researchMode === 'deep') {
      setResearchPhase("Initializing deep research...");
    } else {
      setResearchPhase("Starting research...");
    }

    try {
      let fullAnswer = "";
      const collectedSources: Source[] = [];
      let hasStartedAnswer = false;

      // Use the streaming API
      for await (const event of apiService.researchStream(
        {
          query: prompt,
          mode: researchMode as 'quick' | 'balanced' | 'deep',
          profile: researchProfile
        },
        (statusEvent) => {
          // Update research phase from status events
          console.debug('[SSE] Status event:', statusEvent.message);
          if (statusEvent.message) {
            setResearchPhase(statusEvent.message);
          }
        },
        (sourceEvent) => {
          // Collect sources as they're discovered
          console.debug('[SSE] Source event:', sourceEvent.url);
          const source: Source = {
            url: sourceEvent.url,
            title: sourceEvent.title,
            domain: getDomain(sourceEvent.url)
          };
          if (!collectedSources.some(s => s.url === source.url)) {
            collectedSources.push(source);
          }
        }
      )) {
        console.debug('[SSE] Event:', event.type, event.data?.content?.length || event.data);
        
        if (event.type === 'synthesis') {
          // Accumulate answer chunks
          fullAnswer += event.data.content;
          
          // Clear phase indicator once we start getting answer
          if (researchPhase) {
            setResearchPhase(null);
          }

          // Track if this is the first answer chunk
          const isFirstChunk = !hasStartedAnswer;
          if (isFirstChunk) {
            hasStartedAnswer = true;
          }

          // Update the session with streaming answer
          setSessions(prev => prev.map(s => {
            if (s.id !== sessionId) return s;
            
            const newMessages = [...s.messages];
            const modelMsg: Message = { 
              role: 'model', 
              content: fullAnswer,
              sources: collectedSources.length > 0 ? [...collectedSources] : undefined
            };

            if (isFirstChunk) {
              newMessages.push(modelMsg);
            } else {
              const lastIdx = newMessages.length - 1;
              if (newMessages[lastIdx]?.role === 'model') {
                newMessages[lastIdx] = modelMsg;
              }
            }
            return { ...s, messages: newMessages };
          }));
        } else if (event.type === 'complete') {
          // Final answer with all sources
          const completeData = event.data;
          const answer = completeData.answer || fullAnswer;
          
          // Convert backend sources to our format
          const finalSources: Source[] = collectedSources;

          setSessions(prev => prev.map(s => {
            if (s.id !== sessionId) return s;
            
            const newMessages = [...s.messages];
            const lastIdx = newMessages.length - 1;
            
            if (newMessages[lastIdx]?.role === 'model') {
              newMessages[lastIdx] = { 
                role: 'model', 
                content: answer,
                sources: finalSources.length > 0 ? finalSources : undefined
              };
            }
            return { ...s, messages: newMessages };
          }));
        } else if (event.type === 'error') {
          throw new Error(event.data.error);
        }
      }
    } catch (error) {
      console.error("Diogenes API error:", error);
      setResearchPhase(null);
      setSessions(prev => prev.map(s => 
        s.id === sessionId 
          ? { ...s, messages: [...s.messages, { role: 'model', content: "I encountered an error connecting to the research backend. Please ensure the API server is running and try again." }] } 
          : s
      ));
    } finally {
      setIsStreaming(false);
      setResearchPhase(null);
    }
  };

  const handleSubmit = async (e?: React.FormEvent<HTMLFormElement>) => {
    const prompt = input.trim();
    if (!prompt || isStreaming) return;

    let currentSessionId = activeChatId;

    if (!currentSessionId) {
      const newId = Date.now().toString();
      const newSession: ChatSession = {
        id: newId,
        title: prompt,
        messages: [],
        createdAt: Date.now(),
        mode: researchMode,
        profile: researchProfile
      };
      setSessions(prev => [newSession, ...prev]);
      currentSessionId = newId;
      setActiveChatId(newId);
    }

    // Add user message to state immediately
    const userMsg: Message = { role: 'user', content: prompt };
    setSessions(prev => prev.map(s => 
      s.id === currentSessionId ? { ...s, messages: [...s.messages, userMsg] } : s
    ));
    
    setInput(""); 
    
    // Call the research API
    await runDiogenesResearch(currentSessionId, prompt);
  };

  const handleRegenerate = async () => {
    if (!activeChatId || isStreaming) return;

    const session = sessions.find(s => s.id === activeChatId);
    if (!session || session.messages.length === 0) return;

    const lastMsg = session.messages[session.messages.length - 1];
    let promptToRun = "";

    if (lastMsg.role === 'model') {
       // Remove the last model message and use the user message before it
       const lastUserMsg = session.messages[session.messages.length - 2];
       if (!lastUserMsg || lastUserMsg.role !== 'user') return; // Should not happen
       promptToRun = lastUserMsg.content;
       
       // Update state: Remove model message, keep user message
       const messagesForState = session.messages.slice(0, -1);
       setSessions(prev => prev.map(s => s.id === activeChatId ? { ...s, messages: messagesForState } : s));
    } else {
       // Last message is user (error state or interrupted), run it
       promptToRun = lastMsg.content;
    }

    // Call the research API
    await runDiogenesResearch(activeChatId, promptToRun);
  };

  const placeholders = useMemo(() => activeChatId ? FOLLOW_UP_PLACEHOLDERS : LANDING_PLACEHOLDERS, [activeChatId]);

  // --- Grouped Sessions Memo ---
  const groupedSessions = useMemo(() => {
    const groups: Record<string, ChatSession[]> = {};
    const order = ["Today", "Yesterday", "Previous 7 Days", "Previous 30 Days"];
    
    sessions.forEach(session => {
      const groupName = getSessionGroup(session.createdAt);
      if (!groups[groupName]) {
        groups[groupName] = [];
      }
      groups[groupName].push(session);
    });

    const sortedGroups = Object.keys(groups).sort((a, b) => {
      const idxA = order.indexOf(a);
      const idxB = order.indexOf(b);
      if (idxA !== -1 && idxB !== -1) return idxA - idxB;
      if (idxA !== -1) return -1;
      if (idxB !== -1) return 1;
      return 0; 
    });

    return sortedGroups.map(title => ({
      title,
      items: groups[title]
    }));
  }, [sessions]);

  // --- Markdown Components Configuration ---
  const markdownComponents = useMemo(() => ({
    // a tag is overridden in render to have access to session state
    table: ({ node, ...props }: any) => (
      <div className="my-6 w-full overflow-x-auto rounded-lg border border-foreground/10 bg-foreground/5 shadow-sm">
        <table className="w-full text-sm text-left border-collapse" {...props} />
      </div>
    ),
    thead: ({ node, ...props }: any) => (
      <thead className="bg-foreground/5 text-foreground font-medium border-b border-foreground/10" {...props} />
    ),
    tbody: ({ node, ...props }: any) => (
      <tbody className="divide-y divide-foreground/5" {...props} />
    ),
    tr: ({ node, ...props }: any) => (
      <tr className="transition-colors hover:bg-foreground/5" {...props} />
    ),
    th: ({ node, ...props }: any) => (
      <th className="px-4 py-3 text-left font-semibold text-foreground whitespace-nowrap" {...props} />
    ),
    td: ({ node, ...props }: any) => (
      <td className="px-4 py-3 text-foreground align-top leading-relaxed" {...props} />
    ),
    ul: ({ node, ...props }: any) => (
      <ul className="my-4 ml-6 list-disc marker:text-foreground space-y-1" {...props} />
    ),
    ol: ({ node, ...props }: any) => (
      <ol className="my-4 ml-6 list-decimal marker:text-foreground space-y-1" {...props} />
    ),
    li: ({ node, ...props }: any) => (
      <li className="pl-1" {...props} />
    ),
    blockquote: ({ node, ...props }: any) => (
      <blockquote className="border-l-4 border-accent/40 pl-4 py-1 my-4 text-foreground italic bg-foreground/5 rounded-r-lg" {...props} />
    ),
    code: ({ node, inline, className, children, ...props }: any) => {
       if (inline) {
          return <code className="px-1.5 py-0.5 rounded-md bg-foreground/10 text-accent font-mono text-[0.9em] border border-foreground/5" {...props}>{children}</code>
       }
       return (
         <div className="relative my-4 rounded-lg overflow-hidden border border-foreground/10 bg-foreground/5">
            <div className="absolute top-2 right-2 flex gap-1">
               <div className="w-2.5 h-2.5 rounded-full bg-red-500/20"></div>
               <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/20"></div>
               <div className="w-2.5 h-2.5 rounded-full bg-green-500/20"></div>
            </div>
            <code className={cn(className, "block p-4 pt-8 overflow-x-auto font-mono text-sm text-foreground leading-relaxed")} {...props}>{children}</code>
         </div>
       );
    }
  }), []);

  return (
    <WarpShaderHero isChatting={!!activeChatId}>
      <div className="flex h-screen w-full text-foreground overflow-hidden relative font-inter">
        
        {/* Settings Modal */}
        <AnimatePresence>
          {showSettingsModal && (
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
            >
               <motion.div 
                initial={{ scale: 0.95, opacity: 0, y: 20 }}
                animate={{ scale: 1, opacity: 1, y: 0 }}
                exit={{ scale: 0.95, opacity: 0, y: 20 }}
                className="w-full max-w-4xl h-[600px] bg-background/95 backdrop-blur-xl border border-foreground/10 rounded-2xl shadow-2xl flex overflow-hidden"
              >
                {/* ... existing settings modal code ... */}
                <div className="w-64 bg-foreground/5 border-r border-foreground/10 p-6 flex flex-col gap-2">
                  <h2 className="text-xl font-semibold mb-6 px-2 flex items-center gap-2">
                    <Settings className="w-5 h-5 text-accent" />
                    Settings
                  </h2>
                  {[
                    { id: 'general', icon: User, label: 'General' },
                    { id: 'intelligence', icon: Cpu, label: 'Intelligence' },
                    { id: 'appearance', icon: Palette, label: 'Appearance' },
                    { id: 'data', icon: Database, label: 'Data & Memory' }
                  ].map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setActiveSettingsTab(tab.id as any)}
                      className={cn(
                        "flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all text-left",
                        activeSettingsTab === tab.id 
                          ? "bg-foreground/10 text-foreground shadow-sm" 
                          : "text-foreground/50 hover:text-foreground hover:bg-foreground/5"
                      )}
                    >
                      <tab.icon className="w-4 h-4" />
                      {tab.label}
                    </button>
                  ))}
                </div>
                
                {/* Settings Content */}
                <div className="flex-1 p-8 overflow-y-auto custom-scrollbar bg-background/40 relative">
                  <button 
                    onClick={() => setShowSettingsModal(false)}
                    className="absolute top-6 right-6 p-2 rounded-full hover:bg-foreground/10 text-foreground/40 hover:text-foreground transition-colors"
                  >
                    <X className="w-5 h-5" />
                  </button>

                  <AnimatePresence mode="wait">
                     {activeSettingsTab === 'general' && (
                      <motion.div key="general" initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} className="space-y-6 max-w-lg">
                        <div>
                          <h3 className="text-lg font-medium mb-1">User Profile</h3>
                          <p className="text-sm text-foreground/50 mb-4">How Diogenes addresses you.</p>
                          <label className="text-xs font-medium text-foreground uppercase mb-1 block">Username</label>
                          <input type="text" value={settings.username} onChange={(e) => setSettings({...settings, username: e.target.value})} className="w-full bg-foreground/5 border border-foreground/10 rounded-lg p-3 text-foreground mb-4 focus:outline-none focus:border-accent/50" />
                          <label className="text-xs font-medium text-foreground uppercase mb-1 block">Title / Role</label>
                          <input type="text" value={settings.userTitle} onChange={(e) => setSettings({...settings, userTitle: e.target.value})} className="w-full bg-foreground/5 border border-foreground/10 rounded-lg p-3 text-foreground mb-4 focus:outline-none focus:border-accent/50" />
                          <label className="text-xs font-medium text-foreground uppercase mb-1 block">Language</label>
                          <input type="text" value={settings.language} onChange={(e) => setSettings({...settings, language: e.target.value})} className="w-full bg-foreground/5 border border-foreground/10 rounded-lg p-3 text-foreground focus:outline-none focus:border-accent/50" />
                        </div>
                      </motion.div>
                     )}
                     
                     {activeSettingsTab === 'intelligence' && (
                      <motion.div key="intelligence" initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} className="space-y-6 max-w-lg">
                        {isLoadingSettings ? (
                          <div className="flex items-center justify-center py-12">
                            <Loader2 className="w-6 h-6 animate-spin text-accent" />
                            <span className="ml-2 text-foreground/50">Loading settings...</span>
                          </div>
                        ) : (
                          <>
                            {/* Service Status */}
                            <div className="p-4 rounded-lg bg-foreground/5 border border-foreground/10">
                              <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                                <Activity className="w-4 h-4" />
                                Services Status
                              </h4>
                              <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                  <span className="text-sm text-foreground/70">Ollama</span>
                                  <div className="flex items-center gap-2">
                                    <div className={cn(
                                      "w-2 h-2 rounded-full",
                                      servicesStatus?.ollama.status === 'online' ? "bg-green-500" : servicesStatus?.ollama.status === 'degraded' ? "bg-yellow-500" : "bg-red-500"
                                    )} />
                                    <span className="text-xs text-foreground/50">
                                      {servicesStatus?.ollama.status === 'online' ? 'Connected' : servicesStatus?.ollama.status === 'degraded' ? 'Degraded' : 'Disconnected'}
                                    </span>
                                  </div>
                                </div>
                                <div className="flex items-center justify-between">
                                  <span className="text-sm text-foreground/70">SearXNG</span>
                                  <div className="flex items-center gap-2">
                                    <div className={cn(
                                      "w-2 h-2 rounded-full",
                                      servicesStatus?.searxng.status === 'online' ? "bg-green-500" : servicesStatus?.searxng.status === 'degraded' ? "bg-yellow-500" : "bg-red-500"
                                    )} />
                                    <span className="text-xs text-foreground/50">
                                      {servicesStatus?.searxng.status === 'online' ? 'Connected' : servicesStatus?.searxng.status === 'degraded' ? 'Degraded' : 'Disconnected'}
                                    </span>
                                  </div>
                                </div>
                              </div>
                            </div>

                            {/* LLM Settings */}
                            <div>
                              <h3 className="text-lg font-medium mb-1">Language Model</h3>
                              <p className="text-sm text-foreground/50 mb-4">Configure which AI model powers Diogenes.</p>
                              
                              <label className="text-xs font-medium text-foreground uppercase mb-1 block">Ollama Base URL</label>
                              <div className="flex gap-2 mb-4">
                                <input 
                                  type="text" 
                                  value={intelligenceSettings.llmBaseUrl} 
                                  onChange={(e) => setIntelligenceSettings({...intelligenceSettings, llmBaseUrl: e.target.value})} 
                                  className="flex-1 bg-foreground/5 border border-foreground/10 rounded-lg p-3 text-foreground focus:outline-none focus:border-accent/50" 
                                  placeholder="http://localhost:11434"
                                />
                                <button 
                                  onClick={() => handleTestConnection('ollama')}
                                  className="px-3 py-2 rounded-lg bg-accent/10 hover:bg-accent/20 text-accent text-sm font-medium transition-colors"
                                >
                                  Test
                                </button>
                              </div>

                              <label className="text-xs font-medium text-foreground uppercase mb-1 block">Model</label>
                              <select 
                                value={intelligenceSettings.selectedModel}
                                onChange={(e) => setIntelligenceSettings({...intelligenceSettings, selectedModel: e.target.value})}
                                className="w-full bg-foreground/5 border border-foreground/10 rounded-lg p-3 text-foreground mb-4 focus:outline-none focus:border-accent/50"
                              >
                                {availableModels.length > 0 ? (
                                  availableModels.map(model => (
                                    <option key={model.name} value={model.name}>
                                      {model.name} {model.size ? `(${model.size})` : ''}
                                    </option>
                                  ))
                                ) : (
                                  <option value={intelligenceSettings.selectedModel}>{intelligenceSettings.selectedModel}</option>
                                )}
                              </select>

                              <label className="text-xs font-medium text-foreground uppercase mb-1 block">Temperature ({intelligenceSettings.temperature})</label>
                              <input 
                                type="range" 
                                min="0" 
                                max="2" 
                                step="0.1" 
                                value={intelligenceSettings.temperature} 
                                onChange={(e) => setIntelligenceSettings({...intelligenceSettings, temperature: parseFloat(e.target.value)})} 
                                className="w-full mb-1 accent-accent"
                              />
                              <p className="text-xs text-foreground/40 mb-4">Lower = more focused, Higher = more creative</p>

                              <label className="text-xs font-medium text-foreground uppercase mb-1 block">Max Tokens</label>
                              <input 
                                type="number" 
                                value={intelligenceSettings.maxTokens} 
                                onChange={(e) => setIntelligenceSettings({...intelligenceSettings, maxTokens: parseInt(e.target.value) || 4096})} 
                                className="w-full bg-foreground/5 border border-foreground/10 rounded-lg p-3 text-foreground mb-4 focus:outline-none focus:border-accent/50" 
                              />
                            </div>

                            {/* Search Settings */}
                            <div>
                              <h3 className="text-lg font-medium mb-1">Search Engine</h3>
                              <p className="text-sm text-foreground/50 mb-4">Configure the search backend (SearXNG).</p>
                              
                              <label className="text-xs font-medium text-foreground uppercase mb-1 block">SearXNG Base URL</label>
                              <div className="flex gap-2 mb-4">
                                <input 
                                  type="text" 
                                  value={intelligenceSettings.searchBaseUrl} 
                                  onChange={(e) => setIntelligenceSettings({...intelligenceSettings, searchBaseUrl: e.target.value})} 
                                  className="flex-1 bg-foreground/5 border border-foreground/10 rounded-lg p-3 text-foreground focus:outline-none focus:border-accent/50" 
                                  placeholder="http://localhost:8080"
                                />
                                <button 
                                  onClick={() => handleTestConnection('searxng')}
                                  className="px-3 py-2 rounded-lg bg-accent/10 hover:bg-accent/20 text-accent text-sm font-medium transition-colors"
                                >
                                  Test
                                </button>
                              </div>

                              <label className="text-xs font-medium text-foreground uppercase mb-1 block">Max Search Results</label>
                              <input 
                                type="number" 
                                min="1" 
                                max="50" 
                                value={intelligenceSettings.maxSearchResults} 
                                onChange={(e) => setIntelligenceSettings({...intelligenceSettings, maxSearchResults: parseInt(e.target.value) || 10})} 
                                className="w-full bg-foreground/5 border border-foreground/10 rounded-lg p-3 text-foreground mb-4 focus:outline-none focus:border-accent/50" 
                              />
                            </div>

                            {/* Agent Settings */}
                            <div>
                              <h3 className="text-lg font-medium mb-1">Research Agent</h3>
                              <p className="text-sm text-foreground/50 mb-4">Control how the research agent behaves.</p>
                              
                              <label className="text-xs font-medium text-foreground uppercase mb-1 block">Max Sources per Query</label>
                              <input 
                                type="number" 
                                min="1" 
                                max="20" 
                                value={intelligenceSettings.maxSources} 
                                onChange={(e) => setIntelligenceSettings({...intelligenceSettings, maxSources: parseInt(e.target.value) || 8})} 
                                className="w-full bg-foreground/5 border border-foreground/10 rounded-lg p-3 text-foreground mb-4 focus:outline-none focus:border-accent/50" 
                              />

                              <label className="text-xs font-medium text-foreground uppercase mb-1 block">Max Iterations (Deep Research)</label>
                              <input 
                                type="number" 
                                min="1" 
                                max="10" 
                                value={intelligenceSettings.maxIterations} 
                                onChange={(e) => setIntelligenceSettings({...intelligenceSettings, maxIterations: parseInt(e.target.value) || 3})} 
                                className="w-full bg-foreground/5 border border-foreground/10 rounded-lg p-3 text-foreground mb-4 focus:outline-none focus:border-accent/50" 
                              />
                            </div>

                            {/* Save Button */}
                            <button 
                              onClick={handleSaveIntelligenceSettings}
                              disabled={settingsSaveStatus === 'saving'}
                              className={cn(
                                "w-full py-3 px-4 rounded-lg font-medium transition-all flex items-center justify-center gap-2",
                                settingsSaveStatus === 'saved' 
                                  ? "bg-green-500/20 text-green-500 border border-green-500/30"
                                  : settingsSaveStatus === 'error'
                                  ? "bg-red-500/20 text-red-500 border border-red-500/30"
                                  : "bg-accent text-background hover:opacity-90"
                              )}
                            >
                              {settingsSaveStatus === 'saving' && <Loader2 className="w-4 h-4 animate-spin" />}
                              {settingsSaveStatus === 'saved' && <Check className="w-4 h-4" />}
                              {settingsSaveStatus === 'error' && <X className="w-4 h-4" />}
                              {settingsSaveStatus === 'idle' && 'Save Settings'}
                              {settingsSaveStatus === 'saving' && 'Saving...'}
                              {settingsSaveStatus === 'saved' && 'Saved!'}
                              {settingsSaveStatus === 'error' && 'Error Saving'}
                            </button>
                          </>
                        )}
                      </motion.div>
                     )}

                     {activeSettingsTab === 'appearance' && (
                      <motion.div key="appearance" initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} className="space-y-6 max-w-lg">
                        <div>
                          <h3 className="text-lg font-medium mb-1">Theme</h3>
                          <p className="text-sm text-foreground/50 mb-4">Choose how Diogenes looks.</p>
                          <div className="grid grid-cols-3 gap-3">
                            {(['diogenes', 'light', 'dark'] as const).map((t) => (
                              <button
                                key={t}
                                onClick={() => setTheme(t)}
                                className={cn(
                                  "p-4 rounded-lg border text-sm font-medium capitalize transition-all",
                                  theme === t 
                                    ? "border-accent bg-accent/10 text-accent" 
                                    : "border-foreground/10 text-foreground/70 hover:border-foreground/20 hover:bg-foreground/5"
                                )}
                              >
                                {t === 'diogenes' ? 'Default' : t}
                              </button>
                            ))}
                          </div>
                        </div>
                      </motion.div>
                     )}

                     {activeSettingsTab === 'data' && (
                      <motion.div key="data" initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} className="space-y-6 max-w-lg">
                        <div>
                          <h3 className="text-lg font-medium mb-1">Local Data</h3>
                          <p className="text-sm text-foreground/50 mb-4">Manage your conversation history and settings stored locally.</p>
                          
                          <div className="space-y-3">
                            <button 
                              onClick={handleExportData}
                              className="w-full py-3 px-4 rounded-lg bg-foreground/5 hover:bg-foreground/10 border border-foreground/10 text-foreground font-medium transition-colors text-left flex items-center gap-3"
                            >
                              <Download className="w-5 h-5 text-accent" />
                              <div>
                                <div className="text-sm font-medium">Export Data</div>
                                <div className="text-xs text-foreground/50">Download all your sessions and settings as JSON</div>
                              </div>
                            </button>
                            
                            <button 
                              onClick={handleClearHistory}
                              className="w-full py-3 px-4 rounded-lg bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 text-red-500 font-medium transition-colors text-left flex items-center gap-3"
                            >
                              <Trash2 className="w-5 h-5" />
                              <div>
                                <div className="text-sm font-medium">Clear All History</div>
                                <div className="text-xs text-red-500/70">Permanently delete all local conversations</div>
                              </div>
                            </button>
                          </div>
                        </div>

                        <div>
                          <h3 className="text-lg font-medium mb-1">Statistics</h3>
                          <p className="text-sm text-foreground/50 mb-4">Your usage at a glance.</p>
                          <div className="p-4 rounded-lg bg-foreground/5 border border-foreground/10">
                            <div className="grid grid-cols-2 gap-4">
                              <div>
                                <div className="text-2xl font-bold text-foreground">{sessions.length}</div>
                                <div className="text-xs text-foreground/50">Total Sessions</div>
                              </div>
                              <div>
                                <div className="text-2xl font-bold text-foreground">
                                  {sessions.reduce((acc, s) => acc + s.messages.length, 0)}
                                </div>
                                <div className="text-xs text-foreground/50">Total Messages</div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </motion.div>
                     )}
                  </AnimatePresence>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Sidebar */}
        <motion.aside 
          initial={false}
          animate={{ width: isSidebarOpen ? SIDEBAR_WIDTH : 0, opacity: isSidebarOpen ? 1 : 0 }}
          transition={SHARED_TRANSITION}
          className="h-full bg-glass/40 backdrop-blur-3xl border-r border-foreground/5 flex flex-col z-50 overflow-hidden relative shadow-2xl shrink-0"
        >
          {/* Top Section */}
          <div className="p-3 flex items-center justify-between gap-2 shrink-0">
             <button 
               onClick={createNewChat}
               className="flex-1 flex items-center justify-between px-3 py-2 rounded-lg hover:bg-foreground/10 transition-colors text-foreground hover:text-foreground group border border-transparent hover:border-foreground/5"
             >
                <div className="flex items-center gap-2">
                   <div className="w-6 h-6 rounded-full bg-foreground/10 flex items-center justify-center">
                     <Plus className="w-3.5 h-3.5 text-foreground" />
                   </div>
                   <span className="text-sm font-medium">New chat</span>
                </div>
             </button>
             <button 
               onClick={() => setIsSidebarOpen(false)}
               className="p-2 rounded-lg hover:bg-foreground/10 text-foreground hover:text-foreground transition-colors"
               title="Close sidebar"
             >
               <PanelLeftClose className="w-5 h-5" />
             </button>
          </div>
          
          {/* Session List */}
          <div className="flex-1 overflow-y-auto px-3 custom-scrollbar py-2">
             {groupedSessions.length === 0 ? (
                <div className="px-2 py-8 text-center text-xs text-foreground">
                   No recent history
                </div>
             ) : (
                <>
                  <div className="px-2 pt-2 pb-4 text-xs font-semibold text-foreground uppercase tracking-wider">
                    Your chats
                  </div>
                  <div className="space-y-6">
                    {groupedSessions.map(group => (
                       <div key={group.title}>
                          <div className="px-2 pb-2 text-[11px] font-medium text-foreground">
                             {group.title}
                          </div>
                          <div className="space-y-0.5">
                             {group.items.map(session => (
                                <button
                                   key={session.id}
                                   onClick={() => handleSidebarSelect(session.id)}
                                   className={cn(
                                      "w-full flex items-center gap-2 px-2 py-2 rounded-lg text-sm text-left transition-all group relative overflow-hidden",
                                      activeChatId === session.id 
                                         ? 'bg-foreground/10 text-foreground' 
                                         : 'text-foreground hover:bg-foreground/5 hover:text-foreground'
                                   )}
                                >
                                   <span className="truncate flex-1 text-[13px]">{session.title}</span>
                                </button>
                             ))}
                          </div>
                       </div>
                    ))}
                  </div>
                </>
             )}
          </div>

          {/* User Menu */}
          <div className="p-3 border-t border-foreground/5 bg-glass/20 relative z-20">
             <AnimatePresence>
                {isUserMenuOpen && (
                   <motion.div
                      initial={{ opacity: 0, y: 10, scale: 0.95 }}
                      animate={{ opacity: 1, y: 0, scale: 1 }}
                      exit={{ opacity: 0, y: 10, scale: 0.95 }}
                      transition={{ duration: 0.2 }}
                      className="absolute bottom-full left-0 right-0 mb-2 mx-3 bg-background/90 backdrop-blur-xl border border-foreground/10 rounded-xl shadow-2xl overflow-hidden z-50 flex flex-col p-1"
                   >
                      <button onClick={() => { setShowSettingsModal(true); setIsUserMenuOpen(false); }} className="flex items-center gap-3 px-3 py-2 text-sm text-foreground hover:text-foreground hover:bg-foreground/10 rounded-lg transition-colors text-left"><Settings className="w-4 h-4" /><span>Settings</span></button>
                      <button onClick={() => { handleExportData(); setIsUserMenuOpen(false); }} className="flex items-center gap-3 px-3 py-2 text-sm text-foreground hover:text-foreground hover:bg-foreground/10 rounded-lg transition-colors text-left"><Download className="w-4 h-4" /><span>Export Data</span></button>
                      <div className="h-px bg-foreground/5 my-1" />
                      <button onClick={() => { handleClearHistory(); setIsUserMenuOpen(false); }} className="flex items-center gap-3 px-3 py-2 text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-colors text-left"><Trash2 className="w-4 h-4" /><span>Clear History</span></button>
                   </motion.div>
                )}
             </AnimatePresence>
             <button onClick={() => setIsUserMenuOpen(!isUserMenuOpen)} className="w-full flex items-center justify-between group p-2 rounded-xl hover:bg-foreground/5 transition-colors">
               <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-accent to-background border border-foreground/10 flex items-center justify-center shrink-0 shadow-sm overflow-hidden">
                    <span className="text-xs font-bold text-foreground">{settings.username.slice(0,1).toUpperCase()}</span>
                  </div>
                  <div className="flex flex-col items-start overflow-hidden">
                    <span className="text-sm font-medium text-foreground truncate w-24 text-left">{settings.username}</span>
                    <span className="text-[10px] text-foreground truncate w-24 text-left">{settings.userTitle}</span>
                  </div>
               </div>
               <div className="text-foreground group-hover:text-foreground transition-colors"><MoreHorizontal className="w-4 h-4" /></div>
             </button>
          </div>
        </motion.aside>

        {/* Toggle Button */}
        <AnimatePresence>
          {!isSidebarOpen && (
            <motion.button
              key="open-toggle"
              initial={{ x: -60, opacity: 0 }}
              animate={{ x: 16, opacity: 1 }}
              exit={{ x: -60, opacity: 0 }}
              transition={SHARED_TRANSITION}
              onClick={() => setIsSidebarOpen(true)}
              className="absolute top-4 left-0 z-[60] p-2 bg-glass/40 backdrop-blur-md border border-foreground/10 rounded-xl text-foreground hover:text-foreground transition-all shadow-xl flex items-center justify-center w-10 h-10"
            >
              <PanelLeftOpen className="w-5 h-5" />
            </motion.button>
          )}
        </AnimatePresence>

        {/* Main Content Area */}
        <main className="flex-1 relative h-full flex flex-col items-center overflow-hidden">
          
          {/* Header Bar */}
          <header className="w-full h-16 bg-transparent flex items-center justify-between px-6 z-40 shrink-0 sticky top-0 pointer-events-none">
             <div className="flex items-center gap-4 pointer-events-auto">
               {!isSidebarOpen && <div className="w-8" />}
               <span className="text-sm font-semibold tracking-wider text-foreground uppercase">Diogenes</span>
             </div>
             <div className="flex bg-foreground/5 backdrop-blur-md rounded-full p-1 border border-foreground/10 pointer-events-auto">
                <button onClick={() => setTheme('diogenes')} className={cn("p-2 rounded-full", theme === 'diogenes' ? "bg-foreground/20 text-accent" : "text-foreground")}><Flame className="w-4 h-4" /></button>
                <button onClick={() => setTheme('light')} className={cn("p-2 rounded-full", theme === 'light' ? "bg-foreground/20 text-accent" : "text-foreground")}><Sun className="w-4 h-4" /></button>
                <button onClick={() => setTheme('dark')} className={cn("p-2 rounded-full", theme === 'dark' ? "bg-foreground/20 text-accent" : "text-foreground")}><Moon className="w-4 h-4" /></button>
             </div>
          </header>

          {/* Scrollable Content */}
          <motion.div 
            layout
            className={cn(
              "w-full overflow-hidden flex flex-col",
              activeChatId ? "flex-1 min-h-0" : "flex-1"
            )}
            transition={SHARED_TRANSITION}
          >
            <div 
              ref={scrollRef}
              className="flex-1 overflow-y-auto overflow-x-hidden custom-scrollbar scroll-smooth relative"
            >
              <div className="max-w-3xl mx-auto w-full px-4 md:px-8 min-h-full flex flex-col justify-start">
                <AnimatePresence mode="wait">
                  {activeChatId && (
                    <motion.div 
                      key="thread-content"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ duration: 0.6 }}
                      className="space-y-12 pt-8 pb-4 w-full"
                    >
                      {/* Session Info Header */}
                      {activeSession?.mode && (
                        <motion.div 
                          initial={{ opacity: 0, y: -20 }}
                          animate={{ opacity: 1, y: 0 }}
                          className="flex items-center gap-4 text-xs font-mono text-foreground mb-2"
                        >
                           <span className="flex items-center gap-1"><LayoutTemplate className="w-3 h-3" /> {activeSession.profile?.toUpperCase()}</span>
                           <span>•</span>
                           <span className="flex items-center gap-1">
                             {RESEARCH_MODES.find(m => m.id === activeSession.mode)?.icon && 
                               React.createElement(RESEARCH_MODES.find(m => m.id === activeSession.mode)!.icon, { className: "w-3 h-3" })}
                             {activeSession.mode?.toUpperCase()} MODE
                           </span>
                        </motion.div>
                      )}

                      {(() => {
                        const pairs = [];
                        for (let i = 0; i < (activeSession?.messages.length || 0); i++) {
                          const msg = activeSession!.messages[i];
                          if (msg.role === 'user') {
                            const nextMsg = activeSession!.messages[i+1];
                            pairs.push({
                              user: msg,
                              model: nextMsg?.role === 'model' ? nextMsg : null
                            });
                          }
                        }
                        return pairs;
                      })().map((pair, idx, arr) => (
                        <div key={idx} className="flex flex-col gap-6">
                          
                          <motion.h2 
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="text-2xl md:text-3xl font-medium text-foreground tracking-tight"
                          >
                            {pair.user.content}
                          </motion.h2>

                          {/* Phase Indicator / Loading - Moved here */}
                          {idx === arr.length - 1 && isStreaming && researchPhase && (
                            <div className="py-2 space-y-4">
                               <div className="flex items-center gap-3 text-accent animate-pulse">
                                  <div className="h-4 w-4 relative">
                                    <div className="absolute inset-0 rounded-full border-2 border-accent/30"></div>
                                    <div className="absolute inset-0 rounded-full border-2 border-accent border-t-transparent animate-spin"></div>
                                  </div>
                                  <span className="text-sm font-medium tracking-wide">
                                    {researchPhase}
                                  </span>
                               </div>
                            </div>
                          )}

                          {pair.model && (
                            <motion.div
                              initial={{ opacity: 0 }}
                              animate={{ opacity: 1 }}
                              transition={{ delay: 0.3 }}
                              className="relative"
                            >
                              <div className="flex items-center gap-2 text-foreground text-xs uppercase tracking-widest font-semibold mb-3">
                                <BookOpen className="w-3 h-3" />
                                Analysis
                              </div>
                              <div className="prose prose-invert prose-lg max-w-none text-foreground leading-relaxed">
                                <ReactMarkdown 
                                  remarkPlugins={[remarkGfm]}
                                  components={{
                                    ...markdownComponents,
                                    a: ({ node, href, children, ...props }) => {
                                      if (href?.startsWith('#cite-')) {
                                        const indexStr = href.replace('#cite-', '');
                                        const index = parseInt(indexStr, 10);
                                        const source = pair.model?.sources?.[index - 1];
                                        return <CitationChip index={index} source={source} />;
                                      }
                                      return <a href={href} {...props} target="_blank" rel="noopener noreferrer" className="text-foreground underline decoration-foreground/30 underline-offset-2 hover:decoration-foreground/60 transition-all">{children}</a>;
                                    }
                                  }}
                                >
                                  {pair.model.content ? pair.model.content.replace(/\[\s*(\d+(?:\s*,\s*\d+)*)\s*\]/g, (match, nums) => {
                                    return nums.split(',').map(n => ` [${n.trim()}](#cite-${n.trim()})`).join('');
                                  }) : ''}
                                </ReactMarkdown>
                              </div>
                              
                              {/* Message Footer / Actions */}
                              <div className="mt-8 pt-4 flex items-center justify-between border-t border-foreground/5">
                                 <div className="flex items-center gap-2">
                                    <button 
                                      onClick={() => handleCopy(pair.model?.content || "", idx)}
                                      className={cn(
                                        "p-2 rounded-full text-foreground hover:bg-foreground/5 transition-colors",
                                        copiedId === `${activeChatId}-${idx}` ? "text-green-500 bg-green-500/10" : "hover:text-foreground"
                                      )}
                                      title="Copy"
                                    >
                                      {copiedId === `${activeChatId}-${idx}` ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                                    </button>
                                    <button 
                                      onClick={handleRegenerate}
                                      disabled={isStreaming}
                                      className={cn(
                                         "p-2 rounded-full text-foreground hover:bg-foreground/5 transition-colors",
                                         isStreaming ? "opacity-50 cursor-not-allowed" : "hover:text-foreground"
                                      )}
                                      title="Regenerate"
                                    >
                                      <RefreshCw className={cn("w-4 h-4", isStreaming && "animate-spin")} />
                                    </button>
                                    <div className="h-4 w-px bg-foreground/10 mx-1" />
                                    <button className="p-2 rounded-full text-foreground hover:text-foreground hover:bg-foreground/5 transition-colors" title="Helpful">
                                      <ThumbsUp className="w-4 h-4" />
                                    </button>
                                    <button className="p-2 rounded-full text-foreground hover:text-foreground hover:bg-foreground/5 transition-colors" title="Not Helpful">
                                      <ThumbsDown className="w-4 h-4" />
                                    </button>
                                 </div>

                                 {pair.model.sources && pair.model.sources.length > 0 && (
                                    <button 
                                      onClick={() => setViewSourcesFor(pair.model.sources || null)}
                                      className="flex items-center gap-2 pl-2 pr-3 py-1.5 rounded-full bg-foreground/5 hover:bg-foreground/10 text-xs font-medium text-foreground transition-colors border border-foreground/5"
                                    >
                                       <div className="flex -space-x-1.5">
                                          {pair.model.sources.slice(0, 3).map((s, i) => {
                                             const domain = s.domain || getDomain(s.url || '');
                                             return (
                                             <div key={i} className="w-5 h-5 rounded-full border border-background bg-foreground/10 overflow-hidden relative z-10">
                                                <img 
                                                   src={`https://www.google.com/s2/favicons?domain=${domain}&sz=64`} 
                                                   className="w-full h-full object-cover"
                                                   alt=""
                                                />
                                             </div>
                                          )})}
                                       </div>
                                       <span>{pair.model.sources.length} sources</span>
                                       <Layers className="w-3.5 h-3.5 ml-1 opacity-50" />
                                    </button>
                                 )}
                              </div>
                            </motion.div>
                          )}
                        </div>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </div>
          </motion.div>

          {/* Sources Side Panel (Right) */}
          <AnimatePresence>
             {viewSourcesFor && (
                <motion.div
                   initial={{ x: "100%", opacity: 0 }}
                   animate={{ x: 0, opacity: 1 }}
                   exit={{ x: "100%", opacity: 0 }}
                   transition={{ type: "spring", damping: 30, stiffness: 300 }}
                   className="absolute top-0 right-0 bottom-0 w-80 md:w-96 bg-background/95 backdrop-blur-3xl border-l border-foreground/10 z-[60] shadow-2xl flex flex-col"
                >
                   <div className="flex items-center justify-between p-4 border-b border-foreground/5">
                      <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
                         <Layers className="w-4 h-4 text-accent" />
                         <span>{viewSourcesFor.length} Sources</span>
                      </div>
                      <button 
                         onClick={() => setViewSourcesFor(null)}
                         className="p-2 rounded-full hover:bg-foreground/10 text-foreground hover:text-foreground transition-colors"
                      >
                         <X className="w-4 h-4" />
                      </button>
                   </div>
                   <div className="flex-1 overflow-y-auto custom-scrollbar p-3 space-y-2">
                      {viewSourcesFor.map((source, i) => (
                         <SidebarSourceCard key={i} source={source} index={i} />
                      ))}
                   </div>
                </motion.div>
             )}
          </AnimatePresence>

          {/* Unified Central Input Area with Research Controls */}
          <motion.div
            layout
            transition={SHARED_TRANSITION}
            className={cn(
              "z-50 flex flex-col items-center justify-end shrink-0",
              activeChatId 
                ? "w-full" 
                : "w-full max-w-3xl px-4 pb-0"
            )}
          >
            {/* ... (Keep input area exactly as is) ... */}
            <div className={cn("w-full transition-all duration-500", activeChatId ? "max-w-3xl px-4 md:px-8 pb-6 pt-2" : "pb-0")}>
              <AnimatePresence>
                {!activeChatId && (
                  <motion.div 
                    key="landing-title"
                    layout
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95, y: -20 }}
                    transition={SHARED_TRANSITION}
                    className="text-center mb-8"
                  >
                    <h1 className="text-4xl md:text-6xl font-serif font-medium tracking-tight text-foreground mb-4">
                      Where knowledge begins
                    </h1>
                    <p className="text-foreground text-lg">
                      Ask anything. We'll search the world for you.
                    </p>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Input Area */}
              <motion.div layout className="w-full flex flex-col gap-3 relative">
                 {isInputMenuOpen && (
                   <div className="fixed inset-0 z-40 bg-transparent" onClick={() => setIsInputMenuOpen(false)} />
                 )}
                 
                 <AnimatePresence>
                   {isInputMenuOpen && (
                      <motion.div
                         initial={{ opacity: 0, y: 10, scale: 0.95 }}
                         animate={{ opacity: 1, y: 0, scale: 1 }}
                         exit={{ opacity: 0, y: 10, scale: 0.95 }}
                         transition={{ duration: 0.2 }}
                         className="absolute bottom-[calc(100%+12px)] left-0 w-80 bg-background/95 backdrop-blur-2xl border border-foreground/10 rounded-2xl shadow-2xl p-2 flex flex-col gap-1 overflow-hidden z-[60]"
                      >
                         <div className="px-3 py-2 text-[10px] font-bold text-foreground uppercase tracking-widest">
                            Research Intensity
                         </div>
                         <div className="flex p-1 bg-foreground/5 rounded-lg border border-foreground/5 mb-2">
                            {RESEARCH_MODES.map((mode) => (
                               <button
                                  key={mode.id}
                                  type="button"
                                  onClick={() => { setResearchMode(mode.id); }}
                                  className={cn(
                                     "flex-1 flex flex-col items-center gap-1 py-2 rounded-md transition-all",
                                     researchMode === mode.id 
                                        ? "bg-background text-foreground shadow-sm ring-1 ring-foreground/10" 
                                        : "text-foreground hover:text-foreground hover:bg-foreground/5"
                                  )}
                               >
                                  <mode.icon className="w-4 h-4" />
                                  <span className="text-[10px] font-medium">{mode.label}</span>
                               </button>
                            ))}
                         </div>

                         <div className="px-3 py-2 text-[10px] font-bold text-foreground uppercase tracking-widest border-t border-foreground/5 pt-3">
                            Perspective Profile
                         </div>
                         <div className="grid grid-cols-2 gap-1 p-1">
                            {RESEARCH_PROFILES.map((profile) => (
                               <button
                                  key={profile.id}
                                  type="button"
                                  onClick={() => { setResearchProfile(profile.id); }}
                                  className={cn(
                                     "flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-all text-left",
                                     researchProfile === profile.id 
                                        ? "bg-foreground/10 text-foreground" 
                                        : "text-foreground hover:text-foreground hover:bg-foreground/5"
                                  )}
                               >
                                  <profile.icon className="w-3.5 h-3.5" />
                                  <span>{profile.label}</span>
                                  {researchProfile === profile.id && <Check className="w-3 h-3 ml-auto text-accent" />}
                               </button>
                            ))}
                         </div>
                      </motion.div>
                   )}
                 </AnimatePresence>

                 <div className="w-full relative z-50">
                    <PlaceholdersAndVanishInput 
                      placeholders={placeholders}
                      onChange={handleInputChange}
                      onSubmit={handleSubmit}
                      className="bg-foreground/5 backdrop-blur-2xl border-foreground/10"
                      leftAction={
                         <button
                           type="button"
                           onClick={() => setIsInputMenuOpen(!isInputMenuOpen)}
                           className={cn(
                              "w-8 h-8 rounded-full flex items-center justify-center transition-all duration-200 border shadow-sm",
                              isInputMenuOpen 
                                 ? "bg-foreground text-background border-foreground" 
                                 : "bg-zinc-100/10 text-foreground border-transparent hover:bg-foreground/10"
                           )}
                        >
                           <Plus className={cn("w-4 h-4 transition-transform duration-300", isInputMenuOpen ? "rotate-45" : "rotate-0")} />
                        </button>
                      }
                    />
                 </div>
              </motion.div>

              <AnimatePresence>
                {activeChatId && (
                  <motion.p 
                    key="fine-print"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="mt-3 text-[10px] text-foreground text-center tracking-wide font-medium"
                  >
                    DIOGENES ENGINE V2.0
                  </motion.p>
                )}
              </AnimatePresence>
            </div>
          </motion.div>

          {/* Bottom Spacer (Only for Landing) */}
          <motion.div 
            layout
            className={cn(
              "w-full transition-all duration-700",
              activeChatId ? "h-0" : "flex-1"
            )}
            transition={SHARED_TRANSITION}
          />

        </main>
      </div>

      <style>{`
        /* Hide scrollbar for Chrome, Safari and Opera */
        .scrollbar-none::-webkit-scrollbar {
          display: none;
        }
        /* Hide scrollbar for IE, Edge and Firefox */
        .scrollbar-none {
          -ms-overflow-style: none;  /* IE and Edge */
          scrollbar-width: none;  /* Firefox */
        }
        .prose pre {
          background-color: rgba(var(--glass), 0.4) !important;
          border: 1px solid rgba(var(--foreground), 0.1);
          padding: 1.25rem;
          border-radius: 1rem;
          overflow-x: auto;
          margin: 1.5rem 0;
        }
        .prose code {
          color: rgb(var(--accent));
          font-weight: 500;
          background-color: rgba(var(--foreground), 0.05);
          padding: 0.2rem 0.4rem;
          border-radius: 0.25rem;
        }
        .prose h1, .prose h2, .prose h3 { color: rgb(var(--foreground)); margin-top: 2rem; }
        .prose strong { color: rgb(var(--foreground)); }
        .prose a { color: rgb(var(--accent)); text-decoration: none; border-bottom: 1px solid rgba(var(--accent), 0.3); transition: all 0.2s; }
        .prose a:hover { border-bottom-color: rgb(var(--accent)); }
        .prose ul > li::marker { color: rgba(var(--foreground), 1); }
      `}</style>
    </WarpShaderHero>
  );
}
