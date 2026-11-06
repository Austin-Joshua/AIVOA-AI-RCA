import React, { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  AlertCircle,
  Check,
  Edit2,
  ShieldCheck,
  ShieldAlert,
  Building2,
  Cpu,
  Layers,
  Scale,
  Save,
} from 'lucide-react';
import { saveInvestigationDeviation, verifyDeviation } from '../../store/investigationSlice';
import { setDraftPatch } from '../../store/copilotSlice';
import { setNotification } from '../../store/uiSlice';
import { AiBadge } from '../common/AiBadge';
import { SeverityBadge } from '../common/StatusBadge';

export const DeviationSection = () => {
  const dispatch = useDispatch();
  const currentInvestigation = useSelector((state) => state.investigation.currentInvestigation);
  const { draftPatches, riskAssessment, highlightedFieldKey } = useSelector((state) => state.copilot);
  const currentUser = useSelector((state) => state.auth.user);
  const deviation = currentInvestigation?.deviation;

  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({
    deviation_number: '',
    deviation_type: 'MAJOR',
    severity: 'Major',
    batch_number: '',
    product_name: '',
    unit_operation: '',
    equipment_id: '',
    bpr_number: '',
    target_yield_kg: '',
    actual_yield_kg: '',
    description: '',
    immediate_containment: '',
  });

  const getFieldValue = (key) => {
    if (isEditing) return formData[key] ?? '';
    return deviation?.[key] || draftPatches?.[key]?.value || '';
  };

  const handleStartEditing = () => {
    setFormData({
      deviation_number: deviation?.deviation_number || draftPatches.deviation_number?.value || '',
      deviation_type: deviation?.deviation_type || 'MAJOR',
      severity: deviation?.severity || riskAssessment?.suggested_severity || 'Major',
      batch_number: deviation?.batch_number || draftPatches.batch_number?.value || '',
      product_name: deviation?.product_name || draftPatches.product_name?.value || '',
      unit_operation: deviation?.unit_operation || draftPatches.unit_operation?.value || '',
      equipment_id: deviation?.equipment_id || draftPatches.equipment_id?.value || '',
      bpr_number: deviation?.bpr_number || draftPatches.bpr_number?.value || '',
      target_yield_kg: deviation?.target_yield_kg || draftPatches.target_yield_kg?.value || '',
      actual_yield_kg: deviation?.actual_yield_kg || draftPatches.actual_yield_kg?.value || '',
      description: deviation?.description || draftPatches.description?.value || '',
      immediate_containment:
        deviation?.immediate_containment ||
        draftPatches.immediate_containment?.value ||
        riskAssessment?.suggested_next_action ||
        '',
    });
    setIsEditing(true);
  };

  if (!currentInvestigation) {
    return (
      <div className="bg-white rounded-xl border border-dashed border-slate-300 p-8 text-center">
        <AlertCircle className="w-10 h-10 text-slate-400 mx-auto mb-3" />
        <h3 className="text-base font-semibold text-slate-800">No Active Investigation Selected</h3>
        <p className="text-sm text-slate-500 mt-1 max-w-md mx-auto">
          Create a new investigation dossier or load a demo scenario to begin.
        </p>
      </div>
    );
  }

  const handleFieldChange = (field_key, value) => {
    setFormData((prev) => ({ ...prev, [field_key]: value }));
    dispatch(
      setDraftPatch({
        field_key,
        value,
        status: 'USER_CORRECTION',
        reason: 'Investigator edited form field directly',
        user_attributed: currentUser?.full_name || 'Investigator',
      })
    );
  };

  const handleSave = async () => {
    if (!currentInvestigation) return;
    const currentData = isEditing
      ? formData
      : {
          deviation_number:
            deviation?.deviation_number ||
            draftPatches.deviation_number?.value ||
            '',
          deviation_type: deviation?.deviation_type || 'MAJOR',
          severity: deviation?.severity || riskAssessment?.suggested_severity || 'Major',
          batch_number: deviation?.batch_number || draftPatches.batch_number?.value || '',
          product_name: deviation?.product_name || draftPatches.product_name?.value || '',
          unit_operation: deviation?.unit_operation || draftPatches.unit_operation?.value || '',
          equipment_id: deviation?.equipment_id || draftPatches.equipment_id?.value || '',
          bpr_number: deviation?.bpr_number || draftPatches.bpr_number?.value || '',
          target_yield_kg: deviation?.target_yield_kg || draftPatches.target_yield_kg?.value || null,
          actual_yield_kg: deviation?.actual_yield_kg || draftPatches.actual_yield_kg?.value || null,
          description: deviation?.description || draftPatches.description?.value || '',
          immediate_containment:
            deviation?.immediate_containment ||
            draftPatches.immediate_containment?.value ||
            riskAssessment?.suggested_next_action ||
            '',
        };
    const payload = {
      ...currentData,
      target_yield_kg: currentData.target_yield_kg ? Number(currentData.target_yield_kg) : null,
      actual_yield_kg: currentData.actual_yield_kg ? Number(currentData.actual_yield_kg) : null,
      is_ai_populated: true,
      is_verified: false,
    };
    await dispatch(
      saveInvestigationDeviation({
        investigationId: currentInvestigation.id,
        deviationData: payload,
      })
    );
    dispatch(
      setNotification({
        type: 'success',
        message: 'Deviation details committed to investigation dossier.',
      })
    );
    setIsEditing(false);
  };

  const handleVerify = () => {
    if (deviation?.id) {
      dispatch(verifyDeviation(deviation.id));
    }
  };

  const getFieldStatus = (key) => {
    if (draftPatches[key]) {
      return draftPatches[key].status;
    }
    const val = getFieldValue(key);
    if (!val || val === 'UNRECORDED') return 'MISSING';
    if (deviation?.is_ai_populated) return 'SOURCE_FACT';
    return null;
  };

  const renderBadge = (key) => {
    const status = getFieldStatus(key);
    if (!status) return null;

    if (status === 'USER_CORRECTION') {
      return (
        <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-blue-100 dark:bg-blue-950/80 text-blue-800 dark:text-blue-300 border border-blue-200 dark:border-blue-800">
          Edited by you
        </span>
      );
    }
    if (status === 'SOURCE_FACT') {
      return (
        <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-emerald-100 dark:bg-emerald-950/80 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
          AI - Source Fact
        </span>
      );
    }
    if (status === 'AI_INFERENCE') {
      return (
        <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-amber-100 dark:bg-amber-950/80 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
          AI - Inference
        </span>
      );
    }
    if (status === 'MISSING') {
      return (
        <span className="text-[10px] font-bold px-1.5 py-0.2 rounded bg-rose-100 dark:bg-rose-950/80 text-rose-800 dark:text-rose-300 border border-rose-200 dark:border-rose-800">
          Missing
        </span>
      );
    }
    return null;
  };

  const isHighlighted = (key) => highlightedFieldKey === key;

  return (
    <div id="section-deviation" className="skeuo-card rounded-2xl overflow-hidden mb-6 font-sans">
      {/* AI Risk Assessment Card (Prominently displayed when assessed) */}
      {riskAssessment && (
        <div className="bg-gradient-to-r from-amber-500/15 via-amber-50/80 to-blue-50/50 dark:from-amber-950/40 dark:via-[#0c0e1a] dark:to-[#080a14] border-b border-amber-300 dark:border-amber-900/60 p-4">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs font-black text-amber-900 dark:text-amber-300 uppercase tracking-wider flex items-center gap-1.5 font-mono">
              <ShieldAlert className="w-4 h-4 text-amber-600 dark:text-amber-400" />
              AI Risk Assessment & Immediate Triage
            </span>
            <span className="text-xs font-black uppercase px-2.5 py-0.5 rounded-full bg-amber-200 dark:bg-amber-900/80 text-amber-950 dark:text-amber-200 border border-amber-300 dark:border-amber-700 font-mono">
              {riskAssessment.suggested_severity} Severity
            </span>
          </div>
          <p className="text-xs text-amber-950 dark:text-amber-200 leading-relaxed font-semibold">
            {riskAssessment.initial_risk_text}
          </p>
          <div className="mt-2 text-xs text-amber-900 dark:text-amber-300 bg-white/80 dark:bg-[#060814]/90 p-2.5 rounded-xl border border-amber-200 dark:border-amber-900/50 flex items-center gap-2">
            <strong className="shrink-0 text-amber-950 dark:text-amber-200 font-black">Immediate Containment:</strong>
            <span className="truncate font-medium">{riskAssessment.suggested_next_action}</span>
          </div>
        </div>
      )}

      {/* Header Bar */}
      <div className="bg-gradient-to-b from-blue-50/80 to-slate-100/60 dark:from-[#0c0e1a] dark:to-[#080a14] px-5 py-4 border-b border-slate-200/90 dark:border-[#1e2236] flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <span className="font-mono text-sm font-extrabold text-blue-900 dark:text-blue-300 skeuo-well px-3 py-1 rounded-xl">
            {getFieldValue('deviation_number') || 'DEV-2026-DRAFT'}
          </span>
          <SeverityBadge severity={getFieldValue('severity') || 'Major'} />
          {deviation && (
            <AiBadge
              isAiSuggested={deviation.is_ai_populated}
              isVerified={deviation.is_verified}
              onVerify={handleVerify}
              label={deviation.is_ai_populated ? 'AI Populated' : 'Manual Entry'}
            />
          )}
        </div>
        <div className="flex items-center gap-2.5">
          {isEditing ? (
            <button
              onClick={handleSave}
              className="skeuo-btn-primary flex items-center gap-1.5 text-xs font-bold px-3.5 py-1.5 rounded-xl transition cursor-pointer"
            >
              <Check className="w-3.5 h-3.5" /> Save Changes
            </button>
          ) : (
            <>
              <button
                onClick={handleStartEditing}
                className="skeuo-btn-secondary flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-xl transition cursor-pointer"
              >
                <Edit2 className="w-3.5 h-3.5" /> Edit Form
              </button>
              <button
                onClick={handleSave}
                className="skeuo-btn-primary flex items-center gap-1.5 text-xs font-bold px-3.5 py-1.5 rounded-xl transition cursor-pointer"
                title="Commit draft form to investigation dossier"
              >
                <Save className="w-3.5 h-3.5" /> Commit Form
              </button>
            </>
          )}
        </div>
      </div>

      {/* Main Content Fields — Bento Grid Architecture */}
      <div className="p-5 space-y-4">
        {/* Bento Module 1: 4 Core Manufacturing Parameters */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
          {/* Batch Number */}
          <div
            className={`p-3.5 rounded-2xl border transition skeuo-card bg-white dark:bg-zinc-950/90 ${
              isHighlighted('batch_number')
                ? 'ring-2 ring-cyan-500 bg-cyan-50/50 dark:bg-cyan-950/30 border-cyan-400 dark:border-cyan-700'
                : 'border-slate-200 dark:border-zinc-800/80 shadow-2xs'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-bold text-slate-500 dark:text-zinc-400 uppercase tracking-wider flex items-center gap-1.5 font-mono">
                <Layers className="w-3.5 h-3.5 text-blue-500 dark:text-blue-400" /> Batch Number
              </span>
              {renderBadge('batch_number')}
            </div>
            {isEditing ? (
              <input
                type="text"
                value={formData.batch_number}
                onChange={(e) => handleFieldChange('batch_number', e.target.value)}
                className="w-full px-2.5 py-1.5 text-xs border rounded-xl bg-white dark:bg-black border-slate-300 dark:border-zinc-700 text-slate-900 dark:text-zinc-100 font-mono focus:ring-2 focus:ring-cyan-500"
              />
            ) : (
              <div className="skeuo-well p-2 rounded-xl">
                <p className="font-bold text-xs text-slate-900 dark:text-zinc-100 font-mono truncate">
                  {getFieldValue('batch_number') || '--'}
                </p>
              </div>
            )}
          </div>

          {/* Product Name */}
          <div
            className={`p-3.5 rounded-2xl border transition skeuo-card bg-white dark:bg-zinc-950/90 ${
              isHighlighted('product_name')
                ? 'ring-2 ring-cyan-500 bg-cyan-50/50 dark:bg-cyan-950/30 border-cyan-400 dark:border-cyan-700'
                : 'border-slate-200 dark:border-zinc-800/80 shadow-2xs'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-bold text-slate-500 dark:text-zinc-400 uppercase tracking-wider flex items-center gap-1.5 font-mono">
                <Building2 className="w-3.5 h-3.5 text-indigo-500 dark:text-indigo-400" /> Product Name
              </span>
              {renderBadge('product_name')}
            </div>
            {isEditing ? (
              <input
                type="text"
                value={formData.product_name}
                onChange={(e) => handleFieldChange('product_name', e.target.value)}
                className="w-full px-2.5 py-1.5 text-xs border rounded-xl bg-white dark:bg-black border-slate-300 dark:border-zinc-700 text-slate-900 dark:text-zinc-100 focus:ring-2 focus:ring-cyan-500"
              />
            ) : (
              <div className="skeuo-well p-2 rounded-xl">
                <p className="font-bold text-xs text-slate-900 dark:text-zinc-100 truncate">
                  {getFieldValue('product_name') || '--'}
                </p>
              </div>
            )}
          </div>

          {/* Unit Operation */}
          <div
            className={`p-3.5 rounded-2xl border transition skeuo-card bg-white dark:bg-zinc-950/90 ${
              isHighlighted('unit_operation')
                ? 'ring-2 ring-cyan-500 bg-cyan-50/50 dark:bg-cyan-950/30 border-cyan-400 dark:border-cyan-700'
                : 'border-slate-200 dark:border-zinc-800/80 shadow-2xs'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-bold text-slate-500 dark:text-zinc-400 uppercase tracking-wider flex items-center gap-1.5 font-mono">
                <Layers className="w-3.5 h-3.5 text-cyan-500 dark:text-cyan-400" /> Unit Operation
              </span>
              {renderBadge('unit_operation')}
            </div>
            {isEditing ? (
              <input
                type="text"
                value={formData.unit_operation}
                onChange={(e) => handleFieldChange('unit_operation', e.target.value)}
                className="w-full px-2.5 py-1.5 text-xs border rounded-xl bg-white dark:bg-black border-slate-300 dark:border-zinc-700 text-slate-900 dark:text-zinc-100 focus:ring-2 focus:ring-cyan-500"
              />
            ) : (
              <div className="skeuo-well p-2 rounded-xl">
                <p className="font-bold text-xs text-slate-900 dark:text-zinc-100 truncate">
                  {getFieldValue('unit_operation') || '--'}
                </p>
              </div>
            )}
          </div>

          {/* Equipment ID */}
          <div
            className={`p-3.5 rounded-2xl border transition skeuo-card bg-white dark:bg-zinc-950/90 ${
              isHighlighted('equipment_id')
                ? 'ring-2 ring-cyan-500 bg-cyan-50/50 dark:bg-cyan-950/30 border-cyan-400 dark:border-cyan-700'
                : 'border-slate-200 dark:border-zinc-800/80 shadow-2xs'
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-bold text-slate-500 dark:text-zinc-400 uppercase tracking-wider flex items-center gap-1.5 font-mono">
                <Cpu className="w-3.5 h-3.5 text-purple-500 dark:text-purple-400" /> Equipment ID
              </span>
              {renderBadge('equipment_id')}
            </div>
            {isEditing ? (
              <input
                type="text"
                value={formData.equipment_id}
                onChange={(e) => handleFieldChange('equipment_id', e.target.value)}
                className="w-full px-2.5 py-1.5 text-xs border rounded-xl bg-white dark:bg-black border-slate-300 dark:border-zinc-700 text-slate-900 dark:text-zinc-100 font-mono focus:ring-2 focus:ring-cyan-500"
              />
            ) : (
              <div className="skeuo-well p-2 rounded-xl">
                <p className="font-bold text-xs text-slate-900 dark:text-zinc-100 font-mono truncate">
                  {getFieldValue('equipment_id') || '--'}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Bento Module 2: Yield & BPR Tracking (2-Column Bento) */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
          <div className="p-3.5 rounded-2xl border skeuo-card bg-white dark:bg-zinc-950/90 border-slate-200 dark:border-zinc-800/80 flex items-center justify-between">
            <div className="flex-1 pr-3">
              <span className="text-[11px] font-bold text-slate-500 dark:text-zinc-400 uppercase tracking-wider flex items-center gap-1.5 font-mono">
                <Scale className="w-3.5 h-3.5 text-teal-500 dark:text-teal-400" /> Target vs Actual Yield (kg)
              </span>
              {getFieldValue('target_yield_kg') || getFieldValue('actual_yield_kg') ? (
                <div className="skeuo-well p-2 rounded-xl mt-2">
                  <p className="text-xs font-semibold text-slate-800 dark:text-zinc-200 font-mono">
                    Target: {getFieldValue('target_yield_kg') || '--'} kg | Actual:{' '}
                    {getFieldValue('actual_yield_kg') || '--'} kg
                  </p>
                </div>
              ) : (
                <div className="flex items-center gap-2 mt-2 skeuo-well p-2 rounded-xl">
                  <span className="text-xs italic text-slate-400 dark:text-zinc-500">Not provided</span>
                  <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-50 dark:bg-amber-950/80 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800">Missing</span>
                </div>
              )}
            </div>
            {getFieldValue('target_yield_kg') && getFieldValue('actual_yield_kg') && (
              <span
                className={`text-xs font-bold px-2.5 py-1 rounded-xl shrink-0 font-mono border ${
                  Number(getFieldValue('actual_yield_kg')) < Number(getFieldValue('target_yield_kg')) * 0.95
                    ? 'bg-rose-100 dark:bg-rose-950 text-rose-800 dark:text-rose-300 border-rose-300 dark:border-rose-800'
                    : 'bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 border-emerald-300 dark:border-emerald-800'
                }`}
              >
                {(
                  (Number(getFieldValue('actual_yield_kg')) / Number(getFieldValue('target_yield_kg'))) *
                  100
                ).toFixed(1)}
                % Yield
              </span>
            )}
          </div>

          <div className="p-3.5 rounded-2xl border skeuo-card bg-white dark:bg-zinc-950/90 border-slate-200 dark:border-zinc-800/80">
            <span className="text-[11px] font-bold text-slate-500 dark:text-zinc-400 uppercase tracking-wider block font-mono">
              Batch Production Record (BPR)
            </span>
            {getFieldValue('bpr_number') ? (
              <div className="skeuo-well p-2 rounded-xl mt-2">
                <p className="text-xs font-mono font-bold text-slate-800 dark:text-zinc-100 truncate">
                  {getFieldValue('bpr_number')}
                </p>
              </div>
            ) : (
              <div className="flex items-center gap-2 mt-2 skeuo-well p-2 rounded-xl">
                <span className="text-xs italic text-slate-400 dark:text-zinc-500">Not provided</span>
                <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-50 dark:bg-amber-950/80 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800">Missing</span>
              </div>
            )}
          </div>
        </div>

        {/* Bento Module 3: Technical Deviation Narrative */}
        <div
          className={`p-4 rounded-2xl border transition skeuo-card bg-white dark:bg-zinc-950/90 ${
            isHighlighted('description')
              ? 'ring-2 ring-cyan-500 bg-cyan-50/50 dark:bg-cyan-950/30 border-cyan-400 dark:border-cyan-700'
              : 'border-slate-200 dark:border-zinc-800/80 shadow-2xs'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs font-bold text-slate-700 dark:text-zinc-200 uppercase tracking-wider font-mono">
              Technical Deviation Narrative
            </label>
            {renderBadge('description')}
          </div>
          {isEditing ? (
            <textarea
              rows={3}
              value={formData.description}
              onChange={(e) => handleFieldChange('description', e.target.value)}
              className="w-full text-xs border rounded-xl p-3 bg-white dark:bg-black border-slate-300 dark:border-zinc-700 text-slate-900 dark:text-zinc-100 focus:ring-2 focus:ring-cyan-500 font-sans leading-relaxed"
            />
          ) : (
            <div className="p-3.5 rounded-xl skeuo-well dark:bg-black text-xs text-slate-800 dark:text-zinc-200 leading-relaxed font-sans">
              {getFieldValue('description') || 'Awaiting incident report from Copilot...'}
            </div>
          )}
        </div>

        {/* Bento Module 4: Immediate Containment Actions */}
        <div
          className={`p-4 rounded-2xl border transition skeuo-card bg-white dark:bg-zinc-950/90 ${
            isHighlighted('immediate_containment')
              ? 'ring-2 ring-cyan-500 bg-cyan-50/50 dark:bg-cyan-950/30 border-cyan-400 dark:border-cyan-700'
              : 'border-emerald-200/80 dark:border-emerald-900/40 bg-emerald-50/30 dark:bg-emerald-950/10'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs font-bold text-slate-700 dark:text-zinc-200 uppercase tracking-wider flex items-center gap-1.5 font-mono">
              <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" /> Immediate Quarantine & Containment
            </label>
            {renderBadge('immediate_containment')}
          </div>
          {isEditing ? (
            <textarea
              rows={2}
              value={formData.immediate_containment}
              onChange={(e) => handleFieldChange('immediate_containment', e.target.value)}
              className="w-full text-xs border rounded-xl p-3 bg-white dark:bg-black border-slate-300 dark:border-zinc-700 text-slate-900 dark:text-zinc-100 focus:ring-2 focus:ring-emerald-500 font-sans"
            />
          ) : (
            <div className="p-3.5 rounded-xl bg-emerald-50/60 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-900/50 text-xs text-emerald-950 dark:text-emerald-300 font-medium leading-relaxed">
              {getFieldValue('immediate_containment') || 'No immediate containment documented.'}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DeviationSection;
