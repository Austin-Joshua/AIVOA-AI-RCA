import React, { useState, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  FileSearch,
  HelpCircle,
  GitBranch,
  MessageSquare,
  Workflow,
  Sparkles,
  Cpu,
} from 'lucide-react';
import { setActiveTab } from '../../store/copilotSlice';
import api from '../../services/api';
import DocumentIntakeTab from './DocumentIntakeTab';
import EvidenceGapsTab from './EvidenceGapsTab';
import RcaEngineTab from './RcaEngineTab';
import CopilotChatTab from './CopilotChatTab';
import WorkflowTraceTab from './WorkflowTraceTab';

export const CopilotPanel = () => {
  const dispatch = useDispatch();
  const { activeTab, intakeExtraction, rcaProposal } = useSelector((state) => state.copilot);
  const currentInvestigation = useSelector((state) => state.investigation.currentInvestigation);
  const [aiConfig, setAiConfig] = useState(null);

  useEffect(() => {
    api.get('/config/ai')
      .then((res) => setAiConfig(res.data))
      .catch(() => {});
  }, []);

  const openGapsCount = currentInvestigation?.evidence_gaps
    ? currentInvestigation.evidence_gaps.filter((g) => g.status === 'OPEN').length
    : intakeExtraction?.missing_information?.length || null;

  const tabs = [
    { id: 'chat', label: 'Chat', icon: MessageSquare },
    { id: 'intake', label: 'Intake', icon: FileSearch, badge: intakeExtraction ? 'Ready' : null },
    { id: 'gaps', label: 'Gaps', icon: HelpCircle, badge: openGapsCount || null },
    { id: 'engine', label: 'RCA', icon: GitBranch, badge: rcaProposal ? 'Ready' : null },
    { id: 'workflow', label: 'Trace', icon: Workflow },
  ];

  return (
    <div className="skeuo-surface-raised rounded-2xl overflow-hidden flex flex-col h-full max-h-full border border-slate-300 dark:border-[#1e2236] shadow-xl font-sans">
      {/* ── Copilot Header — Royal Blue with Gold Accent ────────────────── */}
      <div className="shrink-0 bg-gradient-to-b from-blue-50 to-white dark:from-[#0c0e1a] dark:to-[#060814] p-4 text-slate-900 dark:text-white flex items-center justify-between border-b border-blue-200 dark:border-[#1e2236] shadow-xs dark:shadow-inner">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-blue-100 dark:bg-blue-950/50 border border-blue-300 dark:border-blue-600/40 flex items-center justify-center text-amber-600 dark:text-amber-400 shadow-xs dark:shadow-md">
            <Sparkles className="w-4 h-4 animate-ambient-glow" />
          </div>
          <div>
            <h3 className="font-extrabold text-sm tracking-tight text-slate-900 dark:text-white flex items-center gap-1.5">
              AI Investigation Copilot
            </h3>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 font-mono flex items-center gap-1.5 mt-0.5">
              <Cpu className="w-3 h-3 text-blue-700 dark:text-blue-400" />
              LangGraph &amp; Groq ({aiConfig?.model || 'llama-3.3-70b-versatile'})
            </p>
          </div>
        </div>
      </div>

      {/* ── Physical Skeuomorphic Tab Strip ───────────────────────────── */}
      <div className="shrink-0 flex border-b border-slate-200 dark:border-[#1e2236] bg-slate-50/90 dark:bg-[#060814] px-2 pt-2 gap-1.5 overflow-x-auto scrollbar-none shadow-xs">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => dispatch(setActiveTab(tab.id))}
              className={`flex items-center gap-1.5 py-2 px-3 text-xs font-bold rounded-t-xl transition-all border-t border-x -mb-px shrink-0 select-none cursor-pointer ${
                isActive
                  ? 'bg-white dark:bg-[#0c0e1a] text-blue-700 dark:text-blue-400 border-slate-200 dark:border-[#1e2236] border-b-transparent dark:border-b-transparent shadow-sm'
                  : 'bg-transparent text-slate-500 dark:text-slate-400 border-transparent hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200/50 dark:hover:bg-[#12152a]/60'
              }`}
            >
              <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-blue-700 dark:text-blue-400' : 'text-slate-400 dark:text-slate-500'}`} />
              <span>{tab.label}</span>
              {tab.badge && (
                <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-amber-100 dark:bg-amber-950/50 text-amber-800 dark:text-amber-300 font-bold border border-amber-300 dark:border-amber-700/60">
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* ── Tab Body ─────────────────────────────────────────────────── */}
      <div className="flex-1 min-h-0 overflow-y-auto p-4 bg-white dark:bg-[#060814]">
        {activeTab === 'intake' && <DocumentIntakeTab />}
        {activeTab === 'gaps' && <EvidenceGapsTab />}
        {activeTab === 'engine' && <RcaEngineTab />}
        {activeTab === 'chat' && <CopilotChatTab />}
        {activeTab === 'workflow' && <WorkflowTraceTab aiConfig={aiConfig} />}
      </div>
    </div>
  );
};

export default CopilotPanel;
