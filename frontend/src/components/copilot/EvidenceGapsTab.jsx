import React, { useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import {
  CheckCircle2,
  Send,
  FileQuestion,
  ShieldAlert,
} from 'lucide-react';
import { respondToEvidenceGap, resolveEvidenceGap } from '../../store/investigationSlice';
import { setNotification } from '../../store/uiSlice';

export const EvidenceGapsTab = () => {
  const dispatch = useDispatch();
  const currentInvestigation = useSelector((state) => state.investigation.currentInvestigation);
  const currentUser = useSelector((state) => state.auth.user);
  const gaps = currentInvestigation?.evidence_gaps || [];

  const [answers, setAnswers] = useState({});
  const [submittingId, setSubmittingId] = useState(null);

  const handleRecordAnswer = async (gap) => {
    const ans = (answers[gap.id] || '').trim();
    if (!ans) return;

    setSubmittingId(gap.id);
    try {
      await dispatch(
        respondToEvidenceGap({
          gapId: gap.id,
          response: ans,
          responderName: currentUser?.full_name || currentInvestigation?.lead_investigator || 'Lead Investigator',
        })
      ).unwrap();

      dispatch(
        setNotification({
          type: 'success',
          message: `Response recorded for '${gap.category}' gap.`,
        })
      );
      setAnswers({ ...answers, [gap.id]: '' });
    } catch (err) {
      dispatch(
        setNotification({
          type: 'error',
          message: `Failed to record response: ${err}`,
        })
      );
    } finally {
      setSubmittingId(null);
    }
  };

  const handleResolveGap = async (gap) => {
    try {
      await dispatch(
        resolveEvidenceGap({
          gapId: gap.id,
          resolverName: currentUser?.full_name || currentInvestigation?.lead_investigator || 'Lead Investigator',
          resolutionNotes: 'Verified that requested record was examined and incorporated into investigation dossier.',
        })
      ).unwrap();

      dispatch(
        setNotification({
          type: 'success',
          message: `Evidence gap #${gap.id} marked as RESOLVED.`,
        })
      );
    } catch (err) {
      dispatch(
        setNotification({
          type: 'error',
          message: `Failed to resolve gap: ${err}`,
        })
      );
    }
  };

  return (
    <div className="space-y-4">
      <div className="p-3 bg-amber-50/70 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800/60 rounded-xl flex items-start gap-2.5">
        <ShieldAlert className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
        <div className="text-xs text-amber-900 dark:text-amber-200 leading-relaxed">
          <strong>Evidence Gap Detection:</strong> The investigation engine identified the following missing records required to substantiate root cause causality before QA closure.
        </div>
      </div>

      {gaps.length === 0 ? (
        <div className="p-6 bg-slate-50 dark:bg-zinc-950/80 border border-dashed border-slate-300 dark:border-zinc-800 rounded-xl text-center">
          <FileQuestion className="w-8 h-8 text-slate-400 dark:text-zinc-600 mx-auto mb-2" />
          <p className="text-xs font-semibold text-slate-700 dark:text-zinc-300">No Evidence Gaps Identified</p>
          <p className="text-[11px] text-slate-500 dark:text-zinc-500 mt-1">
            Complete incident intake or run RCA analysis to detect evidence deficiencies and missing manufacturing records.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {gaps.map((gap) => (
            <div
              key={gap.id}
              className={`p-3.5 rounded-xl border transition ${gap.is_resolved
                  ? 'bg-emerald-50/30 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-800/50'
                  : 'bg-white dark:bg-zinc-950 border-slate-200 dark:border-zinc-800 shadow-2xs space-y-2'
                }`}
            >
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <span className="text-[11px] font-bold uppercase tracking-wider text-slate-600 dark:text-zinc-400 font-mono">
                  {gap.category}
                </span>

                <div className="flex items-center gap-1.5">
                  <span
                    className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full ${gap.urgency === 'HIGH'
                        ? 'bg-rose-100 dark:bg-rose-950 text-rose-800 dark:text-rose-300 border border-rose-200 dark:border-rose-900'
                        : 'bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-900'
                      }`}
                  >
                    {gap.urgency} URGENCY
                  </span>

                  {gap.is_resolved ? (
                    <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-800 dark:text-emerald-300 bg-emerald-100 dark:bg-emerald-950/80 px-2 py-0.5 rounded-full border border-emerald-300 dark:border-emerald-800">
                      <CheckCircle2 className="w-3 h-3 text-emerald-600 dark:text-emerald-400" /> RESOLVED
                    </span>
                  ) : (
                    <button
                      onClick={() => handleResolveGap(gap)}
                      className="px-2 py-0.5 text-[10px] font-bold rounded-full bg-slate-100 dark:bg-zinc-800 hover:bg-emerald-100 dark:hover:bg-emerald-950 text-slate-700 dark:text-zinc-300 hover:text-emerald-800 dark:hover:text-emerald-300 border border-slate-200 dark:border-zinc-700 transition cursor-pointer"
                      title="Mark this gap as resolved"
                    >
                      Mark Resolved
                    </button>
                  )}
                </div>
              </div>

              <p className="text-xs font-semibold text-slate-900 dark:text-zinc-100 leading-snug">
                {gap.question}
              </p>

              <p className="text-[11px] text-slate-500 dark:text-zinc-400 italic">
                <strong>Why Required:</strong> {gap.impact_description}
              </p>

              {gap.suggested_record && (
                <p className="text-[11px] text-blue-700 dark:text-cyan-400 font-medium">
                  <strong>Suggested Record:</strong> {gap.suggested_record}
                </p>
              )}

              {/* Existing Investigator Response History */}
              {gap.investigator_response && (
                <div className="p-2.5 bg-slate-50 dark:bg-black border border-slate-200 dark:border-zinc-800 rounded-lg text-xs space-y-1">
                  <div className="flex items-center justify-between text-[10px] text-slate-500 dark:text-zinc-400">
                    <span>
                      <strong>Response by {gap.responded_by || 'Investigator'}:</strong>
                    </span>
                    {gap.response_timestamp && (
                      <span>{new Date(gap.response_timestamp).toLocaleString()}</span>
                    )}
                  </div>
                  <p className="text-slate-800 dark:text-zinc-200 font-medium leading-relaxed">
                    {gap.investigator_response}
                  </p>
                </div>
              )}

              {/* Response Input */}
              {!gap.is_resolved && (
                <div className="pt-2 flex gap-1.5">
                  <input
                    type="text"
                    placeholder="Enter findings / record number (e.g. CAL-2026-88 reviewed)..."
                    value={answers[gap.id] || ''}
                    onChange={(e) => setAnswers({ ...answers, [gap.id]: e.target.value })}
                    className="flex-1 text-xs px-2.5 py-1.5 border border-slate-200 dark:border-zinc-800 rounded-lg bg-slate-50 dark:bg-black text-slate-900 dark:text-white placeholder:text-slate-400 dark:placeholder:text-zinc-600 focus:bg-white dark:focus:bg-black"
                  />
                  <button
                    onClick={() => handleRecordAnswer(gap)}
                    disabled={submittingId === gap.id || !(answers[gap.id] || '').trim()}
                    className="p-1.5 rounded-lg bg-blue-600 dark:bg-cyan-600 hover:bg-blue-700 dark:hover:bg-cyan-500 text-white disabled:opacity-50 transition cursor-pointer"
                    title="Submit answer to database"
                  >
                    <Send className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default EvidenceGapsTab;
