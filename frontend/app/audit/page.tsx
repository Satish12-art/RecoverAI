"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { fetchAuditEvents } from "@/lib/api";
import { AuditEventItem } from "@/types";
import { Badge } from "@/components/ui/Badge";
import { SkeletonTable } from "@/components/ui/Skeleton";
import { LoadingError, EmptyState } from "@/components/ui/LoadingError";
import {
  ScrollText,
  ShieldCheck,
  Search,
  RotateCcw,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  AlertTriangle,
  Lock,
} from "lucide-react";

export default function AuditPage() {
  const [events, setEvents] = useState<AuditEventItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  // Filters
  const [toolFilter, setToolFilter] = useState("");
  const [policyFilter, setPolicyFilter] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  const loadAudit = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchAuditEvents({
        page,
        page_size: pageSize,
        tool_name: toolFilter || undefined,
        policy_decision: policyFilter || undefined,
        search: searchQuery || undefined,
      });
      setEvents(data.items || []);
      setTotal(data.total || 0);
    } catch (err: any) {
      setError(err.message || "Failed to load audit events");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAudit();
  }, [page, toolFilter, policyFilter]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadAudit();
  };

  const handleReset = () => {
    setToolFilter("");
    setPolicyFilter("");
    setSearchQuery("");
    setPage(1);
  };

  const totalPages = Math.ceil(total / pageSize) || 1;

  const policyGuardrails = [
    { rule: "Rule 1: Already Paid", action: "STOP", desc: "Prevents duplicate charges on settled payments." },
    { rule: "Rule 2: Risk Flagged", action: "STOP", desc: "Halts retries immediately on velocity/fraud alerts." },
    { rule: "Rule 3: Opted Out", action: "STOP", desc: "Respects customer marketing and contact opt-outs." },
    { rule: "Rule 4: Invalid State", action: "STOP", desc: "Non-failed payment records are ignored." },
    { rule: "Rule 5: Unknown Action", action: "REJECT", desc: "Arbitrary hallucinated actions rejected by schema." },
    { rule: "Rule 6: Retry Limit (≥2)", action: "ESCALATE", desc: "Caps auto-retries at 2 to protect merchant reputation." },
    { rule: "Rule 7: Probability (<60%)", action: "ESCALATE", desc: "Low likelihood cases escalated for ops review." },
    { rule: "Rule 8: Confidence (<70%)", action: "ESCALATE", desc: "Uncertain predictions escalated to human ops." },
    { rule: "Rule 9: High Amount (>₹50k)", action: "ESCALATE", desc: "Transactions > ₹50,000 require manual sign-off." },
    { rule: "Rule 10: All Checks Pass", action: "APPROVE", desc: "Safe actions execute via bounded write tools." },
  ];

  return (
    <div className="p-6 lg:p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-[#1e2638]">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight font-sans">Audit Trail & Governance Console</h2>
          <p className="text-xs text-slate-400 font-mono mt-0.5">
            Immutable log of all agent tool executions, policy gates, and outcome observations
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono text-slate-400 bg-[#0f1420] border border-[#1e2638] px-3 py-1.5 rounded-lg shadow-sm">
          <Lock className="w-3.5 h-3.5 text-emerald-400" />
          <span>Audit Log Immutable</span>
        </div>
      </div>

      {/* 1. TOP POLICY GUARDRAIL PANEL */}
      <div className="bg-[#0f1420] border border-[#1e2638] rounded-2xl p-6 space-y-4 shadow-sm">
        <div className="flex items-center justify-between pb-3 border-b border-[#1e2638]">
          <div>
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              Active Deterministic Policy Guardrails (10 Rules)
            </h3>
            <p className="text-[11px] text-slate-400">Enforced before any financial write action can execute</p>
          </div>
          <span className="text-[10px] font-mono text-emerald-400 px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20">
            ZERO BYPASS
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-2.5 pt-1">
          {policyGuardrails.map((g, idx) => (
            <div key={idx} className="p-2.5 rounded-xl bg-[#080b12] border border-[#161c28] text-xs space-y-1">
              <div className="flex items-center justify-between font-mono">
                <span className="font-semibold text-slate-200 text-[11px]">{g.rule.split(":")[0]}</span>
                <Badge
                  size="sm"
                  variant={
                    g.action === "APPROVE"
                      ? "approved"
                      : g.action === "ESCALATE"
                      ? "escalate"
                      : "stop"
                  }
                >
                  {g.action}
                </Badge>
              </div>
              <p className="text-[10px] text-slate-400 leading-tight">{g.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* 2. SEARCH AND FILTER BAR */}
      <div className="bg-[#0f1420] border border-[#1e2638] rounded-2xl p-4 space-y-3 shadow-sm">
        <form onSubmit={handleSearch} className="flex flex-col md:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search audit trail by reasoning summary or policy decision..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#080b12] border border-[#161c28] rounded-lg pl-9 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 font-mono"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium rounded-lg transition-colors font-mono"
          >
            Search Logs
          </button>
        </form>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 pt-1">
          <div>
            <label className="text-[10px] uppercase font-mono text-slate-400 block mb-1">Tool Executed</label>
            <select
              value={toolFilter}
              onChange={(e) => { setToolFilter(e.target.value); setPage(1); }}
              className="w-full bg-[#080b12] border border-[#161c28] rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-blue-500 font-mono"
            >
              <option value="">All Tools</option>
              <option value="request_payment_retry">request_payment_retry</option>
              <option value="send_recovery_message">send_recovery_message</option>
              <option value="escalate_to_human">escalate_to_human</option>
              <option value="observe_outcome">observe_outcome</option>
            </select>
          </div>

          <div>
            <label className="text-[10px] uppercase font-mono text-slate-400 block mb-1">Policy Gate Decision</label>
            <select
              value={policyFilter}
              onChange={(e) => { setPolicyFilter(e.target.value); setPage(1); }}
              className="w-full bg-[#080b12] border border-[#161c28] rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-blue-500 font-mono"
            >
              <option value="">All Policy Decisions</option>
              <option value="APPROVED">Approved</option>
              <option value="STOPPED">Stopped</option>
              <option value="ESCALATED">Escalated</option>
              <option value="REJECTED">Rejected</option>
            </select>
          </div>

          <div className="flex items-end md:col-span-2">
            <button
              type="button"
              onClick={handleReset}
              className="py-1.5 px-4 bg-[#121622] hover:bg-[#182030] border border-[#1e2638] text-slate-300 rounded-lg text-xs font-medium transition-colors flex items-center justify-center gap-1.5 font-mono"
            >
              <RotateCcw className="w-3.5 h-3.5" /> Reset Filters
            </button>
          </div>
        </div>
      </div>

      {/* 3. AUDIT EVENTS TABLE */}
      {loading ? (
        <SkeletonTable rows={10} />
      ) : error ? (
        <LoadingError message={error} onRetry={loadAudit} />
      ) : events.length === 0 ? (
        <EmptyState title="No Audit Records Found" message="Execute a simulation from the dashboard to populate live audit records." />
      ) : (
        <div className="bg-[#0f1420] border border-[#1e2638] rounded-2xl overflow-hidden shadow-lg">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#080b12] text-slate-400 uppercase font-mono text-[11px] border-b border-[#1e2638]">
                <tr>
                  <th className="py-3 px-4">Event ID / Time</th>
                  <th className="py-3 px-4">Case / Payment</th>
                  <th className="py-3 px-4">Tool Name</th>
                  <th className="py-3 px-4">Policy Gate</th>
                  <th className="py-3 px-4">Reasoning Summary</th>
                  <th className="py-3 px-4">Policy Rationale</th>
                  <th className="py-3 px-4 text-right">Actor</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#161c28] text-slate-300 font-mono text-[11px]">
                {events.map((ev) => (
                  <tr key={ev.id} className="hover:bg-[#121724] transition-colors">
                    <td className="py-3.5 px-4">
                      <div className="text-white font-bold">#{ev.id}</div>
                      <div className="text-[10px] text-slate-400">
                        {ev.created_at ? new Date(ev.created_at).toLocaleTimeString() : "—"}
                      </div>
                    </td>
                    <td className="py-3.5 px-4">
                      {ev.recovery_case_id ? (
                        <Link
                          href={`/cases/${ev.recovery_case_id}`}
                          className="text-blue-400 hover:text-blue-300 font-medium underline underline-offset-2"
                        >
                          Case #{ev.recovery_case_id}
                        </Link>
                      ) : (
                        <span className="text-slate-500">—</span>
                      )}
                      {ev.external_payment_id && (
                        <div className="text-[10px] text-slate-400">{ev.external_payment_id}</div>
                      )}
                    </td>
                    <td className="py-3.5 px-4 font-semibold text-slate-200">
                      <span className="px-2 py-0.5 rounded bg-[#080b12] border border-[#161c28]">
                        {ev.tool_name}
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      <Badge variant={ev.policy_decision.toLowerCase()}>
                        {ev.policy_decision}
                      </Badge>
                    </td>
                    <td className="py-3.5 px-4 font-sans text-xs text-slate-300 max-w-xs truncate">
                      {ev.reasoning_summary}
                    </td>
                    <td className="py-3.5 px-4 font-sans text-[11px] text-slate-400 max-w-xs truncate">
                      {ev.policy_reason}
                    </td>
                    <td className="py-3.5 px-4 text-right text-slate-400">
                      <span className="px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 text-[10px]">
                        {ev.actor}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="p-4 border-t border-[#1e2638] flex items-center justify-between text-xs text-slate-400">
            <div>
              Showing Page <strong className="text-white font-mono">{page}</strong> of <strong className="text-white font-mono">{totalPages}</strong> ({total} events)
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
