"use client";

import React from "react";
import { CheckCircle2, Circle, AlertTriangle, XCircle, ArrowRight } from "lucide-react";

export interface TimelineStep {
  name: string;
  status: "completed" | "active" | "pending" | "failed" | "skipped";
  detail?: string;
  timestamp?: string;
}

interface StateTimelineProps {
  currentStatus?: string;
  actionExecuted?: boolean;
}

export function StateTimeline({ currentStatus = "OPEN", actionExecuted = false }: StateTimelineProps) {
  const isTerminal = ["RECOVERED", "FAILED", "ESCALATED", "STOPPED"].includes(currentStatus);
  const isRecovered = currentStatus === "RECOVERED";
  const isEscalated = currentStatus === "ESCALATED";
  const isStopped = currentStatus === "STOPPED";

  const steps = [
    { name: "DETECTED", desc: "Webhook ingested" },
    { name: "ELIGIBILITY", desc: "Non-risk & non-paid check" },
    { name: "CONTEXT", desc: "Customer profile loaded" },
    { name: "SCORING", desc: "Propensity & ERV evaluated" },
    { name: "DIAGNOSING", desc: "LLM error categorization" },
    { name: "DECISION", desc: "Action proposed" },
    { name: "POLICY", desc: "Deterministic safety gate" },
    { name: "ACTION", desc: actionExecuted ? "Executed bounded tool" : "Safe exit" },
  ];

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
        {steps.map((step, idx) => {
          const isDone = isTerminal || (currentStatus !== "OPEN" && idx < 6);
          const isCurrent = !isTerminal && currentStatus !== "OPEN" && idx === 6;

          return (
            <div
              key={step.name}
              className={`p-2.5 rounded-lg border text-xs flex flex-col justify-between transition-all ${
                isDone
                  ? "bg-[#0d1522] border-blue-500/30 text-slate-200"
                  : isCurrent
                  ? "bg-blue-950/40 border-blue-400 text-white shadow-sm shadow-blue-500/20"
                  : "bg-[#0a0d14] border-[#1a2130] text-slate-400"
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="font-mono text-[10px] text-slate-400">0{idx + 1}</span>
                {isDone ? (
                  <CheckCircle2 className="w-3.5 h-3.5 text-blue-400" />
                ) : isCurrent ? (
                  <span className="w-2 h-2 rounded-full bg-blue-400 animate-ping" />
                ) : (
                  <Circle className="w-3 h-3 text-slate-600" />
                )}
              </div>
              <div>
                <div className={`font-mono font-bold text-[11px] ${isDone ? "text-blue-300" : isCurrent ? "text-white" : "text-slate-500"}`}>
                  {step.name}
                </div>
                <div className="text-[9px] text-slate-400 leading-tight mt-0.5">
                  {step.desc}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Terminal Outcome Banner */}
      <div
        className={`p-3 rounded-lg border flex items-center justify-between font-mono text-xs ${
          isRecovered
            ? "bg-emerald-950/20 border-emerald-500/40 text-emerald-300"
            : isEscalated
            ? "bg-amber-950/20 border-amber-500/40 text-amber-300"
            : isStopped
            ? "bg-rose-950/20 border-rose-500/40 text-rose-300"
            : "bg-[#0f131d] border-[#1e2638] text-slate-300"
        }`}
      >
        <div className="flex items-center gap-2">
          <span className="font-semibold uppercase tracking-wider text-[11px]">Final Lifecycle State:</span>
          <span className="font-bold px-2 py-0.5 rounded bg-black/40 border border-white/10 text-xs">
            {currentStatus}
          </span>
        </div>
        <span className="text-[10px] text-slate-400">
          {isRecovered
            ? "Funds recovered & settled"
            : isEscalated
            ? "Routed to human review queue"
            : isStopped
            ? "Blocked by deterministic risk gate"
            : "Awaiting recovery agent trigger"}
        </span>
      </div>
    </div>
  );
}
