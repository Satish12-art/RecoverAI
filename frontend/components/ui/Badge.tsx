import React from "react";

export type BadgeVariant =
  | "retry"
  | "message"
  | "escalate"
  | "stop"
  | "approved"
  | "rejected"
  | "stopped"
  | "escalated"
  | "recovered"
  | "recovering"
  | "failed"
  | "open"
  | "automatic"
  | "human_review"
  | "info"
  | "neutral";

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant | string;
  size?: "sm" | "md";
  className?: string;
}

export function Badge({ children, variant = "neutral", size = "md", className = "" }: BadgeProps) {
  const norm = (variant || "").toLowerCase();

  const variantStyles: Record<string, string> = {
    // Actions
    retry: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    message: "bg-cyan-500/10 text-cyan-400 border-cyan-500/20",
    escalate: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    stop: "bg-rose-500/10 text-rose-400 border-rose-500/20",

    // Policy decisions
    approved: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    rejected: "bg-rose-500/10 text-rose-400 border-rose-500/20",
    stopped_policy: "bg-rose-500/10 text-rose-400 border-rose-500/20",
    escalated_policy: "bg-amber-500/10 text-amber-400 border-amber-500/20",

    // Case / Outcome statuses
    recovered: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30 font-semibold",
    recovering: "bg-blue-500/15 text-blue-400 border-blue-500/30 animate-pulse",
    failed: "bg-rose-500/10 text-rose-400 border-rose-500/20",
    escalated_status: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    stopped_status: "bg-slate-500/10 text-slate-400 border-slate-500/20",
    open: "bg-slate-500/10 text-slate-300 border-slate-500/20",

    // Flow types
    automatic: "bg-indigo-500/10 text-indigo-300 border-indigo-500/20",
    human_review: "bg-amber-500/10 text-amber-300 border-amber-500/20",

    // Generic
    info: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    neutral: "bg-slate-800 text-slate-300 border-slate-700",
  };

  let appliedKey = norm;
  if (norm === "approve") appliedKey = "approved";
  if (norm === "reject") appliedKey = "rejected";
  if (norm === "stop") appliedKey = "stop";
  if (norm === "escalate") appliedKey = "escalate";
  if (norm === "recovered") appliedKey = "recovered";

  const style = variantStyles[appliedKey] || variantStyles.neutral;
  const sizeClass = size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-xs";

  return (
    <span
      className={`inline-flex items-center font-mono font-medium rounded border ${sizeClass} ${style} ${className}`}
    >
      {children}
    </span>
  );
}
