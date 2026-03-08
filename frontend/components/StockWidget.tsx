"use client";

import React, { useState, useEffect, useCallback } from "react";
import { TrendingUp, TrendingDown, RefreshCw, Search } from "lucide-react";
import { cn } from "../lib/utils";

interface StockQuote {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  high: number;
  low: number;
  open: number;
  previousClose: number;
  volume: string;
}

interface StockWidgetProps {
  className?: string;
  defaultSymbol?: string;
}

const POPULAR_TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"];

async function fetchStockQuote(symbol: string): Promise<StockQuote | null> {
  try {
    // Use the backend stock widget endpoint
    const resp = await fetch(`/api/v1/widgets/stock?symbol=${encodeURIComponent(symbol)}`);
    if (!resp.ok) return null;
    return await resp.json();
  } catch {
    return null;
  }
}

export default function StockWidget({ className, defaultSymbol }: StockWidgetProps) {
  const [quote, setQuote] = useState<StockQuote | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchInput, setSearchInput] = useState(defaultSymbol ?? "");
  const [activeSymbol, setActiveSymbol] = useState(defaultSymbol ?? "");

  const loadQuote = useCallback(async (symbol: string) => {
    if (!symbol.trim()) return;
    setLoading(true);
    setError(null);
    const data = await fetchStockQuote(symbol.trim().toUpperCase());
    if (data) {
      setQuote(data);
      setActiveSymbol(symbol.trim().toUpperCase());
    } else {
      setError("Could not load stock data");
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    if (defaultSymbol) {
      loadQuote(defaultSymbol);
    }
  }, [defaultSymbol, loadQuote]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    loadQuote(searchInput);
  };

  const isPositive = quote ? quote.change >= 0 : true;

  return (
    <div className={cn("bg-glass/30 backdrop-blur-xl border border-foreground/10 rounded-2xl p-5 md:p-6", className)}>
      {/* Search bar */}
      <form onSubmit={handleSearch} className="flex items-center gap-2 mb-4">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-foreground/40" />
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search ticker (e.g. AAPL)"
            maxLength={10}
            className="w-full pl-8 pr-3 py-2 text-xs bg-foreground/5 border border-foreground/10 rounded-lg text-foreground placeholder:text-foreground/30 focus:outline-none focus:ring-1 focus:ring-accent/50"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !searchInput.trim()}
          className="px-3 py-2 text-xs bg-accent/20 hover:bg-accent/30 text-accent rounded-lg transition-colors disabled:opacity-40"
        >
          Go
        </button>
      </form>

      {/* Quick tickers */}
      {!quote && !loading && !error && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {POPULAR_TICKERS.map((t) => (
            <button
              key={t}
              onClick={() => {
                setSearchInput(t);
                loadQuote(t);
              }}
              className="px-2.5 py-1 text-[10px] font-medium text-foreground/50 bg-foreground/5 hover:bg-foreground/10 rounded-md transition-colors"
            >
              {t}
            </button>
          ))}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="animate-pulse space-y-3">
          <div className="h-4 w-20 bg-foreground/10 rounded" />
          <div className="h-10 w-28 bg-foreground/10 rounded" />
          <div className="flex gap-4">
            <div className="h-3 w-16 bg-foreground/5 rounded" />
            <div className="h-3 w-16 bg-foreground/5 rounded" />
          </div>
        </div>
      )}

      {/* Error */}
      {error && !loading && (
        <p className="text-xs text-foreground/40">{error}</p>
      )}

      {/* Quote display */}
      {quote && !loading && (
        <>
          {/* Header */}
          <div className="flex items-center justify-between mb-2">
            <div>
              <span className="text-sm font-semibold text-foreground">{quote.symbol}</span>
              {quote.name && (
                <span className="ml-2 text-xs text-foreground/50">{quote.name}</span>
              )}
            </div>
            <button
              onClick={() => loadQuote(activeSymbol)}
              className="p-1.5 rounded-full hover:bg-foreground/10 text-foreground/40 hover:text-foreground transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Price */}
          <div className="flex items-end gap-3 mb-3">
            <div className="text-3xl font-light text-foreground tracking-tight">
              ${quote.price.toFixed(2)}
            </div>
            <div className={cn("flex items-center gap-1 text-sm font-medium pb-1", isPositive ? "text-green-500" : "text-red-500")}>
              {isPositive ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
              {isPositive ? "+" : ""}{quote.change.toFixed(2)} ({isPositive ? "+" : ""}{quote.changePercent.toFixed(2)}%)
            </div>
          </div>

          {/* Stats grid */}
          <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-xs text-foreground/50">
            <div className="flex justify-between">
              <span>Open</span>
              <span className="text-foreground/70">${quote.open.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span>Prev Close</span>
              <span className="text-foreground/70">${quote.previousClose.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span>High</span>
              <span className="text-foreground/70">${quote.high.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span>Low</span>
              <span className="text-foreground/70">${quote.low.toFixed(2)}</span>
            </div>
            {quote.volume && (
              <div className="flex justify-between col-span-2">
                <span>Volume</span>
                <span className="text-foreground/70">{quote.volume}</span>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
