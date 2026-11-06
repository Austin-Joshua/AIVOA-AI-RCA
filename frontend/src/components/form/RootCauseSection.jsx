import React, { useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import {
  Target,
  CheckCircle2,
  AlertOctagon,
  FileCheck,
  Layers,
  ShieldCheck,
  AlertTriangle,
  XCircle,
  Link2,
  FileText,
  Plus,
} from 'lucide-react';
import { AiBadge } from '../common/AiBadge';
import {
  confirmRootCause,
  rejectRootCause,
  unlinkRootCauseEvidence,
  addRootCause,
} from '../../store/investigationSlice';
import { setNotification } from '../../store/uiSlice';

export const RootCauseSection = () => {
  const dispatch = useDispatch();
  const currentInvestigation = useSelector((state) => state.investigation.currentInvestigation);
  const currentUser = useSelector((state) => state.auth.user);
  const rootCauses = currentInvestigation?.root_causes || [];

  const isQAOrAdmin = currentUser?.role === 'QA_APPROVER' || currentUser?.role === 'ADMIN';
  const isLeadInvestigator = Boolean(
    currentInvestigation?.lead_investigator_id &&
      currentUser?.id &&
      currentInvestigation.lead_investigator_id === currentUser.id
  );
  const canConfirm = isQAOrAdmin && !isLeadInvestigator;

  const primaryCause = rootCauses.find((rc) => rc.is_primary) || rootCauses[0];
  const contributingCauses = rootCauses.filter((rc) => !rc.is_primary);

  // Human review modal state
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [targetCause, setTargetCause] = useState(null);
  const [investigatorName, setInvestigatorName] = useState(
    currentUser?.full_name || currentInvestigation?.lead_investigator || 'QA Director'
  );
  const [justification, setJustification] = useState('');
  const [rejectRationale, setRejectRationale] = useState('');
  const [showDismissModal, setShowDismissModal] = useState(null);
  const [dismissRationale, setDismissRationale] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Manual Add Root Cause State
  const [showAddModal, setShowAddModal] = useState(false);
  const [newStatement, setNewStatement] = useState('');
  const [newCategory, setNewCategory] = useState('EQUIPMENT_FAILURE');
  const [newIsPrimary, setNewIsPrimary] = useState(false);
  const [newRationale, setNewRationale] = useState('');

  const handleCreateRootCause = async (e) => {
    e.preventDefault();
    if (!newStatement.trim() || !currentInvestigation) return;
    setIsSubmitting(true);
    try {
      await dispatch(
        addRootCause({
          investigationId: currentInvestigation.id,
          data: {
            cause_statement: newStatement.trim(),
            category: newCategory,
            is_primary: newIsPrimary,
            rationale: newRationale.trim() || null,
            status: 'PROPOSED',
            source_type: 'MANUAL',
            is_ai_suggested: false,
            is_verified: false,
          },
        })
      ).unwrap();
      dispatch(
        setNotification({
          type: 'success',
          message: 'Root Cause proposal created (classified as PROPOSED).',
        })
      );
      setShowAddModal(false);
      setNewStatement('');
      setNewRationale('');
    } catch (err) {
      dispatch(setNotification({ type: 'error', message: String(err) }));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDismissContradiction = async (e) => {
    e.preventDefault();
    if (!showDismissModal || !dismissRationale || dismissRationale.length < 10) {
      dispatch(
        setNotification({
          type: 'error',
          message: 'Disposition rationale must be at least 10 characters explaining scientific resolution.',
        })
      );
      return;
    }
    setIsSubmitting(true);
    try {
      await dispatch(
        unlinkRootCauseEvidence({
          rootCauseId: primaryCause.id,
          linkId: showDismissModal.id,
          dispositionRationale: dismissRationale,
          investigatorName,
        })
      ).unwrap();
      dispatch(
        setNotification({
          type: 'success',
          message: 'Contradiction formally resolved and recorded in historical disposition dossier.',
        })
      );
      setShowDismissModal(null);
      setDismissRationale('');
    } catch (err) {
      dispatch(setNotification({ type: 'error', message: String(err) }));
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!primaryCause) {
    return (
      <div className="bg-white dark:bg-slate-900 rounded-xl border border-dashed border-slate-300 dark:border-slate-700 p-6 text-center mb-6">
        <Target className="w-8 h-8 text-slate-400 mx-auto mb-2" />
        <h4 className="text-sm font-semibold text-slate-700">Root Cause Evaluation Pending</h4>
        <p className="text-xs text-slate-500 mt-1">
          Complete the 5-Whys and Fishbone analyses or click "Run Full RCA Engine" in the Copilot to synthesize the primary root cause.
        </p>
      </div>
    );
  }

  // Supporting and contradictory evidence from evidence_links
  const supportingLinks = (primaryCause.evidence_links || []).filter(
    (l) => l.relationship_type === 'SUPPORTING'
  );
  const contradictoryLinks = (primaryCause.evidence_links || []).filter(
    (l) => l.relationship_type === 'CONTRADICTORY'
  );
  const hasVerifiedSupporting = supportingLinks.some((l) => l.evidence?.is_verified);
  const hasContradictions = contradictoryLinks.length > 0;

  const openConfirmModal = (cause) => {
    setTargetCause(cause);
    setInvestigatorName(currentUser?.full_name || 'QA Director');
    setJustification('');
    setShowConfirmModal(true);
  };

  const openRejectModal = (cause) => {
    setTargetCause(cause);
    setRejectRationale('');
    setShowRejectModal(true);
  };

  const handleConfirmSubmit = async () => {
    if (!targetCause || !investigatorName.trim() || !justification.trim()) return;

    setIsSubmitting(true);
    try {
      await dispatch(
        confirmRootCause({
          rootCauseId: targetCause.id,
          investigatorName: investigatorName.trim(),
          justification: justification.trim(),
        })
      ).unwrap();

      dispatch(
        setNotification({
          type: 'success',
          message: `Root Cause #${targetCause.id} formally CONFIRMED by ${investigatorName}.`,
        })
      );
      setShowConfirmModal(false);
    } catch (err) {
      dispatch(
        setNotification({
          type: 'error',
          message: `Confirmation rejected: ${err}`,
        })
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRejectSubmit = async () => {
    if (!targetCause || !investigatorName.trim() || !rejectRationale.trim()) return;

    setIsSubmitting(true);
    try {
      await dispatch(
        rejectRootCause({
          rootCauseId: targetCause.id,
          investigatorName: investigatorName.trim(),
          rationale: rejectRationale.trim(),
        })
      ).unwrap();

      dispatch(
        setNotification({
          type: 'success',
          message: `Root Cause #${targetCause.id} classified as REJECTED.`,
        })
      );
      setShowRejectModal(false);
    } catch (err) {
      dispatch(
        setNotification({
          type: 'error',
          message: `Rejection failed: ${err}`,
        })
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div id="section-rootcause" className="skeuo-card rounded-2xl overflow-hidden mb-6 font-sans">
      {/* Header */}
      <div className="bg-gradient-to-b from-blue-50/80 to-slate-100/60 dark:from-[#0c0e1a] dark:to-[#080a14] px-5 py-4 border-b border-slate-300 dark:border-[#1e2236] flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-blue-100 dark:bg-blue-950/60 border border-blue-300 dark:border-blue-700/50 flex items-center justify-center text-blue-800 dark:text-blue-300 shadow-sm">
            <Target className="w-4 h-4" />
          </div>
          <h3 className="font-extrabold text-slate-900 dark:text-white text-sm tracking-tight">
            Synthesized Root Cause &amp; Contributing Factors
          </h3>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="skeuo-btn-secondary flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-xl transition cursor-pointer"
        >
          <Plus className="w-3.5 h-3.5 text-rose-500" /> Add Root Cause Proposal
        </button>
      </div>

      <div className="p-5 space-y-4">
        {/* Primary Root Cause Card */}
        <div
          className={`p-4 rounded-xl border-2 transition ${
            primaryCause.status === 'CONFIRMED'
              ? 'border-emerald-300 dark:border-emerald-800 bg-emerald-50/20 dark:bg-emerald-950/20'
              : primaryCause.status === 'REJECTED'
              ? 'border-slate-300 dark:border-zinc-800 bg-slate-50/60 dark:bg-zinc-950/60 opacity-80'
              : 'border-rose-200 dark:border-rose-900/40 bg-rose-50/30 dark:bg-rose-950/20'
          }`}
        >
          <div className="flex items-center justify-between gap-2 mb-2 flex-wrap">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="flex items-center gap-1 text-xs font-bold uppercase tracking-wider text-rose-800 dark:text-rose-300 bg-rose-100 dark:bg-rose-950 px-2.5 py-0.5 rounded-full border border-rose-200 dark:border-rose-800 font-mono">
                <AlertOctagon className="w-3.5 h-3.5 text-rose-600 dark:text-rose-400" /> Primary Root Cause
              </span>
              <span className="text-xs font-mono font-semibold px-2 py-0.5 rounded bg-white dark:bg-black text-slate-700 dark:text-zinc-300 border border-slate-200 dark:border-zinc-800">
                {primaryCause.category}
              </span>

              {/* Status Badge */}
              <span
                className={`text-[10px] font-extrabold uppercase px-2.5 py-0.5 rounded-full border font-mono ${
                  primaryCause.status === 'CONFIRMED'
                    ? 'bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 border-emerald-300 dark:border-emerald-800'
                    : primaryCause.status === 'REJECTED'
                    ? 'bg-slate-200 dark:bg-zinc-900 text-slate-700 dark:text-zinc-400 border-slate-300 dark:border-zinc-700'
                    : 'bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 border-amber-300 dark:border-amber-800'
                }`}
              >
                STATUS: {primaryCause.status || 'PROPOSED'}
              </span>

              {primaryCause.source_type && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-100 dark:bg-zinc-900 text-slate-600 dark:text-zinc-400 border border-slate-200 dark:border-zinc-800">
                  {primaryCause.source_type}
                </span>
              )}
            </div>

            <AiBadge
              isAiSuggested={primaryCause.is_ai_suggested}
              isVerified={primaryCause.is_verified}
            />
          </div>

          <p className="text-sm font-semibold text-slate-900 dark:text-zinc-100 leading-snug mt-1">
            {primaryCause.cause_statement}
          </p>

          {primaryCause.confirmed_by && (
            <div className="mt-2 text-xs text-emerald-800 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/40 p-2 rounded border border-emerald-200 dark:border-emerald-900/50 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
              <span>
                Confirmed by <strong>{primaryCause.confirmed_by}</strong> on{' '}
                {primaryCause.confirmed_at ? new Date(primaryCause.confirmed_at).toLocaleDateString() : 'N/A'}
              </span>
            </div>
          )}

          {primaryCause.rejected_by && (
            <div className="mt-2 text-xs text-rose-800 bg-rose-50 p-2 rounded border border-rose-200 flex items-center gap-1.5">
              <XCircle className="w-3.5 h-3.5 text-rose-600 shrink-0" />
              <span>
                Rejected by <strong>{primaryCause.rejected_by}</strong>. Reason:{' '}
                {primaryCause.rejection_reason || 'Ruled out by investigator'}
              </span>
            </div>
          )}

          {/* Evidence Basis Summary */}
          {primaryCause.evidence_summary && (
            <div className="mt-3 pt-2.5 border-t border-slate-200 flex items-start gap-1.5 text-xs text-slate-600">
              <FileCheck className="w-4 h-4 text-blue-500 shrink-0 mt-0.5" />
              <span>
                <strong>Evidence Basis:</strong> {primaryCause.evidence_summary}
              </span>
            </div>
          )}

          {/* Contradictory Evidence Alert Banner */}
          {hasContradictions && (
            <div className="mt-3 p-3 bg-amber-50 dark:bg-amber-950/30 border border-amber-300 dark:border-amber-900/50 rounded-xl text-xs text-amber-900 dark:text-amber-200 space-y-2">
              <div className="flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
                <div>
                  <strong>Contradictory Evidence Detected:</strong> Found {contradictoryLinks.length} conflicting record(s).
                  In accordance with cGMP standards, this cause cannot be confirmed until empirical contradictions are investigated and resolved.
                </div>
              </div>
              <div className="space-y-1.5 pt-1">
                {contradictoryLinks.map((link) => (
                  <div key={link.id} className="flex items-center justify-between p-2 bg-white dark:bg-black rounded-lg border border-amber-200 dark:border-amber-900/50 gap-2">
                    <span className="font-medium text-slate-800 dark:text-zinc-200 text-[11px]">
                      {link.evidence?.title || `Evidence #${link.evidence_id}`}: {link.relevance_explanation || 'No rationale logged'}
                    </span>
                    <button
                      type="button"
                      onClick={() => setShowDismissModal(link)}
                      className="px-2.5 py-1 bg-amber-600 hover:bg-amber-700 text-white rounded text-[11px] font-semibold transition shrink-0 cursor-pointer"
                    >
                      Dismiss with Rationale
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Historical Contradiction Dispositions Dossier */}
          {primaryCause.dispositions && primaryCause.dispositions.length > 0 && (
            <div className="mt-3 pt-2 border-t border-slate-100">
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-1.5 flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" /> Resolved Contradiction Dispositions ({primaryCause.dispositions.length})
              </span>
              <div className="space-y-1.5">
                {primaryCause.dispositions.map((disp) => (
                  <div key={disp.id} className="p-2 bg-emerald-50/50 rounded border border-emerald-200 text-xs text-slate-700">
                    <div className="flex items-center justify-between font-semibold text-emerald-900 text-[11px]">
                      <span>Dismissed by: {disp.dismissed_by}</span>
                      <span>{new Date(disp.dismissed_at).toLocaleDateString()}</span>
                    </div>
                    <p className="mt-0.5 text-slate-600 italic">"{disp.disposition_rationale}"</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Relational Supporting Evidence Links */}
          {supportingLinks.length > 0 && (
            <div className="mt-3 pt-2 border-t border-slate-100">
              <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-1.5 flex items-center gap-1">
                <Link2 className="w-3.5 h-3.5 text-slate-400" /> Corroborating Evidence Dossier ({supportingLinks.length})
              </span>
              <div className="flex flex-wrap gap-1.5">
                {supportingLinks.map((link) => (
                  <span
                    key={link.id}
                    className={`inline-flex items-center gap-1 text-[11px] px-2.5 py-1 rounded-lg border font-medium ${
                      link.evidence?.is_verified
                        ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                        : 'bg-white text-slate-700 border-slate-200'
                    }`}
                  >
                    <FileText className="w-3 h-3 text-slate-400" />
                    <span>{link.evidence?.title || `Evidence #${link.evidence_id}`}</span>
                    {link.evidence?.is_verified && (
                      <CheckCircle2 className="w-3 h-3 text-emerald-600 ml-0.5" title="Verified by investigator" />
                    )}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Investigator Verification Notes */}
          {primaryCause.investigator_notes && (
            <div className="mt-3 p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-700">
              <strong>Human Review Record:</strong> {primaryCause.investigator_notes}
            </div>
          )}

          {/* Action Bar for Human Confirmation / Rejection */}
          <div className="mt-4 pt-3 border-t border-slate-200 flex items-center justify-between flex-wrap gap-2">
            <span className="text-[11px] text-slate-500 italic">
              {primaryCause.status === 'CONFIRMED'
                ? 'Formally confirmed by authorized quality professional.'
                : primaryCause.status === 'REJECTED'
                ? 'Hypothesis ruled out by investigation team.'
                : 'AI proposed hypothesis. Requires human review and verification.'}
            </span>

            {primaryCause.status !== 'CONFIRMED' && (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => openRejectModal(primaryCause)}
                  className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-slate-300 text-slate-700 hover:bg-rose-50 hover:text-rose-700 transition flex items-center gap-1"
                >
                  <XCircle className="w-3.5 h-3.5 text-slate-400" />
                  <span>Reject Cause</span>
                </button>

                <button
                  onClick={() => openConfirmModal(primaryCause)}
                  className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white transition flex items-center gap-1.5 shadow-2xs"
                >
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>Confirm as Root Cause</span>
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Contributing Factors */}
        {contributingCauses.length > 0 && (
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-600 mb-2 flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5 text-slate-500" /> Secondary Contributing Factors
            </h4>
            <div className="space-y-2">
              {contributingCauses.map((factor) => (
                <div
                  key={factor.id}
                  className="p-3.5 rounded-lg border border-slate-200 bg-slate-50 flex items-start justify-between gap-3"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-semibold text-slate-800">
                        {factor.cause_statement}
                      </span>
                      <span className="text-[10px] font-mono uppercase px-1.5 py-0.2 rounded bg-white text-slate-600 border border-slate-200">
                        {factor.category}
                      </span>
                    </div>
                    {factor.evidence_summary && (
                      <span className="text-xs text-slate-500 block">
                        Trace: {factor.evidence_summary}
                      </span>
                    )}
                  </div>
                  <AiBadge
                    isAiSuggested={factor.is_ai_suggested}
                    isVerified={factor.is_verified}
                  />
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Confirmation Modal */}
      {showConfirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 dark:bg-black/80 backdrop-blur-xs p-4 animate-fade-in">
          <div className="bg-white dark:bg-black rounded-2xl border border-slate-200 dark:border-zinc-800 shadow-xl max-w-md w-full p-6 space-y-4">
            <h4 className="font-bold text-base text-slate-900 dark:text-zinc-100 flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-emerald-600 dark:text-emerald-400" /> Confirm Primary Root Cause
            </h4>
            <p className="text-xs text-slate-600 dark:text-zinc-400 leading-relaxed">
              You are formally confirming that this causal statement has been corroborated by physical manufacturing evidence.
            </p>

            {!isQAOrAdmin && (
              <div className="p-3 bg-rose-50 dark:bg-rose-950/40 border border-rose-300 dark:border-rose-900/50 rounded-lg text-xs text-rose-900 dark:text-rose-200">
                <strong>Authorization Restriction:</strong> Root cause confirmation strictly requires <strong>QA_APPROVER</strong> or <strong>ADMIN</strong> role. You are currently authenticated as <strong>{currentUser?.role || 'INVESTIGATOR'}</strong>. Switch to a QA account to formally confirm.
              </div>
            )}

            {isLeadInvestigator && isQAOrAdmin && (
              <div className="p-3 bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-900/50 rounded-lg text-xs text-amber-900 dark:text-amber-200">
                <strong>Separation of Duties Restriction:</strong> You are the assigned lead investigator for this investigation. In accordance with cGMP regulations, the lead investigator cannot formally confirm their own root cause hypothesis. An independent QA reviewer is required.
              </div>
            )}

            {!hasVerifiedSupporting && (
              <div className="p-3 bg-amber-50 dark:bg-amber-950/40 border border-amber-300 dark:border-amber-900/50 rounded-lg text-xs text-amber-900 dark:text-amber-200">
                <strong>Evidence Barrier:</strong> No verified supporting evidence document is currently linked. In the dossier above, click <strong>"Verify"</strong> on at least one attached evidence record before confirmation.
              </div>
            )}

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-zinc-300 mb-1">Investigator Name</label>
                <input
                  type="text"
                  value={investigatorName}
                  onChange={(e) => setInvestigatorName(e.target.value)}
                  className="w-full text-xs px-3 py-2 border rounded-lg bg-white dark:bg-black border-slate-300 dark:border-zinc-700 text-slate-900 dark:text-zinc-100 focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-zinc-300 mb-1">
                  Scientific Justification & Evidence Citations
                </label>
                <textarea
                  rows={4}
                  placeholder="Detail the technical evidence, maintenance logs, and physical inspections that substantiate this finding..."
                  value={justification}
                  onChange={(e) => setJustification(e.target.value)}
                  className="w-full text-xs px-3 py-2 border rounded-lg bg-white dark:bg-black border-slate-300 dark:border-zinc-700 text-slate-900 dark:text-zinc-100 focus:ring-2 focus:ring-emerald-500"
                />
              </div>

              <div className="pt-3 flex justify-end gap-2 border-t border-slate-100 dark:border-zinc-800">
                <button
                  type="button"
                  onClick={() => setShowConfirmModal(false)}
                  className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-slate-300 dark:border-zinc-700 text-slate-700 dark:text-zinc-300 hover:bg-slate-100 dark:hover:bg-zinc-800 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={!canConfirm || !hasVerifiedSupporting || !investigatorName.trim() || justification.trim().length < 10 || isSubmitting}
                  onClick={handleConfirmSubmit}
                  className="px-4 py-1.5 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white disabled:opacity-50 shadow-2xs cursor-pointer"
                >
                  {isSubmitting ? 'Confirming...' : 'Sign & Confirm Root Cause'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Rejection Modal */}
      {showRejectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 dark:bg-black/80 backdrop-blur-xs p-4 animate-fade-in">
          <div className="bg-white dark:bg-black rounded-2xl border border-slate-200 dark:border-zinc-800 shadow-xl max-w-md w-full p-6 space-y-4">
            <h4 className="font-bold text-base text-slate-900 dark:text-zinc-100 flex items-center gap-2">
              <XCircle className="w-5 h-5 text-rose-600 dark:text-rose-400" /> Reject Causal Hypothesis
            </h4>
            <p className="text-xs text-slate-600 dark:text-zinc-400 leading-relaxed">
              Record the technical rationale for dismissing this proposed cause.
            </p>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-zinc-300 mb-1">Investigator Name</label>
                <input
                  type="text"
                  value={investigatorName}
                  onChange={(e) => setInvestigatorName(e.target.value)}
                  className="w-full text-xs px-3 py-2 border rounded-lg bg-white dark:bg-black border-slate-300 dark:border-zinc-700 text-slate-900 dark:text-zinc-100 focus:ring-2 focus:ring-rose-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-zinc-300 mb-1">Rejection Rationale</label>
                <textarea
                  rows={3}
                  placeholder="Explain why evidence refutes this cause or why it was ruled out..."
                  value={rejectRationale}
                  onChange={(e) => setRejectRationale(e.target.value)}
                  className="w-full text-xs px-3 py-2 border rounded-lg bg-white dark:bg-black border-slate-300 dark:border-zinc-700 text-slate-900 dark:text-zinc-100 focus:ring-2 focus:ring-rose-500"
                />
              </div>

              <div className="pt-3 flex justify-end gap-2 border-t border-slate-100 dark:border-zinc-800">
                <button
                  type="button"
                  onClick={() => setShowRejectModal(false)}
                  className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-slate-300 dark:border-zinc-700 text-slate-700 dark:text-zinc-300 hover:bg-slate-100 dark:hover:bg-zinc-800 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={!investigatorName.trim() || rejectRationale.trim().length < 5 || isSubmitting}
                  onClick={handleRejectSubmit}
                  className="px-4 py-1.5 text-xs font-semibold rounded-lg bg-rose-600 hover:bg-rose-700 text-white disabled:opacity-50 shadow-2xs cursor-pointer"
                >
                  {isSubmitting ? 'Rejecting...' : 'Confirm Rejection'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Contradiction Disposition Modal */}
      {showDismissModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 dark:bg-black/80 backdrop-blur-xs p-4 animate-fade-in">
          <div className="bg-white dark:bg-black rounded-2xl border border-slate-200 dark:border-zinc-800 shadow-xl max-w-md w-full p-6 space-y-4">
            <h4 className="font-bold text-base text-slate-900 dark:text-zinc-100 flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-amber-600 dark:text-amber-400" /> Dismiss Contradictory Evidence
            </h4>
            <p className="text-xs text-slate-600 dark:text-zinc-400 leading-relaxed">
              cGMP compliance requires documenting why this contradictory finding does not refute the primary root cause.
            </p>

            <form onSubmit={handleDismissContradiction} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-zinc-300 mb-1">
                  Scientific Disposition Rationale <span className="text-rose-500">* (min 10 chars)</span>
                </label>
                <textarea
                  rows={3}
                  required
                  minLength={10}
                  value={dismissRationale}
                  onChange={(e) => setDismissRationale(e.target.value)}
                  placeholder="Explain why this data was resolved, refuted, or determined non-causal..."
                  className="w-full text-xs px-3 py-2 border rounded-lg bg-white dark:bg-black border-slate-300 dark:border-zinc-700 text-slate-900 dark:text-zinc-100 focus:ring-2 focus:ring-amber-500"
                />
              </div>

              <div className="pt-3 flex justify-end gap-2 border-t border-slate-100 dark:border-zinc-800">
                <button
                  type="button"
                  onClick={() => setShowDismissModal(null)}
                  className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-slate-300 dark:border-zinc-700 text-slate-700 dark:text-zinc-300 hover:bg-slate-100 dark:hover:bg-zinc-800 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || dismissRationale.trim().length < 10}
                  className="px-4 py-1.5 text-xs font-semibold rounded-lg bg-amber-600 hover:bg-amber-700 text-white disabled:opacity-50 shadow-2xs cursor-pointer"
                >
                  {isSubmitting ? 'Recording...' : 'Record Disposition & Dismiss'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      {/* Add Manual Root Cause Proposal Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 dark:bg-black/80 backdrop-blur-xs p-4 animate-fade-in">
          <div className="bg-white dark:bg-black rounded-2xl border border-slate-200 dark:border-zinc-800 shadow-xl max-w-md w-full p-6 space-y-4">
            <h4 className="font-bold text-base text-slate-900 dark:text-zinc-100 flex items-center gap-2">
              <Plus className="w-5 h-5 text-rose-600 dark:text-rose-400" /> Add Root Cause Proposal
            </h4>
            <p className="text-xs text-slate-600 dark:text-zinc-400 leading-relaxed">
              Create a manual causal proposal for investigator evaluation. Proposals always start with PROPOSED status.
            </p>

            <form onSubmit={handleCreateRootCause} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-zinc-300 mb-1">
                  Cause Statement <span className="text-rose-500">*</span>
                </label>
                <textarea
                  rows={2}
                  required
                  placeholder="Detail the failure mechanism..."
                  value={newStatement}
                  onChange={(e) => setNewStatement(e.target.value)}
                  className="w-full text-xs px-3 py-2 border rounded-lg bg-white dark:bg-black border-slate-300 dark:border-zinc-700 text-slate-900 dark:text-zinc-100 focus:ring-2 focus:ring-rose-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-zinc-300 mb-1">Category</label>
                  <select
                    value={newCategory}
                    onChange={(e) => setNewCategory(e.target.value)}
                    className="w-full text-xs px-2.5 py-1.5 border rounded-lg bg-white dark:bg-black border-slate-300 dark:border-zinc-700 text-slate-900 dark:text-zinc-100"
                  >
                    <option value="EQUIPMENT_FAILURE">EQUIPMENT_FAILURE</option>
                    <option value="HUMAN_ERROR">HUMAN_ERROR</option>
                    <option value="PROCEDURE">PROCEDURE</option>
                    <option value="RAW_MATERIAL">RAW_MATERIAL</option>
                    <option value="SYSTEMIC">SYSTEMIC</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 dark:text-zinc-300 mb-1">Classification</label>
                  <select
                    value={newIsPrimary ? 'PRIMARY' : 'CONTRIBUTING'}
                    onChange={(e) => setNewIsPrimary(e.target.value === 'PRIMARY')}
                    className="w-full text-xs px-2.5 py-1.5 border rounded-lg bg-white dark:bg-black border-slate-300 dark:border-zinc-700 text-slate-900 dark:text-zinc-100"
                  >
                    <option value="PRIMARY">Primary Cause</option>
                    <option value="CONTRIBUTING">Contributing Factor</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-zinc-300 mb-1">
                  Rationale / Mechanism (Optional)
                </label>
                <textarea
                  rows={2}
                  placeholder="Explain why this factor is causal..."
                  value={newRationale}
                  onChange={(e) => setNewRationale(e.target.value)}
                  className="w-full text-xs px-3 py-2 border rounded-lg bg-white dark:bg-black border-slate-300 dark:border-zinc-700 text-slate-900 dark:text-zinc-100"
                />
              </div>

              <div className="pt-3 flex justify-end gap-2 border-t border-slate-100 dark:border-zinc-800">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-slate-300 dark:border-zinc-700 text-slate-700 dark:text-zinc-300 hover:bg-slate-100 dark:hover:bg-zinc-800 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting || !newStatement.trim()}
                  className="px-4 py-1.5 text-xs font-semibold rounded-lg bg-rose-600 hover:bg-rose-700 text-white disabled:opacity-50 shadow-2xs cursor-pointer"
                >
                  {isSubmitting ? 'Creating...' : 'Create Proposal'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default RootCauseSection;
