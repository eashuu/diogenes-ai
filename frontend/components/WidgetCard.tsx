"use client";

import React from "react";
import { Calculator, ArrowRight, Ruler, BookOpen } from "lucide-react";
import { cn } from "../lib/utils";

type WidgetType = "calculator" | "unit_conversion" | "definition";

interface WidgetResult {
  type: WidgetType;
  expression?: string;
  result?: string;
  from_unit?: string;
  to_unit?: string;
  from_value?: number;
  to_value?: number;
  word?: string;
  definition?: string;
}

interface WidgetCardProps {
  widget: WidgetResult;
  className?: string;
}

const ICONS: Record<WidgetType, React.ElementType> = {
  calculator: Calculator,
  unit_conversion: Ruler,
  definition: BookOpen,
};

const LABELS: Record<WidgetType, string> = {
  calculator: "Calculator",
  unit_conversion: "Unit Conversion",
  definition: "Definition",
};

export default function WidgetCard({ widget, className }: WidgetCardProps) {
  const Icon = ICONS[widget.type] ?? Calculator;
  const label = LABELS[widget.type] ?? "Widget";

  return (
    <div
      className={cn(
        "bg-glass/30 backdrop-blur-xl border border-foreground/10 rounded-2xl p-4 md:p-5",
        className
      )}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-3 text-foreground/50">
        <Icon className="w-4 h-4 text-accent/70" />
        <span className="text-xs font-medium uppercase tracking-wider">{label}</span>
      </div>

      {/* Calculator result */}
      {widget.type === "calculator" && widget.expression && widget.result && (
        <div className="space-y-1">
          <div className="text-sm text-foreground/60 font-mono">{widget.expression}</div>
          <div className="text-3xl font-light text-foreground tracking-tight font-mono">
            = {widget.result}
          </div>
        </div>
      )}

      {/* Unit conversion */}
      {widget.type === "unit_conversion" && (
        <div className="flex items-center gap-3">
          <div className="text-center">
            <div className="text-2xl font-light text-foreground tracking-tight">{widget.from_value}</div>
            <div className="text-xs text-foreground/50 mt-1">{widget.from_unit}</div>
          </div>
          <ArrowRight className="w-5 h-5 text-accent/60 shrink-0" />
          <div className="text-center">
            <div className="text-2xl font-light text-foreground tracking-tight">{widget.to_value}</div>
            <div className="text-xs text-foreground/50 mt-1">{widget.to_unit}</div>
          </div>
        </div>
      )}

      {/* Definition */}
      {widget.type === "definition" && widget.word && widget.definition && (
        <div className="space-y-2">
          <div className="text-lg font-medium text-foreground">{widget.word}</div>
          <p className="text-sm text-foreground/70 leading-relaxed">{widget.definition}</p>
        </div>
      )}
    </div>
  );
}

export type { WidgetResult };
