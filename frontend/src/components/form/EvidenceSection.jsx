import React, { useState } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import {
  FileText,
  Upload,
  CheckCircle2,
  Clock,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  Trash2,
  ExternalLink,
  Plus,
} from 'lucide-react';
import { uploadEvidence, verifyEvidence, deleteEvidence } from '../../store/investigationSlice';
import { setNotification } from '../../store/uiSlice';
import { Button, Input, Textarea, Select, Card, CardHeader, CardContent, ConfirmDialog } from '../ui';

export const EvidenceSection = () => {
  const dispatch = useDispatch();
  const currentInvestigation = useSelector((state) => state.investigation.currentInvestigation);
  const currentUser = useSelector((state) => state.auth.user);
  const evidences = currentInvestigation?.evidences || [];

  const [expandedId, setExpandedId] = useState(null);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showVerifyModal, setShowVerifyModal] = useState(null); // holds evidence item
  const [deleteTarget, setDeleteTarget] = useState(null); // holds { id, title } for ConfirmDialog
  const [investigatorName, setInvestigatorName] = useState(
    () => currentUser?.full_name || currentInvestigation?.lead_investigator || 'Lead Investigator'
  );
  const [verifyNotes, setVerifyNotes] = useState('');

  // Upload modal state
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadTitle, setUploadTitle] = useState('');
  const [uploadType, setUploadType] = useState('DOCUMENT');
  const [uploadClassification, setUploadClassification] = useState('PRIMARY_SOURCE');
  const [isUploading, setIsUploading] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const toggleExpand = (id) => {
    setExpandedId(expandedId === id ? null : id);
  };

  const handleUploadSubmit = async (e) => {
    e.preventDefault();
    if (!selectedFile || !currentInvestigation) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', selectedFile);
    if (uploadTitle) formData.append('title', uploadTitle);
    formData.append('evidence_type', uploadType);
    formData.append('classification', uploadClassification);

    try {
      await dispatch(
        uploadEvidence({
          investigationId: currentInvestigation.id,
          formData,
        })
      ).unwrap();
      dispatch(
        setNotification({
          type: 'success',
          message: `Evidence file '${selectedFile.name}' successfully uploaded and indexed.`,
        })
      );
      setShowUploadModal(false);
      setSelectedFile(null);
      setUploadTitle('');
    } catch (err) {
      dispatch(
        setNotification({
          type: 'error',
          message: `Upload failed: ${err}`,
        })
      );
    } finally {
      setIsUploading(false);
    }
  };

  const handleVerifySubmit = async () => {
    if (!showVerifyModal || !investigatorName.trim()) return;

    try {
      await dispatch(
        verifyEvidence({
          evidenceId: showVerifyModal.id,
          investigatorName: investigatorName.trim(),
          notes: verifyNotes.trim() || undefined,
        })
      ).unwrap();
      dispatch(
        setNotification({
          type: 'success',
          message: `Evidence #${showVerifyModal.id} formally verified by ${investigatorName}.`,
        })
      );
      setShowVerifyModal(null);
      setVerifyNotes('');
    } catch (err) {
      dispatch(
        setNotification({
          type: 'error',
          message: `Verification failed: ${err}`,
        })
      );
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);
    try {
      await dispatch(deleteEvidence(deleteTarget.id)).unwrap();
      dispatch(
        setNotification({
          type: 'success',
          message: `Evidence #${deleteTarget.id} deleted.`,
        })
      );
      setDeleteTarget(null);
    } catch (err) {
      dispatch(
        setNotification({
          type: 'error',
          message: `Deletion failed: ${err}`,
        })
      );
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <Card id="section-evidence" className="mb-6">
      {/* Header */}
      <CardHeader
        icon={<FileText className="w-5 h-5 text-blue-700 dark:text-blue-400" />}
        title="Evidence Dossier & Source Traceability"
        badge={
          <span className="text-xs px-2 py-0.5 rounded bg-amber-50 dark:bg-amber-950/50 text-amber-900 dark:text-amber-300 font-extrabold border border-amber-300 dark:border-amber-700/60 font-mono">
            {evidences.length} {evidences.length === 1 ? 'Record' : 'Records'}
          </span>
        }
        action={
          <Button
            variant="primary"
            size="xs"
            onClick={() => setShowUploadModal(true)}
            icon={<Upload className="w-3.5 h-3.5" />}
          >
            Upload Evidence
          </Button>
        }
      />

      <CardContent>
        {evidences.length === 0 ? (
          <div className="p-6 border border-dashed border-slate-300 dark:border-zinc-800 rounded-xl text-center bg-slate-50/50 dark:bg-zinc-950/40">
            <FileText className="w-8 h-8 text-slate-400 dark:text-zinc-500 mx-auto mb-2" />
            <p className="text-xs font-semibold text-slate-700 dark:text-zinc-200">No Evidence Records Attached Yet</p>
            <p className="text-[11px] text-slate-500 dark:text-zinc-400 mt-1">
              Upload deviation PDFs, SCADA logs, calibration certificates, or complete intake in the Copilot to establish evidence traceability.
            </p>
            <Button
              variant="outline"
              size="xs"
              className="mt-3"
              onClick={() => setShowUploadModal(true)}
              icon={<Plus className="w-3.5 h-3.5 text-blue-600" />}
            >
              Upload First Document
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            {evidences.map((ev) => {
              const isExpanded = expandedId === ev.id;
              const hasHash = Boolean(ev.file_hash_sha256);

              return (
                <div
                  key={ev.id}
                  className={`rounded-xl border transition ${
                    ev.is_verified
                      ? 'border-emerald-200 dark:border-emerald-900/50 bg-emerald-50/20 dark:bg-emerald-950/20'
                      : 'border-slate-200 dark:border-zinc-800 bg-white dark:bg-zinc-950 shadow-2xs'
                  }`}
                >
                  <div className="p-3.5 flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <span className="text-xs font-bold text-slate-900 dark:text-zinc-100 truncate">
                          {ev.title}
                        </span>
                        <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-slate-100 dark:bg-zinc-900 text-slate-700 dark:text-zinc-300 border border-slate-200 dark:border-zinc-800 font-semibold">
                          {ev.evidence_type}
                        </span>
                        <span className="text-[10px] uppercase px-2 py-0.5 rounded bg-blue-50 dark:bg-blue-950/80 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800 font-semibold">
                          {ev.classification}
                        </span>

                        {ev.is_archived && (
                          <span className="inline-flex items-center gap-1 text-[10px] font-bold text-slate-600 dark:text-zinc-400 bg-slate-100 dark:bg-zinc-900 px-2 py-0.5 rounded-full border border-slate-300 dark:border-zinc-800">
                            SOFT-ARCHIVED
                          </span>
                        )}

                        {ev.is_verified ? (
                          <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-800 dark:text-emerald-300 bg-emerald-100 dark:bg-emerald-950 px-2 py-0.5 rounded-full border border-emerald-300 dark:border-emerald-800">
                            <CheckCircle2 className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
                            VERIFIED by {ev.verified_by || 'Investigator'}
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 text-[10px] font-bold text-amber-800 dark:text-amber-300 bg-amber-100 dark:bg-amber-950 px-2 py-0.5 rounded-full border border-amber-300 dark:border-amber-800">
                            <Clock className="w-3 h-3 text-amber-600 dark:text-amber-400" />
                            UNVERIFIED AI/RAW SOURCE
                          </span>
                        )}
                      </div>

                      <div className="flex items-center gap-3 text-[11px] text-slate-500 dark:text-zinc-400 flex-wrap">
                        {ev.source_location && (
                          <span>
                            <strong>Location:</strong> {ev.source_location}
                          </span>
                        )}
                        {ev.original_filename && (
                          <span>
                            <strong>File:</strong> {ev.original_filename}
                          </span>
                        )}
                        {ev.file_size_bytes && (
                          <span>({(ev.file_size_bytes / 1024).toFixed(1)} KB)</span>
                        )}
                        {hasHash && (
                          <span className="font-mono text-[10px] text-slate-400 dark:text-zinc-500" title={ev.file_hash_sha256}>
                            SHA-256: {ev.file_hash_sha256.substring(0, 10)}...
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      {ev.download_url && (
                        <a
                          href={ev.download_url}
                          download={ev.original_filename || true}
                          className="p-1.5 rounded-lg border border-slate-200 dark:border-zinc-800 bg-slate-50 dark:bg-zinc-900 hover:bg-blue-50 dark:hover:bg-zinc-800 text-slate-600 dark:text-zinc-300 hover:text-blue-600 transition flex items-center gap-1 text-xs"
                          title="Download original file with SHA-256 verification"
                          target="_blank"
                          rel="noreferrer"
                        >
                          <ExternalLink className="w-4 h-4 text-slate-500 dark:text-zinc-400 hover:text-blue-600" />
                        </a>
                      )}

                      {!ev.is_verified && !ev.is_archived && (
                        <Button
                          variant="success"
                          size="xs"
                          onClick={() => {
                            setInvestigatorName(currentUser?.full_name || currentInvestigation?.lead_investigator || 'Lead Investigator');
                            setShowVerifyModal(ev);
                          }}
                          icon={<ShieldCheck className="w-3.5 h-3.5" />}
                          title="Formally verify this evidence document"
                        >
                          Verify
                        </Button>
                      )}

                      <button
                        onClick={() => toggleExpand(ev.id)}
                        className="p-1.5 rounded-lg border border-slate-200 dark:border-zinc-800 bg-slate-50 dark:bg-zinc-900 hover:bg-slate-100 dark:hover:bg-zinc-800 text-slate-600 dark:text-zinc-300 transition"
                        title={isExpanded ? 'Collapse excerpt' : 'View extracted source excerpt'}
                        aria-label="Toggle excerpt"
                      >
                        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </button>

                      {!ev.is_verified && (
                        <button
                          onClick={() => setDeleteTarget({ id: ev.id, title: ev.title })}
                          className="p-1.5 rounded-lg border border-slate-200 dark:border-zinc-800 bg-slate-50 dark:bg-zinc-900 hover:bg-rose-50 dark:hover:bg-rose-950/40 text-slate-400 hover:text-rose-600 transition"
                          title="Delete evidence"
                          aria-label="Delete evidence"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Expandable Verbatim Excerpt */}
                  {isExpanded && (
                    <div className="px-4 pb-4 pt-1 border-t border-slate-100 bg-slate-50/70 rounded-b-xl space-y-2">
                      <div className="flex items-center justify-between text-[11px] text-slate-500 font-semibold pt-1">
                        <span>Verbatim Source Excerpt:</span>
                        {ev.verification_date && (
                          <span className="text-emerald-700 font-medium">
                            Verified on {new Date(ev.verification_date).toLocaleString()}
                          </span>
                        )}
                      </div>
                      <div className="p-3 bg-white dark:bg-black rounded-lg border border-slate-200 dark:border-zinc-800 text-xs font-mono text-slate-800 dark:text-zinc-200 leading-relaxed max-h-56 overflow-y-auto whitespace-pre-wrap">
                        {ev.extracted_text || 'No extracted text available for this record.'}
                      </div>
                      {ev.investigator_notes && (
                        <div className="p-2.5 bg-blue-50/60 dark:bg-blue-950/40 rounded-lg border border-blue-200 dark:border-blue-900/50 text-xs text-blue-900 dark:text-blue-200">
                          <strong>Investigator Notes:</strong> {ev.investigator_notes}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </CardContent>

      {/* Upload Evidence Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 dark:bg-black/80 backdrop-blur-xs p-4 animate-fade-in">
          <div className="bg-white dark:bg-black rounded-2xl border border-slate-200 dark:border-zinc-800 shadow-xl max-w-md w-full p-6 space-y-4">
            <h4 className="font-bold text-base text-slate-900 dark:text-zinc-100 flex items-center gap-2">
              <Upload className="w-5 h-5 text-blue-600 dark:text-cyan-400" /> Upload Supplementary Evidence
            </h4>
            <p className="text-xs text-slate-500 dark:text-zinc-400">
              Attach supporting records (SCADA telemetry export, calibration certificate, HPLC report, or shift log).
            </p>

            <form onSubmit={handleUploadSubmit} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-zinc-300 mb-1">Select File (.pdf, .txt, .csv)</label>
                <input
                  type="file"
                  required
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) {
                      setSelectedFile(f);
                      if (!uploadTitle) setUploadTitle(f.name.replace(/\.[^/.]+$/, ''));
                    }
                  }}
                  className="w-full text-xs file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-blue-50 dark:file:bg-zinc-800 file:text-blue-700 dark:file:text-cyan-300 hover:file:bg-blue-100 dark:hover:file:bg-zinc-700 border border-slate-200 dark:border-zinc-700 rounded-lg p-1.5 bg-slate-50 dark:bg-zinc-950 text-slate-900 dark:text-zinc-100"
                />
              </div>

              <Input
                label="Evidence Title"
                placeholder="e.g. CV-301 Actuator Stroke Calibration Certificate"
                value={uploadTitle}
                onChange={(e) => setUploadTitle(e.target.value)}
              />

              <div className="grid grid-cols-2 gap-3">
                <Select
                  label="Evidence Type"
                  value={uploadType}
                  onChange={(e) => setUploadType(e.target.value)}
                >
                  <option value="DOCUMENT">Document</option>
                  <option value="BATCH_RECORD">Batch Record</option>
                  <option value="SCADA_TREND">SCADA Trend</option>
                  <option value="CALIBRATION_CERT">Calibration Cert</option>
                  <option value="LAB_HPLC">Lab HPLC Report</option>
                  <option value="LOGBOOK">Logbook Entry</option>
                  <option value="INTERVIEW">Interview</option>
                  <option value="SOP">SOP Standard</option>
                </Select>

                <Select
                  label="Classification"
                  value={uploadClassification}
                  onChange={(e) => setUploadClassification(e.target.value)}
                >
                  <option value="PRIMARY_SOURCE">Primary Source</option>
                  <option value="ANALYTICAL_DATA">Analytical Data</option>
                  <option value="SYSTEM_TELEMETRY">System Telemetry</option>
                  <option value="TESTIMONIAL">Testimonial</option>
                  <option value="REGULATORY_STANDARD">Regulatory Standard</option>
                </Select>
              </div>

              <div className="pt-3 flex justify-end gap-2 border-t border-slate-100 dark:border-zinc-800">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setShowUploadModal(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  disabled={!selectedFile}
                  loading={isUploading}
                >
                  Save & Extract
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Verify Evidence Modal */}
      {showVerifyModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 dark:bg-black/80 backdrop-blur-xs p-4 animate-fade-in">
          <div className="bg-white dark:bg-black rounded-2xl border border-slate-200 dark:border-zinc-800 shadow-xl max-w-md w-full p-6 space-y-4">
            <h4 className="font-bold text-base text-slate-900 dark:text-zinc-100 flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-emerald-600 dark:text-emerald-400" /> Verify Evidence Authenticity
            </h4>
            <p className="text-xs text-slate-600 dark:text-zinc-400">
              Formally verify that <strong>"{showVerifyModal.title}"</strong> has been examined and corroborates physical manufacturing records.
            </p>

            {showVerifyModal.uploaded_by_user_id === currentUser?.id && (
              <div className="p-2.5 rounded-lg border border-amber-300 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/40 text-amber-900 dark:text-amber-200 text-xs">
                <strong>Separation of Duties Notice:</strong> You originally uploaded or ingested this evidence record. In accordance with cGMP standards, verification requires an independent QA reviewer.
              </div>
            )}

            <div className="space-y-3">
              <Input
                label="Investigator Name"
                required
                value={investigatorName}
                onChange={(e) => setInvestigatorName(e.target.value)}
              />

              <Textarea
                label="Verification Justification / Audit Notes"
                rows={3}
                placeholder="e.g. Examined physical batch log and verified calibration sticker CAL-2026-88 on reactor valve actuator."
                value={verifyNotes}
                onChange={(e) => setVerifyNotes(e.target.value)}
              />

              <div className="pt-3 flex justify-end gap-2 border-t border-slate-100 dark:border-zinc-800">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setShowVerifyModal(null)}
                >
                  Cancel
                </Button>
                <Button
                  type="button"
                  variant="success"
                  size="sm"
                  disabled={!investigatorName.trim()}
                  onClick={handleVerifySubmit}
                >
                  Sign & Verify Record
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Accessible Confirm Dialog replacing window.confirm */}
      <ConfirmDialog
        isOpen={Boolean(deleteTarget)}
        title="Delete Evidence Record"
        message={`Are you sure you want to permanently delete evidence record '${deleteTarget?.title}'? This action is tracked in the cGMP audit trail.`}
        confirmText="Delete Record"
        cancelText="Keep Record"
        variant="danger"
        loading={isDeleting}
        onClose={() => setDeleteTarget(null)}
        onConfirm={confirmDelete}
      />
    </Card>
  );
};

export default EvidenceSection;
