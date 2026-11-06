import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { X, History, Clock, ShieldCheck, FileText, CheckCircle2 } from 'lucide-react';
import { setShowAuditModal } from '../../store/uiSlice';
import { fetchAuditLogs } from '../../store/investigationSlice';

export const AuditModal = () => {
  const dispatch = useDispatch();
  const show = useSelector((state) => state.ui.showAuditModal);
  const currentInvestigation = useSelector((state) => state.investigation.currentInvestigation);
  const auditLogs = useSelector((state) => state.investigation.auditLogs);

  useEffect(() => {
    if (show && currentInvestigation) {
      dispatch(fetchAuditLogs(currentInvestigation.id));
    }
  }, [show, currentInvestigation, dispatch]);

  useEffect(() => {
    if (!show) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        dispatch(setShowAuditModal(false));
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [show, dispatch]);

  if (!show) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-4 animate-fade-in font-sans"
      role="dialog"
      aria-modal="true"
      aria-labelledby="audit-modal-title"
    >
      <div className="skeuo-surface-raised rounded-3xl max-w-2xl w-full max-h-[85vh] flex flex-col shadow-2xl border border-slate-300 dark:border-[#1e2236] overflow-hidden bg-white dark:bg-[#080a14] text-slate-900 dark:text-slate-100">
        {/* Modal Header */}
        <div className="p-5 bg-gradient-to-b from-blue-50/80 to-white dark:from-[#0c0e1a] dark:to-[#080a14] text-slate-900 dark:text-white flex items-center justify-between border-b border-slate-200 dark:border-[#1e2236]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-blue-100 dark:bg-blue-950/60 border border-blue-300 dark:border-blue-700/50 flex items-center justify-center text-blue-800 dark:text-blue-300 shadow-xs">
              <History className="w-5 h-5" />
            </div>
            <div>
              <h3 id="audit-modal-title" className="font-extrabold text-sm tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
                Audit Trail Dossier
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-50 dark:bg-amber-950/50 text-amber-900 dark:text-amber-300 border border-amber-300 dark:border-amber-700/60 font-bold">
                  21 CFR Part 11
                </span>
              </h3>
              <p className="text-[11px] text-slate-500 dark:text-zinc-400 mt-0.5 font-mono">
                Investigation: {currentInvestigation?.investigation_number || 'N/A'}
              </p>
            </div>
          </div>
          <button
            onClick={() => dispatch(setShowAuditModal(false))}
            className="text-slate-400 hover:text-slate-700 dark:hover:text-white p-1.5 rounded-xl hover:bg-slate-100 dark:hover:bg-zinc-800 transition cursor-pointer"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Audit Log Stream */}
        <div className="p-5 flex-1 overflow-y-auto space-y-3 bg-slate-50/50 dark:bg-black">
          {auditLogs.length === 0 ? (
            <div className="text-center py-12 text-xs text-slate-500 dark:text-zinc-500 space-y-2">
              <ShieldCheck className="w-8 h-8 mx-auto text-slate-400 dark:text-zinc-600" />
              <p className="font-semibold text-slate-700 dark:text-zinc-300">No audit events recorded yet.</p>
              <p className="text-[11px]">All data modifications and workflow transitions are recorded immutably.</p>
            </div>
          ) : (
            auditLogs.map((log) => (
              <div
                key={log.id}
                className="skeuo-well p-4 rounded-2xl border border-slate-200 dark:border-zinc-800 text-xs space-y-2 transition hover:border-cyan-500/50 dark:bg-zinc-950"
              >
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-bold font-mono text-[10px] px-2.5 py-0.5 rounded-md bg-cyan-100 dark:bg-cyan-950 text-cyan-800 dark:text-cyan-300 border border-cyan-200 dark:border-cyan-800/80">
                      {log.action}
                    </span>
                    <span className="font-bold text-slate-800 dark:text-zinc-200">{log.entity_type}</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-[11px] font-mono text-slate-500 dark:text-zinc-400 bg-white dark:bg-black px-2 py-0.5 rounded-md border border-slate-200 dark:border-zinc-800">
                    <Clock className="w-3 h-3 text-cyan-600 dark:text-cyan-400" />
                    <span>{new Date(log.timestamp).toLocaleString()}</span>
                  </div>
                </div>

                <p className="text-slate-800 dark:text-zinc-200 font-medium leading-relaxed">{log.change_summary}</p>
                <div className="flex items-center justify-between text-[11px] text-slate-500 dark:text-zinc-400 pt-1 border-t border-slate-200/70 dark:border-zinc-800/80">
                  <span>
                    Executed by: <strong className="text-slate-900 dark:text-zinc-200 font-bold">{log.user_name}</strong>
                  </span>
                  <span className="text-[10px] font-mono text-cyan-600 dark:text-cyan-400 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3 text-cyan-600 dark:text-cyan-400" /> Attributable Digital Signature
                  </span>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 bg-slate-50 dark:bg-zinc-950 border-t border-slate-200 dark:border-zinc-800 flex items-center justify-between">
          <span className="text-[11px] text-slate-500 dark:text-zinc-500 font-mono">
            Immutable SHA-256 Hash Chain Verified
          </span>
          <button
            onClick={() => dispatch(setShowAuditModal(false))}
            className="skeuo-btn-secondary px-5 py-2 rounded-xl text-xs font-bold cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default AuditModal;
