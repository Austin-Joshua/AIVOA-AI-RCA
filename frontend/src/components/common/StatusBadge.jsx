import React from 'react';

export const SeverityBadge = ({ severity }) => {
  const sev = (severity || 'MAJOR').toUpperCase();
  const styles = {
    CRITICAL: 'bg-rose-100 text-rose-800 border-rose-300',
    MAJOR: 'bg-amber-100 text-amber-800 border-amber-300',
    MINOR: 'bg-blue-100 text-blue-800 border-blue-300',
  };

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold border ${styles[sev] || styles.MAJOR}`}>
      {sev}
    </span>
  );
};

export const CauseStatusBadge = ({ status }) => {
  const st = (status || 'HYPOTHESIS').toUpperCase();
  const styles = {
    CONFIRMED: 'bg-emerald-100 text-emerald-800 border-emerald-300 font-bold',
    RULED_OUT: 'bg-slate-100 text-slate-500 border-slate-300 line-through',
    HYPOTHESIS: 'bg-amber-100 text-amber-800 border-amber-300',
  };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs border ${styles[st] || styles.HYPOTHESIS}`}>
      {st.replace('_', ' ')}
    </span>
  );
};

export const CapaTypeBadge = ({ type }) => {
  const t = (type || 'CORRECTIVE_ACTION').toUpperCase();
  const styles = {
    CORRECTION: 'bg-purple-100 text-purple-800 border-purple-200',
    CORRECTIVE_ACTION: 'bg-blue-100 text-blue-800 border-blue-200',
    PREVENTIVE_ACTION: 'bg-teal-100 text-teal-800 border-teal-200',
  };

  const labels = {
    CORRECTION: 'Correction (Immediate)',
    CORRECTIVE_ACTION: 'Corrective Action',
    PREVENTIVE_ACTION: 'Preventive Action',
  };

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-semibold border ${styles[t] || styles.CORRECTIVE_ACTION}`}>
      {labels[t] || t}
    </span>
  );
};

export const CapaStatusBadge = ({ status }) => {
  const st = (status || 'PROPOSED').toUpperCase();
  const styles = {
    PROPOSED: 'bg-amber-50 text-amber-800 border-amber-300 font-medium',
    APPROVED: 'bg-blue-50 text-blue-800 border-blue-300 font-semibold',
    IN_PROGRESS: 'bg-indigo-50 text-indigo-800 border-indigo-300 font-semibold',
    COMPLETED: 'bg-emerald-50 text-emerald-800 border-emerald-300 font-semibold',
    EFFECTIVENESS_VERIFIED: 'bg-teal-100 text-teal-900 border-teal-400 font-bold',
    OPEN: 'bg-amber-50 text-amber-800 border-amber-300 font-medium',
    CLOSED: 'bg-emerald-50 text-emerald-800 border-emerald-300 font-semibold',
  };

  const labels = {
    PROPOSED: 'Proposed',
    APPROVED: 'QA Approved',
    IN_PROGRESS: 'In Progress',
    COMPLETED: 'Completed',
    EFFECTIVENESS_VERIFIED: 'Effectiveness Verified',
    OPEN: 'Proposed',
    CLOSED: 'Completed',
  };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs border ${styles[st] || styles.PROPOSED}`}>
      {labels[st] || st.replace('_', ' ')}
    </span>
  );
};
