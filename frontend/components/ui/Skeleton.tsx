import React from "react";

export function SkeletonCard({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse bg-[#1a1d27] border border-[#2a2d3a] rounded-xl p-5 ${className}`}
    >
      <div className="h-4 bg-slate-800 rounded w-1/3 mb-3"></div>
      <div className="h-8 bg-slate-800 rounded w-2/3 mb-2"></div>
      <div className="h-3 bg-slate-800 rounded w-1/2"></div>
    </div>
  );
}

export function SkeletonTable({ rows = 5 }: { rows?: number }) {
  return (
    <div className="animate-pulse bg-[#1a1d27] border border-[#2a2d3a] rounded-xl overflow-hidden p-4 space-y-3">
      <div className="h-6 bg-slate-800 rounded w-full mb-4"></div>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-10 bg-slate-800/60 rounded w-full"></div>
      ))}
    </div>
  );
}
