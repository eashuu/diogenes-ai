
"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { cn } from "../../lib/utils";

export function PlaceholdersAndVanishInput({
  placeholders,
  onChange,
  onSubmit,
  leftAction,
  className,
}: {
  placeholders: string[];
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
  leftAction?: React.ReactNode;
  className?: string;
}) {
  const [currentPlaceholder, setCurrentPlaceholder] = useState(0);

  // Interval for placeholder rotation
  const intervalRef = useRef<any>(null);
  const startAnimation = () => {
    intervalRef.current = setInterval(() => {
      setCurrentPlaceholder((prev) => (prev + 1) % placeholders.length);
    }, 3000);
  };
  
  const handleVisibilityChange = () => {
    if (document.visibilityState !== "visible" && intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    } else if (document.visibilityState === "visible") {
      startAnimation();
    }
  };

  useEffect(() => {
    if (currentPlaceholder >= placeholders.length) {
      setCurrentPlaceholder(0);
    }
    startAnimation();
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [placeholders]);

  const canvasRef = useRef<HTMLCanvasElement>(null);
  const formRef = useRef<HTMLFormElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [value, setValue] = useState("");
  const [animating, setAnimating] = useState(false);
  const newDataRef = useRef<any[]>([]);

  // Constants for layout
  const LEFT_OFFSET = leftAction ? 52 : 20;

  const draw = useCallback((inputValue: string) => {
    if (!inputRef.current || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d", { willReadFrequently: true });
    if (!ctx) return;

    const rect = inputRef.current.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return; // Prevent IndexSizeError

    canvas.width = rect.width;
    canvas.height = rect.height;
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    const computedStyles = getComputedStyle(inputRef.current);
    const fontSize = parseFloat(computedStyles.getPropertyValue("font-size")) || 16;
    const fontFamily = computedStyles.fontFamily || "sans-serif";
    const color = computedStyles.color;

    ctx.font = `${fontSize}px ${fontFamily}`;
    ctx.fillStyle = color;
    ctx.textBaseline = "middle";
    
    ctx.fillText(inputValue, LEFT_OFFSET, canvas.height / 2);

    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const pixelData = imageData.data;
    const newData: any[] = [];

    for (let t = 0; t < canvas.height; t++) {
      let i = 4 * t * canvas.width;
      for (let n = 0; n < canvas.width; n++) {
        let e = i + 4 * n;
        // Check alpha channel (> 0) to ensure we catch black text too
        if (pixelData[e + 3] > 0) {
          newData.push({
            x: n,
            y: t,
            color: [
              pixelData[e],
              pixelData[e + 1],
              pixelData[e + 2],
              pixelData[e + 3],
            ],
          });
        }
      }
    }

    newDataRef.current = newData.map(({ x, y, color }) => ({
      x,
      y,
      r: 1,
      color: `rgba(${color[0]}, ${color[1]}, ${color[2]}, ${color[3]})`,
    }));
  }, [LEFT_OFFSET]);
  
  const animate = (start: number, text: string) => {
    const animateFrame = (pos: number = 0) => {
      requestAnimationFrame(() => {
        const newArr = [];
        for (let i = 0; i < newDataRef.current.length; i++) {
          const current = newDataRef.current[i];
          if (current.x < pos) {
            newArr.push(current);
          } else {
            if (current.r <= 0) {
              current.r = 0;
              continue;
            }
            current.x += Math.random() > 0.5 ? 1 : -1;
            current.y += Math.random() > 0.5 ? 1 : -1;
            current.r -= 0.05 * Math.random();
            newArr.push(current);
          }
        }
        newDataRef.current = newArr;
        
        const ctx = canvasRef.current?.getContext("2d");
        const inputEl = inputRef.current;
        
        if (ctx && canvasRef.current && inputEl) {
          ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);
          
          // 1. Draw Static Text (Clipped) for high performance
          // The static text part is x <= pos.
          ctx.save();
          ctx.beginPath();
          ctx.rect(0, 0, Math.max(0, pos), canvasRef.current.height);
          ctx.clip();
          
          const computedStyles = getComputedStyle(inputEl);
          ctx.font = `${parseFloat(computedStyles.fontSize)}px ${computedStyles.fontFamily}`;
          ctx.fillStyle = computedStyles.color;
          ctx.textBaseline = "middle";
          ctx.fillText(text, LEFT_OFFSET, canvasRef.current.height / 2);
          ctx.restore();

          // 2. Draw Particles
          newDataRef.current.forEach((t) => {
            const { x, y, r, color } = t;
            if (x > pos) {
              ctx.beginPath();
              ctx.rect(x, y, r, r);
              ctx.fillStyle = color;
              ctx.fill();
            }
          });
        }

        if (newDataRef.current.length > 0) {
          animateFrame(pos - 8);
        } else {
          setValue("");
          setAnimating(false);
          // Final clear
          if (ctx) ctx.clearRect(0, 0, canvasRef.current!.width, canvasRef.current!.height);
        }
      });
    };
    animateFrame(start);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !animating) {
      vanishAndSubmit();
    }
  };

  const vanishAndSubmit = () => {
    const currentValue = inputRef.current?.value || "";
    if (currentValue && inputRef.current) {
      setAnimating(true);
      draw(currentValue);

      const maxX = newDataRef.current.reduce(
        (prev, current) => (current.x > prev ? current.x : prev),
        0
      );
      animate(maxX, currentValue);
    }
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    vanishAndSubmit();
    onSubmit && onSubmit(e);
  };

  return (
    <form
      ref={formRef}
      className={cn(
        "w-full relative mx-auto bg-foreground/5 backdrop-blur-xl h-12 rounded-full shadow-sm transition-all duration-200 border border-foreground/10 overflow-hidden flex items-center group",
        "hover:border-accent/30 focus-within:border-accent/50 focus-within:ring-1 focus-within:ring-accent/20",
        className
      )}
      onSubmit={handleSubmit}
    >
      {/* Left Action Area */}
      {leftAction && (
         <div className="absolute left-0 top-0 bottom-0 w-[52px] z-50 flex items-center justify-center bg-foreground/0">
            {leftAction}
         </div>
      )}
      
      <div className="relative w-full h-full flex items-center overflow-hidden">
        {/* Particle Canvas */}
        <canvas
          className={cn(
            "absolute inset-0 pointer-events-none w-full h-full z-10", 
            !animating ? "opacity-0" : "opacity-100"
          )}
          ref={canvasRef}
        />

        {/* The actual input */}
        <input
          onChange={(e) => {
            if (!animating) {
              setValue(e.target.value);
              onChange && onChange(e);
            }
          }}
          onKeyDown={handleKeyDown}
          ref={inputRef}
          value={value}
          type="text"
          className={cn(
            "w-full h-full bg-transparent text-sm sm:text-base text-foreground border-none focus:outline-none focus:ring-0 placeholder:text-transparent z-20 relative",
            animating && "text-transparent caret-transparent",
            leftAction ? "pl-[52px]" : "pl-5",
            "pr-12"
          )}
        />

        {/* Placeholders */}
        <div 
          className={cn(
            "absolute inset-y-0 flex items-center pointer-events-none overflow-hidden right-12 z-0",
            leftAction ? "left-[52px]" : "left-5"
          )}
        >
          <AnimatePresence mode="wait">
            {!value && (
              <motion.p
                initial={{ y: 5, opacity: 0 }}
                key={`current-placeholder-${currentPlaceholder}`}
                animate={{ y: 0, opacity: 1 }}
                exit={{ y: -10, opacity: 0 }}
                transition={{ duration: 0.3, ease: "linear" }}
                className="text-foreground/40 text-sm sm:text-base font-normal truncate w-full"
              >
                {placeholders[currentPlaceholder]}
              </motion.p>
            )}
          </AnimatePresence>
        </div>

        {/* Submit Button */}
        <button
          disabled={!value}
          type="submit"
          className="absolute right-2 h-8 w-8 z-50 rounded-full flex items-center justify-center transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-foreground/10 text-foreground"
        >
          <motion.svg
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="h-4 w-4"
          >
            <path stroke="none" d="M0 0h24v24H0z" fill="none" />
            <motion.path
              d="M5 12l14 0"
              initial={{
                strokeDasharray: "50%",
                strokeDashoffset: "50%",
              }}
              animate={{
                strokeDashoffset: value ? 0 : "50%",
              }}
              transition={{
                duration: 0.3,
                ease: "linear",
              }}
            />
            <path d="M13 18l6 -6" />
            <path d="M13 6l6 6" />
          </motion.svg>
        </button>
      </div>
    </form>
  );
}
