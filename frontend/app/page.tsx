"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  fetchDashboard,
  fetchCases,
  runSimulation,
  resetSimulation,
  fetchRazorpayStatus,
  triggerRazorpayTestWebhook,
} from "@/lib/api";
import {
  DashboardMetrics,
  RecoveryCaseItem,
  SimulationRunResult,
} from "@/types";
import { Badge } from "@/components/ui/Badge";
import { SkeletonCard, SkeletonTable } from "@/components/ui/Skeleton";
import { LoadingError } from "@/components/ui/LoadingError";
import {
  TrendingUp,
  AlertTriangle,
  ShieldCheck,
  Zap,
  Play,
  ArrowRight,
  Sparkles,
  CheckCircle2,
  Send,
  Webhook,
  Bot,
  Activity,
  ChevronRight,
  Lock,
  RotateCcw,
} from "lucide-react";

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [cases, setCases] = useState<RecoveryCaseItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Simulation runner state
  const [simLimit, setSimLimit] = useState<number | "all">(100);
  const [simRunning, setSimRunning] = useState(false);
  const [simResetting, setSimResetting] = useState(false);
  const [simResult, setSimResult] = useState<SimulationRunResult | null>(null);
  const [simError, setSimError] = useState<string | null>(null);

  // Razorpay Test Webhook Console state
  const [rzpStatus, setRzpStatus] = useState<any>(null);
  const [rzpEventType, setRzpEventType] = useState("payment.failed");
  const [rzpAmount, setRzpAmount] = useState(4999.0);
  const [rzpReason, setRzpReason] = useState("temporary_bank_error");
  const [rzpSending, setRzpSending] = useState(false);
  const [rzpResult, setRzpResult] = useState<any>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [dashData, casesData, rzpData] = await Promise.all([
        fetchDashboard(),
        fetchCases({ page: 1, page_size: 10, sort_by: "expected_recovery_value" }),
        fetchRazorpayStatus().catch(() => null),
      ]);
      setMetrics(dashData);
      setCases(casesData.items || []);
      setRzpStatus(rzpData);
    } catch (err: any) {
      setError(err.message || "Failed to load dashboard data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRunSimulation = async () => {
    try {
      setSimRunning(true);
      setSimError(null);
      const res = await runSimulation({
        limit: simLimit === "all" ? undefined : simLimit,
        all_payments: simLimit === "all",
        seed: 42,
        mode: "mock",
      });
      setSimResult(res);
      await loadData();
    } catch (err: any) {
      setSimError(err.message || "Simulation execution failed");
    } finally {
      setSimRunning(false);
    }
  };

  const handleResetSimulation = async () => {
    if (!confirm("Reset database simulation state and reseed initial 100 cases?")) {
      return;
    }
    try {
      setSimResetting(true);
      setSimError(null);
      setSimResult(null);
      await resetSimulation({ seed: 42, initial_limit: 100 });
      await loadData();
    } catch (err: any) {
      setSimError(err.message || "Simulation reset failed");
    } finally {
      setSimResetting(false);
    }
  };

  const handleTriggerTestWebhook = async () => {
    try {
      setRzpSending(true);
      setRzpResult(null);
      const res = await triggerRazorpayTestWebhook({
        event_type: rzpEventType,
        amount: Number(rzpAmount),
        failure_code: "BAD_REQUEST_ERROR",
        failure_reason: rzpReason,
        customer_email: "test.merchant@example.com",
        customer_name: "Razorpay Test Customer",
      });
      setRzpResult(res);
      await loadData();
    } catch (err: any) {
      alert(`Test webhook error: ${err.message}`);
    } finally {
      setRzpSending(false);
    }
  };

  const formatCurrency = (val?: number) => {
    if (val === undefined || val === null) return "₹0.00";
    if (val >= 10000000) {
      return `₹${(val / 10000000).toFixed(2)} Cr`;
    }
    if (val >= 100000) {
      return `₹${(val / 100000).toFixed(2)} L`;
    }
    return `₹${val.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  if (loading && !metrics) {
    return (
      <div className="p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
        <SkeletonTable rows={6} />
      </div>
    );
  }

  if (error && !metrics) {
    return (
      <div className="p-6 lg:p-8 max-w-7xl mx-auto">
        <LoadingError message={error} onRetry={loadData} />
      </div>
    );
  }

  return (
    <div className="p-6 lg:p-8 space-y-8 max-w-7xl mx-auto">
      {/* Simulation & Test Mode Notice Banner */}
      <div className="bg-[#121622] border border-amber-500/30 rounded-xl px-4 py-2.5 flex flex-col sm:flex-row items-start sm:items-center justify-between text-xs text-amber-300 font-mono gap-2 shadow-sm">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span>
          <span>SIMULATION MODE — Synthetic Dataset (Seed 42) + Razorpay Test Webhooks · Zero real money moved</span>
        </div>
        <span className="text-slate-400 text-[11px] flex items-center gap-1">
          <Lock className="w-3 h-3 text-slate-400" />
          Deterministic Policy Gating Enforced
        </span>
      </div>

      {/* DASHBOARD HERO & ARCHITECTURE FLOW */}
      <div className="rounded-2xl bg-gradient-to-r from-[#0d121f] via-[#101728] to-[#0d121f] border border-[#1e273a] p-6 lg:p-8 relative overflow-hidden shadow-xl">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
          <div className="space-y-2 max-w-2xl">
            <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-[11px] font-mono font-medium">
              <Bot className="w-3.5 h-3.5 text-blue-400" />
              <span>BOUNDED AI RECOVERY INFRASTRUCTURE</span>
            </div>
            <h2 className="text-2xl lg:text-3xl font-bold text-white tracking-tight">
              AI Revenue Recovery Infrastructure
            </h2>
            <p className="text-sm text-slate-300 leading-relaxed">
              AI agents that turn failed payments into recovered revenue through deterministic scoring, diagnostic reasoning, and strict policy governance.
            </p>
          </div>

          {/* Architecture Badges Flow */}
          <div className="flex flex-wrap items-center gap-1.5 p-3 rounded-xl bg-[#080b12]/80 border border-[#1a2233] font-mono text-[11px]">
            <span className="px-2 py-1 rounded bg-rose-500/10 text-rose-300 border border-rose-500/20 font-semibold">
              DETECT
            </span>
            <ChevronRight className="w-3.5 h-3.5 text-slate-500" />
            <span className="px-2 py-1 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20 font-semibold">
              DIAGNOSE
            </span>
            <ChevronRight className="w-3.5 h-3.5 text-slate-500" />
            <span className="px-2 py-1 rounded bg-blue-500/10 text-blue-300 border border-blue-500/20 font-semibold">
              DECIDE
            </span>
            <ChevronRight className="w-3.5 h-3.5 text-slate-500" />
            <span className="px-2 py-1 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 font-semibold">
              ACT
            </span>
            <ChevronRight className="w-3.5 h-3.5 text-slate-500" />
            <span className="px-2 py-1 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 font-bold">
              RECOVER
            </span>
          </div>
        </div>
      </div>

      {/* 1. TOP EXECUTIVE KPI ROW */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        {/* Gross Risk */}
        <div className="bg-[#0f1420] border border-[#1e2638] rounded-xl p-5 relative overflow-hidden transition-all hover:border-[#2a354c]">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-1">
            <span>Gross Revenue at Risk</span>
            <AlertTriangle className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-bold text-white tracking-tight font-mono">
            {formatCurrency(metrics?.gross_revenue_at_risk)}
          </div>
          <div className="text-[11px] text-slate-400 mt-2">
            Failed transaction volume
          </div>
        </div>

        {/* Potentially Recoverable */}
        <div className="bg-[#0f1420] border border-[#1e2638] rounded-xl p-5 relative overflow-hidden transition-all hover:border-[#2a354c]">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-1">
            <span>Potentially Recoverable</span>
            <Sparkles className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-bold text-white tracking-tight font-mono">
            {formatCurrency(metrics?.potentially_recoverable_revenue)}
          </div>
          <div className="text-[11px] text-blue-400 mt-2 font-mono">
            Propensity ≥ 60% eligible
          </div>
        </div>

        {/* Expected Recovery Value */}
        <div className="bg-[#0f1420] border border-[#1e2638] rounded-xl p-5 relative overflow-hidden transition-all hover:border-[#2a354c]">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-1">
            <span>Expected Recovery (ERV)</span>
            <Zap className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-white tracking-tight font-mono">
            {formatCurrency(metrics?.total_expected_recovery_value)}
          </div>
          <div className="text-[11px] text-slate-400 mt-2">
            Amount × Recovery Probability
          </div>
        </div>

        {/* Revenue Recovered */}
        <div className="bg-[#0f1420] border border-emerald-500/40 rounded-xl p-5 relative overflow-hidden shadow-lg shadow-emerald-950/30 transition-all">
          <div className="flex items-center justify-between text-emerald-400 text-xs font-semibold mb-1">
            <span>Revenue Recovered</span>
            <TrendingUp className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 tracking-tight font-mono">
            {formatCurrency(metrics?.revenue_recovered)}
          </div>
          <div className="text-[11px] text-slate-400 mt-2 font-mono">
            Observed settled outcomes
          </div>
        </div>

        {/* Recovery Rate */}
        <div className="bg-[#0f1420] border border-[#1e2638] rounded-xl p-5 relative overflow-hidden transition-all hover:border-[#2a354c]">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-1">
            <span>Recovery Rate</span>
            <CheckCircle2 className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-white tracking-tight font-mono">
            {(metrics?.recovery_rate || 0).toFixed(1)}%
          </div>
          <div className="text-[11px] text-slate-400 mt-2">
            Of potentially recoverable pool
          </div>
        </div>
      </div>

      {/* 2. THREE-TIER REVENUE FUNNEL & SIMULATION CONTROLS */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Three-Tier Revenue Funnel */}
        <div className="lg:col-span-2 bg-[#0f1420] border border-[#1e2638] rounded-2xl p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-semibold text-white">Three-Tier Revenue Hierarchy</h3>
              <p className="text-xs text-slate-400">Deterministic pipeline from failed risk to verified settled recovery</p>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 bg-[#141b2b] text-cyan-300 rounded border border-cyan-500/20">
              AUTONOMOUS PIPELINE
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
            {/* Tier 1 */}
            <div className="p-4 rounded-xl bg-[#080b12] border border-[#1a2233] relative">
              <div className="text-xs text-slate-400 mb-1 flex items-center justify-between">
                <span>Tier 1: Gross at Risk</span>
                <span className="text-[10px] font-mono text-rose-400">INPUT</span>
              </div>
              <div className="text-lg font-bold text-rose-400 mb-2 font-mono">
                {formatCurrency(metrics?.gross_revenue_at_risk)}
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Total failed payment volume entering the system before eligibility filtering.
              </p>
            </div>

            {/* Tier 2 */}
            <div className="p-4 rounded-xl bg-[#080b12] border border-[#1a2233] relative">
              <div className="text-xs text-slate-400 mb-1 flex items-center justify-between">
                <span>Tier 2: Potentially Recoverable</span>
                <span className="text-[10px] font-mono text-blue-400">SCORED</span>
              </div>
              <div className="text-lg font-bold text-blue-400 mb-2 font-mono">
                {formatCurrency(metrics?.potentially_recoverable_revenue)}
              </div>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Eligible revenue meeting recovery probability threshold (P ≥ 60%) without risk flags.
              </p>
            </div>

            {/* Tier 3 */}
            <div className="p-4 rounded-xl bg-[#080b12] border border-emerald-500/30 bg-emerald-950/10 relative">
              <div className="text-xs text-emerald-400 mb-1 flex items-center justify-between">
                <span>Tier 3: Revenue Recovered</span>
                <span className="text-[10px] font-mono text-emerald-400 font-semibold">CONFIRMED</span>
              </div>
              <div className="text-lg font-bold text-emerald-400 mb-2 font-mono">
                {formatCurrency(metrics?.revenue_recovered)}
              </div>
              <p className="text-[11px] text-slate-300 leading-relaxed">
                Verified settled revenue after policy approval and successful execution.
              </p>
            </div>
          </div>
        </div>

        {/* Live Simulation Control Panel */}
        <div className="bg-[#0f1420] border border-[#1e2638] rounded-2xl p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-base font-semibold text-white flex items-center gap-2">
                <Zap className="w-4 h-4 text-blue-400" />
                Live Simulation Runner
              </h3>
              <span className="text-[10px] font-mono text-emerald-400 px-2 py-0.5 bg-emerald-500/10 rounded border border-emerald-500/20">
                READY
              </span>
            </div>
            <p className="text-xs text-slate-400 mb-4">
              Execute bounded AI recovery loops across synthetic failed transactions.
            </p>

            <div className="space-y-3 mb-6">
              <div>
                <label className="text-[11px] text-slate-400 block mb-1.5 font-medium">
                  Payment Batch Size
                </label>
                <div className="grid grid-cols-4 gap-2">
                  {[10, 50, 100, "all"].map((opt) => (
                    <button
                      key={String(opt)}
                      type="button"
                      onClick={() => setSimLimit(opt as any)}
                      className={`py-1.5 text-xs font-mono rounded border transition-colors ${
                        simLimit === opt
                          ? "bg-blue-600 text-white border-blue-500 font-semibold shadow-sm"
                          : "bg-[#080b12] text-slate-400 border-[#1a2233] hover:text-white"
                      }`}
                    >
                      {opt === "all" ? "ALL (2k)" : opt}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex items-center justify-between text-xs text-slate-400 pt-1">
                <span>Mode: <strong className="text-slate-200">Mock LLM (Deterministic)</strong></span>
                <span>Seed: <strong className="text-slate-200 font-mono">42</strong></span>
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <button
                onClick={handleRunSimulation}
                disabled={simRunning || simResetting}
                className={`flex-1 py-2.5 px-4 rounded-lg font-medium text-sm transition-all flex items-center justify-center gap-2 ${
                  simRunning
                    ? "bg-blue-600/50 text-white cursor-wait animate-pulse"
                    : "bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-900/30"
                }`}
              >
                {simRunning ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></span>
                    Running Agent...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-white" />
                    Run Recovery Simulation
                  </>
                )}
              </button>

              <button
                onClick={handleResetSimulation}
                disabled={simRunning || simResetting}
                title="Reset simulation outcomes back to clean initial state"
                className={`py-2.5 px-3 rounded-lg text-xs font-mono font-medium transition-all flex items-center justify-center gap-1.5 border ${
                  simResetting
                    ? "bg-slate-800 text-slate-400 border-slate-700 cursor-wait animate-pulse"
                    : "bg-[#0c101a] hover:bg-[#151c2d] text-slate-300 border-[#1e293b] hover:text-white"
                }`}
              >
                <RotateCcw className={`w-3.5 h-3.5 ${simResetting ? "animate-spin" : ""}`} />
                <span>{simResetting ? "Resetting..." : "Reset"}</span>
              </button>
            </div>

            {simResult && !simRunning && (
              <div className="mt-3 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-300 space-y-1">
                <div className="font-semibold flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    <span>Batch Complete ({simResult.payments_processed} payments)</span>
                  </div>
                  <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/40 px-1.5 py-0.5 rounded border border-emerald-500/20">
                    {simResult.duration_seconds.toFixed(2)}s
                  </span>
                </div>
                <div className="text-[11px] text-slate-300">
                  Recovered: <strong className="text-white">{simResult.recovered_cases}</strong> · Recovered This Batch: <strong className="text-emerald-400 font-semibold">{formatCurrency(simResult.batch_revenue_recovered ?? simResult.revenue_recovered)}</strong>
                </div>
                <div className="text-[10px] text-slate-400 flex items-center justify-between pt-0.5 border-t border-emerald-500/10">
                  <span>Batch Rate: <strong className="text-slate-200">{(simResult.batch_recovery_rate ?? simResult.recovery_rate ?? 0).toFixed(1)}%</strong></span>
                  <span>Cumulative Recovered: <strong className="text-slate-200">{formatCurrency(simResult.cumulative_revenue_recovered ?? metrics?.revenue_recovered)}</strong></span>
                </div>
              </div>
            )}

            {simError && (
              <div className="mt-3 p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-xs text-rose-400">
                {simError}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 3. RAZORPAY TEST-MODE WEBHOOK CONSOLE */}
      <div className="bg-[#0f1420] border border-[#1e2638] rounded-2xl p-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-4 border-b border-[#1e2638]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/20 border border-indigo-500/40 flex items-center justify-center">
              <Webhook className="w-4 h-4 text-indigo-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-semibold text-white">Razorpay Test-Mode Webhook Ingestion</h3>
                <Badge variant="automatic">TEST MODE ONLY</Badge>
              </div>
              <p className="text-xs text-slate-400">
                Real-time test webhook ingestion feeding the authoritative RecoverAI pipeline
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
            <span className="flex items-center gap-1 text-emerald-400">
              <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
              Webhook Ready
            </span>
            <span>· Endpoint: <strong className="text-slate-300">/api/webhooks/razorpay</strong></span>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 pt-4">
          <div className="lg:col-span-2 space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div>
                <label className="text-[10px] uppercase font-mono text-slate-400 block mb-1">Event Type</label>
                <select
                  value={rzpEventType}
                  onChange={(e) => setRzpEventType(e.target.value)}
                  className="w-full bg-[#080b12] border border-[#1a2233] rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-indigo-500 font-mono"
                >
                  <option value="payment.failed">payment.failed</option>
                  <option value="payment.captured">payment.captured</option>
                  <option value="payment.authorized">payment.authorized</option>
                </select>
              </div>

              <div>
                <label className="text-[10px] uppercase font-mono text-slate-400 block mb-1">Amount (₹)</label>
                <input
                  type="number"
                  value={rzpAmount}
                  onChange={(e) => setRzpAmount(Number(e.target.value))}
                  className="w-full bg-[#080b12] border border-[#1a2233] rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-indigo-500 font-mono"
                />
              </div>

              <div>
                <label className="text-[10px] uppercase font-mono text-slate-400 block mb-1">Failure Reason</label>
                <select
                  value={rzpReason}
                  onChange={(e) => setRzpReason(e.target.value)}
                  disabled={rzpEventType !== "payment.failed"}
                  className="w-full bg-[#080b12] border border-[#1a2233] rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-indigo-500 font-mono disabled:opacity-40"
                >
                  <option value="temporary_bank_error">temporary_bank_error</option>
                  <option value="network_error">network_error</option>
                  <option value="expired_card">expired_card</option>
                  <option value="authentication_failure">authentication_failure</option>
                  <option value="fraud_risk_detected">fraud_risk_detected (risk_flagged)</option>
                </select>
              </div>
            </div>

            <button
              onClick={handleTriggerTestWebhook}
              disabled={rzpSending}
              className="py-2 px-4 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-medium rounded-lg transition-colors inline-flex items-center gap-2 shadow-lg shadow-indigo-950/30"
            >
              <Send className="w-3.5 h-3.5" />
              {rzpSending ? "Ingesting Webhook..." : "Send Test Razorpay Webhook"}
            </button>
          </div>

          <div className="p-3.5 rounded-lg bg-[#080b12] border border-[#1a2233] text-xs flex flex-col justify-between">
            {rzpResult ? (
              <div className="space-y-1.5">
                <div className="text-emerald-400 font-semibold flex items-center gap-1">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Webhook Ingested & Evaluated
                </div>
                <div className="text-[11px] text-slate-300 font-mono">
                  Payment: <strong className="text-white">{rzpResult.result?.external_payment_id}</strong>
                </div>
                {rzpResult.result?.recovery_case_id && (
                  <div className="text-[11px] text-slate-300">
                    Case: <Link href={`/cases/${rzpResult.result.recovery_case_id}`} className="text-blue-400 underline font-mono">Case #{rzpResult.result.recovery_case_id}</Link>
                  </div>
                )}
                {rzpResult.result?.agent_result && (
                  <div className="text-[10px] text-slate-400 font-mono">
                    Decision: {rzpResult.result.agent_result.recommended_action || rzpResult.result.agent_result.outcome}
                  </div>
                )}
              </div>
            ) : (
              <div className="text-slate-500 text-[11px] leading-relaxed">
                Click <strong>Send Test Razorpay Webhook</strong> to simulate an incoming failure event and trace its progression through the bounded AI agent.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 4. DEMO CASE QUICK-ACCESS CARDS */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-semibold text-white">Judge Demo Reference Scenarios</h3>
            <p className="text-xs text-slate-400">Explore verified decision pathways through the bounded recovery agent</p>
          </div>
          <span className="text-xs text-slate-400">4 Reference Archetypes</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Link
            href="/cases?failure_code=temporary_bank_error&action=retry"
            className="p-4 rounded-xl bg-[#0f1420] border border-[#1e2638] hover:border-blue-500/40 transition-colors block group"
          >
            <div className="flex items-center justify-between mb-2">
              <Badge variant="retry">DEMO 1</Badge>
              <Badge variant="approved">APPROVED</Badge>
            </div>
            <div className="font-semibold text-sm text-white group-hover:text-blue-400 transition-colors">
              Successful Auto-Retry
            </div>
            <div className="text-xs text-slate-400 mt-1">
              Transient bank timeout with prime history (P=89%).
            </div>
          </Link>

          <Link
            href="/cases?failure_code=expired_card&action=message"
            className="p-4 rounded-xl bg-[#0f1420] border border-[#1e2638] hover:border-cyan-500/40 transition-colors block group"
          >
            <div className="flex items-center justify-between mb-2">
              <Badge variant="message">DEMO 2</Badge>
              <Badge variant="approved">APPROVED</Badge>
            </div>
            <div className="font-semibold text-sm text-white group-hover:text-cyan-400 transition-colors">
              Approved Payment Update
            </div>
            <div className="text-xs text-slate-400 mt-1">
              Expired card prompt sent via compliant template.
            </div>
          </Link>

          <Link
            href="/cases?status=ESCALATED"
            className="p-4 rounded-xl bg-[#0f1420] border border-[#1e2638] hover:border-amber-500/40 transition-colors block group"
          >
            <div className="flex items-center justify-between mb-2">
              <Badge variant="escalate">DEMO 3</Badge>
              <Badge variant="escalated">ESCALATED</Badge>
            </div>
            <div className="font-semibold text-sm text-white group-hover:text-amber-400 transition-colors">
              High-Value Governance
            </div>
            <div className="text-xs text-slate-400 mt-1">
              ₹65,000 transaction routed to human operations.
            </div>
          </Link>

          <Link
            href="/cases?failure_code=risk_flagged"
            className="p-4 rounded-xl bg-[#0f1420] border border-[#1e2638] hover:border-rose-500/40 transition-colors block group"
          >
            <div className="flex items-center justify-between mb-2">
              <Badge variant="stop">DEMO 4</Badge>
              <Badge variant="stopped">STOPPED</Badge>
            </div>
            <div className="font-semibold text-sm text-white group-hover:text-rose-400 transition-colors">
              Zero-Call Risk Stop
            </div>
            <div className="text-xs text-slate-400 mt-1">
              Fraud/Velocity risk halted before LLM invocation.
            </div>
          </Link>
        </div>
      </div>

      {/* 5. RECOVERY OPPORTUNITIES QUEUE */}
      <div className="bg-[#0f1420] border border-[#1e2638] rounded-2xl overflow-hidden shadow-lg">
        <div className="p-6 border-b border-[#1e2638] flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-white">Recovery Opportunities Queue</h3>
            <p className="text-xs text-slate-400">Prioritized by Expected Recovery Value (ERV = Amount × Recovery Probability)</p>
          </div>
          <Link
            href="/cases"
            className="text-xs font-medium text-blue-400 hover:text-blue-300 flex items-center gap-1 transition-colors"
          >
            View All Cases ({metrics?.cases_processed || 2077}) <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#080b12] text-slate-400 uppercase font-mono text-[11px] border-b border-[#1e2638]">
              <tr>
                <th className="py-3 px-4">Payment ID</th>
                <th className="py-3 px-4">Customer</th>
                <th className="py-3 px-4">Failure Code</th>
                <th className="py-3 px-4">Amount</th>
                <th className="py-3 px-4">Probability</th>
                <th className="py-3 px-4">Expected Value (ERV)</th>
                <th className="py-3 px-4">AI Action</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Inspect</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#161c28] text-slate-300">
              {cases.map((c) => (
                <tr key={c.id} className="hover:bg-[#121724] transition-colors">
                  <td className="py-3.5 px-4 font-mono text-white font-medium">
                    {c.external_payment_id}
                  </td>
                  <td className="py-3.5 px-4">
                    <div className="text-white font-medium">{c.customer_name}</div>
                    <div className="text-[11px] text-slate-500 font-mono">ID: {c.customer_id}</div>
                  </td>
                  <td className="py-3.5 px-4 font-mono text-slate-300">
                    <span className="px-2 py-0.5 rounded bg-[#080b12] border border-[#1a2233] text-[11px]">
                      {c.failure_code || "unknown"}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 font-semibold text-white font-mono">
                    {formatCurrency(c.amount_at_risk)}
                  </td>
                  <td className="py-3.5 px-4">
                    {c.recovery_probability !== null && c.recovery_probability !== undefined ? (
                      <div className="flex items-center gap-2">
                        <div className="w-12 bg-[#080b12] rounded-full h-1.5 overflow-hidden border border-[#1a2233]">
                          <div
                            className={`h-full rounded-full ${
                              c.recovery_probability >= 0.70
                                ? "bg-emerald-400"
                                : c.recovery_probability >= 0.50
                                ? "bg-blue-400"
                                : "bg-amber-400"
                            }`}
                            style={{ width: `${Math.min(100, c.recovery_probability * 100)}%` }}
                          />
                        </div>
                        <span className="font-mono font-medium">
                          {(c.recovery_probability * 100).toFixed(0)}%
                        </span>
                      </div>
                    ) : (
                      <span className="text-slate-500 font-mono">—</span>
                    )}
                  </td>
                  <td className="py-3.5 px-4 font-mono font-bold text-emerald-400">
                    {formatCurrency(c.expected_recovery_value)}
                  </td>
                  <td className="py-3.5 px-4">
                    <Badge variant={c.recommended_action || "stop"}>
                      {(c.recommended_action || "STOP").toUpperCase()}
                    </Badge>
                  </td>
                  <td className="py-3.5 px-4">
                    <Badge variant={c.status.toLowerCase()}>
                      {c.status}
                    </Badge>
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <Link
                      href={`/cases/${c.id}`}
                      className="px-2.5 py-1 rounded bg-blue-600/10 hover:bg-blue-600/20 text-blue-400 font-medium text-xs border border-blue-500/20 transition-colors inline-flex items-center gap-1"
                    >
                      Trace <ArrowRight className="w-3 h-3" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
