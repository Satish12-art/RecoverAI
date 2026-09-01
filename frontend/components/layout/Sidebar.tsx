"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  RotateCcw,
  BarChart3,
  Scale,
  ScrollText,
  ShieldCheck,
  Zap,
  Activity,
} from "lucide-react";

export function Sidebar() {
  const pathname = usePathname();

  const navSections = [
    {
      title: "OVERVIEW",
      items: [{ label: "Dashboard", href: "/", icon: LayoutDashboard }],
    },
    {
      title: "OPERATIONS",
      items: [{ label: "Recovery Cases", href: "/cases", icon: RotateCcw }],
    },
    {
      title: "INTELLIGENCE",
      items: [
        { label: "Analytics", href: "/analytics", icon: BarChart3 },
        { label: "Evaluation", href: "/evaluation", icon: Scale },
      ],
    },
    {
      title: "GOVERNANCE",
      items: [{ label: "Audit Trail", href: "/audit", icon: ScrollText }],
    },
  ];

  return (
    <aside className="w-64 bg-[#0a0d14] border-r border-[#1a2130] flex flex-col justify-between shrink-0 h-screen sticky top-0 z-30 select-none">
      <div>
        {/* Brand Header */}
        <div className="h-16 flex items-center px-6 border-b border-[#1a2130] gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-blue-600 to-cyan-500 flex items-center justify-center shadow-md shadow-blue-500/20">
            <Zap className="w-4 h-4 text-white" />
          </div>
          <div>
            <div className="font-bold text-base tracking-tight text-white flex items-center gap-1.5 font-sans">
              RecoverAI
              <span className="text-[9px] uppercase font-mono px-1.5 py-0.5 bg-blue-500/10 text-blue-400 rounded border border-blue-500/30">
                Core
              </span>
            </div>
            <div className="text-[10px] text-slate-400 font-mono tracking-wide">
              AUTONOMOUS RECOVERY
            </div>
          </div>
        </div>

        {/* Live Engine Status Card */}
        <div className="px-4 pt-4 pb-2">
          <div className="flex items-center justify-between px-3 py-2 rounded-lg bg-[#0f1420] border border-[#1e2638] text-xs">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-sm shadow-emerald-400/50"></span>
              <span className="font-medium text-slate-200 text-[11px]">Agent Online</span>
            </div>
            <span className="text-[9px] font-mono text-cyan-400 font-semibold px-1.5 py-0.5 rounded bg-cyan-950/40 border border-cyan-500/30">
              POLICY-GATED
            </span>
          </div>
        </div>

        {/* Navigation Sections */}
        <nav className="p-4 space-y-4">
          {navSections.map((section) => (
            <div key={section.title} className="space-y-1">
              <div className="text-[10px] font-semibold text-slate-400 px-3 uppercase tracking-wider font-mono">
                {section.title}
              </div>
              {section.items.map((item) => {
                const Icon = item.icon;
                const active =
                  pathname === item.href ||
                  (item.href !== "/" && pathname.startsWith(item.href));
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-medium transition-all group ${
                      active
                        ? "bg-blue-600/15 text-blue-400 border border-blue-500/30 shadow-sm font-semibold"
                        : "text-slate-400 hover:text-slate-200 hover:bg-[#121724]"
                    }`}
                  >
                    <Icon
                      className={`w-4 h-4 transition-colors ${
                        active
                          ? "text-blue-400"
                          : "text-slate-400 group-hover:text-slate-300"
                      }`}
                    />
                    <span>{item.label}</span>
                    {active && (
                      <span className="ml-auto w-1.5 h-1.5 rounded-full bg-blue-400 shadow-sm shadow-blue-400/80" />
                    )}
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>
      </div>

      {/* Footer Guardrail Badge */}
      <div className="p-4 border-t border-[#1a2130]">
        <div className="p-3 rounded-lg bg-[#0f1420] border border-[#1e2638] flex items-start gap-2.5">
          <ShieldCheck className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
          <div className="text-xs">
            <div className="font-semibold text-slate-200 text-[11px]">Durable Safety Gate</div>
            <div className="text-[10px] text-slate-400 mt-0.5 leading-relaxed">
              10 deterministic policy rules enforce 100% compliance before write actions.
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}
