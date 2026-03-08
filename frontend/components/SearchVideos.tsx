"use client";

import React, { useState, useCallback, useRef } from 'react';
import { Search, Loader2, ExternalLink, Play } from "lucide-react";

interface VideoResult {
  url: string;
  thumbnail: string;
  title: string;
  source: string;
  duration?: string;
}

interface SearchVideosProps {
  query: string;
  isVisible: boolean;
}

export default function SearchVideos({ query, isVisible }: SearchVideosProps) {
  const [videos, setVideos] = useState<VideoResult[]>([]);
  const [loading, setLoading] = useState(false);
  const hasFetched = useRef(false);

  const fetchVideos = useCallback(async () => {
    if (!query || hasFetched.current) return;
    hasFetched.current = true;
    setLoading(true);
    try {
      const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
      const resp = await fetch(`${apiBase}/v1/search/videos?q=${encodeURIComponent(query)}&limit=8`);
      if (resp.ok) {
        const data = await resp.json();
        setVideos(data.results || []);
      }
    } catch {
      // Silently fail
    } finally {
      setLoading(false);
    }
  }, [query]);

  React.useEffect(() => {
    if (isVisible && query) {
      hasFetched.current = false;
      fetchVideos();
    }
  }, [isVisible, query, fetchVideos]);

  if (!isVisible) return null;

  return (
    <div className="mt-6">
      <div className="flex items-center gap-2 text-foreground text-xs uppercase tracking-widest font-semibold mb-3">
        <Play className="w-3 h-3" />
        Videos
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-foreground/50 text-sm">
          <Loader2 className="w-4 h-4 animate-spin" />
          Searching videos...
        </div>
      ) : videos.length === 0 ? (
        <p className="text-foreground/40 text-sm">No videos found.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {videos.map((video, i) => (
            <a
              key={i}
              href={video.url}
              target="_blank"
              rel="noopener noreferrer"
              className="group flex gap-3 rounded-lg overflow-hidden border border-foreground/10 hover:border-accent/30 transition-all bg-foreground/5 p-2"
            >
              <div className="relative w-32 h-20 rounded-md overflow-hidden bg-foreground/10 shrink-0">
                {video.thumbnail ? (
                  <img
                    src={video.thumbnail}
                    alt={video.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    loading="lazy"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-foreground/30">
                    <Play className="w-8 h-8" />
                  </div>
                )}
                {video.duration && (
                  <span className="absolute bottom-1 right-1 text-[9px] font-mono bg-black/70 text-white px-1 rounded">
                    {video.duration}
                  </span>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground line-clamp-2 group-hover:text-accent transition-colors">
                  {video.title}
                </p>
                <p className="text-[10px] text-foreground/50 mt-1 flex items-center gap-1">
                  {video.source}
                  <ExternalLink className="w-2.5 h-2.5" />
                </p>
              </div>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
