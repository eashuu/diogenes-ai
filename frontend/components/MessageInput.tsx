"use client";

import React, { useMemo, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from "framer-motion";
import {
  ChevronUp,
  Zap,
  Scale,
  Microscope,
  Globe,
  GraduationCap,
  Terminal,
  Newspaper,
  Activity,
  Gavel,
  Paperclip,
  X,
} from "lucide-react";
import { PlaceholdersAndVanishInput } from "./ui/placeholders-and-vanish-input";
import { cn } from "../lib/utils";
import {
  RESEARCH_MODES,
  RESEARCH_PROFILES,
  LANDING_PLACEHOLDERS,
  FOLLOW_UP_PLACEHOLDERS,
} from "../lib/types";

const MODE_ICONS: Record<string, React.ElementType> = {
  quick: Zap,
  balanced: Scale,
  deep: Microscope,
};

const PROFILE_ICONS: Record<string, React.ElementType> = {
  general: Globe,
  academic: GraduationCap,
  technical: Terminal,
  news: Newspaper,
  medical: Activity,
  legal: Gavel,
};

interface AttachedFile {
  id: string;
  name: string;
  size: number;
  file: File;
}

interface MessageInputProps {
  input: string;
  isStreaming: boolean;
  activeChatId: string | null;
  researchMode: string;
  researchProfile: string;
  attachedFiles: AttachedFile[];
  onInputChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onSubmit: (e?: React.FormEvent<HTMLFormElement>) => void;
  onModeChange: (mode: string) => void;
  onProfileChange: (profile: string) => void;
  onFilesAttach: (files: AttachedFile[]) => void;
  onFileRemove: (id: string) => void;
}

export type { AttachedFile };

export default function MessageInput({
  input,
  isStreaming,
  activeChatId,
  researchMode,
  researchProfile,
  attachedFiles,
  onInputChange,
  onSubmit,
  onModeChange,
  onProfileChange,
  onFilesAttach,
  onFileRemove,
}: MessageInputProps) {
  const [isMenuOpen, setIsMenuOpen] = React.useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const placeholders = useMemo(
    () => (activeChatId ? FOLLOW_UP_PLACEHOLDERS : LANDING_PLACEHOLDERS),
    [activeChatId]
  );

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    const newFiles: AttachedFile[] = Array.from(files).map(f => ({
      id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      name: f.name,
      size: f.size,
      file: f,
    }));
    onFilesAttach(newFiles);
    if (fileInputRef.current) fileInputRef.current.value = '';
  }, [onFilesAttach]);

  const ModeIcon = MODE_ICONS[researchMode] || Scale;

  return (
    <motion.div layout className="w-full flex flex-col gap-3 relative">
      {isMenuOpen && (
        <div className="fixed inset-0 z-40 bg-transparent" onClick={() => setIsMenuOpen(false)} />
      )}

      {/* Research Control Menu */}
      <AnimatePresence>
        {isMenuOpen && (
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
              {RESEARCH_MODES.map((mode) => {
                const Icon = MODE_ICONS[mode.id] || Scale;
                return (
                  <button
                    key={mode.id}
                    type="button"
                    onClick={() => onModeChange(mode.id)}
                    className={cn(
                      "flex-1 flex flex-col items-center gap-1 py-2 rounded-md transition-all",
                      researchMode === mode.id
                        ? "bg-background text-foreground shadow-sm ring-1 ring-foreground/10"
                        : "text-foreground hover:text-foreground hover:bg-foreground/5"
                    )}
                  >
                    <Icon className="w-4 h-4" />
                    <span className="text-[10px] font-medium">{mode.label}</span>
                  </button>
                );
              })}
            </div>

            <div className="px-3 py-2 text-[10px] font-bold text-foreground uppercase tracking-widest border-t border-foreground/5 pt-3">
              Perspective Profile
            </div>
            <div className="grid grid-cols-2 gap-1 p-1">
              {RESEARCH_PROFILES.map((profile) => {
                const Icon = PROFILE_ICONS[profile.id] || Globe;
                return (
                  <button
                    key={profile.id}
                    type="button"
                    onClick={() => onProfileChange(profile.id)}
                    className={cn(
                      "flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-all text-left",
                      researchProfile === profile.id
                        ? "bg-foreground/10 text-foreground"
                        : "text-foreground hover:text-foreground hover:bg-foreground/5"
                    )}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    {profile.label}
                  </button>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Attached Files Preview */}
      {attachedFiles.length > 0 && (
        <div className="flex flex-wrap gap-2 px-1">
          {attachedFiles.map(f => (
            <div key={f.id} className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-foreground/5 border border-foreground/10 text-xs text-foreground">
              <Paperclip className="w-3 h-3 opacity-50" />
              <span className="truncate max-w-[160px]">{f.name}</span>
              <span className="text-foreground/40">({(f.size / 1024).toFixed(0)}KB)</span>
              <button onClick={() => onFileRemove(f.id)} className="p-0.5 rounded hover:bg-foreground/10 transition-colors">
                <X className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Input */}
      <PlaceholdersAndVanishInput
        placeholders={placeholders}
        onChange={onInputChange}
        onSubmit={onSubmit}
        controlledValue={input}
        leftAction={
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className={cn(
                "flex items-center gap-1.5 px-2.5 py-1.5 rounded-full text-xs font-medium transition-all mr-1",
                isMenuOpen
                  ? "bg-foreground/15 text-foreground"
                  : "bg-foreground/5 hover:bg-foreground/10 text-foreground"
              )}
            >
              <ModeIcon className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">
                {RESEARCH_MODES.find(m => m.id === researchMode)?.label}
              </span>
              <ChevronUp className={cn("w-3 h-3 transition-transform", isMenuOpen && "rotate-180")} />
            </button>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept=".pdf,.docx,.txt,.md,.csv"
              className="hidden"
              onChange={handleFileSelect}
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="p-1.5 rounded-full text-foreground/50 hover:text-foreground hover:bg-foreground/10 transition-all"
              title="Attach files"
            >
              <Paperclip className="w-4 h-4" />
            </button>
          </div>
        }
      />
    </motion.div>
  );
}
