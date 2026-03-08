"use client";

import React from 'react';
import { motion, AnimatePresence } from "framer-motion";
import {
  Plus,
  PanelLeftClose,
  MoreHorizontal,
  Settings,
  Download,
  Trash2
} from "lucide-react";
import { cn } from "../lib/utils";
import type { ChatSession, UserSettings } from "../lib/types";
import { getSessionGroup, SHARED_TRANSITION } from "../lib/types";

interface SidebarProps {
  sessions: ChatSession[];
  activeChatId: string | null;
  isOpen: boolean;
  settings: UserSettings;
  isMobile?: boolean;
  onNewChat: () => void;
  onSelectChat: (id: string) => void;
  onClose: () => void;
  onOpenSettings: () => void;
  onExportData: () => void;
  onClearHistory: () => void;
}

const SIDEBAR_WIDTH = 260;

export default function Sidebar({
  sessions,
  activeChatId,
  isOpen,
  settings,
  isMobile = false,
  onNewChat,
  onSelectChat,
  onClose,
  onOpenSettings,
  onExportData,
  onClearHistory,
}: SidebarProps) {
  const [isUserMenuOpen, setIsUserMenuOpen] = React.useState(false);

  const groupedSessions = React.useMemo(() => {
    const groups: Record<string, ChatSession[]> = {};
    const order = ["Today", "Yesterday", "Previous 7 Days", "Previous 30 Days"];

    sessions.forEach(session => {
      const groupName = getSessionGroup(session.createdAt);
      if (!groups[groupName]) groups[groupName] = [];
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

    return sortedGroups.map(title => ({ title, items: groups[title] }));
  }, [sessions]);

  return (
    <>
      {/* Mobile backdrop */}
      <AnimatePresence>
        {isMobile && isOpen && (
          <motion.div
            key="sidebar-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 bg-black/40 backdrop-blur-sm z-[55]"
            onClick={onClose}
          />
        )}
      </AnimatePresence>

      <motion.aside
        initial={false}
        animate={{ width: isOpen ? SIDEBAR_WIDTH : 0, opacity: isOpen ? 1 : 0 }}
        transition={SHARED_TRANSITION}
        className={cn(
          "h-full bg-glass/40 backdrop-blur-3xl border-r border-foreground/5 flex flex-col overflow-hidden relative shadow-2xl shrink-0",
          isMobile ? "fixed left-0 top-0 z-[60]" : "z-50"
        )}
      >
      {/* Top */}
      <div className="p-3 flex items-center justify-between gap-2 shrink-0">
        <button
          onClick={onNewChat}
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
          onClick={onClose}
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
                        onClick={() => onSelectChat(session.id)}
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
              <button onClick={() => { onOpenSettings(); setIsUserMenuOpen(false); }} className="flex items-center gap-3 px-3 py-2 text-sm text-foreground hover:text-foreground hover:bg-foreground/10 rounded-lg transition-colors text-left">
                <Settings className="w-4 h-4" /><span>Settings</span>
              </button>
              <button onClick={() => { onExportData(); setIsUserMenuOpen(false); }} className="flex items-center gap-3 px-3 py-2 text-sm text-foreground hover:text-foreground hover:bg-foreground/10 rounded-lg transition-colors text-left">
                <Download className="w-4 h-4" /><span>Export Data</span>
              </button>
              <div className="h-px bg-foreground/5 my-1" />
              <button onClick={() => { onClearHistory(); setIsUserMenuOpen(false); }} className="flex items-center gap-3 px-3 py-2 text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-colors text-left">
                <Trash2 className="w-4 h-4" /><span>Clear History</span>
              </button>
            </motion.div>
          )}
        </AnimatePresence>
        <button onClick={() => setIsUserMenuOpen(!isUserMenuOpen)} className="w-full flex items-center justify-between group p-2 rounded-xl hover:bg-foreground/5 transition-colors">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-accent to-background border border-foreground/10 flex items-center justify-center shrink-0 shadow-sm overflow-hidden">
              <span className="text-xs font-bold text-foreground">{settings.username.slice(0, 1).toUpperCase()}</span>
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
    </>
  );
}
