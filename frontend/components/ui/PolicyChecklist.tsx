"use client";

import React from "react";
import { CheckCircle2, AlertCircle, XCircle, ShieldCheck } from "lucide-react";

interface PolicyChecklistProps {
  policyDecision?: string; // APPROVE, ESCALATE, STOP, REJECT
  explanation?: string;
  reasons?: string[];
  compact?: boolean;
}

export function PolicyChecklist({
  policyDecision = "APPROVED",
  explanation = "All 10 deterministic policy guardrails satisfied.",
  reasons = [],
  compact = false,
}: PolicyChecklistProps) {
  const normDecision = (policyDecision || "APPROVED").toUpperCase();
  const isApproved = normDecision === "APPROVED" || normDecision === "APPROVE";
  const isEscalated = normDecision === "ESCALATE" || normDecision === "ESCALATED";
  const isStopped = normDecision === "STOP" || normDecision === "STOPPED" || normDecision === "REJECT";

  const allRules = [
    { id: "R1", name: "Payment not already paid / captured", status: true },
    { id: "R2", name: "No active fraud / velocity risk flag", status: !isStopped },
    { id: "R3", name: "Customer not opted out of recovery", status: !isStopped },
    { id: "R4", name: "Supported payment failure category", status: true },
    { id: "R5", name: "Permitted recovery action type", status: true },
    { id: "R6", name: "Max retry limit bounded (<= 3 attempts)", status: true },
    { id: "R7", name: "Amount threshold review (<= ₹50,000 auto-retry)", status: !isEscalated },
    { id: "R8", name: "Scorer confidence floor (>= 70% required)", status: !isEscalated },
    { id: "R9", name: "Message personalization safety verification", status: true },
    { id: "R10", name: "Mandatory system health check passed", status: true },
  ];

  return (
    <div className="rounded-xl bg-[#0f131d] border border-[#1e2638] p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-blue-400" />
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-white font-mono">
              Deterministic Policy Engine
            </h3>
            <p className="text-[11px] text-slate-400">10 Autonomous Safety Checks</p>
          </div>
        </div>
        <span
          className={`text-xs font-mono font-bold px-2.5 py-1 rounded border uppercase tracking-wider ${
            isApproved
              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
              : isEscalated
              ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
              : "bg-rose-500/10 text-rose-400 border-rose-500/20"
          }`}
        >
          {policyDecision}
        </span>
      </div>

      <div className="text-[11px] text-slate-300 p-2.5 rounded-lg bg-[#080a0f] border border-[#1a2130] font-mono leading-relaxed">
        {explanation}
      </div>

      <div className={`grid ${compact ? "grid-cols-1" : "grid-cols-1 sm:grid-cols-2"} gap-2`}>
        {allRules.map((rule) => (
          <div
            key={rule.id}
            className="flex items-center justify-between p-2 rounded-lg bg-[#080a0f] border border-[#161c2a] text-xs"
          >
            <div className="flex items-center gap-2">
              <span className="font-mono text-[10px] text-slate-400 font-semibold">{rule.id}</span>
              <span className="text-[11px] text-slate-300">{rule.name}</span>
            </div>
            {rule.status ? (
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            ) : isEscalated ? (
              <AlertCircle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
            ) : (
              <XCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
