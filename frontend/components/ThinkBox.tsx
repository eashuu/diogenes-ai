"use client";

import React, { useState } from 'react';
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, BrainCircuit } from "lucide-react";
import { cn } from "../lib/utils";

interface ThinkBoxProps {
  content: string;
  isStreaming?: boolean;
}

export default function ThinkBox({ content, isStreaming }: ThinkBoxProps) {
  const [isOpen, setIsOpen] = useState(true);

  if (!content) return null;

  return (
    <div className="mb-4 rounded-xl border border-purple-500/20 bg-purple-500/5 overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center gap-2 px-4 py-3 text-sm font-medium text-purple-400 hover:bg-purple-500/10 transition-colors"
      >
        <BrainCircuit className="w-4 h-4" />
        <span>Thinking{isStreaming ? '...' : ''}</span>
        <ChevronDown className={cn("w-4 h-4 ml-auto transition-transform", isOpen && "rotate-180")} />
      </button>
      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <div className="px-4 pb-4 text-sm text-foreground/70 whitespace-pre-wrap leading-relaxed max-h-60 overflow-y-auto custom-scrollbar">
              {content}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
