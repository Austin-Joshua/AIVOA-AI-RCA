import React, { useEffect } from 'react';
import { CheckCircle2, AlertTriangle, Info, AlertOctagon, X } from 'lucide-react';

export const Toast = ({
  type = 'info',
  message,
  onDismiss,
  duration = 5000,
  action = null,
}) => {
  useEffect(() => {
    if (duration > 0 && onDismiss) {
      const timer = setTimeout(onDismiss, duration);
      return () => clearTimeout(timer);
    }
  }, [duration, onDismiss]);

  const styles = {
    success: 'bg-emerald-900/95 text-emerald-100 border-emerald-700/80 shadow-emerald-950/20',
    error: 'bg-rose-900/95 text-rose-100 border-rose-700/80 shadow-rose-950/20',
    warning: 'bg-amber-900/95 text-amber-100 border-amber-700/80 shadow-amber-950/20',
    info: 'bg-slate-900/95 text-slate-100 border-slate-700/80 shadow-slate-950/20',
  };

  const icons = {
    success: <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />,
    error: <AlertOctagon className="w-4 h-4 text-rose-400 shrink-0" />,
    warning: <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />,
    info: <Info className="w-4 h-4 text-cyan-400 shrink-0" />,
  };

  return (
    <div
      role="status"
      className={`flex items-center justify-between gap-3 px-4 py-3 rounded-xl border shadow-xl backdrop-blur-xs text-xs font-medium animate-fade-in ${
        styles[type] || styles.info
      }`}
    >
      <div className="flex items-center gap-2.5 min-w-0">
        {icons[type] || icons.info}
        <span className="leading-snug">{message}</span>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {action}
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="p-1 rounded-md opacity-70 hover:opacity-100 hover:bg-white/10 transition"
            aria-label="Dismiss toast"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </div>
  );
};

export default Toast;

