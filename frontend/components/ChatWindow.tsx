"use client";

import React, { useRef, useEffect } from 'react';
import { motion, AnimatePresence } from "framer-motion";
import { Layers, X } from "lucide-react";
import type { Source } from "../lib/api-types";
import type { ChatSession } from "../lib/types";
import { RESEARCH_MODES } from "../lib/types";
import MessageBox from "./MessageBox";
import { SidebarSourceCard } from "./MessageSources";

interface ChatWindowProps {
  session: ChatSession;
  isStreaming: boolean;
  researchPhase: string | null;
  activeChatId: string | null;
  copiedId: string | null;
  onCopy: (text: string, index: number) => void;
  onRegenerate: () => void;
  viewSourcesFor: Source[] | null;
  onViewSources: (sources: Source[] | null) => void;
}

export default function ChatWindow({
  session,
  isStreaming,
  researchPhase,
  activeChatId,
  copiedId,
  onCopy,
  onRegenerate,
  viewSourcesFor,
  onViewSources,
}: ChatWindowProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

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
  }, [session.messages, isStreaming, researchPhase]);

  // Build user/model pairs
  const pairs: { user: ChatSession['messages'][0]; model: ChatSession['messages'][0] | null }[] = [];
  for (let i = 0; i < session.messages.length; i++) {
    const msg = session.messages[i];
    if (msg.role === 'user') {
      const nextMsg = session.messages[i + 1];
      pairs.push({
        user: msg,
        model: nextMsg?.role === 'model' ? nextMsg : null
      });
    }
  }

  return (
    <>
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto overflow-x-hidden custom-scrollbar scroll-smooth relative"
      >
        <div className="max-w-3xl mx-auto w-full px-4 md:px-8 min-h-full flex flex-col justify-start">
          <motion.div
            key="thread-content"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6 }}
            className="space-y-12 pt-8 pb-4 w-full"
          >
            {/* Session Info Header */}
            {session.mode && (
              <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center gap-4 text-xs font-mono text-foreground mb-2"
              >
                <span className="flex items-center gap-1">{session.profile?.toUpperCase()}</span>
                <span>&#8226;</span>
                <span className="flex items-center gap-1">{session.mode?.toUpperCase()} MODE</span>
              </motion.div>
            )}

            {pairs.map((pair, idx) => (
              <MessageBox
                key={idx}
                userMessage={pair.user}
                modelMessage={pair.model}
                pairIndex={idx}
                isLast={idx === pairs.length - 1}
                isStreaming={isStreaming}
                researchPhase={researchPhase}
                sessionMode={session.mode}
                sessionProfile={session.profile}
                activeChatId={activeChatId}
                onCopy={onCopy}
                onRegenerate={onRegenerate}
                onViewSources={(sources) => onViewSources(sources)}
                copiedId={copiedId}
              />
            ))}
          </motion.div>
        </div>
      </div>

      {/* Sources Side Panel */}
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
                onClick={() => onViewSources(null)}
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
    </>
  );
}
