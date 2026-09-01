"use client";

import React from "react";

export function SimulationBanner({ mode = "simulation" }: { mode?: string }) {
  if (mode !== "simulation") return null;

  return (
    <div className="bg-amber-950/40 border-b border-amber-800/50 px-4 py-2 text-xs text-amber-200 flex items-center justify-between">
      <div className="flex items-center space-x-2">
        <span className="inline-block w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
        <span className="font-semibold tracking-wider uppercase">Simulation Mode</span>
        <span className="text-amber-300/70">— No real money is being moved. Recovery actions and amounts are simulated for testing and evaluation.</span>
      </div>
      <span className="bg-amber-900/60 text-amber-300 border border-amber-700/60 px-2 py-0.5 rounded text-[10px] font-mono">
        SAFETY BOUNDED
      </span>
    </div>
  );
}
