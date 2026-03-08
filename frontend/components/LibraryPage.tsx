"use client";

import React, { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Search,
  Calendar,
  Trash2,
  ArrowLeft,
  Clock,
  MessageCircle,
  Download,
  Filter,
} from "lucide-react";
import { cn } from "../lib/utils";
import type { ChatSession } from "../lib/types";
import { getSessionGroup, SHARED_TRANSITION } from "../lib/types";

interface LibraryPageProps {
  sessions: ChatSession[];
  onSelectChat: (id: string) => void;
  onDeleteChat: (id: string) => void;
  onExportChat: (session: ChatSession) => void;
  onBack: () => void;
}

type SortMode = "newest" | "oldest" | "alphabetical";

export default function LibraryPage({
  sessions,
  onSelectChat,
  onDeleteChat,
  onExportChat,
  onBack,
}: LibraryPageProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [sortMode, setSortMode] = useState<SortMode>("newest");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const filteredSessions = useMemo(() => {
    let result = [...sessions];

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (s) =>
          s.title.toLowerCase().includes(q) ||
          s.messages.some((m) => m.content.toLowerCase().includes(q))
      );
    }

    switch (sortMode) {
      case "newest":
        result.sort((a, b) => b.createdAt - a.createdAt);
        break;
      case "oldest":
        result.sort((a, b) => a.createdAt - b.createdAt);
        break;
      case "alphabetical":
        result.sort((a, b) => a.title.localeCompare(b.title));
        break;
    }

    return result;
  }, [sessions, searchQuery, sortMode]);

  const groupedSessions = useMemo(() => {
    if (sortMode === "alphabetical") {
      return [{ title: "All Chats", items: filteredSessions }];
    }
    const groups: Record<string, ChatSession[]> = {};
    filteredSessions.forEach((s) => {
      const g = getSessionGroup(s.createdAt);
      if (!groups[g]) groups[g] = [];
      groups[g].push(s);
    });
    return Object.entries(groups).map(([title, items]) => ({ title, items }));
  }, [filteredSessions, sortMode]);

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleBulkDelete = () => {
    if (
      selectedIds.size > 0 &&
      confirm(`Delete ${selectedIds.size} conversation${selectedIds.size > 1 ? "s" : ""}? This cannot be undone.`)
    ) {
      selectedIds.forEach((id) => onDeleteChat(id));
      setSelectedIds(new Set());
    }
  };

  return (
    <div className="flex-1 w-full max-w-4xl mx-auto px-4 md:px-8 py-6 overflow-y-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <button
          onClick={onBack}
          className="p-2 rounded-lg hover:bg-foreground/10 text-foreground/60 hover:text-foreground transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="text-2xl font-serif font-medium text-foreground">Library</h1>
          <p className="text-sm text-foreground/50">
            {sessions.length} conversation{sessions.length !== 1 ? "s" : ""}
          </p>
        </div>
      </div>

      {/* Controls */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-foreground/40" />
          <input
            type="text"
            placeholder="Search conversations..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 bg-foreground/5 border border-foreground/10 rounded-xl text-sm text-foreground placeholder:text-foreground/30 focus:outline-none focus:border-accent/50"
          />
        </div>
        <div className="flex gap-2">
          <div className="flex bg-foreground/5 rounded-lg border border-foreground/10 p-0.5">
            {(["newest", "oldest", "alphabetical"] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => setSortMode(mode)}
                className={cn(
                  "px-3 py-1.5 rounded-md text-xs font-medium transition-all capitalize",
                  sortMode === mode
                    ? "bg-foreground/10 text-foreground"
                    : "text-foreground/50 hover:text-foreground"
                )}
              >
                {mode === "newest" ? "Newest" : mode === "oldest" ? "Oldest" : "A-Z"}
              </button>
            ))}
          </div>
          {selectedIds.size > 0 && (
            <button
              onClick={handleBulkDelete}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 text-xs font-medium transition-all"
            >
              <Trash2 className="w-3.5 h-3.5" />
              Delete ({selectedIds.size})
            </button>
          )}
        </div>
      </div>

      {/* Sessions */}
      {filteredSessions.length === 0 ? (
        <div className="text-center py-16">
          <MessageCircle className="w-12 h-12 text-foreground/20 mx-auto mb-4" />
          <p className="text-foreground/40 text-sm">
            {searchQuery ? "No conversations match your search." : "No conversations yet. Start a new chat!"}
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {groupedSessions.map((group) => (
            <div key={group.title}>
              <h3 className="text-xs font-semibold text-foreground/40 uppercase tracking-wider mb-3 px-1">
                {group.title}
              </h3>
              <div className="space-y-2">
                <AnimatePresence>
                  {group.items.map((session) => {
                    const msgCount = session.messages.length;
                    const date = new Date(session.createdAt);
                    const lastMsg = session.messages[session.messages.length - 1];
                    const preview = lastMsg
                      ? lastMsg.content.slice(0, 120) + (lastMsg.content.length > 120 ? "..." : "")
                      : "Empty conversation";

                    return (
                      <motion.div
                        key={session.id}
                        layout
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, x: -20 }}
                        className={cn(
                          "group flex items-start gap-3 p-4 rounded-xl border transition-all cursor-pointer",
                          selectedIds.has(session.id)
                            ? "bg-accent/5 border-accent/20"
                            : "bg-foreground/[0.02] border-foreground/5 hover:bg-foreground/5 hover:border-foreground/10"
                        )}
                      >
                        {/* Checkbox */}
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleSelect(session.id);
                          }}
                          className={cn(
                            "mt-1 w-4 h-4 rounded border-2 shrink-0 transition-all flex items-center justify-center",
                            selectedIds.has(session.id)
                              ? "bg-accent border-accent"
                              : "border-foreground/20 group-hover:border-foreground/40"
                          )}
                        >
                          {selectedIds.has(session.id) && (
                            <span className="text-background text-[10px] font-bold">✓</span>
                          )}
                        </button>

                        {/* Content */}
                        <div
                          className="flex-1 min-w-0"
                          onClick={() => onSelectChat(session.id)}
                        >
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-sm font-medium text-foreground truncate">
                              {session.title}
                            </span>
                            {session.mode && (
                              <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-foreground/5 text-foreground/50 capitalize shrink-0">
                                {session.mode}
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-foreground/40 line-clamp-2 mb-2">
                            {preview}
                          </p>
                          <div className="flex items-center gap-3 text-[11px] text-foreground/30">
                            <span className="flex items-center gap-1">
                              <Calendar className="w-3 h-3" />
                              {date.toLocaleDateString()}
                            </span>
                            <span className="flex items-center gap-1">
                              <Clock className="w-3 h-3" />
                              {date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                            </span>
                            <span className="flex items-center gap-1">
                              <MessageCircle className="w-3 h-3" />
                              {msgCount} msg{msgCount !== 1 ? "s" : ""}
                            </span>
                          </div>
                        </div>

                        {/* Actions */}
                        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              onExportChat(session);
                            }}
                            className="p-1.5 rounded-lg hover:bg-foreground/10 text-foreground/40 hover:text-foreground transition-colors"
                            title="Export as Markdown"
                          >
                            <Download className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              if (confirm("Delete this conversation?")) onDeleteChat(session.id);
                            }}
                            className="p-1.5 rounded-lg hover:bg-red-500/10 text-foreground/40 hover:text-red-400 transition-colors"
                            title="Delete"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </motion.div>
                    );
                  })}
                </AnimatePresence>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
