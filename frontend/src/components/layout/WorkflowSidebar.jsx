import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { setActiveStage } from '../../store/investigationSlice';
import {
  FileSearch,
  Crosshair,
  GitFork,
  ShieldAlert,
  ClipboardCheck,
  Check,
  Layers,
} from 'lucide-react';

const STAGES = [
  {
    id: 'INTAKE',
    stepNumber: '01',
    label: '1. Incident Intake',
    subtitle: 'Telemetry & Triage',
    sectionId: 'section-deviation',
    icon: FileSearch,
  },
  {
    id: 'INVESTIGATION',
    stepNumber: '02',
    label: '2. Evidence & Timeline',
    subtitle: 'Corroboration',
    sectionId: 'section-evidence',
    icon: Crosshair,
  },
  {
    id: 'ROOT_CAUSE',
    stepNumber: '03',
    label: '3. 5-Whys & Fishbone',
    subtitle: 'Causality Trees',
    sectionId: 'section-fishbone',
    icon: GitFork,
  },
  {
    id: 'CAPA',
    stepNumber: '04',
    label: '4. CAPA Recommendations',
    subtitle: 'Preventive Actions',
    sectionId: 'section-capa',
    icon: ShieldAlert,
  },
  {
    id: 'APPROVAL',
    stepNumber: '05',
    label: '5. Review & Sign-Off',
    subtitle: '21 CFR Part 11 Gate',
    sectionId: 'section-approval',
    icon: ClipboardCheck,
  },
];

export const WorkflowSidebar = () => {
  const dispatch = useDispatch();
  const activeStage = useSelector((state) => state.investigation.activeStage);
  const currentInvestigation = useSelector((state) => state.investigation.currentInvestigation);

  const activeIndex = STAGES.findIndex((s) => s.id === activeStage);
  const progressPercent = Math.min(100, Math.round(((activeIndex + 1) / STAGES.length) * 100));

  const handleStageClick = (stage) => {
    dispatch(setActiveStage(stage.id));
    const targetEl = document.getElementById(stage.sectionId);
    if (targetEl) {
      targetEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  // Scroll-spy observer: detects which section is currently centered/in view
  useEffect(() => {
    const sectionIds = STAGES.map((s) => s.sectionId);
    const handleScroll = () => {
      const scrollPosition = window.scrollY + 180;
      for (let i = sectionIds.length - 1; i >= 0; i--) {
        const el = document.getElementById(sectionIds[i]);
        if (el && el.offsetTop <= scrollPosition) {
          if (activeStage !== STAGES[i].id) {
            dispatch(setActiveStage(STAGES[i].id));
          }
          break;
        }
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [activeStage, dispatch]);

  return (
    <nav
      aria-label="Investigation Stages Sidebar"
      className="skeuo-surface-raised rounded-2xl p-4 border border-slate-300 dark:border-[#1e2236] shadow-md font-sans"
    >
      {/* ── Sidebar Header: Workflow Stages & Progress ──────────────────── */}
      <div className="pb-3 mb-3 border-b border-slate-200 dark:border-[#1e2236]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-lg bg-blue-100 dark:bg-blue-950/50 border border-blue-300 dark:border-blue-700/50 flex items-center justify-center text-blue-800 dark:text-blue-300">
              <Layers className="w-3.5 h-3.5" />
            </div>
            <h3 className="text-xs font-black uppercase tracking-wider text-slate-800 dark:text-slate-200 font-mono">
              Workflow Stages
            </h3>
          </div>
          <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-amber-50 dark:bg-amber-950/40 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-700/50">
            {activeIndex + 1} / {STAGES.length}
          </span>
        </div>

        {/* Progress Bar — Royal Blue Gradient */}
        <div className="mt-2.5 w-full bg-slate-200 dark:bg-[#12152a] rounded-full h-1.5 overflow-hidden">
          <div
            className="bg-gradient-to-r from-blue-700 to-indigo-600 h-full rounded-full transition-all duration-300"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      {/* ── Vertical Timeline Stages List ──────────────────────────────── */}
      <div className="relative space-y-2">
        {/* Continuous vertical timeline rail line */}
        <div className="absolute left-[19px] top-3 bottom-3 w-[2px] bg-slate-200 dark:bg-[#1e2236] z-0 pointer-events-none" />

        {STAGES.map((stage, idx) => {
          const isActive = activeStage === stage.id;
          const isCompleted = activeIndex > idx || (idx === 4 && currentInvestigation?.is_approved);

          return (
            <div key={stage.id} className="relative z-10">
              <button
                onClick={() => handleStageClick(stage)}
                aria-current={isActive ? 'step' : undefined}
                aria-label={`Stage ${stage.stepNumber}: ${stage.label}`}
                className={`w-full text-left py-2.5 px-2.5 rounded-xl transition-all border select-none cursor-pointer active:translate-y-0.5 flex items-center gap-3 ${
                  isActive
                    ? 'skeuo-step-btn-active shadow-md ring-1 ring-blue-500/40'
                    : isCompleted
                    ? 'bg-slate-50/90 dark:bg-[#0c0e1a]/70 border-emerald-300 dark:border-emerald-800/50 text-slate-800 dark:text-slate-200 hover:border-emerald-400'
                    : 'bg-slate-50/60 dark:bg-[#0c0e1a]/40 border-slate-200 dark:border-[#1e2236]/60 text-slate-600 dark:text-slate-400 hover:border-slate-300 dark:hover:border-[#2a3050] hover:text-slate-900 dark:hover:text-slate-100'
                }`}
              >
                {/* Tactical Step Indicator Badge */}
                <div
                  className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 transition-all font-mono font-bold text-xs z-10 ${
                    isActive
                      ? 'bg-blue-700 dark:bg-blue-600 text-white shadow-md shadow-blue-700/30 ring-2 ring-blue-300 dark:ring-blue-400/30'
                      : isCompleted
                      ? 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800/50'
                      : 'bg-slate-200 dark:bg-[#12152a] text-slate-500 dark:text-slate-400 border border-slate-300 dark:border-[#1e2236]'
                  }`}
                >
                  {isCompleted && !isActive ? (
                    <Check className="w-3.5 h-3.5 stroke-[3]" />
                  ) : (
                    <span className="text-[10px]">{stage.stepNumber}</span>
                  )}
                </div>

                {/* Stage Text & Description */}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-1">
                    <p
                      className={`text-xs font-bold truncate leading-tight tracking-tight ${
                        isActive
                          ? 'text-blue-900 dark:text-white'
                          : 'text-slate-800 dark:text-slate-200'
                      }`}
                    >
                      {stage.label}
                    </p>
                    {isActive && (
                      <span className="w-1.5 h-1.5 rounded-full bg-blue-600 dark:bg-blue-400 animate-pulse shrink-0" />
                    )}
                  </div>
                  <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate leading-none mt-0.5 font-medium">
                    {stage.subtitle}
                  </p>
                </div>
              </button>
            </div>
          );
        })}
      </div>

      {/* ── Investigation Context Summary Card ─────────────────────────── */}
      {currentInvestigation && (
        <div className="mt-4 pt-3 border-t border-slate-200 dark:border-[#1e2236]">
          <div className="p-2.5 rounded-xl bg-blue-50/50 dark:bg-[#0c0e1a] border border-blue-100 dark:border-[#1e2236]/80 text-[11px] space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="text-slate-500 dark:text-slate-400 font-mono text-[10px] uppercase font-bold">
                Deviation
              </span>
              <span className="font-mono font-bold text-slate-900 dark:text-white">
                {currentInvestigation.deviation_number || 'DEV-2026-104'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500 dark:text-slate-400 font-mono text-[10px] uppercase font-bold">
                Batch
              </span>
              <span className="font-mono font-semibold text-blue-800 dark:text-blue-400">
                {currentInvestigation.batch_number || 'API-2026-104'}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-slate-500 dark:text-slate-400 font-mono text-[10px] uppercase font-bold">
                Status
              </span>
              <span
                className={`text-[9px] font-mono font-bold px-1.5 py-0.2 rounded ${
                  currentInvestigation.is_approved
                    ? 'bg-emerald-100 dark:bg-emerald-950/50 text-emerald-800 dark:text-emerald-300'
                    : 'bg-amber-100 dark:bg-amber-950/50 text-amber-800 dark:text-amber-300'
                }`}
              >
                {currentInvestigation.is_approved ? 'QA APPROVED' : 'IN REVIEW'}
              </span>
            </div>
          </div>
        </div>
      )}
    </nav>
  );
};

export default WorkflowSidebar;
