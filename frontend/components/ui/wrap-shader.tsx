
import React, { ReactNode } from 'react';
import { Warp } from "@paper-design/shaders-react";
import { motion } from "framer-motion";
import { useTheme } from "../../lib/theme-provider";

interface WarpShaderHeroProps {
  children?: ReactNode;
  isChatting?: boolean;
}

const THEME_COLORS = {
  diogenes: [
    "hsl(0, 100%, 5%)",     // Very Deep Blood Red
    "hsl(0, 100%, 15%)",    // Dark Crimson
    "hsl(0, 90%, 30%)",     // Rich Red
    "hsl(350, 100%, 50%)"   // Bright Vibrant Red
  ],
  light: [
    "hsl(0, 0%, 100%)",      // White
    "hsl(210, 40%, 96%)",    // Very Light Blue/Gray
    "hsl(210, 60%, 90%)",    // Light Blue
    "hsl(210, 80%, 85%)"     // Soft Blue Accent
  ],
  dark: [
    "hsl(240, 10%, 4%)",     // Almost Black
    "hsl(240, 10%, 10%)",    // Dark Zinc
    "hsl(240, 20%, 15%)",    // Deep Cool Gray
    "hsl(240, 30%, 20%)"     // Lighter Cool Gray
  ]
};

const THEME_GRADIENTS = {
  diogenes: "bg-[radial-gradient(circle_at_center,_var(--tw-gradient-stops))] from-[#450a0a] via-[#1e0000] to-[#0a0000]",
  light: "bg-white",
  dark: "bg-zinc-950"
};

export default function WarpShaderHero({ children, isChatting = false }: WarpShaderHeroProps) {
  const { theme } = useTheme();

  return (
    <main className={`relative min-h-screen w-full overflow-hidden transition-colors duration-700 ${THEME_GRADIENTS[theme]}`}>
      {/* Base Shader Layer - Always present */}
      <div className="absolute inset-0 transition-opacity duration-1000">
        <Warp
          style={{ height: "100%", width: "100%" }}
          proportion={0.45}
          softness={1}
          distortion={0.3}
          swirl={1.0}
          swirlIterations={12}
          shape="checks"
          shapeScale={0.12}
          scale={1.1}
          rotation={0}
          speed={0.6}
          colors={THEME_COLORS[theme]}
        />
      </div>

      {/* Glassy Barrier / Blur Layer - Activated only after chat starts */}
      <motion.div 
        initial={{ backdropFilter: "blur(0px)", opacity: 0 }}
        animate={{ 
          backdropFilter: isChatting ? "blur(4px)" : "blur(0px)",
          opacity: isChatting ? 1 : 0 
        }}
        transition={{ duration: 1.2, ease: "easeOut" }}
        className="absolute inset-0 bg-background/10 pointer-events-none z-10"
      />

      {/* Noise Layers - Fades in when chatting. Hidden in Light mode for cleanliness */}
      {theme !== 'light' && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: isChatting ? 0.4 : 0 }}
            transition={{ duration: 1.5, ease: "easeOut", delay: 0.2 }}
            className="absolute inset-0 pointer-events-none mix-blend-overlay z-15"
            style={{ 
              backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
              backgroundRepeat: 'repeat'
            }}
          />

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: isChatting ? 0.15 : 0 }}
            transition={{ duration: 1.5, ease: "easeOut", delay: 0.3 }}
            className="absolute inset-0 pointer-events-none mix-blend-screen z-15"
            style={{ 
              backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 400 400' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.35' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
              backgroundRepeat: 'repeat'
            }}
          />
        </>
      )}

      {/* Content Layer */}
      <div className="relative z-20 h-full w-full">
        {children}
      </div>

      {/* Static Overlays - Only for Diogenes Theme */}
      {theme === 'diogenes' && (
        <>
          <div className="absolute inset-0 bg-gradient-to-t from-red-950/40 via-transparent to-red-900/10 pointer-events-none z-10" />
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,rgba(0,0,0,0.6)_100%)] pointer-events-none z-30" />
        </>
      )}
    </main>
  );
}
