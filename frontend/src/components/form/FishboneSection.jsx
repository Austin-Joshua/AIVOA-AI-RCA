import React, { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  Layers,
  Plus,
  Trash2,
  User,
  Cpu,
  Package,
  Sliders,
  Gauge,
  ThermometerSnowflake,
  Link2,
  ArrowUpRight,
  X,
  Eye,
  LayoutGrid,
  Sparkles,
} from 'lucide-react';
import {
  addFishboneCause,
  deleteFishboneCause,
  linkFishboneEvidence,
  unlinkFishboneEvidence,
  verifyFishboneCause,
  promoteFishboneCause,
  fetchInvestigationById,
} from '../../store/investigationSlice';
import { generateRcaPackage, applyRcaProposal } from '../../store/copilotSlice';
import { setNotification } from '../../store/uiSlice';
import { Card, CardHeader, CardContent, Button, Input, Textarea, Select } from '../ui';

export const FishboneSection = () => {
  const dispatch = useDispatch();
  const currentInvestigation = useSelector((state) => state.investigation.currentInvestigation);
  const fishboneCauses = currentInvestigation?.fishbone_causes || [];
  const dossierEvidences = (currentInvestigation?.evidences || []).filter((e) => !e.is_archived);

  const [viewMode, setViewMode] = useState('diagram'); // 'diagram' | 'grid'
  const [selectedCauseId, setSelectedCauseId] = useState(null);
  const [activeCategoryModal, setActiveCategoryModal] = useState(null);
  const [newCauseText, setNewCauseText] = useState('');
  const [newRationale, setNewRationale] = useState('');
  const [newEvidence, setNewEvidence] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);

  const handleGenerateWithAI = async () => {
    if (!currentInvestigation?.id) return;
    setIsGenerating(true);
    try {
      const pkg = await dispatch(
        generateRcaPackage({ investigationId: currentInvestigation.id })
      ).unwrap();
      if (pkg) {
        await dispatch(
          applyRcaProposal({ investigationId: currentInvestigation.id, rcaData: pkg })
        ).unwrap();
        await dispatch(fetchInvestigationById(currentInvestigation.id));
        dispatch(
          setNotification({
            type: 'success',
            message: '5-Whys and Fishbone 6M causality network synthesized and applied!',
          })
        );
      }
    } catch (err) {
      dispatch(
        setNotification({
          type: 'error',
          message: `Generation failed: ${err}`,
        })
      );
    } finally {
      setIsGenerating(false);
    }
  };

  // Evidence linking modal state
  const [linkingCauseId, setLinkingCauseId] = useState(null);
  const [selectedEvidenceId, setSelectedEvidenceId] = useState('');
  const [relationshipType, setRelationshipType] = useState('SUPPORTING');
  const [linkExplanation, setLinkExplanation] = useState('');
  const [isSubmittingLink, setIsSubmittingLink] = useState(false);

  const categories = [
    {
      id: 'MAN',
      label: 'Man (Personnel)',
      icon: User,
      color: 'text-indigo-600 bg-indigo-50 border-indigo-200',
      stroke: '#4f46e5',
      position: 'top',
      ribIndex: 0,
    },
    {
      id: 'MACHINE',
      label: 'Machine (Equipment)',
      icon: Cpu,
      color: 'text-rose-600 bg-rose-50 border-rose-200',
      stroke: '#e11d48',
      position: 'top',
      ribIndex: 1,
    },
    {
      id: 'METHOD',
      label: 'Method (SOP & Recipe)',
      icon: Sliders,
      color: 'text-blue-600 bg-blue-50 border-blue-200',
      stroke: '#2563eb',
      position: 'top',
      ribIndex: 2,
    },
    {
      id: 'MATERIAL',
      label: 'Material (Solvent / API)',
      icon: Package,
      color: 'text-amber-600 bg-amber-50 border-amber-200',
      stroke: '#d97706',
      position: 'bottom',
      ribIndex: 0,
    },
    {
      id: 'MEASUREMENT',
      label: 'Measurement (Sensors)',
      icon: Gauge,
      color: 'text-emerald-600 bg-emerald-50 border-emerald-200',
      stroke: '#059669',
      position: 'bottom',
      ribIndex: 1,
    },
    {
      id: 'MILIEU',
      label: 'Environment (Facility / HVAC)',
      icon: ThermometerSnowflake,
      color: 'text-cyan-600 bg-cyan-50 border-cyan-200',
      stroke: '#0891b2',
      position: 'bottom',
      ribIndex: 2,
    },
  ];

  const handleStatusChange = async (cause, newStatus) => {
    if (newStatus === 'VERIFIED') {
      const hasVerifiedSupporting = (cause.evidence_links || []).some(
        (l) => l.relationship_type === 'SUPPORTING' && l.evidence?.is_verified
      );
      if (!hasVerifiedSupporting) {
        dispatch(
          setNotification({
            type: 'error',
            message: `Verification safety rule: Cause in ${cause.category} requires at least one verified piece of supporting evidence before it can be verified.`,
          })
        );
        return;
      }
    }

    try {
      await dispatch(
        verifyFishboneCause({
          causeId: cause.id,
          status: newStatus,
          notes: `Status changed to ${newStatus} by investigator.`,
        })
      ).unwrap();
      dispatch(
        setNotification({
          type: 'success',
          message: `Cause updated to ${newStatus}.`,
        })
      );
    } catch (err) {
      dispatch(setNotification({ type: 'error', message: String(err) }));
    }
  };

  const handlePromoteToRootCause = async (cause) => {
    try {
      const res = await dispatch(
        promoteFishboneCause({
          causeId: cause.id,
          isPrimary: false,
          notes: `Promoted from Fishbone category ${cause.category}`,
        })
      ).unwrap();
      dispatch(
        setNotification({
          type: 'success',
          message: `Hypothesis in ${cause.category} promoted to Root Cause proposal #${res.rootCause.id}!`,
        })
      );
    } catch (err) {
      dispatch(setNotification({ type: 'error', message: String(err) }));
    }
  };

  const handleAddCause = (category) => {
    if (!newCauseText.trim()) return;
    dispatch(
      addFishboneCause({
        investigationId: currentInvestigation.id,
        data: {
          category,
          cause_description: newCauseText.trim(),
          status: 'HYPOTHESIS',
          rationale: newRationale.trim() || null,
          evidence_reference: newEvidence.trim() || null,
          is_ai_suggested: false,
          is_verified: false,
        },
      })
    );
    setNewCauseText('');
    setNewRationale('');
    setNewEvidence('');
    setActiveCategoryModal(null);
  };

  const handleOpenLinkModal = (causeId) => {
    setLinkingCauseId(causeId);
    setSelectedEvidenceId(dossierEvidences[0]?.id || '');
    setRelationshipType('SUPPORTING');
    setLinkExplanation('');
  };

  const handleCreateEvidenceLink = async (e) => {
    e.preventDefault();
    if (!linkingCauseId || !selectedEvidenceId) return;
    setIsSubmittingLink(true);
    try {
      await dispatch(
        linkFishboneEvidence({
          causeId: linkingCauseId,
          evidenceId: parseInt(selectedEvidenceId, 10),
          relationshipType,
          explanation: linkExplanation,
        })
      ).unwrap();
      dispatch(
        setNotification({
          type: 'success',
          message: `Evidence linked to Fishbone cause as ${relationshipType}.`,
        })
      );
      setLinkingCauseId(null);
    } catch (err) {
      dispatch(setNotification({ type: 'error', message: String(err) }));
    } finally {
      setIsSubmittingLink(false);
    }
  };

  const handleUnlinkEvidence = async (causeId, evidenceId) => {
    try {
      await dispatch(unlinkFishboneEvidence({ causeId, evidenceId })).unwrap();
      dispatch(
        setNotification({
          type: 'info',
          message: 'Evidence unlinked from Fishbone cause.',
        })
      );
    } catch (err) {
      dispatch(setNotification({ type: 'error', message: String(err) }));
    }
  };

  const selectedCause = fishboneCauses.find((c) => c.id === selectedCauseId);

  // SVG diagram coordinates:
  // Width: 880, Height: 440
  // Spine line: (60, 220) to (710, 220)
  // Problem box: (710, 180) to (860, 260)
  const ribXCoords = [200, 380, 560];

  return (
    <Card id="section-fishbone" className="mb-6">
      {/* Header */}
      <CardHeader
        icon={<Layers className="w-5 h-5 text-blue-700 dark:text-blue-400" />}
        title="Ishikawa Fishbone Diagram (6Ms Analysis)"
        badge={
          <span className="text-xs px-2 py-0.5 rounded bg-amber-50 dark:bg-amber-950/50 text-amber-900 dark:text-amber-300 font-extrabold border border-amber-300 dark:border-amber-700/60 font-mono">
            {fishboneCauses.length} Hypotheses Mapped
          </span>
        }
        action={
          <div className="flex items-center gap-2">
            <Button
              variant="brand"
              size="xs"
              onClick={handleGenerateWithAI}
              loading={isGenerating}
              icon={<Sparkles className="w-3.5 h-3.5" />}
            >
              Generate 5 Whys & Fishbone with AI
            </Button>
            <div className="flex items-center gap-1.5 bg-slate-100 dark:bg-black p-0.5 rounded-lg border border-slate-200 dark:border-zinc-800">
              <button
                onClick={() => setViewMode('diagram')}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-semibold transition cursor-pointer ${
                  viewMode === 'diagram'
                    ? 'bg-white dark:bg-zinc-900 text-blue-700 dark:text-cyan-400 shadow-2xs'
                    : 'text-slate-600 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-zinc-100'
                }`}
              >
                <Eye className="w-3.5 h-3.5" /> Diagram View
              </button>
              <button
                onClick={() => setViewMode('grid')}
                className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-semibold transition cursor-pointer ${
                  viewMode === 'grid'
                    ? 'bg-white dark:bg-zinc-900 text-blue-700 dark:text-cyan-400 shadow-2xs'
                    : 'text-slate-600 dark:text-zinc-400 hover:text-slate-900 dark:hover:text-zinc-100'
                }`}
              >
                <LayoutGrid className="w-3.5 h-3.5" /> 6Ms Grid
              </button>
            </div>
          </div>
        }
      />

      <CardContent className="space-y-4">
        {fishboneCauses.length === 0 && (
          <div className="p-4 rounded-xl bg-blue-50/80 dark:bg-zinc-950/80 border border-blue-200 dark:border-zinc-800 flex flex-col sm:flex-row items-center justify-between gap-3 animate-fade-in">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-blue-600 dark:bg-cyan-600 text-white flex items-center justify-center shrink-0 shadow-xs">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-800 dark:text-zinc-100">No Fishbone Causes Identified Yet</h4>
                <p className="text-[11px] text-slate-600 dark:text-zinc-400">
                  Run the multi-disciplinary LangGraph RCA engine to synthesize 6Ms hypotheses and 5-Whys root cause paths.
                </p>
              </div>
            </div>
            <Button
              variant="primary"
              size="sm"
              onClick={handleGenerateWithAI}
              loading={isGenerating}
              icon={<Sparkles className="w-4 h-4" />}
            >
              Generate 5 Whys & Fishbone with AI
            </Button>
          </div>
        )}

        <p className="text-xs text-slate-500 leading-relaxed">
          The 6Ms structure multi-disciplinary exploration across manufacturing operations. Click on any cause node in
          the diagram to inspect empirical citations, verify hypotheses, or promote findings to a formal Root Cause proposal.
        </p>

        <div className="flex flex-wrap items-center gap-2 pt-1 pb-1">
          <span className="text-xs font-semibold text-slate-500 mr-1">6Ms Branches:</span>
          {categories.map((cat) => (
            <span
              key={cat.id}
              className={`text-xs px-2.5 py-0.5 rounded-full border font-medium ${cat.color}`}
            >
              {cat.label}
            </span>
          ))}
        </div>

        {/* VIEW 1: INTERACTIVE SVG FISHBONE DIAGRAM */}
        {viewMode === 'diagram' && (
          <div className="space-y-4">
            <div className="w-full overflow-x-auto bg-slate-900 dark:bg-black rounded-xl p-4 shadow-inner border border-slate-800 dark:border-zinc-800">
              <svg
                viewBox="0 0 1020 480"
                className="w-full min-w-[800px] h-auto select-none font-sans"
              >
                <defs>
                  <marker
                    id="arrowhead"
                    markerWidth="10"
                    markerHeight="7"
                    refX="9"
                    refY="3.5"
                    orient="auto"
                  >
                    <polygon points="0 0, 10 3.5, 0 7" fill="#60a5fa" />
                  </marker>
                  <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                    <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#38bdf8" floodOpacity="0.4" />
                  </filter>
                </defs>

                {/* Central Horizontal Spine */}
                <line
                  x1="40"
                  y1="230"
                  x2="760"
                  y2="230"
                  stroke="#60a5fa"
                  strokeWidth="4"
                  markerEnd="url(#arrowhead)"
                  strokeLinecap="round"
                />

                {/* Spine Tail Label */}
                <text x="40" y="222" fill="#94a3b8" fontSize="10" fontWeight="bold">
                  MANUFACTURING PROCESS
                </text>

                {/* Problem Statement Box (Fish Head) */}
                <g transform="translate(770, 160)">
                  <rect
                    width="235"
                    height="135"
                    rx="12"
                    fill="#1e293b"
                    stroke="#38bdf8"
                    strokeWidth="2"
                    filter="url(#glow)"
                  />
                  <text x="117" y="24" fill="#38bdf8" fontSize="10" fontWeight="bold" textAnchor="middle">
                    PROBLEM STATEMENT
                  </text>
                  <text x="117" y="44" fill="#f8fafc" fontSize="11" fontWeight="bold" textAnchor="middle">
                    {currentInvestigation?.deviation?.deviation_number || 'DEV-2026-DRAFT'}
                  </text>
                  <text x="117" y="64" fill="#94a3b8" fontSize="9.5" textAnchor="middle">
                    {currentInvestigation?.deviation?.product_name
                      ? (currentInvestigation.deviation.product_name.length > 28
                          ? currentInvestigation.deviation.product_name.slice(0, 26) + '...'
                          : currentInvestigation.deviation.product_name)
                      : 'Thermal Excursion'}
                  </text>
                  <text x="117" y="82" fill="#cbd5e1" fontSize="9" fontStyle="italic" textAnchor="middle">
                    Batch: {currentInvestigation?.deviation?.batch_number || 'Unassigned'}
                  </text>
                  <text x="117" y="98" fill="#94a3b8" fontSize="8.5" textAnchor="middle">
                    Op: {currentInvestigation?.deviation?.unit_operation || 'Crystallization'}
                  </text>
                  <text x="117" y="114" fill="#f87171" fontSize="8.5" fontWeight="bold" textAnchor="middle">
                    Severity: {currentInvestigation?.deviation?.severity || 'Major'}
                  </text>
                </g>

                {/* Categories & Ribs */}
                {categories.map((cat) => {
                  const isTop = cat.position === 'top';
                  const ribX = ribXCoords[cat.ribIndex];
                  const ribYEnd = 230;
                  const ribYStart = isTop ? 45 : 415;
                  const ribXStart = ribX - 70;

                  const causes = fishboneCauses.filter((c) => c.category === cat.id);

                  return (
                    <g key={cat.id}>
                      {/* Diagonal Rib Line */}
                      <line
                        x1={ribXStart}
                        y1={ribYStart}
                        x2={ribX}
                        y2={ribYEnd}
                        stroke={cat.stroke}
                        strokeWidth="2.5"
                        strokeLinecap="round"
                        opacity="0.85"
                      />

                      {/* Rib Category Label / Pill */}
                      <g
                        transform={`translate(${ribXStart - 50}, ${isTop ? ribYStart - 25 : ribYStart})`}
                        className="cursor-pointer"
                        onClick={() => setActiveCategoryModal(cat.id)}
                      >
                        <rect
                          width="125"
                          height="26"
                          rx="6"
                          fill="#1e293b"
                          stroke={cat.stroke}
                          strokeWidth="1.5"
                        />
                        <text
                          x="62.5"
                          y="17"
                          fill="#f8fafc"
                          fontSize="10"
                          fontWeight="bold"
                          textAnchor="middle"
                        >
                          {cat.label.split(' ')[0]} ({causes.length})
                        </text>
                      </g>

                      {/* Cause Branch Nodes along Rib */}
                      {causes.map((cause, cIdx) => {
                        // Interpolate position along the rib
                        const fraction = (cIdx + 1) / (causes.length + 1);
                        const nodeX = ribXStart + (ribX - ribXStart) * fraction;
                        const nodeY = ribYStart + (ribYEnd - ribYStart) * fraction;
                        const branchLen = 95;
                        const branchX = nodeX - branchLen;
                        const isSelected = selectedCauseId === cause.id;

                        return (
                          <g
                            key={cause.id}
                            className="cursor-pointer group"
                            onClick={() => setSelectedCauseId(cause.id)}
                          >
                            {/* Horizontal branch line */}
                            <line
                              x1={branchX}
                              y1={nodeY}
                              x2={nodeX}
                              y2={nodeY}
                              stroke={isSelected ? '#38bdf8' : '#64748b'}
                              strokeWidth={isSelected ? '2' : '1.5'}
                              strokeDasharray={cause.status === 'RULED_OUT' ? '3,3' : undefined}
                            />
                            {/* Node text box */}
                            <rect
                              x={branchX - 10}
                              y={nodeY - 11}
                              width="105"
                              height="22"
                              rx="5"
                              fill={isSelected ? '#0369a1' : '#0f172a'}
                              stroke={
                                cause.status === 'VERIFIED'
                                  ? '#10b981'
                                  : cause.status === 'RULED_OUT'
                                  ? '#64748b'
                                  : isSelected
                                  ? '#38bdf8'
                                  : '#334155'
                              }
                              strokeWidth={isSelected ? '1.5' : '1'}
                            />
                            <text
                              x={branchX + 42}
                              y={nodeY + 4}
                              fill={
                                cause.status === 'RULED_OUT'
                                  ? '#94a3b8'
                                  : isSelected
                                  ? '#ffffff'
                                  : '#e2e8f0'
                              }
                              fontSize="9.5"
                              fontWeight={isSelected ? 'bold' : 'normal'}
                              textAnchor="middle"
                            >
                              {cause.cause_description.length > 16
                                ? `${cause.cause_description.slice(0, 15)}…`
                                : cause.cause_description}
                            </text>
                          </g>
                        );
                      })}

                      {/* Add Button if empty or to add more */}
                      <g
                        transform={`translate(${ribXStart + 10}, ${isTop ? ribYStart + 15 : ribYStart - 25})`}
                        className="cursor-pointer opacity-70 hover:opacity-100 transition"
                        onClick={() => setActiveCategoryModal(cat.id)}
                      >
                        <circle cx="8" cy="8" r="8" fill="#334155" stroke={cat.stroke} strokeWidth="1" />
                        <text x="8" y="12" fill="#ffffff" fontSize="11" fontWeight="bold" textAnchor="middle">
                          +
                        </text>
                      </g>
                    </g>
                  );
                })}
              </svg>
            </div>

            {/* Selected Cause Inspector Drawer */}
            {selectedCause ? (
              <div className="p-4 rounded-xl border border-blue-200 bg-blue-50/40 space-y-3 animate-fade-in">
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-blue-100 text-blue-900 border border-blue-200 font-bold">
                        {selectedCause.category}
                      </span>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                          selectedCause.status === 'VERIFIED'
                            ? 'bg-emerald-100 text-emerald-800 border-emerald-300'
                            : selectedCause.status === 'RULED_OUT'
                            ? 'bg-slate-100 text-slate-600 border-slate-300'
                            : 'bg-amber-100 text-amber-800 border-amber-300'
                        }`}
                      >
                        STATUS: {selectedCause.status}
                      </span>
                      {selectedCause.promoted_to_root_cause_id && (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-purple-100 text-purple-800 border border-purple-300">
                          PROMOTED TO ROOT CAUSE
                        </span>
                      )}
                    </div>
                    <h4 className="text-sm font-bold text-slate-900 leading-snug">
                      {selectedCause.cause_description}
                    </h4>
                  </div>
                  <button
                    onClick={() => setSelectedCauseId(null)}
                    className="text-slate-400 hover:text-slate-600 p-1"
                    aria-label="Close inspector"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                {selectedCause.rationale && (
                  <p className="text-xs text-slate-600 dark:text-zinc-300 bg-white dark:bg-black p-2.5 rounded-lg border border-slate-200 dark:border-zinc-800">
                    <strong>Plausibility & Mechanism:</strong> {selectedCause.rationale}
                  </p>
                )}

                {/* Evidence Links for this cause */}
                {selectedCause.evidence_links && selectedCause.evidence_links.length > 0 && (
                  <div className="space-y-1">
                    <span className="text-[11px] font-bold text-slate-600 uppercase block">
                      Linked Evidence ({selectedCause.evidence_links.length}):
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {selectedCause.evidence_links.map((link) => (
                        <span
                          key={link.id}
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium border ${
                            link.relationship_type === 'SUPPORTING'
                              ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                              : 'bg-rose-50 text-rose-800 border-rose-200'
                          }`}
                        >
                          <strong>{link.relationship_type}:</strong>
                          <span>{link.evidence?.title || `Evidence #${link.evidence_id}`}</span>
                          <button
                            onClick={() => handleUnlinkEvidence(selectedCause.id, link.evidence_id)}
                            className="text-slate-400 hover:text-rose-600 ml-1"
                            title="Unlink evidence"
                          >
                            <X className="w-3 h-3" />
                          </button>
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Action Bar */}
                <div className="flex items-center justify-between pt-2 border-t border-blue-200/80 flex-wrap gap-2">
                  <div className="flex items-center gap-2">
                    <label className="text-xs font-semibold text-slate-700">Evaluation:</label>
                    <Select
                      value={selectedCause.status}
                      onChange={(e) => handleStatusChange(selectedCause, e.target.value)}
                      className="py-1 text-xs"
                    >
                      <option value="HYPOTHESIS">HYPOTHESIS</option>
                      <option value="VERIFIED">VERIFIED</option>
                      <option value="RULED_OUT">RULED OUT</option>
                    </Select>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="xs"
                      onClick={() => handleOpenLinkModal(selectedCause.id)}
                      icon={<Link2 className="w-3.5 h-3.5 text-blue-600" />}
                    >
                      Link Evidence
                    </Button>
                    {!selectedCause.promoted_to_root_cause_id && (
                      <Button
                        variant="primary"
                        size="xs"
                        onClick={() => handlePromoteToRootCause(selectedCause)}
                        icon={<ArrowUpRight className="w-3.5 h-3.5" />}
                      >
                        Promote to Root Cause
                      </Button>
                    )}
                    <button
                      onClick={() => {
                        dispatch(deleteFishboneCause(selectedCause.id));
                        setSelectedCauseId(null);
                      }}
                      className="text-slate-400 hover:text-rose-600 p-1.5 rounded hover:bg-rose-50 transition"
                      title="Delete cause"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-500 text-center">
                Click any cause box in the diagram above to inspect details, link evidence, or promote to formal root cause.
              </div>
            )}
          </div>
        )}

        {/* VIEW 2: 6Ms GRID VIEW */}
        {viewMode === 'grid' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {categories.map((cat) => {
              const Icon = cat.icon;
              const causes = fishboneCauses.filter((c) => c.category === cat.id);

              return (
                <div
                  key={cat.id}
                  className="rounded-xl border border-slate-200 dark:border-zinc-800 bg-slate-50/50 dark:bg-zinc-950/80 flex flex-col overflow-hidden shadow-2xs"
                >
                  {/* Branch Header */}
                  <div className="px-3.5 py-2.5 bg-white dark:bg-zinc-900 border-b border-slate-200 dark:border-zinc-800 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={`p-1 rounded-md ${cat.color}`}>
                        <Icon className="w-4 h-4" />
                      </span>
                      <span className="text-xs font-bold text-slate-800 dark:text-zinc-100">{cat.label}</span>
                    </div>
                    <button
                      onClick={() => setActiveCategoryModal(cat.id)}
                      className="p-1 rounded hover:bg-slate-100 dark:hover:bg-zinc-800 text-slate-500 dark:text-zinc-400 hover:text-slate-800 dark:hover:text-zinc-100 transition cursor-pointer"
                      title={`Add cause to ${cat.id}`}
                    >
                      <Plus className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  {/* Causes List */}
                  <div className="p-3 space-y-2.5 flex-1">
                    {causes.length === 0 ? (
                      <p className="text-[11px] text-slate-400 dark:text-zinc-500 italic text-center py-4">
                        No factors identified
                      </p>
                    ) : (
                      causes.map((cause) => {
                        const evidenceLinks = cause.evidence_links || [];
                        const isPromoted = Boolean(cause.promoted_to_root_cause_id);

                        return (
                          <div
                            key={cause.id}
                            className="p-2.5 rounded-lg border border-slate-200 dark:border-zinc-800 bg-white dark:bg-black space-y-2 shadow-2xs"
                          >
                            <div className="flex items-start justify-between gap-1.5">
                              <span className="text-xs font-medium text-slate-800 dark:text-zinc-200 leading-snug flex-1">
                                {cause.cause_description}
                              </span>
                              <button
                                onClick={() => dispatch(deleteFishboneCause(cause.id))}
                                className="text-slate-400 hover:text-rose-600 p-0.5 rounded transition cursor-pointer"
                                title="Delete"
                              >
                                <Trash2 className="w-3 h-3" />
                              </button>
                            </div>

                            {cause.rationale && (
                              <p className="text-[11px] text-slate-500 bg-slate-50 p-1.5 rounded">
                                {cause.rationale}
                              </p>
                            )}

                            {/* Evidence Links */}
                            {evidenceLinks.length > 0 && (
                              <div className="flex flex-wrap gap-1">
                                {evidenceLinks.map((link) => (
                                  <span
                                    key={link.id}
                                    className={`inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[9px] font-semibold border ${
                                      link.relationship_type === 'SUPPORTING'
                                        ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                        : 'bg-rose-50 text-rose-700 border-rose-200'
                                    }`}
                                  >
                                    <span>
                                      {link.relationship_type[0]}: {link.evidence?.title || `#${link.evidence_id}`}
                                    </span>
                                    <button
                                      onClick={() => handleUnlinkEvidence(cause.id, link.evidence_id)}
                                      className="text-slate-400 hover:text-rose-600 ml-0.5"
                                    >
                                      <X className="w-2 h-2" />
                                    </button>
                                  </span>
                                ))}
                              </div>
                            )}

                            {/* Status and Actions Bar */}
                            <div className="flex items-center justify-between gap-1 pt-1.5 border-t border-slate-100 flex-wrap">
                              <Select
                                value={cause.status}
                                onChange={(e) => handleStatusChange(cause, e.target.value)}
                                className="py-0.5 text-[10px] w-auto"
                              >
                                <option value="HYPOTHESIS">HYPOTHESIS</option>
                                <option value="VERIFIED">VERIFIED</option>
                                <option value="RULED_OUT">RULED OUT</option>
                              </Select>

                              <div className="flex items-center gap-1">
                                <button
                                  onClick={() => handleOpenLinkModal(cause.id)}
                                  className="p-1 text-slate-500 hover:text-blue-600 hover:bg-blue-50 rounded text-[10px] flex items-center gap-0.5 transition"
                                  title="Link Evidence"
                                >
                                  <Link2 className="w-3 h-3" />
                                </button>

                                {!isPromoted ? (
                                  <button
                                    onClick={() => handlePromoteToRootCause(cause)}
                                    className="px-1.5 py-0.5 text-[10px] font-semibold bg-indigo-50 text-indigo-700 hover:bg-indigo-100 rounded border border-indigo-200 flex items-center gap-0.5 transition"
                                    title="Promote to formal Root Cause proposal"
                                  >
                                    <ArrowUpRight className="w-3 h-3" />
                                    <span>Promote</span>
                                  </button>
                                ) : (
                                  <span className="text-[9px] font-bold px-1 py-0.5 bg-purple-50 text-purple-700 rounded border border-purple-200">
                                    Promoted
                                  </span>
                                )}
                              </div>
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>

      {/* Add Cause Modal */}
      {activeCategoryModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 dark:bg-black/80 backdrop-blur-xs p-4 animate-fade-in">
          <div className="bg-white dark:bg-black rounded-2xl border border-slate-200 dark:border-zinc-800 shadow-xl max-w-md w-full p-6 space-y-4">
            <h4 className="font-bold text-sm text-slate-900 dark:text-zinc-100 flex items-center gap-2">
              <Plus className="w-4 h-4 text-indigo-600 dark:text-cyan-400" />
              Add Hypothesis to {categories.find((c) => c.id === activeCategoryModal)?.label}
            </h4>

            <div className="space-y-3">
              <Input
                label="Cause Hypothesis Statement"
                placeholder="e.g. Seal face scoring allowed lubricant migration..."
                value={newCauseText}
                onChange={(e) => setNewCauseText(e.target.value)}
                required
              />

              <Textarea
                label="Rationale / Mechanism"
                rows={2}
                placeholder="Why is this factor technically plausible?"
                value={newRationale}
                onChange={(e) => setNewRationale(e.target.value)}
              />

              <Input
                label="Evidence Citation (Optional)"
                placeholder="e.g. Maintenance logbook, seal inspection report..."
                value={newEvidence}
                onChange={(e) => setNewEvidence(e.target.value)}
              />

              <div className="pt-3 flex justify-end gap-2 border-t border-slate-100 dark:border-zinc-800">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setActiveCategoryModal(null)}
                >
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => handleAddCause(activeCategoryModal)}
                  disabled={!newCauseText.trim()}
                >
                  Add Hypothesis
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Link Evidence Modal */}
      {linkingCauseId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 dark:bg-black/80 backdrop-blur-xs p-4 animate-fade-in">
          <div className="bg-white dark:bg-black rounded-2xl border border-slate-200 dark:border-zinc-800 shadow-xl max-w-md w-full p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="font-bold text-sm text-slate-900 dark:text-zinc-100 flex items-center gap-2">
                <Link2 className="w-4 h-4 text-indigo-600 dark:text-cyan-400" />
                Link Evidence to Fishbone Cause
              </h4>
              <button
                onClick={() => setLinkingCauseId(null)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-zinc-300 p-1 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateEvidenceLink} className="space-y-3">
              <Select
                label="Select Evidence from Dossier"
                value={selectedEvidenceId}
                onChange={(e) => setSelectedEvidenceId(e.target.value)}
                required
              >
                {dossierEvidences.map((ev) => (
                  <option key={ev.id} value={ev.id}>
                    #{ev.id} - {ev.title} ({ev.evidence_type}) {ev.is_verified ? '✓ Verified' : ''}
                  </option>
                ))}
              </Select>
              {dossierEvidences.length === 0 && (
                <p className="text-[11px] text-amber-600">
                  No active evidence records available in this investigation dossier.
                </p>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Relationship Type
                </label>
                <div className="flex gap-4">
                  <label className="flex items-center gap-1.5 text-xs text-slate-700 cursor-pointer">
                    <input
                      type="radio"
                      name="fb_rel_type"
                      value="SUPPORTING"
                      checked={relationshipType === 'SUPPORTING'}
                      onChange={() => setRelationshipType('SUPPORTING')}
                    />
                    <span className="font-semibold text-emerald-700">Supporting</span>
                  </label>
                  <label className="flex items-center gap-1.5 text-xs text-slate-700 cursor-pointer">
                    <input
                      type="radio"
                      name="fb_rel_type"
                      value="CONTRADICTORY"
                      checked={relationshipType === 'CONTRADICTORY'}
                      onChange={() => setRelationshipType('CONTRADICTORY')}
                    />
                    <span className="font-semibold text-rose-700">Contradictory</span>
                  </label>
                </div>
              </div>

              <Textarea
                label="Relevance Explanation (Optional)"
                rows={2}
                value={linkExplanation}
                onChange={(e) => setLinkExplanation(e.target.value)}
                placeholder="Explain how this record relates to the hypothesis..."
              />

              <div className="pt-3 flex justify-end gap-2 border-t border-slate-100">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setLinkingCauseId(null)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  size="sm"
                  disabled={isSubmittingLink || !selectedEvidenceId}
                  loading={isSubmittingLink}
                >
                  Link Evidence
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </Card>
  );
};

export default FishboneSection;
