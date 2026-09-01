"use client";

import React from "react";

interface ProbabilityMeterProps {
  value: number; // 0.0 to 1.0 or 0 to 100
  label?: string;
  size?: "sm" | "md" | "lg";
}

export function ProbabilityMeter({
  value,
  label = "Recovery Propensity",
  size = "md",
}: ProbabilityMeterProps) {
  const normVal = value <= 1.0 ? value * 100 : value;
  const clamped = Math.min(100, Math.max(0, normVal));
  const strokeWidth = size === "sm" ? 6 : size === "lg" ? 10 : 8;
  const radius = size === "sm" ? 28 : size === "lg" ? 52 : 40;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (clamped / 100) * circumference;

  const colorClass =
    clamped >= 70
      ? "text-emerald-400 stroke-emerald-500"
      : clamped >= 40
      ? "text-amber-400 stroke-amber-500"
      : "text-rose-400 stroke-rose-500";

  return (
    <div className="flex flex-col items-center justify-center">
      <div className="relative flex items-center justify-center">
        <svg
          className="transform -rotate-90"
          width={(radius + strokeWidth) * 2}
          height={(radius + strokeWidth) * 2}
        >
          {/* Background track */}
          <circle
            cx={radius + strokeWidth}
            cy={radius + strokeWidth}
            r={radius}
            className="stroke-[#1a2130]"
            strokeWidth={strokeWidth}
            fill="transparent"
          />
          {/* Progress arc */}
          <circle
            cx={radius + strokeWidth}
            cy={radius + strokeWidth}
            r={radius}
            className={`transition-all duration-1000 ease-out ${colorClass}`}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            fill="transparent"
          />
        </svg>
        <div className="absolute flex flex-col items-center justify-center text-center">
          <span className={`font-mono font-bold tracking-tight ${colorClass} ${size === "sm" ? "text-sm" : size === "lg" ? "text-2xl" : "text-lg"}`}>
            {clamped.toFixed(0)}%
          </span>
          {size !== "sm" && (
            <span className="text-[9px] uppercase tracking-wider text-slate-400 font-mono">
              Score
            </span>
          )}
        </div>
      </div>
      {label && (
        <span className="text-[11px] font-medium text-slate-300 mt-2 font-mono text-center">
          {label}
        </span>
      )}
    </div>
  );
}
