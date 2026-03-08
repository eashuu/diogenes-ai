"use client";

import React from 'react';
import { Flame, Sun, Moon, Compass, BookOpen, Menu } from "lucide-react";
import { cn } from "../lib/utils";
import { useTheme } from "../lib/theme-provider";

interface NavbarProps {
  hasSidebarGap: boolean;
  view?: 'chat' | 'discover' | 'library';
  onViewChange?: (view: 'chat' | 'discover' | 'library') => void;
  onToggleSidebar?: () => void;
  isMobile?: boolean;
}

export default function Navbar({ hasSidebarGap, view, onViewChange, onToggleSidebar, isMobile }: NavbarProps) {
  const { theme, setTheme } = useTheme();

  return (
    <header className="w-full h-14 md:h-16 bg-transparent flex items-center justify-between px-4 md:px-6 z-40 shrink-0 sticky top-0 pointer-events-none">
      <div className="flex items-center gap-2 md:gap-4 pointer-events-auto">
        {isMobile && onToggleSidebar ? (
          <button onClick={onToggleSidebar} className="p-2 rounded-lg hover:bg-foreground/10 transition-colors">
            <Menu className="w-5 h-5 text-foreground" />
          </button>
        ) : (
          hasSidebarGap && <div className="w-8" />
        )}
        <span className="text-sm font-semibold tracking-wider text-foreground uppercase">Diogenes</span>
        {onViewChange && (
          <>
            <button
              onClick={() => onViewChange(view === 'discover' ? 'chat' : 'discover')}
              className={cn(
                "flex items-center gap-1.5 px-2.5 md:px-3 py-1.5 rounded-full text-xs font-medium transition-all",
                view === 'discover'
                  ? "bg-accent/15 text-accent border border-accent/30"
                  : "bg-foreground/5 text-foreground/60 hover:text-foreground hover:bg-foreground/10 border border-foreground/10"
              )}
            >
              <Compass className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Discover</span>
            </button>
            <button
              onClick={() => onViewChange(view === 'library' ? 'chat' : 'library')}
              className={cn(
                "flex items-center gap-1.5 px-2.5 md:px-3 py-1.5 rounded-full text-xs font-medium transition-all",
                view === 'library'
                  ? "bg-accent/15 text-accent border border-accent/30"
                  : "bg-foreground/5 text-foreground/60 hover:text-foreground hover:bg-foreground/10 border border-foreground/10"
              )}
            >
              <BookOpen className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Library</span>
            </button>
          </>
        )}
      </div>
      <div className="flex bg-foreground/5 backdrop-blur-md rounded-full p-0.5 md:p-1 border border-foreground/10 pointer-events-auto">
        <button onClick={() => setTheme('diogenes')} className={cn("p-1.5 md:p-2 rounded-full", theme === 'diogenes' ? "bg-foreground/20 text-accent" : "text-foreground")}><Flame className="w-4 h-4" /></button>
        <button onClick={() => setTheme('light')} className={cn("p-1.5 md:p-2 rounded-full", theme === 'light' ? "bg-foreground/20 text-accent" : "text-foreground")}><Sun className="w-4 h-4" /></button>
        <button onClick={() => setTheme('dark')} className={cn("p-1.5 md:p-2 rounded-full", theme === 'dark' ? "bg-foreground/20 text-accent" : "text-foreground")}><Moon className="w-4 h-4" /></button>
      </div>
    </header>
  );
}
