"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { fetchCaseDetail, triggerAgentRecovery } from "@/lib/api";
import { CaseDetailData } from "@/types";
import { Badge } from "@/components/ui/Badge";
import { SkeletonCard, SkeletonTable } from "@/components/ui/Skeleton";
import { LoadingError } from "@/components/ui/LoadingError";
import { ProbabilityMeter } from "@/components/ui/ProbabilityMeter";
import { StateTimeline } from "@/components/ui/StateTimeline";
import {
  ArrowLeft,
  ShieldCheck,
  Zap,
  CheckCircle2,
  AlertCircle,
  CreditCard,
  User,
  Activity,
  Play,
  RotateCcw,
  Bot,
  Lock,
  ArrowRight,
} from "lucide-react";

export default function CaseDetailPage() {
  const params = useParams();
  const rawId = Array.isArray(params?.id) ? params.id[0] : params?.id;
  const caseId = rawId ? Number(rawId) : null;

  const [caseData, setCaseData] = useState<CaseDetailData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [recovering, setRecovering] = useState(false);

  const loadCase = async () => {
    if (!caseId || isNaN(caseId)) return;
    try {
      setLoading(true);
      setError(null);
      const data = await fetchCaseDetail(caseId);
      setCaseData(data);
    } catch (err: any) {
      setError(err.message || "Failed to load case detail");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (caseId && !isNaN(caseId)) {
      loadCase();
    }
  }, [caseId]);

  const handleTriggerRecovery = async () => {
    if (!caseId || isNaN(caseId)) return;
    try {
      setRecovering(true);
      await triggerAgentRecovery(caseId);
      await loadCase();
    } catch (err: any) {
      alert(`Recovery failed: ${err.message}`);
    } finally {
      setRecovering(false);
    }
  };

  const formatCurrency = (val?: number) => {
    if (val === undefined || val === null) return "₹0.00";
    return `₹${val.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  if (loading && !caseData) {
    return (
      <div className="p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
        <SkeletonCard className="h-24" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <SkeletonCard className="h-96" />
          <SkeletonCard className="h-96" />
        </div>
      </div>
    );
  }

  if (error || !caseData) {
    return (
      <div className="p-6 lg:p-8 max-w-7xl mx-auto">
        <LoadingError message={error || "Case not found"} onRetry={loadCase} />
      </div>
    );
  }

  const { case: c, payment: p, customer: cust, scoring_factors: sf, actions = [], outcomes = [] } = caseData;
  const safeActions = actions || [];
  const safeOutcomes = outcomes || [];
  const latestOutcome = safeOutcomes.length > 0 ? safeOutcomes[safeOutcomes.length - 1] : null;

  // Timeline Steps
  const stateMachineSteps = [
    { title: "DETECTED", desc: "Payment failure captured and initialized.", completed: true },
    { title: "ELIGIBILITY CHECK", desc: "Deterministic gate checked for risk and opt-out.", completed: true },
    { title: "CONTEXT LOADING", desc: "Customer profile, history, and dispute records loaded.", completed: true },
    { title: "SCORING", desc: `Recovery Scorer evaluated Probability (${((c.recovery_probability || 0) * 100).toFixed(0)}%) & Confidence.`, completed: true },
    { title: "DIAGNOSING", desc: c.diagnosis || "Failure pattern diagnosed by bounded reasoning.", completed: Boolean(c.diagnosis) || Boolean(c.recommended_action) },
    { title: "DECISION PENDING", desc: `Recommendation formulated: ${(c.recommended_action || "EVALUATING").toUpperCase()}`, completed: Boolean(c.recommended_action) },
    { title: "POLICY CHECK", desc: "10 deterministic rules evaluated for financial governance.", completed: safeActions.length > 0 || c.status !== "OPEN" },
    { title: "ACTION EXECUTION", desc: safeActions.length > 0 ? `${safeActions[0].tool_name} executed.` : "Waiting or stopped.", completed: safeActions.length > 0 },
    { title: "TERMINAL", desc: `Final Case State: ${c.status}`, completed: c.status !== "OPEN" },
  ];

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      {/* Top Navigation & Case Status Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <Link
            href="/cases"
            className="text-xs text-slate-400 hover:text-slate-200 inline-flex items-center gap-1 mb-2 transition-colors font-mono"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to Recovery Cases
          </Link>
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-bold text-white tracking-tight font-sans">
              Case #{c.id} · <span className="font-mono text-blue-400">{p.external_payment_id}</span>
            </h2>
            <Badge variant={c.status.toLowerCase()}>{c.status}</Badge>
          </div>
        </div>

        {/* Action button */}
        <div className="flex items-center gap-2">
          {c.status === "OPEN" && (
            <button
              onClick={handleTriggerRecovery}
              disabled={recovering}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-medium text-xs rounded-lg transition-colors flex items-center gap-2 shadow-lg shadow-blue-900/30 font-mono"
            >
              <Play className="w-3.5 h-3.5 fill-white" />
              {recovering ? "Running Agent..." : "Run AI Recovery"}
            </button>
          )}
          <button
            onClick={loadCase}
            className="px-3 py-2 bg-[#121622] hover:bg-[#182030] text-slate-300 text-xs font-medium rounded-lg transition-colors flex items-center gap-1.5 border border-[#1e273a] font-mono"
          >
            <RotateCcw className="w-3.5 h-3.5" /> Refresh
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT COLUMN: Payment, Customer, and Recovery Intelligence */}
        <div className="lg:col-span-5 space-y-6">
          {/* Payment Information */}
          <div className="bg-[#0f1420] border border-[#1e2638] rounded-2xl p-5 space-y-4 shadow-sm">
            <div className="flex items-center gap-2 pb-3 border-b border-[#1e2638]">
              <CreditCard className="w-4 h-4 text-blue-400" />
              <h3 className="text-sm font-semibold text-white font-sans">Payment Information</h3>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <span className="text-slate-400 block text-[11px]">Amount at Risk</span>
                <span className="text-base font-bold text-white font-mono">{formatCurrency(p.amount)}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Payment Method</span>
                <span className="font-mono text-slate-200 uppercase font-medium">{p.payment_method}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Failure Code</span>
                <span className="font-mono text-rose-400 font-medium px-2 py-0.5 rounded bg-rose-500/10 border border-rose-500/20 inline-block mt-0.5">
                  {p.failure_code || "unknown"}
                </span>
              </div>
              <div>
                <span className="text-slate-400 block text-[11px]">Risk Flagged</span>
                <span className={`font-mono text-xs font-semibold ${p.risk_flagged ? "text-rose-400" : "text-emerald-400"}`}>
                  {p.risk_flagged ? "YES (Blocked)" : "NO (Clean)"}
                </span>
              </div>
            </div>

            {p.failure_reason && (
              <div className="p-2.5 rounded-lg bg-[#080a0f] border border-[#161c28] text-xs text-slate-300">
                <span className="text-slate-400 block text-[10px] uppercase font-mono mb-0.5 font-semibold">Failure Reason</span>
                {p.failure_reason}
              </div>
            )}
          </div>

          {/* Customer Profile & History */}
          <div className="bg-[#0f1420] border border-[#1e2638] rounded-2xl p-5 space-y-4 shadow-sm">
            <div className="flex items-center gap-2 pb-3 border-b border-[#1e2638]">
              <User className="w-4 h-4 text-cyan-400" />
              <h3 className="text-sm font-semibold text-white font-sans">Customer Profile & History</h3>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-[#161c28]">
                <span className="text-slate-400">Customer Name</span>
                <span className="text-white font-medium">{cust.name}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#161c28]">
                <span className="text-slate-400">Customer ID</span>
                <span className="font-mono text-slate-300">{cust.external_customer_id}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#161c28]">
                <span className="text-slate-400">Tenure</span>
                <span className="text-slate-200">{cust.customer_tenure_days} days</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#161c28]">
                <span className="text-slate-400">Payment History</span>
                <span className="font-mono text-slate-200">
                  <span className="text-emerald-400">{cust.successful_payments}</span> successful /{" "}
                  <span className="text-rose-400">{cust.failed_payments}</span> failed
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#161c28]">
                <span className="text-slate-400">Chargebacks / Disputes</span>
                <span className={`font-mono font-medium ${cust.chargeback_count > 0 ? "text-rose-400" : "text-emerald-400"}`}>
                  {cust.chargeback_count}
                </span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-slate-400">Customer Opted Out</span>
                <span className="font-mono text-slate-200">{cust.opted_out ? "YES (Stop)" : "NO"}</span>
              </div>
            </div>
          </div>

          {/* Recovery Intelligence & Scoring Factors */}
          <div className="bg-[#0f1420] border border-[#1e2638] rounded-2xl p-5 space-y-4 shadow-sm">
            <div className="flex items-center justify-between pb-3 border-b border-[#1e2638]">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-indigo-400" />
                <h3 className="text-sm font-semibold text-white font-sans">Recovery Intelligence</h3>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                Single Source Scorer
              </span>
            </div>

            {/* Circular Meter + Key Metrics */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-center p-3 rounded-xl bg-[#080b12] border border-[#161c28]">
              <div className="sm:col-span-1 flex justify-center">
                <ProbabilityMeter
                  value={c.recovery_probability || 0}
                  label="Probability"
                  size="md"
                />
              </div>
              <div className="sm:col-span-2 space-y-2.5">
                <div>
                  <div className="text-[10px] text-slate-400 uppercase font-mono">Confidence</div>
                  <div className="text-base font-bold text-blue-400 font-mono">
                    {c.scorer_confidence !== null ? `${((c.scorer_confidence || 0) * 100).toFixed(0)}%` : "—"}
                  </div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-400 uppercase font-mono">Expected Value (ERV)</div>
                  <div className="text-base font-bold text-emerald-400 font-mono">
                    {formatCurrency(c.expected_recovery_value)}
                  </div>
                </div>
              </div>
            </div>

            {sf?.factors && sf.factors.length > 0 && (
              <div className="space-y-1.5 pt-2">
                <div className="text-[11px] font-semibold text-slate-400 uppercase font-mono">Contributing Factors</div>
                <div className="space-y-1">
                  {sf.factors.map((f, i) => (
                    <div key={i} className="p-2 rounded-lg bg-[#080b12] border border-[#161c28] flex items-center justify-between text-xs">
                      <div>
                        <div className="text-slate-300 font-medium">{f.factor_name}</div>
                        <div className="text-[10px] text-slate-400">{f.description}</div>
                      </div>
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold uppercase ${
                          (f.impact || "").toLowerCase() === "positive"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : (f.impact || "").toLowerCase() === "negative"
                            ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                            : "bg-slate-800 text-slate-400 border border-slate-700"
                        }`}
                      >
                        {f.impact}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* RIGHT COLUMN: AI Decision, Policy Engine, Timeline, and Audit Trail */}
        <div className="lg:col-span-7 space-y-6">
          {/* AI Decision Card & Policy Governance */}
          <div className="bg-[#0f1420] border border-[#1e2638] rounded-2xl p-6 space-y-5 shadow-sm">
            {/* AI Recommendation */}
            <div className="space-y-3 pb-5 border-b border-[#1e2638]">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Bot className="w-4 h-4 text-blue-400" />
                  <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                    AI Recommendation
                  </h3>
                </div>
                <Badge variant={c.recommended_action || "stop"}>
                  {(c.recommended_action || "STOP").toUpperCase()}
                </Badge>
              </div>

              {c.diagnosis && (
                <div className="p-3.5 rounded-xl bg-[#080b12] border border-[#161c28] text-xs space-y-1">
                  <div className="text-[10px] uppercase font-mono text-slate-400 font-semibold">Failure Diagnosis</div>
                  <div className="text-slate-200 leading-relaxed">{c.diagnosis}</div>
                </div>
              )}
            </div>

            {/* Policy Decision & Guardrail Checks */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                    Policy Engine Decision
                  </h3>
                </div>
                <Badge
                  variant={
                    c.status === "RECOVERING" || c.status === "RECOVERED"
                      ? "approved"
                      : c.status === "ESCALATED"
                      ? "escalated"
                      : "stopped"
                  }
                >
                  {c.status === "RECOVERING" || c.status === "RECOVERED"
                    ? "APPROVED"
                    : c.status === "ESCALATED"
                    ? "ESCALATE (Human Review)"
                    : "STOPPED"}
                </Badge>
              </div>

              {/* Policy Rule Checklist */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs pt-1 font-mono">
                <div className="flex items-center gap-2 text-slate-300 p-2 rounded bg-[#080b12] border border-[#161c28]">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  <span>Payment not already paid</span>
                </div>
                <div className="flex items-center gap-2 text-slate-300 p-2 rounded bg-[#080b12] border border-[#161c28]">
                  <CheckCircle2 className={`w-3.5 h-3.5 shrink-0 ${p.risk_flagged ? "text-rose-400" : "text-emerald-400"}`} />
                  <span className={p.risk_flagged ? "text-rose-400 font-bold" : ""}>Fraud / Velocity check</span>
                </div>
                <div className="flex items-center gap-2 text-slate-300 p-2 rounded bg-[#080b12] border border-[#161c28]">
                  <CheckCircle2 className={`w-3.5 h-3.5 shrink-0 ${cust.opted_out ? "text-rose-400" : "text-emerald-400"}`} />
                  <span className={cust.opted_out ? "text-rose-400 font-bold" : ""}>Customer opt-out check</span>
                </div>
                <div className="flex items-center gap-2 text-slate-300 p-2 rounded bg-[#080b12] border border-[#161c28]">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  <span>Retry limit ({c.retry_count || 0}/2)</span>
                </div>
                <div className="flex items-center gap-2 text-slate-300 p-2 rounded bg-[#080b12] border border-[#161c28]">
                  <CheckCircle2 className={`w-3.5 h-3.5 shrink-0 ${(c.recovery_probability || 0) >= 0.60 ? "text-emerald-400" : "text-amber-400"}`} />
                  <span>Probability threshold (≥ 60%)</span>
                </div>
                <div className="flex items-center gap-2 text-slate-300 p-2 rounded bg-[#080b12] border border-[#161c28]">
                  <CheckCircle2 className={`w-3.5 h-3.5 shrink-0 ${(c.scorer_confidence || 0) >= 0.70 ? "text-emerald-400" : "text-amber-400"}`} />
                  <span>Confidence threshold (≥ 70%)</span>
                </div>
                <div className="flex items-center gap-2 text-slate-300 p-2 rounded bg-[#080b12] border border-[#161c28]">
                  <CheckCircle2 className={`w-3.5 h-3.5 shrink-0 ${p.amount <= 50000 ? "text-emerald-400" : "text-amber-400"}`} />
                  <span className={p.amount > 50000 ? "text-amber-400 font-bold" : ""}>Amount limit (≤ ₹50,000)</span>
                </div>
                <div className="flex items-center gap-2 text-slate-300 p-2 rounded bg-[#080b12] border border-[#161c28]">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  <span>Approved Template Sandbox</span>
                </div>
              </div>
            </div>
          </div>

          {/* State Machine Execution Timeline */}
          <div className="bg-[#0f1420] border border-[#1e2638] rounded-2xl p-6 space-y-4 shadow-sm">
            <div className="flex items-center justify-between pb-3 border-b border-[#1e2638]">
              <div>
                <h3 className="text-sm font-semibold text-white font-sans">Bounded State Machine Timeline</h3>
                <p className="text-[11px] text-slate-400">Strict finite sequence with zero raw chain-of-thought storage</p>
              </div>
              <span className="text-[10px] font-mono text-cyan-400 px-2 py-0.5 bg-cyan-950/40 rounded border border-cyan-500/20">
                MAX_STEPS = 10
              </span>
            </div>

            <div className="space-y-3 relative before:absolute before:left-3.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-[#1a2130]">
              {stateMachineSteps.map((step, idx) => (
                <div key={idx} className="relative pl-9 text-xs">
                  <div
                    className={`absolute left-2 top-1 -translate-x-1/2 w-4 h-4 rounded-full border-2 flex items-center justify-center ${
                      step.completed
                        ? "bg-blue-600 border-blue-400 text-white shadow-sm shadow-blue-500/50"
                        : "bg-[#080a0f] border-[#1e2638] text-slate-600"
                    }`}
                  >
                    {step.completed && <span className="w-1.5 h-1.5 rounded-full bg-white"></span>}
                  </div>
                  <div className="font-mono font-semibold text-white uppercase text-[11px]">
                    {step.title}
                  </div>
                  <div className="text-slate-400 text-[11px] mt-0.5 leading-relaxed">
                    {step.desc}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Executed Actions & Observed Outcomes */}
          {safeActions.length > 0 && (
            <div className="bg-[#0f1420] border border-[#1e2638] rounded-2xl p-5 space-y-3 shadow-sm">
              <h3 className="text-xs font-semibold text-slate-300 uppercase font-mono">
                Audit Trail Action Log
              </h3>
              <div className="space-y-2">
                {safeActions.map((act) => (
                  <div key={act.id} className="p-3.5 rounded-xl bg-[#080b12] border border-[#161c28] text-xs space-y-1.5">
                    <div className="flex items-center justify-between font-mono">
                      <span className="font-semibold text-white">{act.tool_name}</span>
                      <Badge variant={(act.policy_decision || "approved").toLowerCase()}>{act.policy_decision || "APPROVED"}</Badge>
                    </div>
                    <div className="text-slate-300 text-[11px] leading-relaxed">{act.reasoning_summary}</div>
                    <div className="text-[10px] text-slate-400 font-mono">Policy Reason: {act.policy_reason}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {latestOutcome && (
            <div className="bg-[#0f1420] border border-emerald-500/40 bg-emerald-950/15 rounded-2xl p-5 flex items-center justify-between shadow-lg shadow-emerald-950/20">
              <div>
                <div className="text-xs font-semibold text-emerald-400 uppercase font-mono">
                  Observed Outcome: {(latestOutcome.outcome_status || "RECOVERED").toUpperCase()}
                </div>
                <div className="text-slate-300 text-xs mt-0.5">
                  Amount Recovered: <strong className="text-emerald-400 font-mono text-sm">{formatCurrency(latestOutcome.amount_recovered)}</strong>
                </div>
              </div>
              <Badge variant={latestOutcome.successful ? "recovered" : "failed"}>
                {latestOutcome.successful ? "SUCCESSFUL RECOVERY" : "UNSUCCESSFUL"}
              </Badge>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
