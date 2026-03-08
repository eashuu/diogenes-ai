"use client";

import React from 'react';

export default function ResearchSteps({ phase }: { phase: string }) {
  return (
    <div className="py-2 space-y-4">
      <div className="flex items-center gap-3 text-accent animate-pulse">
        <div className="h-4 w-4 relative">
          <div className="absolute inset-0 rounded-full border-2 border-accent/30"></div>
          <div className="absolute inset-0 rounded-full border-2 border-accent border-t-transparent animate-spin"></div>
        </div>
        <span className="text-sm font-medium tracking-wide">{phase}</span>
      </div>
    </div>
  );
}
