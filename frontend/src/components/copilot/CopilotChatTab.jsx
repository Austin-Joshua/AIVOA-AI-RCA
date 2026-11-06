import React, { useState, useEffect, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  Send,
  Bot,
  User,
  Sparkles,
  Paperclip,
  ShieldAlert,
  AlertTriangle,
  FileText,
  Flame,
} from 'lucide-react';
import {
  converseWithCopilot,
  fetchCopilotMessages,
  addUserMessage,
  setHighlightedFieldKey,
  setActiveTab,
  generateRcaPackage,
} from '../../store/copilotSlice';
import { saveInvestigationDeviation } from '../../store/investigationSlice';
import { setNotification } from '../../store/uiSlice';
import api from '../../services/api';

export const CopilotChatTab = () => {
  const dispatch = useDispatch();
  const currentInvestigation = useSelector((state) => state.investigation.currentInvestigation);
  const { chatMessages, isChatting } = useSelector((state) => state.copilot);

  const [inputMessage, setInputMessage] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  // Load persisted chat history for this investigation
  useEffect(() => {
    if (currentInvestigation?.id) {
      dispatch(fetchCopilotMessages(currentInvestigation.id));
    }
  }, [dispatch, currentInvestigation?.id]);

  // Auto-scroll on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, isChatting]);

  const paracetamolSample = `Subject: URGENT: Manufacturing Deviation DEV-2026-104 in Batch API-2026-104 (Crystallizer CR-104)
From: shift.lead@pharma-manufacturing.com
Date: Wed, 05 Nov 2026 09:30:00 +0000
To: qa.investigations@pharma-manufacturing.com

Dear Quality Assurance Team,

We are issuing an urgent deviation notification (Deviation Reference: DEV-2026-104) for Batch API-2026-104 of Paracetamol API in production block 2.
During the crystallization cooling cycle on Reactor CR-104, the process temperature spiked to 86°C for 18 minutes, exceeding the validated operating limit of 75-80°C. Cooling control valve CV-104 failed to stroke open past 15% due to suspected pneumatic air supply pressure loss. Target cooling setpoint was 78.0°C.

Immediate containment:
- Batch API-2026-104 quarantined in mother liquor receiver tank.
- SAP ERP QA Hold placed. Red warning tags on CR-104.`;

  const handleSend = (text, attachedDocId = null) => {
    const msg = text !== undefined ? text : inputMessage;
    if (!msg.trim() && !attachedDocId) return;
    if (!currentInvestigation) return;

    // Idempotency check: guard against repeated incident source submissions
    if (msg.trim().startsWith('Subject: URGENT: Manufacturing Deviation')) {
      const alreadySent = chatMessages.some(
        (m) => m.role === 'user' && m.content.includes('Batch API-2026-104')
      );
      if (alreadySent) {
        dispatch(
          setNotification({
            type: 'warning',
            message: 'Paracetamol incident report already ingested. You can type field corrections or click Commit Form.',
          })
        );
        setInputMessage('');
        return;
      }
    }

    dispatch(addUserMessage(msg));
    dispatch(
      converseWithCopilot({
        investigationId: currentInvestigation.id,
        message: msg,
        attachedDocumentId: attachedDocId,
        currentDraftFields: currentInvestigation.deviation || {},
      })
    );
    setInputMessage('');
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file || !currentInvestigation) return;

    setIsUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await api.post(`/investigations/${currentInvestigation.id}/evidences/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const evidence = res.data;
      handleSend(`Attached document: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`, evidence.id);
    } catch (err) {
      dispatch(
        setNotification({
          type: 'error',
          message: `Failed to upload ${file.name}: ${err.response?.data?.detail || err.message}`,
        })
      );
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleActionClick = (action) => {
    if (
      action.includes('5-Whys') ||
      action.includes('5 Whys') ||
      action.includes('Fishbone') ||
      action.includes('6M') ||
      action.includes('RCA Engine') ||
      action.includes('CAPA')
    ) {
      dispatch(setActiveTab('engine'));
      if (currentInvestigation?.id) {
        dispatch(generateRcaPackage({ investigationId: currentInvestigation.id }));
      }
    } else if (action.includes('Commit') || action.includes('Save')) {
      if (currentInvestigation?.deviation) {
        dispatch(
          saveInvestigationDeviation({
            investigationId: currentInvestigation.id,
            deviationData: currentInvestigation.deviation,
          })
        );
      }
    } else if (action.includes('Gaps') || action.includes('Evidence Gaps')) {
      dispatch(setActiveTab('gaps'));
    } else {
      handleSend(action);
    }
  };

  return (
    <div className="flex flex-col h-full min-h-0 font-sans">
      {/* Dev Quick Loader / Scenario Bar */}
      <div className="shrink-0 flex items-center justify-between pb-2 mb-2 border-b border-slate-200 dark:border-slate-800 text-xs">
        <span className="font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider text-[10px] font-mono">
          Copilot Assistant
        </span>
        <button
          onClick={() => setInputMessage(paracetamolSample)}
          disabled={isChatting}
          className={`skeuo-btn-secondary flex items-center gap-1.5 text-[11px] font-bold px-2.5 py-1 rounded-xl transition cursor-pointer ${
            isChatting ? 'opacity-50 cursor-not-allowed' : ''
          }`}
          title="Paste sample Paracetamol deviation into composer"
        >
          <Flame className="w-3.5 h-3.5 text-amber-500" />
          <span>Load Paracetamol Scenario</span>
        </button>
      </div>

      {/* Message Stream */}
      <div className="flex-1 min-h-0 overflow-y-auto space-y-3.5 pr-1 scrollbar-thin">
        {chatMessages.map((msg, idx) => {
          const isUser = msg.role === 'user';
          return (
            <div
              key={idx}
              className={`flex items-start gap-2.5 ${isUser ? 'flex-row-reverse' : ''}`}
            >
              <div
                className={`w-7 h-7 rounded-xl flex items-center justify-center shrink-0 shadow-sm ${
                  isUser
                    ? 'bg-blue-700 text-white'
                    : 'bg-gradient-to-tr from-blue-900 via-blue-700 to-indigo-800 text-amber-300 shadow-blue-900/25 border border-blue-600/40'
                }`}
              >
                {isUser ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
              </div>

              <div
                className={`max-w-[88%] rounded-2xl p-3.5 text-xs leading-relaxed shadow-sm transition-all ${
                  isUser
                    ? 'bg-gradient-to-b from-blue-700 to-blue-800 text-white rounded-tr-none border border-blue-600/50 shadow-md'
                    : 'skeuo-card text-slate-800 dark:text-slate-100 rounded-tl-none border border-slate-200/90 dark:border-[#1e2236]'
                }`}
              >
                {/* Main message text */}
                <p className="whitespace-pre-wrap font-medium">{msg.content}</p>

                {/* Structured Extraction: Field Patches Grid */}
                {!isUser && msg.fieldPatches && msg.fieldPatches.length > 0 && (
                  <div className="mt-3 pt-2.5 border-t border-slate-200/80 dark:border-[#1e2236]">
                    <span className="text-[10px] font-extrabold text-slate-500 dark:text-slate-400 uppercase tracking-wider flex items-center gap-1.5 mb-2 font-mono">
                      <FileText className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
                      Extracted Technical Parameters ({msg.fieldPatches.length})
                    </span>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {msg.fieldPatches.slice(0, 6).map((patch, pIdx) => (
                        <div
                          key={pIdx}
                          onClick={() => dispatch(setHighlightedFieldKey(patch.field_key))}
                          className="skeuo-well dark:bg-[#080a14] p-2 rounded-xl text-[11px] cursor-pointer hover:border-blue-500 transition border border-slate-200 dark:border-[#1e2236]"
                        >
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-slate-800 dark:text-slate-200 truncate">{patch.label}</span>
                            <span
                              className={`text-[9px] px-1.5 py-0.2 rounded font-extrabold font-mono ${
                                patch.status === 'USER_CORRECTION'
                                  ? 'bg-blue-100 dark:bg-blue-950 text-blue-800 dark:text-blue-300 border border-blue-300 dark:border-blue-800'
                                  : patch.status === 'SOURCE_FACT'
                                  ? 'bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800'
                                  : 'bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-800'
                              }`}
                            >
                              {patch.status === 'USER_CORRECTION'
                                ? 'User Edit'
                                : patch.status === 'SOURCE_FACT'
                                ? 'Source Fact'
                                : 'AI Inference'}
                            </span>
                          </div>
                          <p className="font-mono text-slate-900 dark:text-slate-100 truncate mt-1 font-extrabold">
                            {String(patch.value || '--')}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Risk Assessment Card */}
                {!isUser && msg.riskAssessment && (
                  <div className="mt-2.5 p-3 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900/50 text-[11px]">
                    <div className="flex items-center justify-between font-bold text-amber-900 dark:text-amber-200 mb-1">
                      <span className="flex items-center gap-1.5 uppercase font-mono text-[10px]">
                        <ShieldAlert className="w-3.5 h-3.5 text-amber-600" /> AI Risk Classification:
                      </span>
                      <span className="px-2 py-0.5 rounded-full bg-amber-200 dark:bg-amber-900 text-amber-950 dark:text-amber-200 text-[10px] font-bold">
                        {msg.riskAssessment.suggested_severity}
                      </span>
                    </div>
                    <p className="text-amber-950 dark:text-amber-300 leading-relaxed font-medium">
                      {msg.riskAssessment.rationale}
                    </p>
                    <div className="mt-1.5 pt-1.5 border-t border-amber-200/60 dark:border-amber-800/60 text-[10px] text-amber-900 dark:text-amber-300 font-medium">
                      <strong>Immediate Triage:</strong> {msg.riskAssessment.suggested_next_action}
                    </div>
                  </div>
                )}

                {/* Missing Fields Tags */}
                {!isUser && msg.missingFields && msg.missingFields.length > 0 && (
                  <div className="mt-2.5 pt-2 border-t border-slate-200 dark:border-zinc-800">
                    <span className="text-[10px] font-bold text-rose-600 dark:text-rose-400 uppercase tracking-wider flex items-center gap-1 mb-1.5 font-mono">
                      <AlertTriangle className="w-3 h-3 text-rose-500" /> Identified Evidence Gaps:
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {msg.missingFields.map((gap, gIdx) => (
                        <span
                          key={gIdx}
                          className="text-[10px] bg-rose-50 dark:bg-rose-950/50 border border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-300 px-2.5 py-0.5 rounded-lg font-medium"
                        >
                          {gap.question || gap.category}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Suggested Actions Chips */}
                {!isUser && msg.suggestedActions?.length > 0 && (
                  <div className="mt-3 pt-2 border-t border-slate-200 dark:border-zinc-800">
                    <span className="text-[10px] font-bold text-slate-500 dark:text-zinc-400 uppercase tracking-wider block mb-1.5 font-mono">
                      Suggested Actions:
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {msg.suggestedActions.map((action, aIdx) => (
                        <button
                          key={aIdx}
                          onClick={() => handleActionClick(action)}
                          className="skeuo-btn-secondary text-[11px] font-extrabold px-3 py-1 rounded-xl transition cursor-pointer text-blue-700 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
                        >
                          • {action}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {/* Timestamp */}
                <span
                  className={`text-[9px] font-mono block mt-2 text-right ${
                    isUser ? 'text-blue-200' : 'text-slate-400 dark:text-slate-500'
                  }`}
                >
                  {msg.timestamp}
                </span>
              </div>
            </div>
          );
        })}

        {isChatting && (
          <div className="flex items-center gap-2 text-xs text-slate-600 dark:text-slate-300 italic p-3 bg-slate-50 dark:bg-[#0c0e1a] rounded-xl border border-slate-200 dark:border-[#1e2236]">
            <Sparkles className="w-4 h-4 text-amber-500 animate-spin shrink-0" />
            <span className="font-semibold">Copilot is analyzing source text &amp; mapping deviation fields...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Composer & Document Drop */}
      <div className="shrink-0 pt-3 border-t border-slate-200 dark:border-[#1e2236] bg-white dark:bg-[#060814]">
        <div className="flex items-center gap-2 mb-2">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            accept=".pdf,.txt,.eml,.json"
            className="hidden"
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isUploading || isChatting}
            className="skeuo-btn-secondary p-1.5 px-2.5 rounded-xl transition flex items-center gap-1.5 text-[11px] font-semibold cursor-pointer"
            title="Attach deviation PDF, email or text file"
          >
            <Paperclip className="w-3.5 h-3.5 text-slate-500 dark:text-zinc-400" />
            <span className="hidden sm:inline">Attach File</span>
          </button>
          <span className="text-[10px] text-slate-400 dark:text-zinc-500 font-medium">
            Paste report or say: "sorry, batch is API-2026-104"
          </span>
        </div>

        <div className="flex gap-2">
          <div className="flex-1 skeuo-well dark:bg-black rounded-xl overflow-hidden">
            <textarea
              rows={2}
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              placeholder="Type incident report, correction statement, or ask Copilot..."
              className="w-full text-xs p-3 bg-transparent text-slate-900 dark:text-zinc-100 placeholder:text-slate-400 dark:placeholder:text-zinc-600 focus:outline-none resize-none font-sans"
            />
          </div>
          <button
            onClick={() => handleSend()}
            disabled={!inputMessage.trim() || isChatting}
            className="skeuo-btn-primary px-4 py-2 rounded-xl transition flex flex-col items-center justify-center shrink-0 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed shadow-md"
            title="Send to Copilot"
          >
            <Send className="w-4 h-4" />
            <span className="text-[9px] mt-0.5 font-bold uppercase font-mono">Send</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default CopilotChatTab;
