import React from "react";

interface LoadingErrorProps {
  message?: string;
  onRetry?: () => void;
}

export function LoadingError({
  message = "Unable to connect to RecoverAI Backend API",
  onRetry,
}: LoadingErrorProps) {
  return (
    <div className="bg-[#1a1d27] border border-rose-500/20 rounded-xl p-8 text-center max-w-lg mx-auto my-8">
      <div className="w-12 h-12 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center mx-auto mb-4 text-xl">
        ✕
      </div>
      <h3 className="text-lg font-semibold text-white mb-2">Backend Connection Error</h3>
      <p className="text-slate-400 text-sm mb-6">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors inline-flex items-center gap-2"
        >
          <span>↻</span> Retry Connection
        </button>
      )}
    </div>
  );
}

export function EmptyState({
  title = "No Records Found",
  message = "No items match your active filters or dataset queries.",
}: {
  title?: string;
  message?: string;
}) {
  return (
    <div className="bg-[#1a1d27] border border-[#2a2d3a] rounded-xl p-12 text-center my-6">
      <div className="w-12 h-12 rounded-full bg-slate-800 border border-slate-700 text-slate-400 flex items-center justify-center mx-auto mb-3 text-lg">
        ∅
      </div>
      <h4 className="text-base font-medium text-white mb-1">{title}</h4>
      <p className="text-slate-400 text-xs max-w-sm mx-auto">{message}</p>
    </div>
  );
}
