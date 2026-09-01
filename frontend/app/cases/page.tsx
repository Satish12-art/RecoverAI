"use client";

import React, { useEffect, useState, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { fetchCases } from "@/lib/api";
import { RecoveryCaseItem } from "@/types";
import { Badge } from "@/components/ui/Badge";
import { SkeletonTable } from "@/components/ui/Skeleton";
import { LoadingError, EmptyState } from "@/components/ui/LoadingError";
import {
  Search,
  ArrowRight,
  ChevronLeft,
  ChevronRight,
  RotateCcw,
  Bot,
} from "lucide-react";

function CasesContent() {
  const searchParams = useSearchParams();
  const initFailureCode = searchParams.get("failure_code") || "";
  const initAction = searchParams.get("action") || "";
  const initStatus = searchParams.get("status") || "";

  const [cases, setCases] = useState<RecoveryCaseItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filter states
  const [statusFilter, setStatusFilter] = useState(initStatus);
  const [actionFilter, setActionFilter] = useState(initAction);
  const [failureFilter, setFailureFilter] = useState(initFailureCode);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("expected_recovery_value");

  const loadCases = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchCases({
        page,
        page_size: pageSize,
        status: statusFilter || undefined,
        action: actionFilter || undefined,
        failure_code: failureFilter || undefined,
        search: searchQuery || undefined,
        sort_by: sortBy,
      });
      setCases(data.items || []);
      setTotal(data.total || 0);
    } catch (err: any) {
      setError(err.message || "Failed to load recovery cases");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCases();
  }, [page, statusFilter, actionFilter, failureFilter, sortBy]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadCases();
  };

  const handleResetFilters = () => {
    setStatusFilter("");
    setActionFilter("");
    setFailureFilter("");
    setSearchQuery("");
    setSortBy("expected_recovery_value");
    setPage(1);
  };

  const formatCurrency = (val?: number) => {
    if (val === undefined || val === null) return "₹0.00";
    return `₹${val.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  return (
    <div className="p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-[#1e2638]">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight font-sans">Recovery Cases</h2>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            Inspect individual failed transactions, AI decision traces, and policy governance
          </p>
        </div>
        <div className="text-xs font-mono text-slate-400 bg-[#0f1420] border border-[#1e2638] px-3 py-1.5 rounded-lg self-start md:self-auto shadow-sm">
          Total Cases: <strong className="text-white">{total.toLocaleString()}</strong>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="bg-[#0f1420] border border-[#1e2638] rounded-2xl p-4 space-y-4 shadow-sm">
        <form onSubmit={handleSearchSubmit} className="flex flex-col md:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by Payment ID (e.g. pay_0000017) or Customer Name..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#080b12] border border-[#161c28] rounded-lg pl-9 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 font-mono"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium rounded-lg transition-colors font-mono"
          >
            Search
          </button>
        </form>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 pt-1">
          {/* Status Filter */}
          <div>
            <label className="text-[10px] uppercase font-mono text-slate-400 block mb-1">Status</label>
            <select
              value={statusFilter}
              onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
              className="w-full bg-[#080b12] border border-[#161c28] rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-blue-500 font-mono"
            >
              <option value="">All Statuses</option>
              <option value="RECOVERING">Recovering</option>
              <option value="RECOVERED">Recovered</option>
              <option value="FAILED">Failed</option>
              <option value="ESCALATED">Escalated</option>
              <option value="STOPPED">Stopped</option>
              <option value="OPEN">Open</option>
            </select>
          </div>

          {/* Action Filter */}
          <div>
            <label className="text-[10px] uppercase font-mono text-slate-400 block mb-1">AI Action</label>
            <select
              value={actionFilter}
              onChange={(e) => { setActionFilter(e.target.value); setPage(1); }}
              className="w-full bg-[#080b12] border border-[#161c28] rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-blue-500 font-mono"
            >
              <option value="">All Actions</option>
              <option value="retry">Retry</option>
              <option value="message">Message</option>
              <option value="escalate">Escalate</option>
              <option value="stop">Stop</option>
            </select>
          </div>

          {/* Failure Code Filter */}
          <div>
            <label className="text-[10px] uppercase font-mono text-slate-400 block mb-1">Failure Code</label>
            <select
              value={failureFilter}
              onChange={(e) => { setFailureFilter(e.target.value); setPage(1); }}
              className="w-full bg-[#080b12] border border-[#161c28] rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-blue-500 font-mono"
            >
              <option value="">All Failure Codes</option>
              <option value="temporary_bank_error">temporary_bank_error</option>
              <option value="network_error">network_error</option>
              <option value="insufficient_funds">insufficient_funds</option>
              <option value="expired_card">expired_card</option>
              <option value="authentication_failure">authentication_failure</option>
              <option value="risk_flagged">risk_flagged</option>
              <option value="unknown_failure">unknown_failure</option>
            </select>
          </div>

          {/* Sort Filter */}
          <div>
            <label className="text-[10px] uppercase font-mono text-slate-400 block mb-1">Sort By</label>
            <select
              value={sortBy}
              onChange={(e) => { setSortBy(e.target.value); setPage(1); }}
              className="w-full bg-[#080b12] border border-[#161c28] rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-blue-500 font-mono"
            >
              <option value="expected_recovery_value">Expected Value (ERV) DESC</option>
              <option value="amount">Amount at Risk DESC</option>
              <option value="id">Latest Case ID</option>
            </select>
          </div>

          {/* Reset Button */}
          <div className="flex items-end">
            <button
              type="button"
              onClick={handleResetFilters}
              className="w-full py-1.5 px-3 bg-[#121622] hover:bg-[#182030] border border-[#1e2638] text-slate-300 rounded-lg text-xs font-medium transition-colors flex items-center justify-center gap-1.5 font-mono"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Reset Filters
            </button>
          </div>
        </div>
      </div>

      {/* Content Table */}
      {loading ? (
        <SkeletonTable rows={10} />
      ) : error ? (
        <LoadingError message={error} onRetry={loadCases} />
      ) : cases.length === 0 ? (
        <EmptyState title="No Recovery Cases Found" message="Try clearing your filters or running a simulation from the dashboard." />
      ) : (
        <div className="bg-[#0f1420] border border-[#1e2638] rounded-2xl overflow-hidden shadow-lg">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#080b12] text-slate-400 uppercase font-mono text-[11px] border-b border-[#1e2638]">
                <tr>
                  <th className="py-3 px-4">Case / Payment ID</th>
                  <th className="py-3 px-4">Customer</th>
                  <th className="py-3 px-4">Failure Code</th>
                  <th className="py-3 px-4">Amount at Risk</th>
                  <th className="py-3 px-4">Recovery Probability</th>
                  <th className="py-3 px-4">Expected Value (ERV)</th>
                  <th className="py-3 px-4">AI Action</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#161c28] text-slate-300">
                {cases.map((c) => (
                  <tr key={c.id} className="hover:bg-[#121724] transition-colors">
                    <td className="py-3.5 px-4 font-mono font-medium text-white">
                      <div>{c.external_payment_id}</div>
                      <div className="text-[10px] text-slate-400">Case #{c.id}</div>
                    </td>
                    <td className="py-3.5 px-4">
                      <div className="text-white font-medium">{c.customer_name}</div>
                      <div className="text-[11px] text-slate-400 font-mono">Cust ID: {c.customer_id}</div>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-slate-300">
                      <span className="px-2 py-0.5 rounded bg-[#080b12] border border-[#161c28] text-[11px]">
                        {c.failure_code || "unknown"}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 font-semibold text-white font-mono">
                      {formatCurrency(c.amount_at_risk)}
                    </td>
                    <td className="py-3.5 px-4">
                      {c.recovery_probability !== null && c.recovery_probability !== undefined ? (
                        <div className="flex items-center gap-2">
                          <div className="w-12 bg-[#080b12] rounded-full h-1.5 overflow-hidden border border-[#161c28]">
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
                        className="px-3 py-1 rounded bg-blue-600/10 hover:bg-blue-600/20 text-blue-400 font-medium text-xs border border-blue-500/20 transition-colors inline-flex items-center gap-1 font-mono"
                      >
                        Inspect <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="p-4 border-t border-[#1e2638] flex items-center justify-between text-xs text-slate-400">
            <div>
              Showing Page <strong className="text-white font-mono">{page}</strong> of <strong className="text-white font-mono">{totalPages}</strong> ({total} cases)
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="px-3 py-1.5 rounded bg-[#121622] hover:bg-[#182030] border border-[#1e2638] disabled:opacity-40 disabled:cursor-not-allowed text-white flex items-center gap-1 transition-colors font-mono"
              >
                <ChevronLeft className="w-3.5 h-3.5" /> Previous
              </button>
              <button
                type="button"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="px-3 py-1.5 rounded bg-[#121622] hover:bg-[#182030] border border-[#1e2638] disabled:opacity-40 disabled:cursor-not-allowed text-white flex items-center gap-1 transition-colors font-mono"
              >
                Next <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function CasesPage() {
  return (
    <Suspense fallback={<div className="p-8"><SkeletonTable rows={10} /></div>}>
      <CasesContent />
    </Suspense>
  );
}
