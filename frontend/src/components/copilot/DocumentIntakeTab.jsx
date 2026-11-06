import React, { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  Upload,
  FileText,
  Mail,
  CheckCircle2,
  Sparkles,
  ArrowRight,
  AlertTriangle,
  RotateCcw,
  Eye,
  EyeOff,
  Hash,
  ShieldCheck,
  AlertCircle,
  HelpCircle,
} from 'lucide-react';
import {
  parseIncidentFile,
  parseIncidentText,
  applyExtractionToForm,
  clearExtraction,
  updateExtractedField,
  toggleFieldAccepted,
  acceptAllFields,
  rejectAllFields,
  acceptAllSourceFacts,
} from '../../store/copilotSlice';
import { setNotification } from '../../store/uiSlice';

export const DocumentIntakeTab = () => {
  const dispatch = useDispatch();
  const { currentInvestigation } = useSelector((state) => state.investigation);
  const { intakeExtraction, isExtracting, extractionError } = useSelector((state) => state.copilot);

  const [inputMode, setInputMode] = useState('pdf'); // 'pdf', 'text', 'email'
  const [textContent, setTextContent] = useState('');
  const [showSourceViewer, setShowSourceViewer] = useState(false);
  const [statusFilter, setStatusFilter] = useState('ALL');

  const sampleParacetamolDemo = `PHARMACEUTICAL MANUFACTURING DEVIATION REPORT [FICTIONAL DEMONSTRATION DATA]
Plant: API Manufacturing Block 2
Incident Number: DEV-2026-104
Date of Occurrence: 05-Nov-2026 09:30 UTC
Product: Paracetamol API
Batch Number: API-2026-104
BPR Reference: BPR-PCM-104-REV1
Unit Operation: Crystallization (Reactor CR-104)
Equipment Tag: Crystallizer CR-104

DESCRIPTION OF DEVIATION:
During controlled crystallization of Paracetamol API batch API-2026-104 in reactor CR-104, a thermal excursion occurred.
Approved operating temperature range: 75.0°C to 80.0°C.
Illustrative observed temperature: 86.0°C (exceeding upper operating limit by 6.0°C).
Illustrative excursion duration: 18 minutes.
SCADA telemetry indicates primary cooling loop bypass solenoid SV-104 failed to de-energize upon high temperature interlock trigger.

EVIDENCE OBSERVATIONS & GAPS:
- Observed: Physical inspection of solenoid SV-104 revealed mechanical stem binding.
- Observed: In-process sample IP-104 showed agglomeration; mother liquor yield impact pending HPLC purity test.
- Missing Evidence: Cooling valve calibration record for CV-104 is missing.
- Missing Evidence: Operator shift handover logbook is not attached.

IMMEDIATE CONTAINMENT:
Batch API-2026-104 immediately placed under physical QA quarantine in mother liquor hold tank. Reactor CR-104 locked out pending mechanical inspection.`;

  // Sample quick templates for realistic testing
  const samplePdfDeviation = `PHARMACEUTICAL MANUFACTURING DEVIATION REPORT
Plant: API Manufacturing Block 4
Incident Number: DEV-2026-084
Date of Occurrence: 04-Nov-2026 14:15 UTC
Product: Atorvastatin Calcium Trihydrate API
Batch Number: B2026-API-044
BPR Reference: BPR-ATV-044-REV2
Unit Operation: Crystallization (Stage 4)
Equipment Tag: Reactor RX-301

DESCRIPTION OF DEVIATION:
During the controlled cooling crystallization cycle of batch B2026-API-044, reactor RX-301 experienced an uncommanded temperature overshoot. Process recipe required a cooling ramp from 50.0°C to 20.0°C at 0.5°C/min. At 14:15, the temperature abruptly rose to 38.4°C and remained out of specification (>24.0°C) for 42 minutes.
SCADA logs show cooling control valve CV-04 demand was 100%, but actual valve position feedback stayed at 12%. Mother liquor sample ML-044 showed altered crystal aspect ratio.

IMMEDIATE CONTAINMENT:
Batch B2026-API-044 was immediately placed under physical QA quarantine and flagged in SAP. Mother liquor hold tank isolated. Sampling scheduled for HPLC related substances test.`;

  const sampleEmail = `Subject: URGENT: Deviation Notification - Crystallization Excursion Batch B2026-API-044
From: production.lead@aivoa-pharma.com
Date: Wed, 04 Nov 2026 15:00:00 +0000
To: quality.investigations@aivoa-pharma.com

Team,
Please initiate an immediate RCA. During crystallization of Atorvastatin batch B2026-API-044 in RX-301, cooling water valve CV-04 jammed at 12% stroke. Temperature peaked at 38.4°C against a 22.0°C target limit.
Batch is currently quarantined in the mother liquor vessel. Maintenance reports potential actuator pneumatic leakage.`;

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      dispatch(parseIncidentFile({ file, investigationId: currentInvestigation?.id }));
    }
  };

  const handleTextSubmit = () => {
    if (!textContent.trim()) return;
    dispatch(
      parseIncidentText({
        content: textContent,
        isEmail: inputMode === 'email',
        investigationId: currentInvestigation?.id,
      })
    );
  };

  const handleApplyToForm = async () => {
    if (!currentInvestigation || !intakeExtraction) return;
    try {
      await dispatch(
        applyExtractionToForm({
          investigationId: currentInvestigation.id,
          extractionData: intakeExtraction,
          reviewedFields: intakeExtraction.extracted_fields,
        })
      ).unwrap();
      dispatch(
        setNotification({
          type: 'success',
          message: 'Reviewed deviation fields & evidence successfully applied and persisted in PostgreSQL!',
        })
      );
    } catch (err) {
      dispatch(
        setNotification({
          type: 'error',
          message: `Failed to apply extraction: ${err}`,
        })
      );
    }
  };

  const extractedFields = intakeExtraction?.extracted_fields || [];
  const filteredFields = extractedFields.filter((f) => {
    if (statusFilter === 'ALL') return true;
    return f.status === statusFilter;
  });

  const acceptedCount = extractedFields.filter((f) => f.is_accepted).length;

  return (
    <div className="space-y-4">
      {/* Input Mode Selector */}
      <div className="flex rounded-lg bg-slate-100 dark:bg-black p-1 border border-slate-200 dark:border-zinc-800">
        <button
          onClick={() => setInputMode('pdf')}
          className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 text-xs font-semibold rounded-md transition cursor-pointer ${
            inputMode === 'pdf' ? 'bg-white dark:bg-zinc-900 text-blue-700 dark:text-cyan-400 shadow-2xs' : 'text-slate-600 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-zinc-200'
          }`}
        >
          <Upload className="w-3.5 h-3.5" /> PDF Document
        </button>
        <button
          onClick={() => {
            setInputMode('text');
            setTextContent(samplePdfDeviation);
          }}
          className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 text-xs font-semibold rounded-md transition cursor-pointer ${
            inputMode === 'text' ? 'bg-white dark:bg-zinc-900 text-blue-700 dark:text-cyan-400 shadow-2xs' : 'text-slate-600 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-zinc-200'
          }`}
        >
          <FileText className="w-3.5 h-3.5" /> Incident Text
        </button>
        <button
          onClick={() => {
            setInputMode('email');
            setTextContent(sampleEmail);
          }}
          className={`flex-1 flex items-center justify-center gap-1.5 py-1.5 text-xs font-semibold rounded-md transition cursor-pointer ${
            inputMode === 'email' ? 'bg-white dark:bg-zinc-900 text-blue-700 dark:text-cyan-400 shadow-2xs' : 'text-slate-600 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-zinc-200'
          }`}
        >
          <Mail className="w-3.5 h-3.5" /> Email Intake
        </button>
      </div>

      {/* PDF Upload Mode */}
      {inputMode === 'pdf' && (
        <div className="border-2 border-dashed border-slate-300 dark:border-zinc-800 hover:border-blue-400 dark:hover:border-zinc-700 rounded-xl p-5 text-center transition bg-slate-50/50 dark:bg-zinc-950/40">
          <Upload className="w-8 h-8 text-blue-500 dark:text-cyan-400 mx-auto mb-2" />
          <h4 className="text-xs font-bold text-slate-800 dark:text-zinc-200">Upload Pharmaceutical Deviation Document</h4>
          <p className="text-[11px] text-slate-500 dark:text-zinc-400 mt-1 mb-3">
            Supports multi-page batch records, incident memos, and analytical deviations (.pdf, .txt, .eml).
          </p>
          <label className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-blue-600 dark:bg-cyan-600 hover:bg-blue-700 dark:hover:bg-cyan-500 text-white text-xs font-semibold cursor-pointer shadow-xs transition">
            <span>Browse Files</span>
            <input type="file" accept=".pdf,.txt,.eml,.log" onChange={handleFileUpload} className="hidden" />
          </label>
        </div>
      )}

      {/* Text / Email Mode */}
      {(inputMode === 'text' || inputMode === 'email') && (
        <div className="space-y-2">
          <div className="flex justify-between items-center gap-2 flex-wrap">
            <span className="text-xs font-semibold text-slate-700 dark:text-zinc-300">
              {inputMode === 'email' ? 'Paste Incident Email' : 'Paste Manufacturing Report'}
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setTextContent(sampleParacetamolDemo)}
                className="text-[11px] text-purple-700 dark:text-purple-300 hover:text-purple-900 dark:hover:text-purple-200 bg-purple-50 dark:bg-purple-950/40 px-2 py-0.5 rounded border border-purple-200 dark:border-purple-800 font-semibold transition cursor-pointer"
                title="Load Fictional Demonstration Scenario: Paracetamol Crystallization Excursion DEV-2026-104"
              >
                Load Demo (DEV-2026-104)
              </button>
              <button
                type="button"
                onClick={() => setTextContent(inputMode === 'email' ? sampleEmail : samplePdfDeviation)}
                className="text-[11px] text-blue-600 dark:text-cyan-400 hover:underline font-medium cursor-pointer"
              >
                Sample Data
              </button>
            </div>
          </div>
          <textarea
            rows={5}
            value={textContent}
            onChange={(e) => setTextContent(e.target.value)}
            placeholder="Paste raw text or email headers here..."
            className="w-full text-xs p-3 border border-slate-200 dark:border-zinc-800 rounded-lg bg-white dark:bg-black text-slate-900 dark:text-zinc-100 font-mono focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleTextSubmit}
            disabled={isExtracting || !textContent.trim()}
            className="w-full py-2 rounded-lg bg-blue-600 dark:bg-cyan-600 hover:bg-blue-700 dark:hover:bg-cyan-500 disabled:opacity-50 text-white text-xs font-semibold flex items-center justify-center gap-1.5 transition shadow-xs cursor-pointer"
          >
            {isExtracting ? (
              <>
                <Sparkles className="w-4 h-4 animate-spin" />
                <span>Running LangGraph Ingestion & Citation Validation...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                <span>Extract Structured Information via Groq</span>
              </>
            )}
          </button>
        </div>
      )}

      {/* Loading Indicator */}
      {isExtracting && (
        <div className="p-4 rounded-xl border border-blue-200 dark:border-blue-900 bg-blue-50/60 dark:bg-blue-950/30 text-center space-y-2 animate-pulse">
          <Sparkles className="w-6 h-6 text-blue-600 dark:text-cyan-400 mx-auto animate-spin" />
          <h4 className="text-xs font-bold text-blue-900 dark:text-cyan-200">Extracting Deviation Intelligence...</h4>
          <p className="text-[11px] text-blue-700 dark:text-cyan-400 max-w-sm mx-auto">
            Parsing document structure, verifying verbatim source citations, detecting conflicting evidence, and mapping pharmaceutical parameters.
          </p>
        </div>
      )}

      {/* Error Message */}
      {extractionError && (
        <div className="p-3 rounded-lg border border-rose-200 dark:border-rose-900 bg-rose-50 dark:bg-rose-950/40 text-rose-800 dark:text-rose-200 text-xs flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold">Extraction Error:</span> {extractionError}
          </div>
        </div>
      )}

      {/* Extraction Results & Human Review Interface */}
      {intakeExtraction && (
        <div className="space-y-4">
          {/* Header Action Bar */}
          <div className="p-3 rounded-xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50/70 dark:bg-emerald-950/30 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              <div>
                <h4 className="text-xs font-bold text-emerald-950 dark:text-emerald-200">
                  Document Extracted ({acceptedCount}/{extractedFields.length} fields accepted)
                </h4>
                <p className="text-[10px] text-emerald-800 dark:text-emerald-400">
                  Source: {intakeExtraction.source_type} • Confidence: {Math.round(intakeExtraction.ai_confidence_score * 100)}%
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowSourceViewer(!showSourceViewer)}
                className="text-xs font-medium text-emerald-800 dark:text-emerald-300 hover:text-emerald-950 dark:hover:text-emerald-100 flex items-center gap-1 px-2 py-1 rounded bg-emerald-100/60 dark:bg-emerald-900/40 hover:bg-emerald-100 transition cursor-pointer"
              >
                {showSourceViewer ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                <span>{showSourceViewer ? 'Hide Source' : 'View Source'}</span>
              </button>
              <button
                onClick={() => dispatch(clearExtraction())}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-zinc-200 p-1 cursor-pointer"
                title="Clear Extraction"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Raw Document Source Inspector */}
          {showSourceViewer && (
            <div className="p-3 rounded-lg border border-slate-300 dark:border-zinc-800 bg-slate-900 dark:bg-black text-slate-100 text-xs font-mono space-y-2">
              <div className="flex justify-between items-center text-[10px] text-slate-400 border-b border-slate-800 pb-1.5">
                <span className="flex items-center gap-1">
                  <Hash className="w-3 h-3 text-cyan-400" />
                  SHA-256: {intakeExtraction.source_metadata?.file_hash_sha256?.substring(0, 24)}...
                </span>
                <span>
                  {intakeExtraction.source_metadata?.page_count
                    ? `${intakeExtraction.source_metadata.page_count} Pages`
                    : `${intakeExtraction.source_metadata?.file_size_bytes || 0} bytes`}
                </span>
              </div>
              <div className="max-h-48 overflow-y-auto whitespace-pre-wrap text-[11px] leading-relaxed text-slate-300 scrollbar-thin">
                {intakeExtraction.raw_document_preview || 'No document preview available.'}
              </div>
            </div>
          )}

          {/* Conflicting Information Alert */}
          {intakeExtraction.conflicting_information && intakeExtraction.conflicting_information.length > 0 && (
            <div className="p-3 rounded-lg border border-amber-300 dark:border-amber-800 bg-amber-50/80 dark:bg-amber-950/30 space-y-2">
              <div className="flex items-center gap-1.5 text-xs font-bold text-amber-900 dark:text-amber-200">
                <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                <span>Conflicting Empirical Information Detected ({intakeExtraction.conflicting_information.length})</span>
              </div>
              {intakeExtraction.conflicting_information.map((c, idx) => (
                <div key={idx} className="bg-white dark:bg-zinc-950 p-2.5 rounded border border-amber-200 dark:border-amber-900/60 text-xs space-y-1">
                  <div className="font-semibold text-slate-800 dark:text-zinc-200 text-[11px]">{c.explanation}</div>
                  <div className="grid grid-cols-2 gap-2 text-[10px] mt-1 pt-1 border-t border-slate-100 dark:border-zinc-800">
                    <div className="bg-slate-50 dark:bg-black p-1.5 rounded">
                      <span className="font-bold text-slate-500 dark:text-zinc-400">Claim A:</span> {c.claim_a}
                      {c.source_a && <div className="text-slate-400 font-mono">({c.source_a})</div>}
                    </div>
                    <div className="bg-slate-50 dark:bg-black p-1.5 rounded">
                      <span className="font-bold text-slate-500 dark:text-zinc-400">Claim B:</span> {c.claim_b}
                      {c.source_b && <div className="text-slate-400 font-mono">({c.source_b})</div>}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Review Toolbar & Filter Bar */}
          <div className="space-y-2 pt-1 border-t border-slate-200 dark:border-zinc-800">
            <div className="flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <span className="font-bold text-slate-800 dark:text-zinc-200">Field Review</span>
                <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${
                  acceptedCount > 0 ? 'bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800' : 'bg-slate-100 dark:bg-zinc-900 text-slate-600 dark:text-zinc-400'
                }`}>
                  {acceptedCount} of {extractedFields.length} accepted
                </span>
              </div>
              <div className="flex items-center gap-1.5 text-[10px]">
                <button
                  onClick={() => dispatch(acceptAllSourceFacts())}
                  className="px-2 py-1 rounded bg-emerald-50 dark:bg-emerald-950/60 hover:bg-emerald-100 dark:hover:bg-emerald-900 text-emerald-700 dark:text-emerald-300 font-semibold border border-emerald-200 dark:border-emerald-800 transition cursor-pointer"
                  title="Accept all verified source facts"
                >
                  Accept Facts
                </button>
                <button
                  onClick={() => dispatch(acceptAllFields())}
                  className="px-2 py-1 rounded bg-blue-50 dark:bg-cyan-950/60 hover:bg-blue-100 dark:hover:bg-cyan-900 text-blue-700 dark:text-cyan-300 font-semibold border border-blue-200 dark:border-cyan-800 transition cursor-pointer"
                >
                  Select All
                </button>
                <button
                  onClick={() => dispatch(rejectAllFields())}
                  className="px-2 py-1 rounded bg-slate-100 dark:bg-zinc-900 hover:bg-slate-200 dark:hover:bg-zinc-800 text-slate-600 dark:text-zinc-400 font-semibold transition cursor-pointer"
                >
                  Clear All
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between text-xs">
              <span className="text-[11px] text-slate-500 dark:text-zinc-400">Filter by classification:</span>
              <div className="flex gap-1 text-[10px] font-semibold">
                {['ALL', 'SOURCE_FACT', 'AI_INFERENCE', 'CONFLICTING', 'MISSING'].map((st) => (
                  <button
                    key={st}
                    onClick={() => setStatusFilter(st)}
                    className={`px-2 py-0.5 rounded transition cursor-pointer ${
                      statusFilter === st
                        ? 'bg-slate-800 dark:bg-zinc-800 text-white'
                        : 'bg-slate-100 dark:bg-zinc-900 text-slate-600 dark:text-zinc-400 hover:bg-slate-200 dark:hover:bg-zinc-800'
                    }`}
                  >
                    {st === 'SOURCE_FACT' ? 'Facts' : st === 'AI_INFERENCE' ? 'Inferred' : st === 'CONFLICTING' ? 'Conflicts' : st === 'MISSING' ? 'Missing' : 'All'}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Extracted Fields List */}
          <div className="space-y-2.5 max-h-96 overflow-y-auto pr-1 scrollbar-thin">
            {filteredFields.map((field) => {
              const isFact = field.status === 'SOURCE_FACT';
              const isInferred = field.status === 'AI_INFERENCE';
              const isMissing = field.status === 'MISSING';
              const isConflict = field.status === 'CONFLICTING';

              return (
                <div
                  key={field.field_name}
                  className={`p-3 rounded-lg border transition ${
                    !field.is_accepted
                      ? 'border-slate-200 dark:border-zinc-850 bg-slate-50/60 dark:bg-zinc-950/40 opacity-60'
                      : isConflict
                      ? 'border-rose-300 dark:border-rose-900 bg-rose-50/40 dark:bg-rose-950/20'
                      : isFact
                      ? 'border-emerald-200 dark:border-emerald-900/60 bg-emerald-50/20 dark:bg-emerald-950/20'
                      : isInferred
                      ? 'border-amber-200 dark:border-amber-900/60 bg-amber-50/20 dark:bg-amber-950/20'
                      : 'border-slate-200 dark:border-zinc-800 bg-white dark:bg-zinc-950'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={field.is_accepted}
                        onChange={() => dispatch(toggleFieldAccepted(field.field_name))}
                        className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 h-3.5 w-3.5"
                      />
                      <span className="text-xs font-bold text-slate-800 dark:text-zinc-200">{field.label}</span>
                      {field.user_edited && (
                        <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-blue-100 dark:bg-blue-950 text-blue-700 dark:text-blue-300">
                          Edited
                        </span>
                      )}
                    </div>

                    {/* Status Badge */}
                    <div className="flex items-center gap-1.5">
                      {isFact && (
                        <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800">
                          <ShieldCheck className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
                          Source Fact {field.page_number ? `(Pg ${field.page_number})` : '(Doc Text)'}
                        </span>
                      )}
                      {isInferred && (
                        <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-800">
                          <Sparkles className="w-3 h-3 text-amber-600 dark:text-amber-400" />
                          AI Inferred
                        </span>
                      )}
                      {isConflict && (
                        <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-100 dark:bg-rose-950 text-rose-800 dark:text-rose-300 border border-rose-300 dark:border-rose-900">
                          <AlertTriangle className="w-3 h-3 text-rose-600 dark:text-rose-400" />
                          Conflict
                        </span>
                      )}
                      {isMissing && (
                        <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-slate-100 dark:bg-zinc-800 text-slate-600 dark:text-zinc-400 border border-slate-300 dark:border-zinc-700">
                          <HelpCircle className="w-3 h-3 text-slate-500 dark:text-zinc-400" />
                          Missing
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Value Input (Editable) */}
                  <div className="mt-2 space-y-1">
                    <input
                      type="text"
                      value={field.value || ''}
                      placeholder={isMissing ? 'Not stated in source (click to provide)' : 'Value...'}
                      onChange={(e) =>
                        dispatch(
                          updateExtractedField({
                            field_name: field.field_name,
                            value: e.target.value,
                          })
                        )
                      }
                      className={`w-full text-xs px-2.5 py-1.5 rounded border ${
                        field.user_edited
                          ? 'border-blue-400 dark:border-cyan-600 bg-blue-50/30 dark:bg-cyan-950/30'
                          : 'border-slate-200 dark:border-zinc-800 bg-white dark:bg-black'
                      } font-medium text-slate-800 dark:text-zinc-200 focus:outline-none focus:ring-1 focus:ring-blue-500`}
                    />
                    {field.user_edited && field.original_value && (
                      <div className="text-[10px] text-slate-400 dark:text-zinc-500 italic">
                        Original AI extraction: "{field.original_value}"
                      </div>
                    )}
                  </div>

                  {/* Grounded Citation Excerpt */}
                  {field.source_reference && (
                    <div className="mt-1.5 text-[10px] text-slate-500 dark:text-zinc-400 italic bg-white/70 dark:bg-black/70 p-1.5 rounded border border-slate-100 dark:border-zinc-850">
                      <span className="font-semibold text-slate-600 dark:text-zinc-300 not-italic">Citation: </span>
                      "{field.source_reference}"
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          {/* Missing Evidence Gaps Card */}
          {intakeExtraction.missing_information && intakeExtraction.missing_information.length > 0 && (
            <div className="p-3 rounded-lg border border-slate-200 dark:border-zinc-800 bg-slate-50 dark:bg-zinc-950 space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="font-bold text-slate-800 dark:text-zinc-200 flex items-center gap-1.5">
                  <HelpCircle className="w-3.5 h-3.5 text-blue-600 dark:text-cyan-400" />
                  Identified Evidence Gaps ({intakeExtraction.missing_information.length})
                </span>
                <span className="text-[10px] text-slate-500 dark:text-zinc-400">Will be tracked in Investigation Gaps</span>
              </div>
              <div className="space-y-1.5">
                {intakeExtraction.missing_information.map((gap, gIdx) => (
                  <div key={gIdx} className="bg-white dark:bg-black p-2 rounded border border-slate-200 dark:border-zinc-800 text-[11px] space-y-0.5">
                    <div className="flex justify-between items-center">
                      <span className="font-semibold text-slate-700 dark:text-zinc-300">{gap.category}</span>
                      <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-rose-100 dark:bg-rose-950 text-rose-700 dark:text-rose-300">
                        {gap.urgency}
                      </span>
                    </div>
                    <p className="text-slate-600 dark:text-zinc-400">{gap.question}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Apply to Investigation CTA */}
          <div className="pt-2 border-t border-slate-200 dark:border-zinc-800 space-y-2">
            <button
              onClick={handleApplyToForm}
              disabled={acceptedCount === 0}
              className="w-full py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-xs font-bold flex items-center justify-center gap-2 shadow-sm transition cursor-pointer"
            >
              <span>Apply {acceptedCount} Approved Fields to RCA Investigation</span>
              <ArrowRight className="w-4 h-4" />
            </button>
            <p className="text-[10px] text-slate-500 dark:text-zinc-400 text-center leading-tight">
              All applied data is saved to PostgreSQL and marked as AI suggestions until verified by an investigator.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentIntakeTab;
