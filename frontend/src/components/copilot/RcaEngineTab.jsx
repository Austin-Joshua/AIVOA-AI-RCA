import React, { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  Sparkles,
  GitFork,
  Layers,
  ShieldCheck,
  CheckCircle2,
  ArrowRight,
  RotateCcw,
  Plus,
  Check,
  AlertCircle,
  FileQuestion,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import {
  generateRcaPackage,
  applyRcaProposal,
  applyRcaItem,
  clearRcaProposal,
} from '../../store/copilotSlice';
import { setNotification } from '../../store/uiSlice';

export const RcaEngineTab = () => {
  const dispatch = useDispatch();
  const currentInvestigation = useSelector((state) => state.investigation.currentInvestigation);
  const { rcaProposal, isGeneratingRca, rcaError } = useSelector((state) => state.copilot);

  const [acceptedItems, setAcceptedItems] = useState({});
  const [activeAccordion, setActiveAccordion] = useState('five_whys'); // five_whys, fishbone, root_causes, capas, gaps

  const handleGenerate = () => {
    if (!currentInvestigation) return;
    setAcceptedItems({});
    dispatch(
      generateRcaPackage({
        investigationId: currentInvestigation.id,
        userContext: 'Investigator reviewed SCADA trend and teardown report.',
      })
    );
  };

  const handleApplyAll = () => {
    if (!currentInvestigation || !rcaProposal) return;
    dispatch(
      applyRcaProposal({
        investigationId: currentInvestigation.id,
        rcaData: rcaProposal,
      })
    );
    dispatch(
      setNotification({
        type: 'success',
        message: 'All RCA proposals accepted and applied to RCA Form!',
      })
    );
  };

  const handleAcceptSingleItem = async (itemType, itemData, key) => {
    if (!currentInvestigation) return;
    try {
      await dispatch(
        applyRcaItem({
          investigationId: currentInvestigation.id,
          itemType,
          itemData,
        })
      ).unwrap();
      setAcceptedItems((prev) => ({ ...prev, [key]: true }));
      dispatch(
        setNotification({
          type: 'success',
          message: `Accepted ${itemType.replace('_', ' ')} into investigation.`,
        })
      );
    } catch (err) {
      dispatch(setNotification({ type: 'error', message: String(err) }));
    }
  };

  return (
    <div className="space-y-4">
      {/* Action Banner */}
      <div className="p-4 rounded-xl bg-gradient-to-br from-indigo-50 to-blue-50 dark:from-zinc-900 dark:to-black border border-blue-200 dark:border-zinc-800">
        <h4 className="text-xs font-bold text-slate-800 dark:text-zinc-100 flex items-center gap-1.5 mb-1">
          <Sparkles className="w-4 h-4 text-indigo-600 dark:text-cyan-400" />
          LangGraph Multi-Methodology RCA Engine
        </h4>
        <p className="text-[11px] text-slate-600 dark:text-zinc-400 mb-3 leading-relaxed">
          Executes orchestrated causality chaining using <strong>5-Whys</strong> and <strong>Ishikawa 6Ms</strong>. Formulates root cause hypotheses and CAPA actions grounded strictly in verified dossier evidence.
        </p>
        <button
          onClick={handleGenerate}
          disabled={isGeneratingRca}
          className="w-full py-2.5 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 dark:from-cyan-600 dark:to-blue-600 dark:hover:from-cyan-500 dark:hover:to-blue-500 disabled:opacity-50 text-white text-xs font-bold flex items-center justify-center gap-2 shadow-xs transition cursor-pointer"
        >
          {isGeneratingRca ? (
            <>
              <Sparkles className="w-4 h-4 animate-spin" />
              <span>Analyzing Causality & Evidence...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-4 h-4" />
              <span>Generate Full RCA & CAPA Package</span>
            </>
          )}
        </button>
      </div>

      {rcaError && (
        <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-xs text-rose-800 dark:text-rose-200 flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Inference Unavailable</p>
            <p className="text-[11px] text-rose-700 dark:text-rose-300 mt-0.5">{rcaError}</p>
          </div>
        </div>
      )}

      {/* Generated Proposal Itemized Review */}
      {rcaProposal && (
        <div className="p-4 rounded-xl border border-indigo-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 shadow-2xs space-y-4">
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-xs font-bold text-indigo-950 dark:text-zinc-100">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              RCA Proposal Package Ready for Review
            </span>
            <button
              onClick={() => dispatch(clearRcaProposal())}
              className="text-slate-400 hover:text-slate-600 dark:hover:text-zinc-200 p-1 cursor-pointer"
              title="Reset"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>

          {rcaProposal.investigator_guidance && (
            <div className="p-2.5 rounded-lg bg-amber-50/70 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900/60 text-[11px] text-amber-900 dark:text-amber-200 leading-snug">
              <strong>Investigator Guidance:</strong> {rcaProposal.investigator_guidance}
            </div>
          )}

          {/* Section 1: 5-Whys Proposals */}
          <div className="border border-slate-200 dark:border-zinc-800 rounded-lg overflow-hidden">
            <button
              onClick={() => setActiveAccordion(activeAccordion === 'five_whys' ? null : 'five_whys')}
              className="w-full px-3 py-2 bg-slate-50 dark:bg-black flex items-center justify-between text-xs font-bold text-slate-700 dark:text-zinc-300 cursor-pointer"
            >
              <span className="flex items-center gap-1.5">
                <GitFork className="w-3.5 h-3.5 text-blue-600 dark:text-cyan-400" />
                Proposed 5-Whys Chain ({rcaProposal.five_whys?.length || 0} steps)
              </span>
              {activeAccordion === 'five_whys' ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
            </button>
            {activeAccordion === 'five_whys' && (
              <div className="p-3 space-y-2 bg-white dark:bg-zinc-950 divide-y divide-slate-100 dark:divide-zinc-800/80">
                {rcaProposal.five_whys?.map((step, idx) => {
                  const key = `why_${idx}`;
                  const isAccepted = acceptedItems[key];
                  return (
                    <div key={idx} className="pt-2 first:pt-0 flex items-start justify-between gap-2">
                      <div className="text-[11px] space-y-0.5 flex-1">
                        <span className="font-bold text-blue-700 dark:text-cyan-400">Why #{step.step_number}:</span> {step.question}
                        <p className="text-slate-600 dark:text-zinc-300 bg-slate-50 dark:bg-black p-1.5 rounded text-[11px] border border-slate-100 dark:border-zinc-800">A: {step.answer}</p>
                        {step.evidence_reference && (
                          <span className="text-[10px] text-slate-400 dark:text-zinc-500 font-mono">Ref: {step.evidence_reference}</span>
                        )}
                      </div>
                      <button
                        onClick={() => handleAcceptSingleItem('FIVE_WHYS', step, key)}
                        disabled={isAccepted}
                        className={`px-2 py-1 text-[10px] font-semibold rounded shrink-0 flex items-center gap-1 cursor-pointer ${
                          isAccepted
                            ? 'bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300'
                            : 'bg-blue-50 dark:bg-cyan-950/60 text-blue-700 dark:text-cyan-300 hover:bg-blue-100 dark:hover:bg-cyan-900 border border-blue-200 dark:border-cyan-800'
                        }`}
                      >
                        {isAccepted ? <Check className="w-3 h-3" /> : <Plus className="w-3 h-3" />}
                        {isAccepted ? 'Accepted' : 'Accept'}
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Section 2: Fishbone Proposals */}
          <div className="border border-slate-200 dark:border-zinc-800 rounded-lg overflow-hidden">
            <button
              onClick={() => setActiveAccordion(activeAccordion === 'fishbone' ? null : 'fishbone')}
              className="w-full px-3 py-2 bg-slate-50 dark:bg-black flex items-center justify-between text-xs font-bold text-slate-700 dark:text-zinc-300 cursor-pointer"
            >
              <span className="flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
                Proposed Fishbone Factors ({rcaProposal.fishbone_causes?.length || 0} factors)
              </span>
              {activeAccordion === 'fishbone' ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
            </button>
            {activeAccordion === 'fishbone' && (
              <div className="p-3 space-y-2 bg-white dark:bg-zinc-950 divide-y divide-slate-100 dark:divide-zinc-800/80">
                {rcaProposal.fishbone_causes?.map((cause, idx) => {
                  const key = `fishbone_${idx}`;
                  const isAccepted = acceptedItems[key];
                  return (
                    <div key={idx} className="pt-2 first:pt-0 flex items-start justify-between gap-2">
                      <div className="text-[11px] space-y-0.5 flex-1">
                        <span className="font-bold text-indigo-700 dark:text-indigo-400 uppercase">[{cause.category}]:</span> {cause.cause_description}
                        {cause.rationale && <p className="text-slate-500 dark:text-zinc-400 text-[10px]">Rationale: {cause.rationale}</p>}
                      </div>
                      <button
                        onClick={() => handleAcceptSingleItem('FISHBONE', cause, key)}
                        disabled={isAccepted}
                        className={`px-2 py-1 text-[10px] font-semibold rounded shrink-0 flex items-center gap-1 cursor-pointer ${
                          isAccepted
                            ? 'bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300'
                            : 'bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 hover:bg-indigo-100 dark:hover:bg-indigo-900 border border-indigo-200 dark:border-indigo-800'
                        }`}
                      >
                        {isAccepted ? <Check className="w-3 h-3" /> : <Plus className="w-3 h-3" />}
                        {isAccepted ? 'Accepted' : 'Accept'}
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Section 3: Root Cause Proposals */}
          <div className="border border-slate-200 dark:border-zinc-800 rounded-lg overflow-hidden">
            <button
              onClick={() => setActiveAccordion(activeAccordion === 'root_causes' ? null : 'root_causes')}
              className="w-full px-3 py-2 bg-slate-50 dark:bg-black flex items-center justify-between text-xs font-bold text-slate-700 dark:text-zinc-300 cursor-pointer"
            >
              <span className="flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-purple-600 dark:text-purple-400" />
                Root Cause Proposals ({rcaProposal.root_causes?.length || 0} proposals)
              </span>
              {activeAccordion === 'root_causes' ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
            </button>
            {activeAccordion === 'root_causes' && (
              <div className="p-3 space-y-2 bg-white dark:bg-zinc-950 divide-y divide-slate-100 dark:divide-zinc-800/80">
                {rcaProposal.root_causes?.map((rc, idx) => {
                  const key = `rc_${idx}`;
                  const isAccepted = acceptedItems[key];
                  return (
                    <div key={idx} className="pt-2 first:pt-0 flex items-start justify-between gap-2">
                      <div className="text-[11px] space-y-0.5 flex-1">
                        <span className="font-bold text-purple-700 dark:text-purple-400">
                          {rc.is_primary ? 'Primary Root Cause: ' : 'Contributing Factor: '}
                        </span>
                        <span className="text-slate-800 dark:text-zinc-200">{rc.cause_statement}</span>
                        {rc.rationale && <p className="text-slate-500 dark:text-zinc-400 text-[10px]">Rationale: {rc.rationale}</p>}
                      </div>
                      <button
                        onClick={() => handleAcceptSingleItem('ROOT_CAUSE', rc, key)}
                        disabled={isAccepted}
                        className={`px-2 py-1 text-[10px] font-semibold rounded shrink-0 flex items-center gap-1 cursor-pointer ${
                          isAccepted
                            ? 'bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300'
                            : 'bg-purple-50 dark:bg-purple-950/60 text-purple-700 dark:text-purple-300 hover:bg-purple-100 dark:hover:bg-purple-900 border border-purple-200 dark:border-purple-800'
                        }`}
                      >
                        {isAccepted ? <Check className="w-3 h-3" /> : <Plus className="w-3 h-3" />}
                        {isAccepted ? 'Accepted' : 'Accept (Proposed)'}
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Section 4: CAPA Proposals */}
          <div className="border border-slate-200 dark:border-zinc-800 rounded-lg overflow-hidden">
            <button
              onClick={() => setActiveAccordion(activeAccordion === 'capas' ? null : 'capas')}
              className="w-full px-3 py-2 bg-slate-50 dark:bg-black flex items-center justify-between text-xs font-bold text-slate-700 dark:text-zinc-300 cursor-pointer"
            >
              <span className="flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                Proposed CAPAs ({rcaProposal.capa_actions?.length || 0} actions)
              </span>
              {activeAccordion === 'capas' ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
            </button>
            {activeAccordion === 'capas' && (
              <div className="p-3 space-y-2 bg-white dark:bg-zinc-950 divide-y divide-slate-100 dark:divide-zinc-800/80">
                {rcaProposal.capa_actions?.map((capa, idx) => {
                  const key = `capa_${idx}`;
                  const isAccepted = acceptedItems[key];
                  return (
                    <div key={idx} className="pt-2 first:pt-0 flex items-start justify-between gap-2">
                      <div className="text-[11px] space-y-0.5 flex-1">
                        <span className="font-bold text-emerald-700 dark:text-emerald-400 uppercase">[{capa.action_type}]:</span>{' '}
                        <span className="text-slate-800 dark:text-zinc-200">{capa.description}</span>
                        <p className="text-slate-400 dark:text-zinc-500 text-[10px]">Owner: {capa.owner || 'Unassigned'} | Due: {capa.deadline || '30 Days'}</p>
                      </div>
                      <button
                        onClick={() => handleAcceptSingleItem('CAPA', capa, key)}
                        disabled={isAccepted}
                        className={`px-2 py-1 text-[10px] font-semibold rounded shrink-0 flex items-center gap-1 cursor-pointer ${
                          isAccepted
                            ? 'bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300'
                            : 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-100 dark:hover:bg-emerald-900 border border-emerald-200 dark:border-emerald-800'
                        }`}
                      >
                        {isAccepted ? <Check className="w-3 h-3" /> : <Plus className="w-3 h-3" />}
                        {isAccepted ? 'Accepted' : 'Accept'}
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Section 5: Evidence Gaps */}
          {rcaProposal.evidence_gaps?.length > 0 && (
            <div className="border border-slate-200 dark:border-zinc-800 rounded-lg overflow-hidden">
              <button
                onClick={() => setActiveAccordion(activeAccordion === 'gaps' ? null : 'gaps')}
                className="w-full px-3 py-2 bg-slate-50 dark:bg-black flex items-center justify-between text-xs font-bold text-slate-700 dark:text-zinc-300 cursor-pointer"
              >
                <span className="flex items-center gap-1.5">
                  <FileQuestion className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
                  Identified Evidence Gaps ({rcaProposal.evidence_gaps?.length} gaps)
                </span>
                {activeAccordion === 'gaps' ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
              </button>
              {activeAccordion === 'gaps' && (
                <div className="p-3 space-y-2 bg-white dark:bg-zinc-950 divide-y divide-slate-100 dark:divide-zinc-800/80">
                  {rcaProposal.evidence_gaps.map((gap, idx) => {
                    const key = `gap_${idx}`;
                    const isAccepted = acceptedItems[key];
                    const gapText = typeof gap === 'string' ? gap : gap.question;
                    return (
                      <div key={idx} className="pt-2 first:pt-0 flex items-start justify-between gap-2">
                        <div className="text-[11px] text-slate-700 dark:text-zinc-300 flex-1">
                          {gapText}
                        </div>
                        <button
                          onClick={() => handleAcceptSingleItem('EVIDENCE_GAP', typeof gap === 'string' ? { question: gap } : gap, key)}
                          disabled={isAccepted}
                          className={`px-2 py-1 text-[10px] font-semibold rounded shrink-0 flex items-center gap-1 cursor-pointer ${
                            isAccepted
                              ? 'bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300'
                              : 'bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 hover:bg-amber-100 dark:hover:bg-amber-900 border border-amber-200 dark:border-amber-800'
                          }`}
                        >
                          {isAccepted ? <Check className="w-3 h-3" /> : <Plus className="w-3 h-3" />}
                          {isAccepted ? 'Accepted' : 'Accept'}
                        </button>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* Accept Complete Package Button */}
          <button
            onClick={handleApplyAll}
            className="w-full py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 dark:bg-cyan-600 dark:hover:bg-cyan-500 text-white text-xs font-bold flex items-center justify-center gap-2 shadow-sm transition cursor-pointer"
          >
            <span>Accept All Proposals to Investigation</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
};

export default RcaEngineTab;
