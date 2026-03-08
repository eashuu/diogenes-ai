"use client";

import React, { useState, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from "framer-motion";
import { X, ExternalLink, Search, Loader2 } from "lucide-react";

interface ImageResult {
  url: string;
  thumbnail: string;
  title: string;
  source: string;
}

interface SearchImagesProps {
  query: string;
  isVisible: boolean;
}

export default function SearchImages({ query, isVisible }: SearchImagesProps) {
  const [images, setImages] = useState<ImageResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);
  const hasFetched = useRef(false);

  const fetchImages = useCallback(async () => {
    if (!query || hasFetched.current) return;
    hasFetched.current = true;
    setLoading(true);
    try {
      const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
      const resp = await fetch(`${apiBase}/v1/search/images?q=${encodeURIComponent(query)}&limit=12`);
      if (resp.ok) {
        const data = await resp.json();
        setImages(data.results || []);
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
      fetchImages();
    }
  }, [isVisible, query, fetchImages]);

  if (!isVisible) return null;

  return (
    <div className="mt-6">
      <div className="flex items-center gap-2 text-foreground text-xs uppercase tracking-widest font-semibold mb-3">
        <Search className="w-3 h-3" />
        Images
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-foreground/50 text-sm">
          <Loader2 className="w-4 h-4 animate-spin" />
          Searching images...
        </div>
      ) : images.length === 0 ? (
        <p className="text-foreground/40 text-sm">No images found.</p>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {images.map((img, i) => (
              <button
                key={i}
                onClick={() => setLightboxIndex(i)}
                className="group relative aspect-square rounded-lg overflow-hidden border border-foreground/10 hover:border-accent/30 transition-all bg-foreground/5"
              >
                <img
                  src={img.thumbnail || img.url}
                  alt={img.title}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                  loading="lazy"
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent opacity-0 group-hover:opacity-100 transition-opacity">
                  <div className="absolute bottom-0 left-0 right-0 p-2">
                    <p className="text-white text-[10px] line-clamp-2">{img.title}</p>
                    <p className="text-white/60 text-[9px]">{img.source}</p>
                  </div>
                </div>
              </button>
            ))}
          </div>

          {/* Lightbox */}
          <AnimatePresence>
            {lightboxIndex !== null && images[lightboxIndex] && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 z-[200] flex items-center justify-center bg-black/80 backdrop-blur-sm"
                onClick={() => setLightboxIndex(null)}
              >
                <motion.div
                  initial={{ scale: 0.9 }}
                  animate={{ scale: 1 }}
                  exit={{ scale: 0.9 }}
                  className="relative max-w-4xl max-h-[85vh] m-4"
                  onClick={(e) => e.stopPropagation()}
                >
                  <img
                    src={images[lightboxIndex].url}
                    alt={images[lightboxIndex].title}
                    className="max-w-full max-h-[80vh] object-contain rounded-lg shadow-2xl"
                  />
                  <div className="absolute top-2 right-2 flex gap-2">
                    <a
                      href={images[lightboxIndex].url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-2 rounded-full bg-black/50 text-white hover:bg-black/70 transition-colors"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </a>
                    <button
                      onClick={() => setLightboxIndex(null)}
                      className="p-2 rounded-full bg-black/50 text-white hover:bg-black/70 transition-colors"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                  <p className="text-white text-sm mt-2 text-center">{images[lightboxIndex].title}</p>
                </motion.div>
              </motion.div>
            )}
          </AnimatePresence>
        </>
      )}
    </div>
  );
}
