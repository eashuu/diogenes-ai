"use client";

import React, { useMemo, useState, useCallback } from 'react';
import { motion } from "framer-motion";
import {
  BookOpen,
  Copy,
  RefreshCw,
  ThumbsUp,
  ThumbsDown,
  Check,
  Layers,
  Volume2,
  VolumeX,
  LayoutTemplate,
} from "lucide-react";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from "../lib/utils";
import type { Source } from "../lib/api-types";
import type { Message } from "../lib/types";
import { getDomain, RESEARCH_MODES } from "../lib/types";
import { CitationChip } from "./MessageSources";
import ThinkBox from "./ThinkBox";
import ResearchSteps from "./ResearchSteps";

interface MessageBoxProps {
  userMessage: Message;
  modelMessage: Message | null;
  pairIndex: number;
  isLast: boolean;
  isStreaming: boolean;
  researchPhase: string | null;
  sessionMode?: string;
  sessionProfile?: string;
  activeChatId: string | null;
  onCopy: (text: string, index: number) => void;
  onRegenerate: () => void;
  onViewSources: (sources: Source[]) => void;
  copiedId: string | null;
}

// Parse <think> tags from model content
function parseThinkContent(content: string): { think: string; body: string } {
  const thinkMatch = content.match(/<think>([\s\S]*?)<\/think>/);
  if (thinkMatch) {
    const think = thinkMatch[1].trim();
    const body = content.replace(/<think>[\s\S]*?<\/think>/, '').trim();
    return { think, body };
  }
  // Handle unclosed think tag (still streaming)
  const openMatch = content.match(/<think>([\s\S]*)/);
  if (openMatch && !content.includes('</think>')) {
    return { think: openMatch[1].trim(), body: '' };
  }
  return { think: '', body: content };
}

export default function MessageBox({
  userMessage,
  modelMessage,
  pairIndex,
  isLast,
  isStreaming,
  researchPhase,
  activeChatId,
  onCopy,
  onRegenerate,
  onViewSources,
  copiedId,
}: MessageBoxProps) {
  const [isSpeaking, setIsSpeaking] = useState(false);

  const markdownComponents = useMemo(() => ({
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
        return <code className="px-1.5 py-0.5 rounded-md bg-foreground/10 text-accent font-mono text-[0.9em] border border-foreground/5" {...props}>{children}</code>;
      }
      const lang = className?.replace('language-', '') || '';
      return (
        <div className="relative my-4 rounded-lg overflow-hidden border border-foreground/10 bg-foreground/5">
          <div className="flex items-center justify-between px-4 py-2 bg-foreground/5 border-b border-foreground/10">
            <span className="text-[10px] font-mono text-foreground/50 uppercase">{lang || 'code'}</span>
            <button
              onClick={() => {
                const text = String(children).replace(/\n$/, '');
                navigator.clipboard.writeText(text);
              }}
              className="text-[10px] font-medium text-foreground/40 hover:text-foreground transition-colors flex items-center gap-1"
            >
              <Copy className="w-3 h-3" />
              Copy
            </button>
          </div>
          <code className={cn(className, "block p-4 overflow-x-auto font-mono text-sm text-foreground leading-relaxed")} {...props}>{children}</code>
        </div>
      );
    }
  }), []);

  const handleTTS = useCallback(() => {
    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }
    const text = modelMessage?.content?.replace(/<think>[\s\S]*?<\/think>/g, '').replace(/[#*_`\[\]()]/g, '') || '';
    if (!text) return;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);
    window.speechSynthesis.speak(utterance);
    setIsSpeaking(true);
  }, [isSpeaking, modelMessage?.content]);

  const parsed = modelMessage ? parseThinkContent(modelMessage.content || '') : null;

  return (
    <div className="flex flex-col gap-6">
      {/* User query as heading */}
      <motion.h2
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-2xl md:text-3xl font-medium text-foreground tracking-tight"
      >
        {userMessage.content}
      </motion.h2>

      {/* Phase Indicator */}
      {isLast && isStreaming && researchPhase && (
        <ResearchSteps phase={researchPhase} />
      )}

      {/* Model response */}
      {modelMessage && parsed && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="relative"
        >
          {/* ThinkBox for chain-of-thought */}
          {parsed.think && (
            <ThinkBox
              content={parsed.think}
              isStreaming={isLast && isStreaming && !parsed.body}
            />
          )}

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
                    const index = parseInt(href.replace('#cite-', ''), 10);
                    const source = modelMessage.sources?.[index - 1];
                    return <CitationChip index={index} source={source} />;
                  }
                  return <a href={href} {...props} target="_blank" rel="noopener noreferrer" className="text-foreground underline decoration-foreground/30 underline-offset-2 hover:decoration-foreground/60 transition-all">{children}</a>;
                }
              }}
            >
              {parsed.body ? parsed.body.replace(/\[\s*(\d+(?:\s*,\s*\d+)*)\s*\]/g, (_match, nums) => {
                return nums.split(',').map((n: string) => ` [${n.trim()}](#cite-${n.trim()})`).join('');
              }) : ''}
            </ReactMarkdown>
          </div>

          {/* Message Footer / Actions */}
          <div className="mt-8 pt-4 flex items-center justify-between border-t border-foreground/5">
            <div className="flex items-center gap-2">
              <button
                onClick={() => onCopy(parsed.body || modelMessage.content || "", pairIndex)}
                className={cn(
                  "p-2 rounded-full text-foreground hover:bg-foreground/5 transition-colors",
                  copiedId === `${activeChatId}-${pairIndex}` ? "text-green-500 bg-green-500/10" : "hover:text-foreground"
                )}
                title="Copy"
              >
                {copiedId === `${activeChatId}-${pairIndex}` ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
              </button>
              <button
                onClick={onRegenerate}
                disabled={isStreaming}
                className={cn(
                  "p-2 rounded-full text-foreground hover:bg-foreground/5 transition-colors",
                  isStreaming ? "opacity-50 cursor-not-allowed" : "hover:text-foreground"
                )}
                title="Regenerate"
              >
                <RefreshCw className={cn("w-4 h-4", isStreaming && "animate-spin")} />
              </button>
              <button
                onClick={handleTTS}
                className={cn(
                  "p-2 rounded-full text-foreground hover:bg-foreground/5 transition-colors",
                  isSpeaking && "text-accent bg-accent/10"
                )}
                title={isSpeaking ? "Stop speaking" : "Read aloud"}
              >
                {isSpeaking ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
              </button>
              <div className="h-4 w-px bg-foreground/10 mx-1" />
              <button className="p-2 rounded-full text-foreground hover:text-foreground hover:bg-foreground/5 transition-colors" title="Helpful">
                <ThumbsUp className="w-4 h-4" />
              </button>
              <button className="p-2 rounded-full text-foreground hover:text-foreground hover:bg-foreground/5 transition-colors" title="Not Helpful">
                <ThumbsDown className="w-4 h-4" />
              </button>
            </div>

            {modelMessage.sources && modelMessage.sources.length > 0 && (
              <button
                onClick={() => onViewSources(modelMessage.sources!)}
                className="flex items-center gap-2 pl-2 pr-3 py-1.5 rounded-full bg-foreground/5 hover:bg-foreground/10 text-xs font-medium text-foreground transition-colors border border-foreground/5"
              >
                <div className="flex -space-x-1.5">
                  {modelMessage.sources.slice(0, 3).map((s, i) => {
                    const d = s.domain || getDomain(s.url || '');
                    return (
                      <div key={i} className="w-5 h-5 rounded-full border border-background bg-foreground/10 overflow-hidden relative z-10">
                        <img
                          src={`https://www.google.com/s2/favicons?domain=${encodeURIComponent(d)}&sz=64`}
                          className="w-full h-full object-cover"
                          alt=""
                        />
                      </div>
                    );
                  })}
                </div>
                <span>{modelMessage.sources.length} sources</span>
                <Layers className="w-3.5 h-3.5 ml-1 opacity-50" />
              </button>
            )}
          </div>
        </motion.div>
      )}
    </div>
  );
}
