"use client";

import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from "framer-motion";
import {
  Settings,
  User,
  Cpu,
  Palette,
  Database,
  X,
  Loader2,
  Check,
  Activity,
  Download,
  Trash2,
  Save,
} from "lucide-react";
import { cn } from "../lib/utils";
import { useTheme } from "../lib/theme-provider";
import { apiService } from "../lib/api-service";
import type { LLMModelInfo, AllServicesStatus } from "../lib/api-types";
import type { UserSettings, IntelligenceSettings, ChatSession } from "../lib/types";
import { DEFAULT_INTELLIGENCE_SETTINGS } from "../lib/types";

const PROVIDERS = [
  { id: 'ollama', label: 'Ollama', description: 'Local or remote Ollama' },
  { id: 'openai', label: 'OpenAI', description: 'GPT-4o, o1, o3' },
  { id: 'anthropic', label: 'Anthropic', description: 'Claude Sonnet/Opus' },
  { id: 'groq', label: 'Groq', description: 'Fast cloud inference' },
  { id: 'gemini', label: 'Gemini', description: 'Google AI' },
];

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  settings: UserSettings;
  onSettingsChange: (s: UserSettings) => void;
  sessions: ChatSession[];
  onExportData: () => void;
  onClearHistory: () => void;
}

type Tab = 'general' | 'intelligence' | 'appearance' | 'data';

export default function SettingsModal({
  isOpen,
  onClose,
  settings,
  onSettingsChange,
  sessions,
  onExportData,
  onClearHistory,
}: SettingsModalProps) {
  const [activeTab, setActiveTab] = useState<Tab>('general');
  const [intelligenceSettings, setIntelligenceSettings] = useState<IntelligenceSettings>(DEFAULT_INTELLIGENCE_SETTINGS);
  const [availableModels, setAvailableModels] = useState<LLMModelInfo[]>([]);
  const [servicesStatus, setServicesStatus] = useState<AllServicesStatus | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const { theme, setTheme } = useTheme();

  useEffect(() => {
    if (!isOpen) return;
    const load = async () => {
      setIsLoading(true);
      try {
        const sys = await apiService.getSettings();
        setIntelligenceSettings({
          llmProvider: sys.llm.provider,
          llmBaseUrl: sys.llm.base_url,
          llmApiKey: "",
          selectedModel: sys.llm.models.synthesizer,
          temperature: sys.llm.temperature,
          maxTokens: sys.llm.max_tokens,
          searchBaseUrl: sys.search.base_url,
          maxSearchResults: sys.search.max_results,
          maxSources: sys.agent.max_sources,
          maxIterations: sys.agent.max_iterations,
        });
        const models = await apiService.getAvailableModels();
        setAvailableModels(models);
        const status = await apiService.getServicesStatus();
        setServicesStatus(status);
      } catch {
        // Backend unavailable
      } finally {
        setIsLoading(false);
      }
    };
    load();
  }, [isOpen]);

  const handleSave = async () => {
    setSaveStatus('saving');
    try {
      const llmUpdate: Record<string, any> = {
        provider: intelligenceSettings.llmProvider,
        temperature: intelligenceSettings.temperature,
        max_tokens: intelligenceSettings.maxTokens,
        models: {
          planner: intelligenceSettings.selectedModel,
          extractor: intelligenceSettings.selectedModel,
          synthesizer: intelligenceSettings.selectedModel,
          reflector: intelligenceSettings.selectedModel,
        },
      };
      if (intelligenceSettings.llmProvider === 'ollama') {
        llmUpdate.base_url = intelligenceSettings.llmBaseUrl;
      }
      if (intelligenceSettings.llmApiKey) {
        llmUpdate.api_key = intelligenceSettings.llmApiKey;
      }
      await apiService.updateLLMSettings(llmUpdate);
      await apiService.updateSearchSettings({
        base_url: intelligenceSettings.searchBaseUrl,
        max_results: intelligenceSettings.maxSearchResults,
      });
      await apiService.updateAgentSettings({
        max_sources: intelligenceSettings.maxSources,
        max_iterations: intelligenceSettings.maxIterations,
      });
      setSaveStatus('saved');
      setTimeout(() => setSaveStatus('idle'), 2000);
    } catch {
      setSaveStatus('error');
      setTimeout(() => setSaveStatus('idle'), 3000);
    }
  };

  const handleTest = async (service: 'ollama' | 'searxng') => {
    const url = service === 'ollama' ? intelligenceSettings.llmBaseUrl : intelligenceSettings.searchBaseUrl;
    try {
      const result = await apiService.testServiceConnection(service, url);
      if (result.status === 'online') {
        alert(`${service} connection successful!`);
      } else {
        alert(`Connection failed: ${result.error || 'Service unavailable'}`);
      }
      const s = await apiService.getServicesStatus();
      setServicesStatus(s);
    } catch (err) {
      alert(`Connection test failed: ${err}`);
    }
  };

  if (!isOpen) return null;

  const tabs: { id: Tab; icon: React.ElementType; label: string }[] = [
    { id: 'general', icon: User, label: 'General' },
    { id: 'intelligence', icon: Cpu, label: 'Intelligence' },
    { id: 'appearance', icon: Palette, label: 'Appearance' },
    { id: 'data', icon: Database, label: 'Data & Memory' },
  ];

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[100] flex items-center justify-center p-2 md:p-4 bg-black/60 backdrop-blur-sm"
      >
        <motion.div
          initial={{ scale: 0.95, opacity: 0, y: 20 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.95, opacity: 0, y: 20 }}
          className="w-full max-w-4xl h-[90vh] md:h-[600px] bg-background/95 backdrop-blur-xl border border-foreground/10 rounded-xl md:rounded-2xl shadow-2xl flex flex-col md:flex-row overflow-hidden"
        >
          {/* Tab List */}
          {/* Tab navigation - horizontal on mobile, vertical sidebar on desktop */}
          <div className="md:w-64 bg-foreground/5 border-b md:border-b-0 md:border-r border-foreground/10 p-3 md:p-6 flex md:flex-col gap-2 shrink-0 overflow-x-auto">
            <h2 className="hidden md:flex text-xl font-semibold mb-6 px-2 items-center gap-2">
              <Settings className="w-5 h-5 text-accent" />
              Settings
            </h2>
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  "flex items-center gap-2 md:gap-3 px-3 md:px-4 py-2 md:py-3 rounded-lg md:rounded-xl text-xs md:text-sm font-medium transition-all text-left whitespace-nowrap",
                  activeTab === tab.id
                    ? "bg-foreground/10 text-foreground shadow-sm"
                    : "text-foreground/50 hover:text-foreground hover:bg-foreground/5"
                )}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </div>

          {/* Content */}
          <div className="flex-1 p-4 md:p-8 overflow-y-auto custom-scrollbar bg-background/40 relative">
            <button
              onClick={onClose}
              className="absolute top-3 right-3 md:top-6 md:right-6 p-2 rounded-full hover:bg-foreground/10 text-foreground/40 hover:text-foreground transition-colors z-10"
            >
              <X className="w-5 h-5" />
            </button>

            <AnimatePresence mode="wait">
              {/* GENERAL */}
              {activeTab === 'general' && (
                <motion.div key="general" initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} className="space-y-6 max-w-lg">
                  <div>
                    <h3 className="text-lg font-medium mb-1">User Profile</h3>
                    <p className="text-sm text-foreground/50 mb-4">How Diogenes addresses you.</p>
                    <label className="text-xs font-medium text-foreground uppercase mb-1 block">Username</label>
                    <input type="text" value={settings.username} onChange={(e) => onSettingsChange({ ...settings, username: e.target.value })} className="w-full bg-foreground/5 border border-foreground/10 rounded-lg p-3 text-foreground mb-4 focus:outline-none focus:border-accent/50" />
                    <label className="text-xs font-medium text-foreground uppercase mb-1 block">Title / Role</label>
                    <input type="text" value={settings.userTitle} onChange={(e) => onSettingsChange({ ...settings, userTitle: e.target.value })} className="w-full bg-foreground/5 border border-foreground/10 rounded-lg p-3 text-foreground mb-4 focus:outline-none focus:border-accent/50" />
                    <label className="text-xs font-medium text-foreground uppercase mb-1 block">Language</label>
                    <input type="text" value={settings.language} onChange={(e) => onSettingsChange({ ...settings, language: e.target.value })} className="w-full bg-foreground/5 border border-foreground/10 rounded-lg p-3 text-foreground focus:outline-none focus:border-accent/50" />
                  </div>
                </motion.div>
              )}

              {/* INTELLIGENCE */}
              {activeTab === 'intelligence' && (
                <motion.div key="intelligence" initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} className="space-y-6 max-w-lg">
                  {isLoading ? (
                    <div className="flex items-center justify-center py-12">
                      <Loader2 className="w-6 h-6 animate-spin text-accent" />
                      <span className="ml-2 text-foreground/50">Loading settings...</span>
                    </div>
                  ) : (
                    <>
                      {/* Services Status */}
                      <div className="p-4 rounded-lg bg-foreground/5 border border-foreground/10">
                        <h4 className="text-sm font-medium mb-3 flex items-center gap-2">
                          <Activity className="w-4 h-4" />
                          Services Status
                        </h4>
                        <div className="space-y-2">
                          {['ollama', 'searxng'].map(svc => {
                            const s = svc === 'ollama' ? servicesStatus?.ollama : servicesStatus?.searxng;
                            return (
                              <div key={svc} className="flex items-center justify-between">
                                <span className="text-sm text-foreground/70 capitalize">{svc}</span>
                                <div className="flex items-center gap-2">
                                  <div className={cn("w-2 h-2 rounded-full", s?.status === 'online' ? "bg-green-500" : s?.status === 'degraded' ? "bg-yellow-500" : "bg-red-500")} />
                                  <span className="text-xs text-foreground/50">{s?.status === 'online' ? 'Connected' : s?.status === 'degraded' ? 'Degraded' : 'Disconnected'}</span>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>

                      {/* Provider Selection */}
                      <div>
                        <h3 className="text-lg font-medium mb-1">LLM Provider</h3>
                        <p className="text-sm text-foreground/50 mb-4">Select which AI provider powers Diogenes.</p>
                        <div className="grid grid-cols-2 gap-2 mb-4">
                          {PROVIDERS.map(p => (
                            <button
                              key={p.id}
                              onClick={() => setIntelligenceSettings({ ...intelligenceSettings, llmProvider: p.id })}
                              className={cn(
                                "p-3 rounded-lg border text-left transition-all",
                                intelligenceSettings.llmProvider === p.id
                                  ? "border-accent bg-accent/10 text-foreground"
                                  : "border-foreground/10 text-foreground/70 hover:border-foreground/20 hover:bg-foreground/5"
                              )}
                            >
                              <div className="text-sm font-medium">{p.label}</div>
                              <div className="text-[10px] text-foreground/50">{p.description}</div>
                            </button>
                          ))}
                        </div>
                      </div>

                      {/* Base URL (Ollama) */}
                      {intelligenceSettings.llmProvider === 'ollama' && (
                        <div>
                          <label className="text-xs font-medium text-foreground uppercase mb-1 block">Ollama Base URL</label>
                          <div className="flex gap-2 mb-4">
                            <input
                              type="text"
                              value={intelligenceSettings.llmBaseUrl}
                              onChange={(e) => setIntelligenceSettings({ ...intelligenceSettings, llmBaseUrl: e.target.value })}
                              className="flex-1 bg-foreground/5 border border-foreground/10 rounded-lg p-3 text-foreground focus:outline-none focus:border-accent/50"
                              placeholder="http://localhost:11434"
                            />
                            <button
                              onClick={() => handleTest('ollama')}
                              className="px-3 py-2 rounded-lg bg-accent/10 hover:bg-accent/20 text-accent text-sm font-medium transition-colors"
                            >
                              Test
                            </button>
                          </div>
                        </div>
                      )}

                      {/* API Key (cloud providers) */}
                      {intelligenceSettings.llmProvider !== 'ollama' && (
                        <div>
                          <label className="text-xs font-medium text-foreground uppercase mb-1 block">API Key</label>
                          <input
                            type="password"
                            value={intelligenceSettings.llmApiKey}
                            onChange={(e) => setIntelligenceSettings({ ...intelligenceSettings, llmApiKey: e.target.value })}
                            className="w-full bg-foreground/5 border border-foreground/10 rounded-lg p-3 text-foreground mb-2 focus:outline-none focus:border-accent/50"
                            placeholder={`Enter your ${PROVIDERS.find(p => p.id === intelligenceSettings.llmProvider)?.label || ''} API key`}
                          />
                          <p className="text-xs text-foreground/40 mb-4">Your API key is sent to the backend and stored in memory only. It is never persisted to disk.</p>
                        </div>
                      )}

                      {/* Model */}
                      <div>
                        <label className="text-xs font-medium text-foreground uppercase mb-1 block">Model</label>
                        {intelligenceSettings.llmProvider === 'ollama' && availableModels.length > 0 ? (
                          <select
                            value={intelligenceSettings.selectedModel}
                            onChange={(e) => setIntelligenceSettings({ ...intelligenceSettings, selectedModel: e.target.value })}
                            className="w-full bg-foreground/5 border border-foreground/10 rounded-lg p-3 text-foreground mb-4 focus:outline-none focus:border-accent/50"
                          >
                            {availableModels.map(m => (
                              <option key={m.name} value={m.name}>
                                {m.name} {m.size ? `(${m.size})` : ''}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <input
                            type="text"
                            value={intelligenceSettings.selectedModel}
                            onChange={(e) => setIntelligenceSettings({ ...intelligenceSettings, selectedModel: e.target.value })}
                            className="w-full bg-foreground/5 border border-foreground/10 rounded-lg p-3 text-foreground mb-4 focus:outline-none focus:border-accent/50"
                            placeholder={
                              intelligenceSettings.llmProvider === 'openai' ? 'gpt-4o-mini' :
                              intelligenceSettings.llmProvider === 'anthropic' ? 'claude-sonnet-4-20250514' :
                              intelligenceSettings.llmProvider === 'groq' ? 'llama-3.3-70b-versatile' :
                              intelligenceSettings.llmProvider === 'gemini' ? 'gemini-2.0-flash' :
                              'model-name'
                            }
                          />
                        )}
                      </div>

                      {/* Temperature */}
                      <div>
                        <label className="text-xs font-medium text-foreground uppercase mb-1 block">Temperature ({intelligenceSettings.temperature})</label>
                        <input type="range" min="0" max="2" step="0.1" value={intelligenceSettings.temperature} onChange={(e) => setIntelligenceSettings({ ...intelligenceSettings, temperature: parseFloat(e.target.value) })} className="w-full mb-1 accent-accent" />
                        <p className="text-xs text-foreground/40 mb-4">Lower = more focused, Higher = more creative</p>
                      </div>

                      {/* Max Tokens */}
                      <div>
                        <label className="text-xs font-medium text-foreground uppercase mb-1 block">Max Tokens</label>
                        <input type="number" value={intelligenceSettings.maxTokens} onChange={(e) => setIntelligenceSettings({ ...intelligenceSettings, maxTokens: parseInt(e.target.value) || 4096 })} className="w-full bg-foreground/5 border border-foreground/10 rounded-lg p-3 text-foreground mb-4 focus:outline-none focus:border-accent/50" />
                      </div>

                      {/* Search Settings */}
                      <div>
                        <h3 className="text-lg font-medium mb-1">Search Engine</h3>
                        <p className="text-sm text-foreground/50 mb-4">Configure SearXNG.</p>
                        <label className="text-xs font-medium text-foreground uppercase mb-1 block">SearXNG Base URL</label>
                        <div className="flex gap-2 mb-4">
                          <input type="text" value={intelligenceSettings.searchBaseUrl} onChange={(e) => setIntelligenceSettings({ ...intelligenceSettings, searchBaseUrl: e.target.value })} className="flex-1 bg-foreground/5 border border-foreground/10 rounded-lg p-3 text-foreground focus:outline-none focus:border-accent/50" placeholder="http://localhost:8080" />
                          <button onClick={() => handleTest('searxng')} className="px-3 py-2 rounded-lg bg-accent/10 hover:bg-accent/20 text-accent text-sm font-medium transition-colors">Test</button>
                        </div>
                        <label className="text-xs font-medium text-foreground uppercase mb-1 block">Max Search Results</label>
                        <input type="number" min="1" max="50" value={intelligenceSettings.maxSearchResults} onChange={(e) => setIntelligenceSettings({ ...intelligenceSettings, maxSearchResults: parseInt(e.target.value) || 10 })} className="w-full bg-foreground/5 border border-foreground/10 rounded-lg p-3 text-foreground mb-4 focus:outline-none focus:border-accent/50" />
                      </div>

                      {/* Agent Settings */}
                      <div>
                        <h3 className="text-lg font-medium mb-1">Research Agent</h3>
                        <p className="text-sm text-foreground/50 mb-4">Control research behavior.</p>
                        <label className="text-xs font-medium text-foreground uppercase mb-1 block">Max Sources</label>
                        <input type="number" min="1" max="20" value={intelligenceSettings.maxSources} onChange={(e) => setIntelligenceSettings({ ...intelligenceSettings, maxSources: parseInt(e.target.value) || 8 })} className="w-full bg-foreground/5 border border-foreground/10 rounded-lg p-3 text-foreground mb-4 focus:outline-none focus:border-accent/50" />
                        <label className="text-xs font-medium text-foreground uppercase mb-1 block">Max Iterations (Deep Research)</label>
                        <input type="number" min="1" max="10" value={intelligenceSettings.maxIterations} onChange={(e) => setIntelligenceSettings({ ...intelligenceSettings, maxIterations: parseInt(e.target.value) || 3 })} className="w-full bg-foreground/5 border border-foreground/10 rounded-lg p-3 text-foreground mb-4 focus:outline-none focus:border-accent/50" />
                      </div>

                      {/* Save */}
                      <button
                        onClick={handleSave}
                        disabled={saveStatus === 'saving'}
                        className={cn(
                          "w-full py-3 px-4 rounded-lg font-medium transition-all flex items-center justify-center gap-2",
                          saveStatus === 'saved'
                            ? "bg-green-500/20 text-green-500 border border-green-500/30"
                            : saveStatus === 'error'
                            ? "bg-red-500/20 text-red-500 border border-red-500/30"
                            : "bg-accent text-background hover:opacity-90"
                        )}
                      >
                        {saveStatus === 'saving' && <Loader2 className="w-4 h-4 animate-spin" />}
                        {saveStatus === 'saved' && <Check className="w-4 h-4" />}
                        {saveStatus === 'error' && <X className="w-4 h-4" />}
                        {saveStatus === 'idle' && 'Save Settings'}
                        {saveStatus === 'saving' && 'Saving...'}
                        {saveStatus === 'saved' && 'Saved!'}
                        {saveStatus === 'error' && 'Error Saving'}
                      </button>
                    </>
                  )}
                </motion.div>
              )}

              {/* APPEARANCE */}
              {activeTab === 'appearance' && (
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

              {/* DATA */}
              {activeTab === 'data' && (
                <motion.div key="data" initial={{ opacity: 0, x: 10 }} animate={{ opacity: 1, x: 0 }} className="space-y-6 max-w-lg">
                  <div>
                    <h3 className="text-lg font-medium mb-1">Local Data</h3>
                    <p className="text-sm text-foreground/50 mb-4">Manage your conversation history and settings stored locally.</p>
                    <div className="space-y-3">
                      <button
                        onClick={onExportData}
                        className="w-full py-3 px-4 rounded-lg bg-foreground/5 hover:bg-foreground/10 border border-foreground/10 text-foreground font-medium transition-colors text-left flex items-center gap-3"
                      >
                        <Download className="w-5 h-5 text-accent" />
                        <div>
                          <div className="text-sm font-medium">Export Data</div>
                          <div className="text-xs text-foreground/50">Download all sessions and settings as JSON</div>
                        </div>
                      </button>
                      <button
                        onClick={onClearHistory}
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
    </AnimatePresence>
  );
}
