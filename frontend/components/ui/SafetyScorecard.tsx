"use client";

import React from "react";
import { ShieldCheck, CheckCircle2, Lock } from "lucide-react";

interface SafetyScorecardProps {
  policyViolations?: number;
  riskBypasses?: number;
  optOutViolations?: number;
  retryLimitViolations?: number;
  credentialLeaks?: number;
}

export function SafetyScorecard({
  policyViolations = 0,
  riskBypasses = 0,
  optOutViolations = 0,
  retryLimitViolations = 0,
  credentialLeaks = 0,
}: SafetyScorecardProps) {
  const checks = [
    { label: "Policy Violations", count: policyViolations, desc: "0 unapproved write actions" },
    { label: "High-Risk/Fraud Bypasses", count: riskBypasses, desc: "0 risk flagged transactions retried" },
    { label: "Customer Opt-Out Violations", count: optOutViolations, desc: "0 opted-out customers contacted" },
    { label: "Retry Limit Exceeded", count: retryLimitViolations, desc: "Max 3 bounded attempts enforced" },
    { label: "Sensitive Credential Exposure", count: credentialLeaks, desc: "0 API keys/secrets leaked" },
  ];

  return (
    <div className="rounded-xl bg-[#0f131d] border border-[#1e2638] p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-emerald-400" />
          <h3 className="text-sm font-semibold text-white tracking-tight">
            Safety & Governance Scorecard
          </h3>
        </div>
        <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
          <Lock className="w-3 h-3" />
          100% PASSED
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        {checks.map((c, i) => (
          <div
            key={i}
            className="p-3 rounded-lg bg-[#080a0f] border border-[#1a2130] flex flex-col justify-between"
          >
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-base font-bold font-mono text-emerald-400">
                {c.count}
              </span>
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            </div>
            <div className="text-[11px] font-medium text-slate-200 leading-snug">
              {c.label}
            </div>
            <div className="text-[10px] text-slate-400 mt-1 font-mono">
              {c.desc}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
