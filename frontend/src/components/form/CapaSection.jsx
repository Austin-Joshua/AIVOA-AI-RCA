import React, { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  ShieldAlert,
  Plus,
  Trash2,
  CheckCircle2,
  Calendar,
  User,
  Activity,
  Layers,
  Clock,
  Play,
  CheckCheck,
  ShieldCheck,
  AlertTriangle,
  X,
} from 'lucide-react';
import {
  addCapaAction,
  updateCapaAction,
  approveCapaAction,
  completeCapaAction,
  verifyCapaEffectiveness,
  deleteCapaAction,
} from '../../store/investigationSlice';
import { setNotification } from '../../store/uiSlice';
import { CapaTypeBadge, CapaStatusBadge } from '../common/StatusBadge';
import { Button, Input, Textarea, Select, Card, CardHeader, CardContent, ConfirmDialog } from '../ui';

export const CapaSection = () => {
  const dispatch = useDispatch();
  const currentInvestigation = useSelector((state) => state.investigation.currentInvestigation);
  const currentUser = useSelector((state) => state.auth.user);
  const capaActions = currentInvestigation?.capa_actions || [];
  const rootCauses = currentInvestigation?.root_causes || [];

  const [isAdding, setIsAdding] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [deleteTargetId, setDeleteTargetId] = useState(null); // For ConfirmDialog

  // New CAPA Form state
  const [newCapa, setNewCapa] = useState({
    action_type: 'CORRECTIVE_ACTION',
    description: '',
    rationale: '',
    owner: '',
    deadline: '30 Days',
    effectiveness_criteria: '',
    effectiveness_review_period_days: 30,
    root_cause_id: '',
  });

  // Modal dialog states
  const [approveModalCapa, setApproveModalCapa] = useState(null);
  const [approvalNotes, setApprovalNotes] = useState('');

  const [completeModalCapa, setCompleteModalCapa] = useState(null);
  const [completionNotes, setCompletionNotes] = useState('');

  const [verifyEffModalCapa, setVerifyEffModalCapa] = useState(null);
  const [effectivenessNotes, setEffectivenessNotes] = useState('');

  // Role & Segregation of Duties checks
  const isQAOrAdmin = currentUser?.role === 'QA_APPROVER' || currentUser?.role === 'ADMIN';
  const isLeadInvestigator = Boolean(
    currentInvestigation?.lead_investigator_id &&
      currentUser?.id &&
      currentInvestigation.lead_investigator_id === currentUser.id
  );
  const canApprove = isQAOrAdmin && !isLeadInvestigator;
  const canVerifyEffectiveness = isQAOrAdmin;

  const handleAdd = async (e) => {
    e.preventDefault();
    if (!newCapa.description.trim()) {
      setErrorMessage('Action description is required.');
      return;
    }
    setErrorMessage(null);
    setIsSubmitting(true);
    try {
      const payload = {
        action_type: newCapa.action_type,
        description: newCapa.description.trim(),
        rationale: newCapa.rationale.trim() || null,
        owner: newCapa.owner.trim() || null,
        deadline: newCapa.deadline.trim() || null,
        effectiveness_criteria: newCapa.effectiveness_criteria.trim() || null,
        effectiveness_review_period_days: parseInt(newCapa.effectiveness_review_period_days, 10) || 30,
        root_cause_id: newCapa.root_cause_id ? parseInt(newCapa.root_cause_id, 10) : null,
        status: 'PROPOSED',
        is_verified: false,
        is_ai_suggested: false,
      };

      await dispatch(
        addCapaAction({
          investigationId: currentInvestigation.id,
          data: payload,
        })
      ).unwrap();

      dispatch(
        setNotification({
          type: 'success',
          message: 'CAPA action proposed successfully (status: PROPOSED).',
        })
      );

      setNewCapa({
        action_type: 'CORRECTIVE_ACTION',
        description: '',
        rationale: '',
        owner: '',
        deadline: '30 Days',
        effectiveness_criteria: '',
        effectiveness_review_period_days: 30,
        root_cause_id: '',
      });
      setIsAdding(false);
    } catch (err) {
      setErrorMessage(String(err));
      dispatch(setNotification({ type: 'error', message: String(err) }));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConfirmApprove = async () => {
    if (!approveModalCapa) return;
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      await dispatch(
        approveCapaAction({
          capaId: approveModalCapa.id,
          approvalNotes: approvalNotes.trim() || null,
        })
      ).unwrap();

      dispatch(
        setNotification({
          type: 'success',
          message: `CAPA #${approveModalCapa.id} formally APPROVED by QA.`,
        })
      );
      setApproveModalCapa(null);
      setApprovalNotes('');
    } catch (err) {
      setErrorMessage(String(err));
      dispatch(setNotification({ type: 'error', message: String(err) }));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleStartWork = async (capaId) => {
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      await dispatch(
        updateCapaAction({
          capaId,
          data: { status: 'IN_PROGRESS' },
        })
      ).unwrap();
      dispatch(
        setNotification({
          type: 'success',
          message: `CAPA #${capaId} implementation started (status: IN_PROGRESS).`,
        })
      );
    } catch (err) {
      setErrorMessage(String(err));
      dispatch(setNotification({ type: 'error', message: String(err) }));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConfirmComplete = async () => {
    if (!completeModalCapa) return;
    if (!completionNotes.trim() || completionNotes.trim().length < 5) {
      setErrorMessage('Completion notes must be at least 5 characters documenting action outcome.');
      return;
    }
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      await dispatch(
        completeCapaAction({
          capaId: completeModalCapa.id,
          completionNotes: completionNotes.trim(),
        })
      ).unwrap();

      dispatch(
        setNotification({
          type: 'success',
          message: `CAPA #${completeModalCapa.id} marked as COMPLETED.`,
        })
      );
      setCompleteModalCapa(null);
      setCompletionNotes('');
    } catch (err) {
      setErrorMessage(String(err));
      dispatch(setNotification({ type: 'error', message: String(err) }));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConfirmVerifyEffectiveness = async () => {
    if (!verifyEffModalCapa) return;
    setIsSubmitting(true);
    setErrorMessage(null);
    try {
      await dispatch(
        verifyCapaEffectiveness({
          capaId: verifyEffModalCapa.id,
          verificationNotes: effectivenessNotes.trim() || null,
        })
      ).unwrap();

      dispatch(
        setNotification({
          type: 'success',
          message: `CAPA #${verifyEffModalCapa.id} effectiveness verified and closed.`,
        })
      );
      setVerifyEffModalCapa(null);
      setEffectivenessNotes('');
    } catch (err) {
      setErrorMessage(String(err));
      dispatch(setNotification({ type: 'error', message: String(err) }));
    } finally {
      setIsSubmitting(false);
    }
  };

  const requestDelete = (capaId, status) => {
    if (status === 'EFFECTIVENESS_VERIFIED') {
      dispatch(
        setNotification({
          type: 'error',
          message: 'Cannot delete an effectiveness-verified CAPA action. Records must be preserved for cGMP compliance.',
        })
      );
      return;
    }
    setDeleteTargetId(capaId);
  };

  const executeDelete = async () => {
    if (!deleteTargetId) return;
    setIsSubmitting(true);
    try {
      await dispatch(deleteCapaAction(deleteTargetId)).unwrap();
      dispatch(
        setNotification({
          type: 'success',
          message: `CAPA #${deleteTargetId} deleted successfully.`,
        })
      );
      setDeleteTargetId(null);
    } catch (err) {
      dispatch(setNotification({ type: 'error', message: String(err) }));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card id="section-capa" className="mb-6">
      {/* Header */}
      <CardHeader
        icon={<ShieldAlert className="w-5 h-5 text-blue-700 dark:text-blue-400" />}
        title="Corrective & Preventive Actions (CAPA) Program"
        badge={
          <span className="text-xs px-2 py-0.5 rounded bg-amber-50 dark:bg-amber-950/50 text-amber-900 dark:text-amber-300 font-extrabold border border-amber-300 dark:border-amber-700/60 font-mono">
            {capaActions.length} Actions Planned
          </span>
        }
        action={
          <Button
            variant="outline"
            size="xs"
            onClick={() => {
              setIsAdding(!isAdding);
              setErrorMessage(null);
            }}
            icon={<Plus className="w-3.5 h-3.5 text-purple-600" />}
          >
            Add CAPA Action
          </Button>
        }
      />

      <CardContent className="space-y-6">
        <p className="text-xs text-slate-500 leading-relaxed">
          Each recommended CAPA must demonstrate direct causal alignment with the verified root cause. Every action item
          defines an accountable owner, strict completion deadline, and quantitative effectiveness review criteria.
          QA formal approval is required before action implementation.
        </p>

        {errorMessage && (
          <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 flex items-center justify-between text-xs text-rose-700">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-500 shrink-0" />
              <span>{errorMessage}</span>
            </div>
            <button onClick={() => setErrorMessage(null)} className="text-rose-500 hover:text-rose-700">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Action Items List */}
        {capaActions.length === 0 ? (
          <div className="p-6 text-center border border-dashed border-slate-300 dark:border-zinc-800 rounded-lg bg-slate-50 dark:bg-zinc-950/40">
            <p className="text-xs text-slate-400 dark:text-zinc-500">No CAPA actions drafted yet. Click above or generate via Copilot.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {capaActions.map((action) => {
              const linkedRootCause = rootCauses.find((rc) => rc.id === action.root_cause_id);
              const isProposed = !action.status || action.status === 'PROPOSED' || action.status === 'OPEN';
              const isApproved = action.status === 'APPROVED';
              const isInProgress = action.status === 'IN_PROGRESS';
              const isCompleted = action.status === 'COMPLETED' || action.status === 'CLOSED';
              const isVerified = action.status === 'EFFECTIVENESS_VERIFIED';

              return (
                <div
                  key={action.id}
                  className="bg-slate-50/70 dark:bg-zinc-950 p-4 rounded-xl border border-slate-300 dark:border-zinc-800 hover:border-slate-400 dark:hover:border-zinc-700 transition space-y-3"
                >
                  <div className="flex items-start justify-between gap-2 flex-wrap">
                    <div className="flex items-center gap-2 flex-wrap">
                      <CapaTypeBadge type={action.action_type} />
                      <span className="text-xs font-mono font-medium text-slate-500 dark:text-zinc-400">#{action.id}</span>
                      <CapaStatusBadge status={action.status} />
                      {action.is_ai_suggested && (
                        <span className="text-[10px] font-medium px-2 py-0.5 rounded bg-amber-50 dark:bg-amber-950/80 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
                          AI Suggested
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      {isVerified ? (
                        <span className="inline-flex items-center gap-1 text-xs text-teal-700 dark:text-teal-300 font-semibold bg-teal-50 dark:bg-teal-950/80 px-2 py-0.5 rounded border border-teal-200 dark:border-teal-800">
                          <ShieldCheck className="w-3.5 h-3.5 text-teal-600 dark:text-teal-400" />
                          Effectiveness Verified
                        </span>
                      ) : (
                        <button
                          onClick={() => requestDelete(action.id, action.status)}
                          className="text-slate-400 hover:text-rose-500 dark:hover:text-rose-400 p-1 rounded hover:bg-slate-100 dark:hover:bg-zinc-800 transition cursor-pointer"
                          title="Delete action"
                          aria-label="Delete action"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>
                  </div>

                  <p className="text-sm font-semibold text-slate-900 dark:text-zinc-100 leading-snug">
                    {action.description}
                  </p>

                  {/* Linked Root Cause */}
                  {action.root_cause_id && (
                    <div className="flex items-center gap-1.5 text-xs text-slate-600 dark:text-zinc-300 bg-white dark:bg-black p-2 rounded-lg border border-slate-200 dark:border-zinc-800">
                      <Layers className="w-3.5 h-3.5 text-purple-600 dark:text-purple-400 shrink-0" />
                      <span>
                        <strong>Target Root Cause:</strong> #{action.root_cause_id}
                        {linkedRootCause ? ` — ${linkedRootCause.cause_statement.slice(0, 80)}...` : ''}
                      </span>
                    </div>
                  )}

                  {action.rationale && (
                    <p className="text-xs text-slate-600 dark:text-zinc-300 italic bg-white dark:bg-black p-2.5 rounded-lg border border-slate-200/60 dark:border-zinc-800 whitespace-pre-line">
                      <strong>Rationale & History:</strong> {action.rationale}
                    </p>
                  )}

                  {/* Metadata Row: Owner, Deadline, Effectiveness */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 text-xs border-t border-slate-200 dark:border-zinc-800">
                    <div className="flex items-center gap-1.5 text-slate-700 dark:text-zinc-300">
                      <User className="w-3.5 h-3.5 text-blue-500 dark:text-cyan-400" />
                      <span><strong>Owner:</strong> {action.owner || 'Unassigned'}</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-slate-700 dark:text-zinc-300">
                      <Calendar className="w-3.5 h-3.5 text-amber-500 dark:text-amber-400" />
                      <span><strong>Deadline:</strong> {action.deadline || '30 Days'}</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-slate-700 dark:text-zinc-300">
                      <Activity className="w-3.5 h-3.5 text-emerald-500 dark:text-emerald-400" />
                      <span><strong>Review Window:</strong> {action.effectiveness_review_period_days} Days</span>
                    </div>
                  </div>

                  {action.effectiveness_criteria && (
                    <div className="p-2.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-900/50 text-xs text-emerald-900 dark:text-emerald-300 whitespace-pre-line">
                      <strong>Effectiveness Verification Criteria:</strong> {action.effectiveness_criteria}
                    </div>
                  )}

                  {/* Lifecycle Action Bar */}
                  <div className="pt-2 border-t border-slate-200 dark:border-zinc-800 flex items-center justify-between flex-wrap gap-2">
                    <div className="text-[11px] text-slate-500 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      <span>Current Stage: <strong>{action.status || 'PROPOSED'}</strong></span>
                    </div>

                    <div className="flex items-center gap-2">
                      {/* State 1: PROPOSED -> Requires QA Approval */}
                      {isProposed && (
                        <>
                          {canApprove ? (
                            <Button
                              variant="primary"
                              size="xs"
                              onClick={() => {
                                setApproveModalCapa(action);
                                setApprovalNotes('');
                                setErrorMessage(null);
                              }}
                              icon={<CheckCircle2 className="w-3.5 h-3.5" />}
                            >
                              Approve CAPA
                            </Button>
                          ) : isLeadInvestigator && isQAOrAdmin ? (
                            <span className="text-[11px] text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded font-medium">
                              Lead investigator cannot self-approve (Independent QA Required)
                            </span>
                          ) : (
                            <span className="text-[11px] text-slate-500 bg-slate-100 border border-slate-200 px-2 py-0.5 rounded font-medium">
                              Awaiting QA Approval
                            </span>
                          )}
                        </>
                      )}

                      {/* State 2: APPROVED -> Can Start Implementation or Complete */}
                      {isApproved && (
                        <>
                          <Button
                            variant="secondary"
                            size="xs"
                            onClick={() => handleStartWork(action.id)}
                            disabled={isSubmitting}
                            icon={<Play className="w-3.5 h-3.5" />}
                          >
                            Start Work
                          </Button>
                          <Button
                            variant="success"
                            size="xs"
                            onClick={() => {
                              setCompleteModalCapa(action);
                              setCompletionNotes('');
                              setErrorMessage(null);
                            }}
                            icon={<CheckCheck className="w-3.5 h-3.5" />}
                          >
                            Mark Completed
                          </Button>
                        </>
                      )}

                      {/* State 3: IN_PROGRESS -> Can Complete */}
                      {isInProgress && (
                        <Button
                          variant="success"
                          size="xs"
                          onClick={() => {
                            setCompleteModalCapa(action);
                            setCompletionNotes('');
                            setErrorMessage(null);
                          }}
                          icon={<CheckCheck className="w-3.5 h-3.5" />}
                        >
                          Mark Completed
                        </Button>
                      )}

                      {/* State 4: COMPLETED -> Requires QA Effectiveness Verification */}
                      {isCompleted && (
                        <>
                          {canVerifyEffectiveness ? (
                            <Button
                              variant="brand"
                              size="xs"
                              onClick={() => {
                                setVerifyEffModalCapa(action);
                                setEffectivenessNotes('');
                                setErrorMessage(null);
                              }}
                              icon={<ShieldCheck className="w-3.5 h-3.5" />}
                            >
                              Verify Effectiveness
                            </Button>
                          ) : (
                            <span className="text-[11px] text-slate-500 bg-slate-100 border border-slate-200 px-2 py-0.5 rounded font-medium">
                              Awaiting QA Effectiveness Verification
                            </span>
                          )}
                        </>
                      )}

                      {/* State 5: EFFECTIVENESS_VERIFIED */}
                      {isVerified && (
                        <span className="text-[11px] text-teal-800 bg-teal-50 border border-teal-300 font-semibold px-2 py-0.5 rounded">
                          ✓ Verified & Regulatory Closed
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* Add CAPA Form */}
        {isAdding && (
          <form onSubmit={handleAdd} className="p-4 rounded-xl border border-purple-200 bg-purple-50/30 space-y-3">
            <h4 className="text-xs font-bold text-purple-900 uppercase">New CAPA Action Proposal</h4>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <Select
                label="Action Type"
                value={newCapa.action_type}
                onChange={(e) => setNewCapa({ ...newCapa, action_type: e.target.value })}
              >
                <option value="CORRECTION">Correction (Immediate)</option>
                <option value="CORRECTIVE_ACTION">Corrective Action</option>
                <option value="PREVENTIVE_ACTION">Preventive Action</option>
              </Select>
              <Input
                label="Owner"
                placeholder="e.g. Engineering Lead"
                value={newCapa.owner}
                onChange={(e) => setNewCapa({ ...newCapa, owner: e.target.value })}
              />
              <Input
                label="Deadline"
                placeholder="e.g. 14 Days"
                value={newCapa.deadline}
                onChange={(e) => setNewCapa({ ...newCapa, deadline: e.target.value })}
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <Select
                label="Target Root Cause (Optional)"
                value={newCapa.root_cause_id}
                onChange={(e) => setNewCapa({ ...newCapa, root_cause_id: e.target.value })}
              >
                <option value="">-- Unlinked / General CAPA --</option>
                {rootCauses.map((rc) => (
                  <option key={rc.id} value={rc.id}>
                    #{rc.id} [{rc.status}] - {rc.cause_statement.slice(0, 60)}...
                  </option>
                ))}
              </Select>
              <Input
                label="Effectiveness Review Window (Days)"
                type="number"
                min="1"
                max="365"
                value={newCapa.effectiveness_review_period_days}
                onChange={(e) => setNewCapa({ ...newCapa, effectiveness_review_period_days: e.target.value })}
              />
            </div>

            <Textarea
              label="Action Description"
              required
              rows={2}
              placeholder="Specific actionable mandate..."
              value={newCapa.description}
              onChange={(e) => setNewCapa({ ...newCapa, description: e.target.value })}
            />

            <Input
              label="Quantitative Effectiveness Criteria"
              placeholder="Measurable metric (e.g. Zero pressure excursions across 10 consecutive commercial batches)"
              value={newCapa.effectiveness_criteria}
              onChange={(e) => setNewCapa({ ...newCapa, effectiveness_criteria: e.target.value })}
            />

            <Textarea
              label="Scientific Rationale"
              rows={2}
              placeholder="Why this action will permanently resolve the root cause..."
              value={newCapa.rationale}
              onChange={(e) => setNewCapa({ ...newCapa, rationale: e.target.value })}
            />

            <div className="flex justify-end gap-2 pt-1">
              <Button
                type="button"
                variant="ghost"
                size="xs"
                onClick={() => setIsAdding(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                size="xs"
                loading={isSubmitting}
              >
                Propose CAPA Action
              </Button>
            </div>
          </form>
        )}
      </CardContent>

      {/* Modal 1: QA Approval Modal */}
      {approveModalCapa && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="bg-white dark:bg-black rounded-xl shadow-2xl max-w-lg w-full p-5 space-y-4 border border-slate-200 dark:border-zinc-800 text-slate-900 dark:text-zinc-100">
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-zinc-800 pb-3">
              <div className="flex items-center gap-2 text-blue-700 dark:text-blue-400 font-bold text-sm">
                <CheckCircle2 className="w-4 h-4" />
                <span>Formal QA CAPA Approval</span>
              </div>
              <button onClick={() => setApproveModalCapa(null)} className="text-slate-400 hover:text-slate-600 dark:hover:text-zinc-300">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="text-xs text-slate-600 dark:text-zinc-400 space-y-2">
              <p>
                You are formally approving <strong>CAPA #{approveModalCapa.id}</strong> (
                {approveModalCapa.action_type}):
              </p>
              <p className="p-2.5 rounded bg-slate-50 dark:bg-zinc-950 border border-slate-200 dark:border-zinc-800 font-medium text-slate-800 dark:text-zinc-200">
                {approveModalCapa.description}
              </p>
              <p className="text-[11px] text-slate-500 dark:text-zinc-500">
                By approving, this CAPA transitions to <strong>APPROVED</strong> status and work implementation may
                begin.
              </p>
            </div>

            <Textarea
              label="QA Approval Notes (Optional)"
              rows={3}
              placeholder="Enter QA authorization rationale or special constraints..."
              value={approvalNotes}
              onChange={(e) => setApprovalNotes(e.target.value)}
            />

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-200 dark:border-zinc-800">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setApproveModalCapa(null)}
              >
                Cancel
              </Button>
              <Button
                type="button"
                variant="primary"
                size="sm"
                onClick={handleConfirmApprove}
                loading={isSubmitting}
              >
                Confirm QA Approval
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Modal 2: Implementation Complete Modal */}
      {completeModalCapa && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="bg-white dark:bg-black rounded-xl shadow-2xl max-w-lg w-full p-5 space-y-4 border border-slate-200 dark:border-zinc-800 text-slate-900 dark:text-zinc-100">
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-zinc-800 pb-3">
              <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-400 font-bold text-sm">
                <CheckCheck className="w-4 h-4" />
                <span>Mark CAPA as Completed</span>
              </div>
              <button onClick={() => setCompleteModalCapa(null)} className="text-slate-400 hover:text-slate-600 dark:hover:text-zinc-300">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="text-xs text-slate-600 dark:text-zinc-400 space-y-2">
              <p>
                Documenting implementation completion for <strong>CAPA #{completeModalCapa.id}</strong>:
              </p>
              <p className="p-2.5 rounded bg-slate-50 dark:bg-zinc-950 border border-slate-200 dark:border-zinc-800 font-medium text-slate-800 dark:text-zinc-200">
                {completeModalCapa.description}
              </p>
            </div>

            <Textarea
              label="Completion Notes & Execution Evidence"
              required
              rows={3}
              placeholder="Explain the specific corrective actions taken, work orders executed, or equipment replaced (min 5 characters)..."
              value={completionNotes}
              onChange={(e) => setCompletionNotes(e.target.value)}
            />

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-200 dark:border-zinc-800">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setCompleteModalCapa(null)}
              >
                Cancel
              </Button>
              <Button
                type="button"
                variant="success"
                size="sm"
                onClick={handleConfirmComplete}
                loading={isSubmitting}
              >
                Submit Implementation Completion
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Modal 3: Effectiveness Verification Modal */}
      {verifyEffModalCapa && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-fade-in">
          <div className="bg-white dark:bg-black rounded-xl shadow-2xl max-w-lg w-full p-5 space-y-4 border border-slate-200 dark:border-zinc-800 text-slate-900 dark:text-zinc-100">
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-zinc-800 pb-3">
              <div className="flex items-center gap-2 text-teal-700 dark:text-teal-400 font-bold text-sm">
                <ShieldCheck className="w-4 h-4" />
                <span>Formal QA Effectiveness Verification</span>
              </div>
              <button onClick={() => setVerifyEffModalCapa(null)} className="text-slate-400 hover:text-slate-600 dark:hover:text-zinc-300">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="text-xs text-slate-600 dark:text-zinc-400 space-y-2">
              <p>
                Confirming effectiveness verification for completed <strong>CAPA #{verifyEffModalCapa.id}</strong>:
              </p>
              <div className="p-2.5 rounded bg-slate-50 dark:bg-zinc-950 border border-slate-200 dark:border-zinc-800 space-y-1">
                <p className="font-semibold text-slate-900 dark:text-zinc-100">{verifyEffModalCapa.description}</p>
                <p className="text-slate-600 dark:text-zinc-400">
                  <strong>Defined Criteria:</strong> {verifyEffModalCapa.effectiveness_criteria}
                </p>
              </div>
              <p className="text-[11px] text-slate-500 dark:text-zinc-500">
                By verifying effectiveness, this CAPA record will be permanently locked with status{' '}
                <strong>EFFECTIVENESS_VERIFIED</strong> for cGMP compliance.
              </p>
            </div>

            <Textarea
              label="QA Effectiveness Verification Evidence & Sign-off Notes"
              rows={3}
              placeholder="Document observed commercial batch metrics, monitoring duration, and quantitative proof that recurrence was prevented..."
              value={effectivenessNotes}
              onChange={(e) => setEffectivenessNotes(e.target.value)}
            />

            <div className="flex justify-end gap-2 pt-2 border-t border-slate-200 dark:border-zinc-800">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setVerifyEffModalCapa(null)}
              >
                Cancel
              </Button>
              <Button
                type="button"
                variant="brand"
                size="sm"
                onClick={handleConfirmVerifyEffectiveness}
                loading={isSubmitting}
              >
                Sign & Verify Effectiveness
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Accessible Confirm Dialog replacing window.confirm */}
      <ConfirmDialog
        isOpen={Boolean(deleteTargetId)}
        title="Delete CAPA Action"
        message={`Are you sure you want to permanently delete CAPA Action #${deleteTargetId}? This action cannot be undone.`}
        confirmText="Delete Action"
        cancelText="Cancel"
        variant="danger"
        loading={isSubmitting}
        onClose={() => setDeleteTargetId(null)}
        onConfirm={executeDelete}
      />
    </Card>
  );
};

export default CapaSection;
