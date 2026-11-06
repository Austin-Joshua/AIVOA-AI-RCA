import React from 'react';
import { Sparkles, CheckCircle2 } from 'lucide-react';

export const AiBadge = ({ isAiSuggested, isVerified, onVerify, label = 'AI Suggested' }) => {
  if (isVerified) {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 shadow-sm">
        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
        Investigator Verified
      </span>
    );
  }

  if (isAiSuggested) {
    return (
      <div className="inline-flex items-center gap-1.5">
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-800 border border-amber-200 shadow-sm">
          <Sparkles className="w-3.5 h-3.5 text-amber-500 animate-pulse" />
          {label} (Pending Verification)
        </span>
        {onVerify && (
          <button
            onClick={onVerify}
            type="button"
            className="text-xs text-blue-600 hover:text-blue-800 underline font-medium hover:bg-blue-50 px-1 py-0.5 rounded transition"
          >
            Verify
          </button>
        )}
      </div>
    );
  }

  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200">
      Manual Entry
    </span>
  );
};

export default AiBadge;

