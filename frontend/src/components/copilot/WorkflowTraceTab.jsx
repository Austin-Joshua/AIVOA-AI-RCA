import React from 'react';
import {
  CheckCircle2,
  Workflow,
  Cpu,
} from 'lucide-react';

export const WorkflowTraceTab = ({ aiConfig }) => {
  const activeModel = aiConfig?.model || 'llama-3.3-70b-versatile';
  const nodes = [
    { name: '1. Document Parsing Node', desc: 'PyPDF extraction, header splitting, text cleaning', status: 'ACTIVE' },
    { name: '2. Structured Extraction Node', desc: `Groq ${activeModel} JSON extraction of deviation fields`, status: 'ACTIVE' },
    { name: '3. Field Validation Node', desc: 'Pydantic cGMP batch context and yield verification', status: 'ACTIVE' },
    { name: '4. Missing Info Detection Node', desc: 'Detects logbook, calibration, and raw material gaps', status: 'ACTIVE' },
    { name: '5. Evidence Analysis Node', desc: 'Correlates SCADA telemetry with physical symptoms', status: 'ACTIVE' },
    { name: '6. Investigation Planning Node', desc: 'Dynamically selects 5-Whys and Fishbone 6Ms paths', status: 'ACTIVE' },
    { name: '7. 5-Whys Analysis Node', desc: 'Constructs progressive 5-tier causality chain', status: 'ACTIVE' },
    { name: '8. Fishbone Analysis Node', desc: 'Evaluates Man, Machine, Material, Method, Measurement, Milieu', status: 'ACTIVE' },
    { name: '9. Root Cause Evaluation Node', desc: 'Designates Primary Cause vs Contributing Factors', status: 'ACTIVE' },
    { name: '10. CAPA Generation Node', desc: 'Drafts Correction, Corrective, and Preventive Actions', status: 'ACTIVE' },
    { name: '11. Output Validation Node', desc: 'Enforces unverified AI tags and evidence traceability', status: 'ACTIVE' },
    { name: '12. Human Review Node', desc: 'Packages dossier for investigator sign-off and QA lock', status: 'ACTIVE' },
  ];

  return (
    <div className="space-y-4 font-sans">
      <div className="p-3.5 rounded-2xl bg-gradient-to-b from-zinc-900 to-black dark:from-zinc-950 dark:to-black text-white flex items-center justify-between border border-zinc-800 shadow-md">
        <div className="flex items-center gap-2.5">
          <Workflow className="w-4 h-4 text-cyan-400" />
          <span className="text-xs font-bold font-mono tracking-tight">LangGraph StateGraph Execution</span>
        </div>
        <span className="text-[10px] font-mono px-2.5 py-0.5 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-800 font-bold flex items-center gap-1">
          <Cpu className="w-3 h-3 text-cyan-400" /> {activeModel}
        </span>
      </div>

      <div className="space-y-2">
        {nodes.map((node, idx) => (
          <div
            key={idx}
            className="skeuo-card p-3 rounded-xl border border-slate-200 dark:border-zinc-800 flex items-center justify-between shadow-2xs hover:border-cyan-500/40 transition"
          >
            <div>
              <span className="text-xs font-bold text-slate-800 dark:text-zinc-100 block">{node.name}</span>
              <span className="text-[11px] text-slate-500 dark:text-zinc-400 block mt-0.5">{node.desc}</span>
            </div>
            <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 shrink-0">
              <CheckCircle2 className="w-3 h-3 text-emerald-500" />
              Verified
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default WorkflowTraceTab;
