"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { motion } from "framer-motion";
import {
  TrendingUp,
  FlaskRound,
  Cpu,
  Palette,
  RefreshCw,
  Loader2,
  ExternalLink,
  ArrowRight,
} from "lucide-react";
import { cn } from "../lib/utils";

interface DiscoverArticle {
  title: string;
  url: string;
  thumbnail?: string;
  description?: string;
  source?: string;
}

const CATEGORIES = [
  { id: 'trending', label: 'Trending', icon: TrendingUp },
  { id: 'science', label: 'Science', icon: FlaskRound },
  { id: 'technology', label: 'Technology', icon: Cpu },
  { id: 'culture', label: 'Culture', icon: Palette },
] as const;

interface DiscoverPageProps {
  onStartResearch: (query: string) => void;
}

export default function DiscoverPage({ onStartResearch }: DiscoverPageProps) {
  const [category, setCategory] = useState<string>('trending');
  const [articles, setArticles] = useState<DiscoverArticle[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchArticles = useCallback(async (cat: string) => {
    setLoading(true);
    try {
      const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
      const resp = await fetch(`${apiBase}/v1/discover?category=${encodeURIComponent(cat)}`);
      if (resp.ok) {
        const data = await resp.json();
        // Backend returns "items" with fields: title, url, snippet, source
        const items = data.items || data.articles || [];
        setArticles(items.map((item: any) => ({
          title: item.title || "",
          url: item.url || "",
          description: item.snippet || item.description || "",
          thumbnail: item.thumbnail_url || item.thumbnail || undefined,
          source: item.source || "",
        })));
      }
    } catch {
      setArticles([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchArticles(category);
  }, [category, fetchArticles]);

  return (
    <div className="max-w-4xl mx-auto px-4 md:px-8 py-8">
      <div className="mb-8">
        <h2 className="text-2xl font-semibold text-foreground mb-2">Discover</h2>
        <p className="text-foreground/50 text-sm">Explore what's happening around the world.</p>
      </div>

      {/* Category Tabs */}
      <div className="flex gap-2 mb-8 overflow-x-auto pb-2">
        {CATEGORIES.map(cat => (
          <button
            key={cat.id}
            onClick={() => setCategory(cat.id)}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all whitespace-nowrap",
              category === cat.id
                ? "bg-accent/15 text-accent border border-accent/30"
                : "bg-foreground/5 text-foreground/60 hover:text-foreground hover:bg-foreground/10 border border-foreground/10"
            )}
          >
            <cat.icon className="w-4 h-4" />
            {cat.label}
          </button>
        ))}
        <button
          onClick={() => fetchArticles(category)}
          disabled={loading}
          className="p-2 rounded-full bg-foreground/5 hover:bg-foreground/10 text-foreground/50 hover:text-foreground border border-foreground/10 transition-all"
          title="Refresh"
        >
          <RefreshCw className={cn("w-4 h-4", loading && "animate-spin")} />
        </button>
      </div>

      {/* Articles Grid */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-6 h-6 animate-spin text-accent" />
          <span className="ml-2 text-foreground/50">Loading articles...</span>
        </div>
      ) : articles.length === 0 ? (
        <div className="text-center py-16 text-foreground/40">
          <p>No articles found. Try refreshing or selecting a different category.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {articles.map((article, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="group rounded-xl border border-foreground/10 hover:border-accent/20 bg-foreground/5 hover:bg-foreground/[0.07] transition-all overflow-hidden"
            >
              {article.thumbnail && (
                <div className="aspect-[2/1] overflow-hidden">
                  <img
                    src={article.thumbnail}
                    alt={article.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                    loading="lazy"
                  />
                </div>
              )}
              <div className="p-4">
                <a
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm font-semibold text-foreground group-hover:text-accent transition-colors line-clamp-2 no-underline flex items-start gap-1"
                >
                  {article.title}
                  <ExternalLink className="w-3 h-3 shrink-0 opacity-0 group-hover:opacity-50 transition-opacity mt-0.5" />
                </a>
                {article.description && (
                  <p className="text-xs text-foreground/50 mt-2 line-clamp-2">{article.description}</p>
                )}
                <div className="flex items-center justify-between mt-3">
                  {article.source && (
                    <span className="text-[10px] text-foreground/40">{article.source}</span>
                  )}
                  <button
                    onClick={() => onStartResearch(article.title)}
                    className="flex items-center gap-1 text-[10px] font-medium text-accent/70 hover:text-accent transition-colors"
                  >
                    Research this
                    <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );
}
