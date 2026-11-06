import React, { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { X, FlaskConical, Plus } from 'lucide-react';
import { setShowNewModal, setNotification } from '../../store/uiSlice';
import { createInvestigation, fetchInvestigationById } from '../../store/investigationSlice';
import { Button, Input } from '../ui';

export const NewInvestigationModal = () => {
  const dispatch = useDispatch();
  const show = useSelector((state) => state.ui.showNewModal);
  const currentUser = useSelector((state) => state.auth.user);

  const [title, setTitle] = useState('');
  const [investigator, setInvestigator] = useState(() => currentUser?.full_name || 'Lead Investigator');

  if (!show) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title.trim()) return;

    const res = await dispatch(
      createInvestigation({
        title: title.trim(),
        lead_investigator: investigator.trim() || currentUser?.full_name || 'Lead Investigator',
        stage: 'INTAKE',
        status: 'IN_INVESTIGATION',
      })
    );

    if (res.payload?.id) {
      dispatch(fetchInvestigationById(res.payload.id));
    }

    dispatch(
      setNotification({
        type: 'success',
        message: 'New RCA Investigation opened! Please upload or paste incident documentation.',
      })
    );

    setTitle('');
    dispatch(setShowNewModal(false));
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-4 animate-fade-in font-sans"
      role="dialog"
      aria-modal="true"
    >
      <div className="skeuo-surface-raised rounded-3xl max-w-md w-full shadow-2xl border border-slate-300 dark:border-[#1e2236] overflow-hidden bg-white dark:bg-[#080a14] text-slate-900 dark:text-slate-100">
        <div className="px-5 py-4 bg-gradient-to-b from-blue-50/80 to-white dark:from-[#0c0e1a] dark:to-[#080a14] text-slate-900 dark:text-white flex items-center justify-between border-b border-slate-200 dark:border-[#1e2236]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-blue-100 dark:bg-blue-950/60 border border-blue-300 dark:border-blue-700/50 flex items-center justify-center text-blue-800 dark:text-blue-300 shadow-xs">
              <FlaskConical className="w-5 h-5 text-amber-500" />
            </div>
            <div>
              <h3 className="font-extrabold text-sm tracking-tight text-slate-900 dark:text-white">
                Initiate Root Cause Investigation
              </h3>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">Open a new cGMP deviation dossier</p>
            </div>
          </div>
          <button
            onClick={() => dispatch(setShowNewModal(false))}
            className="text-slate-400 hover:text-slate-700 dark:hover:text-white p-1.5 rounded-xl hover:bg-slate-100 dark:hover:bg-zinc-800 transition cursor-pointer"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <Input
            label="Investigation Scope & Title"
            required
            autoFocus
            placeholder="e.g. Temperature Excursion in Paracetamol API Crystallization"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            helperText="Include unit operation, batch number, or deviation brief"
          />

          <Input
            label="Lead Investigator"
            required
            value={investigator}
            onChange={(e) => setInvestigator(e.target.value)}
            helperText="Responsible person conducting root cause analysis"
          />

          <div className="pt-3 flex items-center justify-end gap-3 border-t border-slate-200 dark:border-zinc-800">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => dispatch(setShowNewModal(false))}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              icon={<Plus className="w-4 h-4" />}
            >
              Open Investigation
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default NewInvestigationModal;
