import React, { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  GitFork,
  ArrowDown,
  Plus,
  Trash2,
  Check,
  Edit2,
  FileText,
  Link2,
  AlertTriangle,
  ShieldCheck,
  CheckCircle2,
  X,
  Sparkles,
} from 'lucide-react';
import {
  addFiveWhyStep,
  updateFiveWhyStep,
  deleteFiveWhyStep,
  linkFiveWhysEvidence,
  unlinkFiveWhysEvidence,
  verifyFiveWhysStep,
  fetchInvestigationById,
} from '../../store/investigationSlice';
import { generateRcaPackage, applyRcaProposal } from '../../store/copilotSlice';
import { setNotification } from '../../store/uiSlice';
import { Button } from '../ui';
import { AiBadge } from '../common/AiBadge';

export const FiveWhysSection = () => {
  const dispatch = useDispatch();
  const currentInvestigation = useSelector((state) => state.investigation.currentInvestigation);
  const fiveWhys = currentInvestigation?.five_whys || [];
  const dossierEvidences = (currentInvestigation?.evidences || []).filter((e) => !e.is_archived);

  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({ question: '', answer: '', evidence_reference: '' });

  const [isAdding, setIsAdding] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);

  const handleGenerateWithAI = async () => {
    if (!currentInvestigation?.id) return;
    setIsGenerating(true);
    try {
      const pkg = await dispatch(
        generateRcaPackage({ investigationId: currentInvestigation.id })
      ).unwrap();
      if (pkg) {
        await dispatch(
          applyRcaProposal({ investigationId: currentInvestigation.id, rcaData: pkg })
        ).unwrap();
        await dispatch(fetchInvestigationById(currentInvestigation.id));
        dispatch(
          setNotification({
            type: 'success',
            message: '5-Whys and Fishbone 6M causality network synthesized and applied!',
          })
        );
      }
    } catch (err) {
      const errorMsg =
        typeof err === 'string'
          ? err
          : err?.detail || err?.message || 'Failed to generate RCA package. Please verify deviation details.';
      dispatch(
        setNotification({
          type: 'error',
          message: `Generation failed: ${errorMsg}`,
        })
      );
    } finally {
      setIsGenerating(false);
    }
  };
  const [newStep, setNewStep] = useState({
    step_number: fiveWhys.length + 1,
    question: '',
    answer: '',
    evidence_reference: '',
  });

  // Evidence linking modal state
  const [linkingStepId, setLinkingStepId] = useState(null);
  const [selectedEvidenceId, setSelectedEvidenceId] = useState('');
  const [relationshipType, setRelationshipType] = useState('SUPPORTING');
  const [linkExplanation, setLinkExplanation] = useState('');
  const [isSubmittingLink, setIsSubmittingLink] = useState(false);

  const handleStartEdit = (step) => {
    setEditingId(step.id);
    setEditForm({
      question: step.question,
      answer: step.answer,
      evidence_reference: step.evidence_reference || '',
    });
  };

  const handleSaveEdit = (stepId) => {
    dispatch(
      updateFiveWhyStep({
        stepId,
        data: editForm,
      })
    );
    setEditingId(null);
  };

  const handleToggleVerify = async (step) => {
    if (step.is_verified) {
      // Un-verify
      await dispatch(
        verifyFiveWhysStep({
          stepId: step.id,
          isVerified: false,
          notes: 'Unverified by investigator',
        })
      );
      dispatch(
        setNotification({
          type: 'info',
          message: `Why #${step.step_number} marked as unverified hypothesis.`,
        })
      );
    } else {
      // Check for verified supporting evidence
      const hasVerifiedSupporting = (step.evidence_links || []).some(
        (l) => l.relationship_type === 'SUPPORTING' && l.evidence?.is_verified
      );

      if (!hasVerifiedSupporting) {
        dispatch(
          setNotification({
            type: 'error',
            message: `Verification safety rule: Why #${step.step_number} requires at least one verified piece of supporting evidence before it can be verified.`,
          })
        );
        return;
      }

      try {
        await dispatch(
          verifyFiveWhysStep({
            stepId: step.id,
            isVerified: true,
            notes: 'Verified by investigator with supporting empirical evidence.',
          })
        ).unwrap();
        dispatch(
          setNotification({
            type: 'success',
            message: `Why #${step.step_number} verified with supporting evidence.`,
          })
        );
      } catch (err) {
        dispatch(setNotification({ type: 'error', message: String(err) }));
      }
    }
  };

  const handleAddStep = () => {
    if (!newStep.question || !newStep.answer) return;
    dispatch(
      addFiveWhyStep({
        investigationId: currentInvestigation.id,
        data: {
          step_number: fiveWhys.length + 1,
          question: newStep.question,
          answer: newStep.answer,
          evidence_reference: newStep.evidence_reference,
          is_ai_suggested: false,
          is_verified: false,
        },
      })
    );
    setNewStep({ step_number: fiveWhys.length + 2, question: '', answer: '', evidence_reference: '' });
    setIsAdding(false);
  };

  const handleOpenLinkModal = (stepId) => {
    setLinkingStepId(stepId);
    setSelectedEvidenceId(dossierEvidences[0]?.id || '');
    setRelationshipType('SUPPORTING');
    setLinkExplanation('');
  };

  const handleCreateEvidenceLink = async (e) => {
    e.preventDefault();
    if (!linkingStepId || !selectedEvidenceId) return;
    setIsSubmittingLink(true);
    try {
      await dispatch(
        linkFiveWhysEvidence({
          stepId: linkingStepId,
          evidenceId: parseInt(selectedEvidenceId, 10),
          relationshipType,
          explanation: linkExplanation,
        })
      ).unwrap();
      dispatch(
        setNotification({
          type: 'success',
          message: `Evidence linked to Why step as ${relationshipType}.`,
        })
      );
      setLinkingStepId(null);
    } catch (err) {
      dispatch(setNotification({ type: 'error', message: String(err) }));
    } finally {
      setIsSubmittingLink(false);
    }
  };

  const handleUnlinkEvidence = async (stepId, evidenceId) => {
    try {
      await dispatch(unlinkFiveWhysEvidence({ stepId, evidenceId })).unwrap();
      dispatch(
        setNotification({
          type: 'info',
          message: 'Evidence unlinked from Why step.',
        })
      );
    } catch (err) {
      dispatch(setNotification({ type: 'error', message: String(err) }));
    }
  };

  return (
    <div id="section-fivewhys" className="skeuo-card rounded-2xl overflow-hidden mb-6 font-sans">
      {/* Header */}
      <div className="bg-gradient-to-b from-blue-50/80 to-slate-100/60 dark:from-[#0c0e1a] dark:to-[#080a14] px-5 py-4 border-b border-slate-300 dark:border-[#1e2236] flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-blue-100 dark:bg-blue-950/60 border border-blue-300 dark:border-blue-700/50 flex items-center justify-center text-blue-800 dark:text-blue-300 shadow-sm">
            <GitFork className="w-4 h-4" />
          </div>
          <h3 className="font-extrabold text-slate-900 dark:text-white text-sm tracking-tight">
            5 Whys Root Cause Methodology
          </h3>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-50 dark:bg-amber-950/50 text-amber-900 dark:text-amber-300 font-extrabold border border-amber-300 dark:border-amber-700/60">
            {fiveWhys.length} Steps Documented
          </span>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="brand"
            size="xs"
            onClick={handleGenerateWithAI}
            loading={isGenerating}
            icon={<Sparkles className="w-3.5 h-3.5" />}
          >
            Generate 5 Whys & Fishbone with AI
          </Button>
          <button
            onClick={() => setIsAdding(!isAdding)}
            className="skeuo-btn-secondary flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-xl transition cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5 text-cyan-600 dark:text-cyan-400" /> Add Why Step
          </button>
        </div>
      </div>

      <div className="p-5">
        {fiveWhys.length === 0 && (
          <div className="mb-5 p-4 rounded-xl bg-blue-50/80 dark:bg-zinc-950/80 border border-blue-200 dark:border-zinc-800 flex flex-col sm:flex-row items-center justify-between gap-3 animate-fade-in">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-blue-600 dark:bg-cyan-600 text-white flex items-center justify-center shrink-0 shadow-xs">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-800 dark:text-zinc-100">No 5-Whys Steps Documented Yet</h4>
                <p className="text-[11px] text-slate-600 dark:text-zinc-400">
                  Synthesize a progressive root cause causality chain using the AI RCA engine.
                </p>
              </div>
            </div>
            <Button
              variant="primary"
              size="sm"
              onClick={handleGenerateWithAI}
              loading={isGenerating}
              icon={<Sparkles className="w-4 h-4" />}
            >
              Generate 5 Whys & Fishbone with AI
            </Button>
          </div>
        )}
        <p className="text-xs text-slate-500 dark:text-zinc-400 mb-5 leading-relaxed">
          The 5 Whys drill down from the observed manufacturing symptom to the underlying equipment, procedural, or system failure. Every verified step must be supported by empirical evidence.
        </p>

        {/* Sequential Cascade */}
        <div className="space-y-4">
          {fiveWhys.map((step, index) => {
            const isLast = index === fiveWhys.length - 1;
            const isEditing = editingId === step.id;
            const evidenceLinks = step.evidence_links || [];

            return (
              <React.Fragment key={step.id}>
                <div
                  className={`p-4 rounded-xl border transition ${
                    isLast && fiveWhys.length >= 3
                      ? 'bg-rose-50/40 dark:bg-rose-950/20 border-rose-300 dark:border-rose-900/50'
                      : 'bg-slate-50/70 dark:bg-zinc-950/90 border-slate-300 dark:border-zinc-800'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white ${
                        isLast && fiveWhys.length >= 4 ? 'bg-rose-600' : 'bg-blue-600 dark:bg-sky-600'
                      }`}>
                        {step.step_number}
                      </span>
                      <span className="text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-zinc-400">
                        {isLast && fiveWhys.length >= 4 ? 'Root Cause Why' : `Why #${step.step_number}`}
                      </span>

                      {/* Verification Status Badge */}
                      <button
                        onClick={() => handleToggleVerify(step)}
                        className={`text-[11px] font-semibold px-2 py-0.5 rounded flex items-center gap-1 transition ${
                          step.is_verified
                            ? 'bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800'
                            : 'bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-800 hover:bg-amber-200 dark:hover:bg-amber-900'
                        }`}
                        title={step.is_verified ? 'Click to unverify' : 'Click to verify (requires verified supporting evidence)'}
                      >
                        {step.is_verified ? (
                          <>
                            <ShieldCheck className="w-3 h-3 text-emerald-600" />
                            <span>VERIFIED</span>
                          </>
                        ) : (
                          <>
                            <AlertTriangle className="w-3 h-3 text-amber-600" />
                            <span>HYPOTHESIS</span>
                          </>
                        )}
                      </button>

                      <AiBadge
                        isAiSuggested={step.is_ai_suggested}
                        isVerified={step.is_verified}
                      />
                    </div>

                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleOpenLinkModal(step.id)}
                        className="p-1 rounded hover:bg-blue-100 text-blue-600 flex items-center gap-1 text-[11px] font-semibold px-1.5"
                        title="Link Evidence"
                      >
                        <Link2 className="w-3.5 h-3.5" />
                        <span className="hidden sm:inline">Link Evidence</span>
                      </button>
                      {isEditing ? (
                        <button
                          onClick={() => handleSaveEdit(step.id)}
                          className="p-1 rounded hover:bg-emerald-100 text-emerald-700"
                          title="Save"
                        >
                          <Check className="w-4 h-4" />
                        </button>
                      ) : (
                        <button
                          onClick={() => handleStartEdit(step)}
                          className="p-1 rounded hover:bg-slate-200 text-slate-600"
                          title="Edit"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                      )}
                      <button
                        onClick={() => dispatch(deleteFiveWhyStep(step.id))}
                        className="p-1 rounded hover:bg-rose-100 text-rose-600"
                        title="Delete"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  {isEditing ? (
                    <div className="space-y-2 mt-2">
                      <input
                        type="text"
                        value={editForm.question}
                        onChange={(e) => setEditForm({ ...editForm, question: e.target.value })}
                        className="w-full text-xs font-semibold px-2.5 py-1.5 border rounded-lg bg-white dark:bg-black border-slate-300 dark:border-zinc-700 text-slate-900 dark:text-zinc-100"
                        placeholder="Question"
                      />
                      <textarea
                        rows={2}
                        value={editForm.answer}
                        onChange={(e) => setEditForm({ ...editForm, answer: e.target.value })}
                        className="w-full text-xs px-2.5 py-1.5 border rounded-lg bg-white dark:bg-black border-slate-300 dark:border-zinc-700 text-slate-900 dark:text-zinc-100"
                        placeholder="Answer"
                      />
                      <input
                        type="text"
                        value={editForm.evidence_reference}
                        onChange={(e) => setEditForm({ ...editForm, evidence_reference: e.target.value })}
                        className="w-full text-xs px-2.5 py-1 border rounded-lg bg-white dark:bg-black border-slate-300 dark:border-zinc-700 text-slate-900 dark:text-zinc-100"
                        placeholder="Evidence reference string"
                      />
                    </div>
                  ) : (
                    <div>
                      <p className="text-xs font-semibold text-slate-800 dark:text-zinc-100 mb-1">Q: {step.question}</p>
                      <p className="text-xs text-slate-700 dark:text-zinc-200 bg-white dark:bg-black p-2.5 rounded-lg border border-slate-200/80 dark:border-zinc-800 leading-relaxed font-sans">
                        A: {step.answer}
                      </p>

                      {/* Evidence Links */}
                      {evidenceLinks.length > 0 && (
                        <div className="mt-2.5 pt-2 border-t border-slate-200 dark:border-zinc-800 space-y-1">
                          <span className="text-[10px] font-bold text-slate-500 dark:text-zinc-400 uppercase tracking-wider block font-mono">
                            Linked Evidence Dossier ({evidenceLinks.length}):
                          </span>
                          <div className="flex flex-wrap gap-1.5">
                            {evidenceLinks.map((link) => {
                              const isSupporting = link.relationship_type === 'SUPPORTING';
                              return (
                                <span
                                  key={link.id}
                                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium border ${
                                    isSupporting
                                      ? 'bg-emerald-50 dark:bg-emerald-950/80 text-emerald-800 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800'
                                      : 'bg-rose-50 dark:bg-rose-950/80 text-rose-800 dark:text-rose-300 border-rose-200 dark:border-rose-800'
                                  }`}
                                >
                                  <strong>{link.relationship_type}:</strong>
                                  <span>{link.evidence?.title || `Evidence #${link.evidence_id}`}</span>
                                  {link.evidence?.is_verified && (
                                    <CheckCircle2 className="w-2.5 h-2.5 text-emerald-600" title="Verified Evidence" />
                                  )}
                                  <button
                                    onClick={() => handleUnlinkEvidence(step.id, link.evidence_id)}
                                    className="ml-1 text-slate-400 hover:text-rose-600"
                                    title="Unlink"
                                  >
                                    <X className="w-2.5 h-2.5" />
                                  </button>
                                </span>
                              );
                            })}
                          </div>
                        </div>
                      )}

                      {step.evidence_reference && evidenceLinks.length === 0 && (
                        <div className="mt-2 flex items-center gap-1.5 text-xs text-slate-500 font-mono">
                          <FileText className="w-3.5 h-3.5 text-slate-400" />
                          <span>Citation: {step.evidence_reference}</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {!isLast && (
                  <div className="flex justify-center my-1">
                    <ArrowDown className="w-4 h-4 text-blue-400" />
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>

        {/* Add Step Inline Form */}
        {isAdding && (
          <div className="mt-4 p-4 rounded-xl border border-blue-200 dark:border-zinc-800 bg-blue-50/30 dark:bg-zinc-950/80 space-y-3">
            <h4 className="text-xs font-bold text-blue-900 dark:text-cyan-400 uppercase font-mono">Add Next Why Step</h4>
            <input
              type="text"
              placeholder={`Why #${fiveWhys.length + 1} Question...`}
              value={newStep.question}
              onChange={(e) => setNewStep({ ...newStep, question: e.target.value })}
              className="w-full text-xs px-3 py-2 border rounded-lg bg-white dark:bg-black border-slate-300 dark:border-zinc-700 text-slate-900 dark:text-zinc-100"
            />
            <textarea
              rows={2}
              placeholder="Observed or verified answer..."
              value={newStep.answer}
              onChange={(e) => setNewStep({ ...newStep, answer: e.target.value })}
              className="w-full text-xs px-3 py-2 border rounded-lg bg-white dark:bg-black border-slate-300 dark:border-zinc-700 text-slate-900 dark:text-zinc-100"
            />
            <input
              type="text"
              placeholder="Supporting evidence reference..."
              value={newStep.evidence_reference}
              onChange={(e) => setNewStep({ ...newStep, evidence_reference: e.target.value })}
              className="w-full text-xs px-3 py-1.5 border rounded-lg bg-white dark:bg-black border-slate-300 dark:border-zinc-700 text-slate-900 dark:text-zinc-100"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setIsAdding(false)}
                className="px-3 py-1 text-xs font-medium text-slate-600 dark:text-zinc-400 hover:bg-slate-100 dark:hover:bg-zinc-800 rounded"
              >
                Cancel
              </button>
              <button
                onClick={handleAddStep}
                className="px-3 py-1 text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white rounded cursor-pointer"
              >
                Add Step
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Link Evidence Modal */}
      {linkingStepId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 dark:bg-black/80 backdrop-blur-xs p-4">
          <div className="bg-white dark:bg-black rounded-2xl border border-slate-200 dark:border-zinc-800 shadow-xl max-w-md w-full p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="font-bold text-sm text-slate-900 dark:text-zinc-100 flex items-center gap-2">
                <Link2 className="w-4 h-4 text-blue-600 dark:text-cyan-400" />
                Link Evidence to Why Step
              </h4>
              <button
                onClick={() => setLinkingStepId(null)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-zinc-300 p-1 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateEvidenceLink} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-zinc-300 mb-1">
                  Select Evidence from Dossier
                </label>
                <select
                  value={selectedEvidenceId}
                  onChange={(e) => setSelectedEvidenceId(e.target.value)}
                  className="w-full text-xs px-3 py-2 border rounded-lg bg-white dark:bg-black border-slate-300 dark:border-zinc-700 text-slate-900 dark:text-zinc-100"
                  required
                >
                  {dossierEvidences.map((ev) => (
                    <option key={ev.id} value={ev.id}>
                      #{ev.id} - {ev.title} ({ev.evidence_type}) {ev.is_verified ? '✓ Verified' : ''}
                    </option>
                  ))}
                </select>
                {dossierEvidences.length === 0 && (
                  <p className="text-[11px] text-amber-600 mt-1">
                    No active evidence records available in this investigation dossier.
                  </p>
                )}
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Relationship Type
                </label>
                <div className="flex gap-3">
                  <label className="flex items-center gap-1.5 text-xs text-slate-700 cursor-pointer">
                    <input
                      type="radio"
                      name="rel_type"
                      value="SUPPORTING"
                      checked={relationshipType === 'SUPPORTING'}
                      onChange={() => setRelationshipType('SUPPORTING')}
                    />
                    <span className="font-semibold text-emerald-700">Supporting</span>
                  </label>
                  <label className="flex items-center gap-1.5 text-xs text-slate-700 cursor-pointer">
                    <input
                      type="radio"
                      name="rel_type"
                      value="CONTRADICTORY"
                      checked={relationshipType === 'CONTRADICTORY'}
                      onChange={() => setRelationshipType('CONTRADICTORY')}
                    />
                    <span className="font-semibold text-rose-700">Contradictory</span>
                  </label>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Relevance Explanation (Optional)
                </label>
                <textarea
                  rows={2}
                  value={linkExplanation}
                  onChange={(e) => setLinkExplanation(e.target.value)}
                  placeholder="Explain how this record substantiates or refutes the causal step..."
                  className="w-full text-xs px-3 py-2 border rounded-lg"
                />
              </div>

              <div className="pt-3 flex justify-end gap-2 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setLinkingStepId(null)}
                  className="px-3 py-1.5 text-xs font-semibold rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmittingLink || !selectedEvidenceId}
                  className="px-4 py-1.5 text-xs font-semibold rounded-lg bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-50"
                >
                  {isSubmittingLink ? 'Linking...' : 'Link Evidence'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default FiveWhysSection;
