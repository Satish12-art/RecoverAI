"use client";

import React, { useEffect, useState } from "react";
import { fetchDashboard, fetchFailureBreakdown } from "@/lib/api";
import { DashboardMetrics, FailureBreakdownData } from "@/types";
import { SkeletonCard, SkeletonTable } from "@/components/ui/Skeleton";
import { LoadingError } from "@/components/ui/LoadingError";
import {
  BarChart3,
  TrendingUp,
  Activity,
  DollarSign,
  AlertOctagon,
  Percent,
} from "lucide-react";

export default function AnalyticsPage() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [failures, setFailures] = useState<FailureBreakdownData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [dashData, failData] = await Promise.all([
        fetchDashboard(),
        fetchFailureBreakdown(),
      ]);
      setMetrics(dashData);
      setFailures(failData);
    } catch (err: any) {
      setError(err.message || "Failed to load analytics");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const formatCurrency = (val?: number) => {
    if (val === undefined || val === null) return "₹0.00";
    if (val >= 10000000) return `₹${(val / 10000000).toFixed(2)} Cr`;
    if (val >= 100000) return `₹${(val / 100000).toFixed(2)} L`;
    return `₹${val.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  if (loading) {
    return (
      <div className="p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <SkeletonCard className="h-80" />
          <SkeletonCard className="h-80" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6 lg:p-8 max-w-7xl mx-auto">
        <LoadingError message={error} onRetry={loadData} />
      </div>
    );
  }

  const failureItems = failures?.count_by_code
    ? Object.entries(failures.count_by_code).sort((a, b) => b[1] - a[1])
    : [];

  const maxFailureCount = failureItems.length > 0 ? Math.max(...failureItems.map((f) => f[1])) : 1;

  return (
    <div className="p-6 lg:p-8 space-y-8 max-w-7xl mx-auto">
      <div className="pb-2 border-b border-[#1e2638]">
        <h2 className="text-xl font-bold text-white tracking-tight font-sans">Recovery & Portfolio Analytics</h2>
        <p className="text-xs text-slate-400 font-mono mt-0.5">
          Deterministic failure patterns, probability distributions, and recovered yield analysis
        </p>
      </div>

      {/* Top 4 Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[#0f1420] border border-[#1e2638] rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-1">
            <span>Total Payment Failures</span>
            <AlertOctagon className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">
            {failures?.total_failures.toLocaleString() || "2,077"}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">Across 8,000 transactions</div>
        </div>

        <div className="bg-[#0f1420] border border-[#1e2638] rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-1">
            <span>Potentially Recoverable</span>
            <DollarSign className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-bold text-blue-400 font-mono">
            {formatCurrency(metrics?.potentially_recoverable_revenue)}
          </div>
          <div className="text-[11px] text-slate-400 mt-1">Probability threshold ≥ 60%</div>
        </div>

        <div className="bg-[#0f1420] border border-emerald-500/40 rounded-2xl p-5 bg-emerald-950/10 shadow-sm">
          <div className="flex items-center justify-between text-emerald-400 text-xs font-semibold mb-1">
            <span>Confirmed Recovered</span>
            <TrendingUp className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400 font-mono">
            {formatCurrency(metrics?.revenue_recovered)}
          </div>
          <div className="text-[11px] text-slate-400 mt-1 font-mono">Settled cash recoveries</div>
        </div>

        <div className="bg-[#0f1420] border border-[#1e2638] rounded-2xl p-5 shadow-sm">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-1">
            <span>Observed Recovery Rate</span>
            <Percent className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">
            {(metrics?.recovery_rate || 0).toFixed(2)}%
          </div>
          <div className="text-[11px] text-slate-400 mt-1">Yield on recoverable pool</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* A. Failure Breakdown Chart */}
        <div className="bg-[#0f1420] border border-[#1e2638] rounded-2xl p-6 space-y-4 shadow-sm">
          <div className="flex items-center justify-between pb-3 border-b border-[#1e2638]">
            <div>
              <h3 className="text-sm font-semibold text-white font-sans">Failure Code Breakdown</h3>
              <p className="text-[11px] text-slate-400">Distribution of failure codes across failed payments</p>
            </div>
            <BarChart3 className="w-4 h-4 text-blue-400" />
          </div>

          <div className="space-y-3 pt-2">
            {failureItems.map(([code, count]) => {
              const amount = failures?.amount_by_code[code] || 0;
              const pct = ((count / (failures?.total_failures || 1)) * 100).toFixed(1);
              const barWidth = Math.max(8, Math.min(100, (count / maxFailureCount) * 100));

              return (
                <div key={code} className="space-y-1">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="text-slate-300 font-medium">{code}</span>
                    <span className="text-slate-400 text-[11px]">
                      <strong className="text-white">{count}</strong> cases ({pct}%) · {formatCurrency(amount)}
                    </span>
                  </div>
                  <div className="h-2 bg-[#080b12] rounded-full overflow-hidden border border-[#161c28]">
                    <div
                      className={`h-full rounded-full ${
                        code.includes("risk")
                          ? "bg-rose-500"
                          : code.includes("bank")
                          ? "bg-blue-500"
                          : code.includes("card")
                          ? "bg-cyan-500"
                          : "bg-indigo-500"
                      }`}
                      style={{ width: `${barWidth}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* B. Revenue Breakdown */}
        <div className="bg-[#0f1420] border border-[#1e2638] rounded-2xl p-6 space-y-4 shadow-sm">
          <div className="flex items-center justify-between pb-3 border-b border-[#1e2638]">
            <div>
              <h3 className="text-sm font-semibold text-white font-sans">Three-Tier Revenue Breakdown</h3>
              <p className="text-[11px] text-slate-400">Deterministic pipeline progression</p>
            </div>
            <Activity className="w-4 h-4 text-indigo-400" />
          </div>

          <div className="space-y-4 pt-2">
            <div className="p-4 rounded-xl bg-[#080b12] border border-[#161c28] flex items-center justify-between">
              <div>
                <div className="text-xs text-slate-400 font-mono">Gross Volume at Risk</div>
                <div className="text-lg font-bold text-rose-400 font-mono">
                  {formatCurrency(metrics?.gross_revenue_at_risk)}
                </div>
              </div>
              <span className="text-xs font-mono text-slate-400">100% of Failures</span>
            </div>

            <div className="p-4 rounded-xl bg-[#080b12] border border-[#161c28] flex items-center justify-between">
              <div>
                <div className="text-xs text-slate-400 font-mono">Potentially Recoverable (P ≥ 60%)</div>
                <div className="text-lg font-bold text-blue-400 font-mono">
                  {formatCurrency(metrics?.potentially_recoverable_revenue)}
                </div>
              </div>
              <span className="text-xs font-mono text-blue-400 font-semibold">
                {(((metrics?.potentially_recoverable_revenue || 0) / (metrics?.gross_revenue_at_risk || 1)) * 100).toFixed(1)}% of Risk
              </span>
            </div>

            <div className="p-4 rounded-xl bg-[#080b12] border border-[#161c28] flex items-center justify-between">
              <div>
                <div className="text-xs text-slate-400 font-mono">Expected Recovery Value (ERV)</div>
                <div className="text-lg font-bold text-cyan-400 font-mono">
                  {formatCurrency(metrics?.total_expected_recovery_value)}
                </div>
              </div>
              <span className="text-xs font-mono text-slate-400">Weighted Expectation</span>
            </div>

            <div className="p-4 rounded-xl bg-[#080b12] border border-emerald-500/40 bg-emerald-950/15 flex items-center justify-between shadow-sm">
              <div>
                <div className="text-xs text-emerald-400 font-mono font-semibold">Observed Revenue Recovered</div>
                <div className="text-lg font-bold text-emerald-400 font-mono">
                  {formatCurrency(metrics?.revenue_recovered)}
                </div>
              </div>
              <span className="text-xs font-mono text-emerald-400 font-bold">
                {(metrics?.recovery_rate || 0).toFixed(1)}% Recovered
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
