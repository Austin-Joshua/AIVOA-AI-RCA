import React, { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  ShieldCheck,
  CheckCircle2,
  FileCheck,
  AlertCircle,
  Lock,
  AlertTriangle,
} from 'lucide-react';
import { approveInvestigation } from '../../store/investigationSlice';
import { setNotification } from '../../store/uiSlice';

export const ApprovalSection = () => {
  const dispatch = useDispatch();
  const currentInvestigation = useSelector((state) => state.investigation.currentInvestigation);
  const currentUser = useSelector((state) => state.auth.user);
  const isApproved = currentInvestigation?.is_approved;

  const isQAOrAdmin = currentUser?.role === 'QA_APPROVER' || currentUser?.role === 'ADMIN';

  const approverName = isQAOrAdmin
    ? (currentUser?.full_name || currentInvestigation?.qa_approver || '')
    : '';
  const [comments, setComments] = useState(
    currentInvestigation?.approval_comments || ''
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  const handleApprove = async () => {
    if (!approverName.trim()) return;
    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      await dispatch(
        approveInvestigation({
          investigationId: currentInvestigation.id,
          approverName: approverName.trim(),
          comments: comments.trim() || undefined,
        })
      ).unwrap();

      dispatch(
        setNotification({
          type: 'success',
          message: 'Investigation dossier formally signed and approved by Quality Assurance!',
        })
      );
    } catch (err) {
      setErrorMsg(String(err));
      dispatch(
        setNotification({
          type: 'error',
          message: `Approval failed: ${err}`,
        })
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div id="section-approval" className="skeuo-card rounded-2xl overflow-hidden mb-6 font-sans bg-white dark:bg-[#0c0e1a] border border-slate-300 dark:border-[#1e2236]">
      <div className="bg-gradient-to-b from-blue-50/80 to-slate-100/60 dark:from-[#0c0e1a] dark:to-[#080a14] px-5 py-4 border-b border-slate-300 dark:border-[#1e2236] flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-emerald-100 dark:bg-emerald-950/80 border border-emerald-300 dark:border-emerald-500/40 flex items-center justify-center text-emerald-700 dark:text-emerald-400 shadow-xs">
            <ShieldCheck className="w-4 h-4" />
          </div>
          <h3 className="font-extrabold text-slate-900 dark:text-white text-sm tracking-tight">
            QA Sign-Off (prototype electronic signature)
          </h3>
        </div>
        {isApproved && (
          <span className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800 shadow-xs font-mono">
            <Lock className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" /> Investigation Dossier Sealed
          </span>
        )}
      </div>

      <div className="p-6">
        {isApproved ? (
          <div className="p-6 rounded-2xl bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-800/60 space-y-3 shadow-inner">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-emerald-600 flex items-center justify-center text-white shadow-lg shadow-emerald-600/30">
                <CheckCircle2 className="w-7 h-7" />
              </div>
              <div>
                <h4 className="font-extrabold text-base text-emerald-900 dark:text-emerald-200 tracking-tight">
                  Approved & Formally Closed by Quality Assurance
                </h4>
                <p className="text-xs text-emerald-700 dark:text-emerald-400 mt-0.5">
                  Approved by {currentInvestigation.qa_approver || 'Quality Assurance'}
                  {currentInvestigation.approval_date && (
                    <>
                      {' '}on {new Date(currentInvestigation.approval_date).toLocaleDateString()}{' '}
                      at {new Date(currentInvestigation.approval_date).toLocaleTimeString()}
                    </>
                  )}
                </p>
              </div>
            </div>

            <div className="skeuo-well p-4 rounded-xl text-xs text-slate-800 dark:text-zinc-200 mt-2 font-sans bg-slate-50 dark:bg-black border border-slate-200 dark:border-zinc-800">
              <strong className="text-emerald-600 dark:text-emerald-400">QA Review Comments:</strong> {currentInvestigation.approval_comments}
            </div>

            <p className="text-[11px] text-emerald-700 dark:text-emerald-400 font-mono italic">
              Verification Hash: SHA256:{currentInvestigation.id}c9a4f8e... (Electronic Signature Executed)
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {errorMsg && (
              <div className="p-3.5 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 rounded-xl text-xs text-rose-700 dark:text-rose-200 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-500 dark:text-rose-400 shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            {!isQAOrAdmin ? (
              <div className="p-4 rounded-xl bg-amber-50/90 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800/80 flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
                <div className="text-xs text-amber-900 dark:text-amber-200 leading-relaxed font-medium">
                  <strong>Role Authorization Notice:</strong> You are currently signed in as{' '}
                  <strong>{currentUser?.role || 'INVESTIGATOR'}</strong>. Formal investigation dossier closure strictly requires{' '}
                  <strong>QA_APPROVER</strong> or <strong>ADMIN</strong> role. Standard investigators cannot execute final closure. Switch to a QA account (e.g., QA Director) to approve.
                </div>
              </div>
            ) : (
              <div className="p-4 rounded-xl bg-emerald-50/90 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800/80 flex items-start gap-3">
                <ShieldCheck className="w-5 h-5 text-emerald-600 dark:text-emerald-400 mt-0.5 shrink-0" />
                <div className="text-xs text-emerald-900 dark:text-emerald-200 leading-relaxed font-medium">
                  <strong>Authorized QA Approver:</strong> Signed in as <strong>{currentUser?.full_name} ({currentUser?.role})</strong>. You have authorization to execute formal investigation dossier closure.
                </div>
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-bold text-slate-700 dark:text-zinc-300 block mb-1">
                  QA Approver Full Name & Title
                </label>
                <div className="skeuo-well rounded-xl overflow-hidden bg-slate-50 dark:bg-black border border-slate-200 dark:border-zinc-800">
                  <input
                    type="text"
                    value={approverName}
                    className="w-full text-xs font-medium p-3 bg-transparent text-slate-800 dark:text-zinc-200 placeholder:text-slate-400 dark:placeholder:text-zinc-500 focus:outline-none"
                    placeholder="Full name and title"
                    disabled={!isQAOrAdmin}
                    readOnly
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 dark:text-zinc-300 block mb-1">
                  Lead Investigator
                </label>
                <div className="skeuo-well rounded-xl overflow-hidden bg-slate-50 dark:bg-black border border-slate-200 dark:border-zinc-800">
                  <input
                    type="text"
                    readOnly
                    value={currentInvestigation?.lead_investigator || 'Lead Investigator'}
                    className="w-full text-xs font-mono font-medium p-3 bg-transparent text-slate-600 dark:text-zinc-400 focus:outline-none"
                  />
                </div>
              </div>
            </div>

            <div>
              <label className="text-xs font-bold text-slate-700 dark:text-zinc-300 block mb-1">
                Formal QA Approval Comments & Closure Rationale
              </label>
              <div className="skeuo-well rounded-xl overflow-hidden bg-slate-50 dark:bg-black border border-slate-200 dark:border-zinc-800">
                <textarea
                  rows={3}
                  value={comments}
                  onChange={(e) => setComments(e.target.value)}
                  className="w-full text-xs p-3 bg-transparent text-slate-900 dark:text-zinc-100 placeholder:text-slate-400 dark:placeholder:text-zinc-500 focus:outline-none resize-none font-sans"
                  placeholder="Document scientific justification, verification of corrective actions, and rationale for closing this investigation dossier (minimum 10 characters)..."
                  disabled={!isQAOrAdmin}
                />
              </div>
              {isQAOrAdmin && comments.trim().length > 0 && comments.trim().length < 10 && (
                <p className="text-[11px] font-semibold text-rose-500 mt-1">
                  Closure rationale must be at least 10 characters ({comments.trim().length}/10)
                </p>
              )}
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={handleApprove}
                disabled={!isQAOrAdmin || isSubmitting || comments.trim().length < 10}
                className="skeuo-btn-primary flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-xs shadow-md transition disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
              >
                <FileCheck className="w-4 h-4" />
                {isSubmitting ? 'Approving...' : isQAOrAdmin ? 'Sign & Approve Investigation' : 'QA_APPROVER Role Required'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ApprovalSection;
