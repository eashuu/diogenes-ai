"use client";

import { useState, useEffect, useCallback } from 'react';
import WarpShaderHero from "./components/ui/wrap-shader";
import { PanelLeftOpen } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { apiService } from "./lib/api-service";
import type { Source } from "./lib/api-types";
import type { ChatSession, Message, UserSettings } from "./lib/types";
import {
  DEFAULT_SETTINGS,
  SHARED_TRANSITION,
  getDomain,
} from "./lib/types";
import type { AttachedFile } from "./components/MessageInput";

import Sidebar from "./components/Sidebar";
import Navbar from "./components/Navbar";
import EmptyChat from "./components/EmptyChat";
import ChatWindow from "./components/ChatWindow";
import MessageInput from "./components/MessageInput";
import SettingsModal from "./components/SettingsModal";
import DiscoverPage from "./components/DiscoverPage";
import LibraryPage from "./components/LibraryPage";

import { useToast } from "./components/ToastProvider";

function useIsMobile(breakpoint = 768) {
  const [isMobile, setIsMobile] = useState(false);
  useEffect(() => {
    const mql = window.matchMedia(`(max-width: ${breakpoint - 1}px)`);
    setIsMobile(mql.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mql.addEventListener('change', handler);
    return () => mql.removeEventListener('change', handler);
  }, [breakpoint]);
  return isMobile;
}

export default function DiogenesResearch() {
  const isMobile = useIsMobile();
  const { addToast } = useToast();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [input, setInput] = useState("");

  // Research State
  const [researchMode, setResearchMode] = useState<string>('balanced');
  const [researchProfile, setResearchProfile] = useState<string>('general');
  const [researchPhase, setResearchPhase] = useState<string | null>(null);

  // Sources Panel
  const [viewSourcesFor, setViewSourcesFor] = useState<Source[] | null>(null);

  // UI
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([]);

  // Settings
  const [settings, setSettings] = useState<UserSettings>(DEFAULT_SETTINGS);

  // View mode: 'chat', 'discover', or 'library'
  const [view, setView] = useState<'chat' | 'discover' | 'library'>('chat');

  const activeSession = sessions.find(s => s.id === activeChatId);

  // Auto-close sidebar on mobile, auto-open on desktop
  useEffect(() => {
    setIsSidebarOpen(!isMobile);
  }, [isMobile]);

  // ---- Persistence ----
  useEffect(() => {
    const saved = localStorage.getItem('diogenes_sessions_v2');
    if (saved) setSessions(JSON.parse(saved));
    const savedSettings = localStorage.getItem('diogenes_settings');
    if (savedSettings) setSettings({ ...DEFAULT_SETTINGS, ...JSON.parse(savedSettings) });
  }, []);

  useEffect(() => {
    if (sessions.length > 0) localStorage.setItem('diogenes_sessions_v2', JSON.stringify(sessions));
  }, [sessions]);

  useEffect(() => {
    localStorage.setItem('diogenes_settings', JSON.stringify(settings));
  }, [settings]);

  // ---- Handlers ----
  const createNewChat = useCallback(() => {
    setActiveChatId(null);
    setResearchMode('balanced');
    setResearchProfile('general');
    setViewSourcesFor(null);
    setAttachedFiles([]);
    setView('chat');
  }, []);

  const handleDeleteChat = useCallback((id: string) => {
    setSessions(prev => prev.filter(s => s.id !== id));
    if (activeChatId === id) setActiveChatId(null);
  }, [activeChatId]);

  const handleExportChat = useCallback((session: ChatSession) => {
    const markdown = [`# ${session.title}\n`, `*${new Date(session.createdAt).toLocaleString()}*\n`];
    session.messages.forEach(m => {
      markdown.push(m.role === 'user' ? `## You\n${m.content}\n` : `## Diogenes\n${m.content}\n`);
      if (m.sources?.length) {
        markdown.push('**Sources:**\n');
        m.sources.forEach((src, i) => markdown.push(`${i + 1}. [${src.title || src.url}](${src.url})\n`));
      }
    });
    const blob = new Blob([markdown.join('\n')], { type: 'text/markdown' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `${session.title.slice(0, 40).replace(/[^a-zA-Z0-9]/g, '-')}.md`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(a.href);
  }, []);

  const handleSidebarSelect = useCallback((id: string) => {
    setActiveChatId(id);
    setViewSourcesFor(null);
    setView('chat');
    if (isMobile) setIsSidebarOpen(false);
  }, [isMobile]);

  const handleClearHistory = useCallback(() => {
    if (confirm("Are you sure you want to delete all local history? This cannot be undone.")) {
      setSessions([]);
      localStorage.removeItem('diogenes_sessions_v2');
      setActiveChatId(null);
      setShowSettingsModal(false);
    }
  }, []);

  const handleExportData = useCallback(() => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify({ settings, sessions }, null, 2));
    const a = document.createElement('a');
    a.setAttribute("href", dataStr);
    a.setAttribute("download", "diogenes_backup.json");
    document.body.appendChild(a);
    a.click();
    a.remove();
  }, [settings, sessions]);

  const handleCopy = useCallback((text: string, index: number) => {
    navigator.clipboard.writeText(text);
    const id = `${activeChatId}-${index}`;
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  }, [activeChatId]);

  // File upload helper
  const uploadFiles = useCallback(async (files: AttachedFile[]): Promise<string[]> => {
    const ids: string[] = [];
    for (const f of files) {
      try {
        const formData = new FormData();
        formData.append('file', f.file);
        const resp = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000/api'}/v1/uploads`, {
          method: 'POST',
          body: formData,
        });
        if (resp.ok) {
          const data = await resp.json();
          if (data.file_id) ids.push(data.file_id);
        }
      } catch {
        console.error('Upload failed for', f.name);
        addToast({ type: 'error', title: 'Upload failed', message: `Could not upload ${f.name}` });
      }
    }
    return ids;
  }, []);

  // ---- Research ----
  const runDiogenesResearch = useCallback(async (sessionId: string, prompt: string, fileIds?: string[]) => {
    setIsStreaming(true);
    setViewSourcesFor(null);
    setResearchPhase(researchMode === 'deep' ? "Initializing deep research..." : "Starting research...");

    try {
      let fullAnswer = "";
      const collectedSources: Source[] = [];
      let hasStartedAnswer = false;

      for await (const event of apiService.researchStream(
        { query: prompt, mode: researchMode as 'quick' | 'balanced' | 'deep', profile: researchProfile },
        (statusEvent) => {
          if (statusEvent.message) setResearchPhase(statusEvent.message);
        },
        (sourceEvent) => {
          const source: Source = { url: sourceEvent.url, title: sourceEvent.title, domain: getDomain(sourceEvent.url) };
          if (!collectedSources.some(s => s.url === source.url)) collectedSources.push(source);
        }
      )) {
        if (event.type === 'synthesis') {
          fullAnswer += event.data.content;
          setResearchPhase(null);
          const isFirstChunk = !hasStartedAnswer;
          if (isFirstChunk) hasStartedAnswer = true;

          setSessions(prev => prev.map(s => {
            if (s.id !== sessionId) return s;
            const newMessages = [...s.messages];
            const modelMsg: Message = { role: 'model', content: fullAnswer, sources: collectedSources.length > 0 ? [...collectedSources] : undefined };
            if (isFirstChunk) {
              newMessages.push(modelMsg);
            } else {
              const lastIdx = newMessages.length - 1;
              if (newMessages[lastIdx]?.role === 'model') newMessages[lastIdx] = modelMsg;
            }
            return { ...s, messages: newMessages };
          }));
        } else if (event.type === 'complete') {
          const answer = event.data.answer || fullAnswer;
          setSessions(prev => prev.map(s => {
            if (s.id !== sessionId) return s;
            const newMessages = [...s.messages];
            const lastIdx = newMessages.length - 1;
            if (newMessages[lastIdx]?.role === 'model') {
              newMessages[lastIdx] = { role: 'model', content: answer, sources: collectedSources.length > 0 ? [...collectedSources] : undefined };
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
      addToast({
        type: 'error',
        title: 'Research failed',
        message: error instanceof Error ? error.message : 'Could not connect to the research backend.',
        duration: 8000,
      });
      setSessions(prev => prev.map(s =>
        s.id === sessionId
          ? { ...s, messages: [...s.messages, { role: 'model' as const, content: "I encountered an error connecting to the research backend. Please ensure the API server is running and try again." }] }
          : s
      ));
    } finally {
      setIsStreaming(false);
      setResearchPhase(null);
    }
  }, [researchMode, researchProfile]);

  const handleSubmit = useCallback(async () => {
    const prompt = input.trim();
    if (!prompt || isStreaming) return;

    if (prompt.length > 10000) {
      addToast({ type: 'warning', title: 'Query too long', message: 'Please keep your query under 10,000 characters.' });
      return;
    }

    let currentSessionId = activeChatId;
    if (!currentSessionId) {
      const newId = Date.now().toString();
      const newSession: ChatSession = { id: newId, title: prompt, messages: [], createdAt: Date.now(), mode: researchMode, profile: researchProfile };
      setSessions(prev => [newSession, ...prev]);
      currentSessionId = newId;
      setActiveChatId(newId);
    }

    let fileIds: string[] | undefined;
    if (attachedFiles.length > 0) {
      fileIds = await uploadFiles(attachedFiles);
      setAttachedFiles([]);
    }

    const userMsg: Message = { role: 'user', content: prompt };
    setSessions(prev => prev.map(s => s.id === currentSessionId ? { ...s, messages: [...s.messages, userMsg] } : s));
    setInput("");
    await runDiogenesResearch(currentSessionId, prompt, fileIds);
  }, [input, isStreaming, activeChatId, researchMode, researchProfile, attachedFiles, uploadFiles, runDiogenesResearch]);

  const handleRegenerate = useCallback(async () => {
    if (!activeChatId || isStreaming) return;
    const session = sessions.find(s => s.id === activeChatId);
    if (!session || session.messages.length === 0) return;

    const lastMsg = session.messages[session.messages.length - 1];
    let promptToRun = "";
    if (lastMsg.role === 'model') {
      const lastUserMsg = session.messages[session.messages.length - 2];
      if (!lastUserMsg || lastUserMsg.role !== 'user') return;
      promptToRun = lastUserMsg.content;
      setSessions(prev => prev.map(s => s.id === activeChatId ? { ...s, messages: s.messages.slice(0, -1) } : s));
    } else {
      promptToRun = lastMsg.content;
    }
    await runDiogenesResearch(activeChatId, promptToRun);
  }, [activeChatId, isStreaming, sessions, runDiogenesResearch]);

  return (
    <WarpShaderHero isChatting={!!activeChatId}>
      <div className="flex h-screen w-full text-foreground overflow-hidden relative font-inter">

        {/* Settings Modal */}
        <SettingsModal
          isOpen={showSettingsModal}
          onClose={() => setShowSettingsModal(false)}
          settings={settings}
          onSettingsChange={setSettings}
          sessions={sessions}
          onExportData={handleExportData}
          onClearHistory={handleClearHistory}
        />

        {/* Sidebar */}
        <Sidebar
          sessions={sessions}
          activeChatId={activeChatId}
          isOpen={isSidebarOpen}
          settings={settings}
          isMobile={isMobile}
          onNewChat={createNewChat}
          onSelectChat={handleSidebarSelect}
          onClose={() => setIsSidebarOpen(false)}
          onOpenSettings={() => setShowSettingsModal(true)}
          onExportData={handleExportData}
          onClearHistory={handleClearHistory}
        />

        {/* Toggle Button — desktop only */}
        <AnimatePresence>
          {!isMobile && !isSidebarOpen && (
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

        {/* Main Content */}
        <main className="flex-1 relative h-full flex flex-col items-center overflow-hidden transition-all duration-300 ease-in-out">
          <Navbar
            hasSidebarGap={!isMobile && !isSidebarOpen}
            view={view}
            onViewChange={setView}
            isMobile={isMobile}
            onToggleSidebar={() => setIsSidebarOpen(prev => !prev)}
          />

          {view === 'discover' ? (
            <div className="flex-1 w-full overflow-y-auto">
              <DiscoverPage onStartResearch={(topic) => {
                setView('chat');
                setActiveChatId(null);
                setInput(topic);
              }} />
            </div>
          ) : view === 'library' ? (
            <LibraryPage
              sessions={sessions}
              onSelectChat={(id) => { setView('chat'); handleSidebarSelect(id); }}
              onDeleteChat={handleDeleteChat}
              onExportChat={handleExportChat}
              onBack={() => setView('chat')}
            />
          ) : (
            <>
              {activeChatId && activeSession ? (
                /* Chat mode: messages take remaining space, input pinned at bottom */
                <>
                  <div className="flex-1 min-h-0 w-full overflow-hidden flex flex-col">
                    <ChatWindow
                      session={activeSession}
                      isStreaming={isStreaming}
                      researchPhase={researchPhase}
                      activeChatId={activeChatId}
                      copiedId={copiedId}
                      onCopy={handleCopy}
                      onRegenerate={handleRegenerate}
                      viewSourcesFor={viewSourcesFor}
                      onViewSources={setViewSourcesFor}
                    />
                  </div>
                  <div className="w-full shrink-0 z-50">
                    <div className="max-w-3xl mx-auto px-4 md:px-8 pb-5 md:pb-7 pt-2">
                      <MessageInput
                        input={input}
                        isStreaming={isStreaming}
                        activeChatId={activeChatId}
                        researchMode={researchMode}
                        researchProfile={researchProfile}
                        attachedFiles={attachedFiles}
                        onInputChange={(e) => setInput(e.target.value)}
                        onSubmit={handleSubmit}
                        onModeChange={setResearchMode}
                        onProfileChange={setResearchProfile}
                        onFilesAttach={(files) => setAttachedFiles(prev => [...prev, ...files])}
                        onFileRemove={(id) => setAttachedFiles(prev => prev.filter(f => f.id !== id))}
                      />
                    </div>
                  </div>
                </>
              ) : (
                /* Empty state: center everything vertically */
                <div className="flex-1 flex flex-col items-center justify-center w-full max-w-3xl mx-auto px-4 md:px-6 pb-8">
                  <EmptyChat onSuggestionClick={(q) => { setInput(q); }} />
                  <div className="w-full mt-2">
                    <MessageInput
                      input={input}
                      isStreaming={isStreaming}
                      activeChatId={activeChatId}
                      researchMode={researchMode}
                      researchProfile={researchProfile}
                      attachedFiles={attachedFiles}
                      onInputChange={(e) => setInput(e.target.value)}
                      onSubmit={handleSubmit}
                      onModeChange={setResearchMode}
                      onProfileChange={setResearchProfile}
                      onFilesAttach={(files) => setAttachedFiles(prev => [...prev, ...files])}
                      onFileRemove={(id) => setAttachedFiles(prev => prev.filter(f => f.id !== id))}
                    />
                  </div>
                </div>
              )}
            </>
          )}
        </main>
      </div>
    </WarpShaderHero>
  );
}
