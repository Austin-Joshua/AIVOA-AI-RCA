import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { setActiveStage } from '../../store/investigationSlice';
import {
  FileSearch,
  Crosshair,
  GitFork,
  ShieldAlert,
  ClipboardCheck,
  ChevronRight,
  Check,
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

export const WorkflowStepper = () => {
  const dispatch = useDispatch();
  const activeStage = useSelector((state) => state.investigation.activeStage);
  const currentInvestigation = useSelector((state) => state.investigation.currentInvestigation);

  const activeIndex = STAGES.findIndex((s) => s.id === activeStage);

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
      aria-label="Investigation Stages Progress"
      className="sticky top-16 z-20 skeuo-stepper backdrop-blur-md px-3 sm:px-6 lg:px-8 xl:px-10 py-2.5 shadow-sm"
    >
      <div className="max-w-[1720px] mx-auto">
        <div className="grid grid-cols-5 gap-2 sm:gap-3 w-full items-center">
          {STAGES.map((stage, idx) => {
            const Icon = stage.icon;
            const isActive = activeStage === stage.id;
            const isCompleted = activeIndex > idx || (idx === 4 && currentInvestigation?.is_approved);

            return (
              <div key={stage.id} className="relative flex items-center">
                <button
                  onClick={() => handleStageClick(stage)}
                  aria-current={isActive ? 'step' : undefined}
                  aria-label={`Stage ${stage.stepNumber}: ${stage.label}`}
                  className={`w-full text-left py-2 px-2.5 sm:px-3 rounded-2xl transition-all border select-none cursor-pointer active:translate-y-0.5 flex items-center gap-2.5 ${
                    isActive
                      ? 'skeuo-step-btn-active shadow-md scale-[1.01] ring-1 ring-cyan-500/50'
                      : isCompleted
                      ? 'bg-slate-50 dark:bg-zinc-950/70 border-emerald-300 dark:border-emerald-800/60 text-slate-800 dark:text-zinc-200 hover:border-emerald-400'
                      : 'bg-slate-50 dark:bg-zinc-950/60 border-slate-300 dark:border-zinc-800 text-slate-600 dark:text-zinc-400 hover:border-slate-400 dark:hover:border-zinc-700 hover:text-slate-900 dark:hover:text-zinc-100'
                  }`}
                >
                  {/* Tactical Badge & Icon */}
                  <div
                    className={`w-7 h-7 sm:w-8 sm:h-8 rounded-xl flex items-center justify-center shrink-0 transition-all font-mono font-bold text-xs ${
                      isActive
                        ? 'bg-cyan-600 dark:bg-cyan-500 text-white shadow-md shadow-cyan-500/30 ring-2 ring-cyan-300 dark:ring-cyan-400/40'
                        : isCompleted
                        ? 'bg-emerald-100 dark:bg-emerald-950/90 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800'
                        : 'bg-slate-200 dark:bg-zinc-900 text-slate-500 dark:text-zinc-400 border border-slate-300 dark:border-zinc-800'
                    }`}
                  >
                    {isCompleted && !isActive ? (
                      <Check className="w-4 h-4 stroke-[3]" />
                    ) : (
                      <Icon className="w-4 h-4" />
                    )}
                  </div>

                  {/* Multi-tier Professional Text */}
                  <div className="min-w-0 flex-1 hidden md:block">
                    <p
                      className={`text-xs font-bold truncate leading-tight tracking-tight ${
                        isActive
                          ? 'text-blue-900 dark:text-white'
                          : 'text-slate-800 dark:text-zinc-200'
                      }`}
                    >
                      {stage.label}
                    </p>
                    <p className="text-[10px] text-slate-500 dark:text-zinc-400 truncate leading-none mt-0.5 font-medium">
                      {stage.subtitle}
                    </p>
                  </div>

                  {/* Mobile Fallback Display */}
                  <div className="md:hidden flex flex-col items-start leading-none min-w-0">
                    <span className="font-mono text-[9px] font-bold text-cyan-600 dark:text-cyan-400">
                      {stage.stepNumber}
                    </span>
                    <span className="text-[10px] font-bold truncate max-w-[45px] text-slate-700 dark:text-zinc-300">
                      {stage.label}
                    </span>
                  </div>
                </button>

                {/* Subtle connecting arrow for stages (hidden on last item) */}
                {idx < STAGES.length - 1 && (
                  <div className="hidden xl:flex absolute -right-2 z-10 text-slate-300 dark:text-zinc-700 pointer-events-none">
                    <ChevronRight className="w-3.5 h-3.5" />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </nav>
  );
};

export default WorkflowStepper;
