"use client";

import React from 'react';
import { motion } from "framer-motion";
import { Sparkles, BookOpen, Code, Globe, Newspaper } from "lucide-react";
import { SHARED_TRANSITION } from "../lib/types";
import WeatherWidget from "./WeatherWidget";

const QUICK_SUGGESTIONS = [
  { icon: Sparkles, label: "Explain quantum computing", gradient: "from-purple-500/10 to-blue-500/10" },
  { icon: BookOpen, label: "Summarize the latest AI research", gradient: "from-green-500/10 to-teal-500/10" },
  { icon: Code, label: "Compare React vs Vue vs Svelte", gradient: "from-orange-500/10 to-red-500/10" },
  { icon: Globe, label: "What's happening in tech today?", gradient: "from-blue-500/10 to-cyan-500/10" },
  { icon: Newspaper, label: "Latest breakthroughs in medicine", gradient: "from-pink-500/10 to-rose-500/10" },
];

interface EmptyChatProps {
  onSuggestionClick?: (query: string) => void;
}

export default function EmptyChat({ onSuggestionClick }: EmptyChatProps) {
  return (
    <motion.div
      key="landing-title"
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95, y: -20 }}
      transition={SHARED_TRANSITION}
      className="text-center mb-6 md:mb-8 w-full"
    >
      <h1 className="text-3xl md:text-6xl font-serif font-medium tracking-tight text-foreground mb-2 md:mb-4">
        Where knowledge begins
      </h1>
      <p className="text-foreground/70 text-base md:text-lg mb-6">
        Ask anything. We'll search the world for you.
      </p>

      {/* Quick Suggestions */}
      {onSuggestionClick && (
        <div className="flex flex-wrap justify-center gap-2 mb-6 max-w-2xl mx-auto">
          {QUICK_SUGGESTIONS.map((s) => (
            <button
              key={s.label}
              onClick={() => onSuggestionClick(s.label)}
              className="flex items-center gap-2 px-3 py-2 rounded-xl text-xs md:text-sm text-foreground/70 hover:text-foreground bg-foreground/5 hover:bg-foreground/10 border border-foreground/5 hover:border-foreground/10 transition-all"
            >
              <s.icon className="w-3.5 h-3.5 text-accent/70" />
              <span className="whitespace-nowrap">{s.label}</span>
            </button>
          ))}
        </div>
      )}

      {/* Weather Widget */}
      <div className="max-w-sm mx-auto">
        <WeatherWidget />
      </div>
    </motion.div>
  );
}
