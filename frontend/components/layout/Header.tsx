"use client";

import React, { useEffect, useState } from "react";
import { fetchHealth } from "@/lib/api";
import { HealthStatus } from "@/types";
import { Bot, Server, ShieldCheck, Zap } from "lucide-react";

export function Header() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchHealth()
      .then((data) => {
        setHealth(data);
        setLoading(false);
      })
      .catch(() => {
        setLoading(false);
      });
  }, []);

  return (
    <header className="h-16 bg-[#0a0d14]/90 backdrop-blur-md border-b border-[#1a2130] px-6 lg:px-8 flex items-center justify-between sticky top-0 z-30 shadow-sm">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
          <Zap className="w-4 h-4 text-white" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-sm lg:text-base font-bold text-white tracking-tight font-sans">
              Autonomous Revenue Recovery
            </h1>
            <span className="hidden sm:inline-block text-[11px] px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 font-mono border border-blue-500/20">
              RecoverAI
            </span>
          </div>
          <p className="text-[11px] text-slate-400 font-normal hidden md:block">
            Detect · Diagnose · Decide · Act · Recover
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2.5">
        {/* AI Agent Telemetry Status */}
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-[#121722] border border-[#1e2738] text-xs shadow-inner">
          <Bot className="w-3.5 h-3.5 text-cyan-400" />
          <span className="text-slate-400 hidden sm:inline text-[11px]">AI Agent:</span>
          <span className="flex items-center gap-1.5 text-cyan-300 font-semibold text-[11px] font-mono">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            ONLINE
          </span>
        </div>

        {/* Backend Server Status */}
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-[#121722] border border-[#1e2738] text-xs shadow-inner">
          <Server className="w-3.5 h-3.5 text-emerald-400" />
          <span className="text-slate-400 hidden sm:inline text-[11px]">Backend:</span>
          {loading ? (
            <span className="text-slate-500 animate-pulse text-[11px]">Connecting...</span>
          ) : health?.status === "ok" ? (
            <span className="flex items-center gap-1.5 text-emerald-400 font-semibold text-[11px] font-mono">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              ONLINE
            </span>
          ) : (
            <span className="flex items-center gap-1.5 text-rose-400 font-medium text-[11px] font-mono">
              <span className="w-2 h-2 rounded-full bg-rose-400" />
              OFFLINE
            </span>
          )}
        </div>

        {/* Operating Mode Indicator */}
        <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/20 text-xs font-mono">
          <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />
          <span className="text-amber-300 font-semibold uppercase tracking-wider text-[10px]">
            {health?.mode || "simulation"} MODE
          </span>
        </div>
      </div>
    </header>
  );
}
