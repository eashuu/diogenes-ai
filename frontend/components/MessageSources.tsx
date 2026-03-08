"use client";

import React from 'react';
import type { Source } from "../lib/api-types";
import { getDomain } from "../lib/types";

export const SidebarSourceCard: React.FC<{ source: Source; index: number }> = ({ source, index }) => {
  const domain = source.domain || getDomain(source.url);

  return (
    <a
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex flex-col gap-1 p-3 rounded-lg hover:bg-foreground/5 transition-colors group no-underline border border-transparent hover:border-foreground/5"
    >
      <div className="flex items-center gap-2">
        <div className="w-4 h-4 rounded-full bg-foreground/10 flex items-center justify-center shrink-0 overflow-hidden">
          <img
            src={`https://www.google.com/s2/favicons?domain=${encodeURIComponent(domain)}&sz=64`}
            alt=""
            className="w-full h-full object-cover opacity-70 group-hover:opacity-100 transition-opacity"
            onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
          />
        </div>
        <span className="text-xs font-medium text-foreground truncate">{domain}</span>
        <span className="text-[10px] text-foreground/80 ml-auto">#{index + 1}</span>
      </div>
      <div className="text-sm font-semibold text-foreground leading-tight line-clamp-2 group-hover:text-accent transition-colors">
        {source.title}
      </div>
      <div className="text-xs text-foreground/80 line-clamp-2 mt-1">
        {source.url}
      </div>
    </a>
  );
};

export const CitationChip = ({ index, source }: { index: number; source?: Source }) => {
  const domain = source ? (source.domain || getDomain(source.url)) : 'source';

  return (
    <a
      href={source?.url || '#'}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1.5 px-2 py-0.5 mx-1 -translate-y-0.5 rounded-full bg-accent/10 hover:bg-accent/20 text-[10px] font-medium text-accent hover:text-accent/80 no-underline transition-all select-none border border-accent/20 align-middle whitespace-nowrap"
      title={source?.title || `Source ${index}`}
      onClick={(e) => e.stopPropagation()}
    >
      <span className="opacity-70 text-[9px] font-bold">[{index}]</span>
      <div className="flex items-center gap-1 max-w-[120px]">
        {source?.url && (
          <img
            src={`https://www.google.com/s2/favicons?domain=${encodeURIComponent(domain)}&sz=64`}
            alt=""
            className="w-2.5 h-2.5 rounded-full opacity-80"
            onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
          />
        )}
        <span className="truncate">{domain}</span>
      </div>
    </a>
  );
};
