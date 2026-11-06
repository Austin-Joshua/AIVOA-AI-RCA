import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import api from '../services/api';
import { fetchInvestigationById } from './investigationSlice';

export const parseIncidentFile = createAsyncThunk(
  'copilot/parseIncidentFile',
  async (payload, { rejectWithValue }) => {
    try {
      const file = payload?.file || payload;
      const investigationId = payload?.investigationId;
      const formData = new FormData();
      formData.append('file', file);
      if (investigationId) {
        formData.append('investigation_id', investigationId);
      }
      const res = await api.post('/intake/parse-file', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to parse incident file');
    }
  }
);

export const parseIncidentText = createAsyncThunk(
  'copilot/parseIncidentText',
  async ({ content, isEmail, investigationId }, { rejectWithValue }) => {
    try {
      const res = await api.post('/intake/parse-text', { 
        content, 
        is_email: isEmail,
        investigation_id: investigationId
      });
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to parse incident text');
    }
  }
);

export const applyExtractionToForm = createAsyncThunk(
  'copilot/applyExtractionToForm',
  async ({ investigationId, extractionData, reviewedFields }, { dispatch, rejectWithValue }) => {
    try {
      const res = await api.post('/intake/apply-to-investigation', {
        investigation_id: investigationId,
        apply_deviation: true,
        apply_evidence: true,
        reviewed_fields: reviewedFields || extractionData.extracted_fields,
        custom_overrides: {
          deviation: extractionData.deviation,
          extracted_findings: extractionData.extracted_findings,
          missing_information: extractionData.missing_information,
          raw_document_preview: extractionData.raw_document_preview,
          source_metadata: extractionData.source_metadata,
        },
        evidence_metadata: extractionData.source_metadata,
      });
      dispatch(fetchInvestigationById(investigationId));
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to apply extraction to form');
    }
  }
);

export const sendCopilotMessage = createAsyncThunk(
  'copilot/sendCopilotMessage',
  async ({ investigationId, message, stage }, { rejectWithValue }) => {
    try {
      const res = await api.post('/copilot/chat', {
        investigation_id: investigationId,
        message,
        context_stage: stage,
      });
      return {
        userMessage: message,
        aiResponse: res.data.response,
        suggestedActions: res.data.suggested_actions,
      };
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to get Copilot response');
    }
  }
);

export const generateRcaPackage = createAsyncThunk(
  'copilot/generateRcaPackage',
  async ({ investigationId, userContext }, { rejectWithValue }) => {
    try {
      const res = await api.post('/copilot/generate-rca', {
        investigation_id: investigationId,
        user_context: userContext,
      });
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to generate RCA package');
    }
  }
);

export const applyRcaProposal = createAsyncThunk(
  'copilot/applyRcaProposal',
  async ({ investigationId, rcaData }, { dispatch, rejectWithValue }) => {
    try {
      const res = await api.post('/copilot/apply-rca-to-investigation', {
        investigation_id: investigationId,
        rca_data: rcaData,
      });
      dispatch(fetchInvestigationById(investigationId));
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to apply RCA proposal');
    }
  }
);

export const applyRcaItem = createAsyncThunk(
  'copilot/applyRcaItem',
  async ({ investigationId, itemType, itemData }, { dispatch, rejectWithValue }) => {
    try {
      const res = await api.post('/copilot/apply-rca-item', {
        investigation_id: investigationId,
        item_type: itemType,
        item_data: itemData,
      });
      dispatch(fetchInvestigationById(investigationId));
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to apply RCA item');
    }
  }
);

export const converseWithCopilot = createAsyncThunk(
  'copilot/converseWithCopilot',
  async ({ investigationId, message, attachedDocumentId, currentDraftFields }, { rejectWithValue }) => {
    try {
      const res = await api.post('/copilot/converse', {
        investigation_id: investigationId,
        message,
        attached_document_id: attachedDocumentId || null,
        current_draft_fields: currentDraftFields || null,
      });
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to converse with Copilot');
    }
  }
);

export const fetchCopilotMessages = createAsyncThunk(
  'copilot/fetchCopilotMessages',
  async (investigationId, { rejectWithValue }) => {
    try {
      const res = await api.get(`/copilot/investigations/${investigationId}/messages`);
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to load conversation history');
    }
  }
);

const initialState = {
  intakeExtraction: null,
  isExtracting: false,
  extractionError: null,
  
  rcaProposal: null,
  isGeneratingRca: false,
  rcaError: null,
  
  chatMessages: [
    {
      role: 'assistant',
      content: 'Welcome to AIVOA.AI RCA Intelligence Copilot. Paste an incident report, drop a deviation PDF/email, or ask any cGMP investigation questions. I will automatically extract technical facts, assess risk, and populate the investigation dossier.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      suggestedActions: ['Load Paracetamol Demo Scenario', 'Ask about 5-Whys methodology', 'Explain ICH Q9 Risk Matrix'],
    },
  ],
  isChatting: false,
  
  // Real-time chat-driven draft patches for form fields (field_key -> FieldPatch)
  draftPatches: {},
  // AI Risk Assessment Card
  riskAssessment: null,
  // Detected missing information items
  missingGaps: [],
  // Field to temporarily highlight
  highlightedFieldKey: null,
  
  activeTab: 'chat', // 'chat', 'intake', 'gaps', 'engine', 'workflow'
};

const copilotSlice = createSlice({
  name: 'copilot',
  initialState,
  reducers: {
    setActiveTab: (state, action) => {
      state.activeTab = action.payload;
    },
    clearExtraction: (state) => {
      state.intakeExtraction = null;
      state.extractionError = null;
    },
    clearRcaProposal: (state) => {
      state.rcaProposal = null;
      state.rcaError = null;
    },
    addUserMessage: (state, action) => {
      state.chatMessages.push({
        role: 'user',
        content: action.payload,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      });
    },
    updateExtractedField: (state, action) => {
      const { field_name, value } = action.payload;
      if (state.intakeExtraction && state.intakeExtraction.extracted_fields) {
        const field = state.intakeExtraction.extracted_fields.find(f => f.field_name === field_name);
        if (field) {
          if (field.original_value === undefined || field.original_value === null) {
            field.original_value = field.value;
          }
          field.value = value;
          field.user_edited = true;
        }
      }
    },
    toggleFieldAccepted: (state, action) => {
      const field_name = action.payload;
      if (state.intakeExtraction && state.intakeExtraction.extracted_fields) {
        const field = state.intakeExtraction.extracted_fields.find(f => f.field_name === field_name);
        if (field) {
          field.is_accepted = !field.is_accepted;
        }
      }
    },
    acceptAllFields: (state) => {
      if (state.intakeExtraction && state.intakeExtraction.extracted_fields) {
        state.intakeExtraction.extracted_fields.forEach(f => {
          if (f.value) {
            f.is_accepted = true;
          }
        });
      }
    },
    rejectAllFields: (state) => {
      if (state.intakeExtraction && state.intakeExtraction.extracted_fields) {
        state.intakeExtraction.extracted_fields.forEach(f => {
          f.is_accepted = false;
        });
      }
    },
    acceptAllSourceFacts: (state) => {
      if (state.intakeExtraction && state.intakeExtraction.extracted_fields) {
        state.intakeExtraction.extracted_fields.forEach(f => {
          if (f.status === 'SOURCE_FACT' && f.value) {
            f.is_accepted = true;
          }
        });
      }
    },
    setDraftPatch: (state, action) => {
      const { field_key, value, status, reason, user_attributed } = action.payload;
      if (field_key) {
        state.draftPatches[field_key] = {
          field_key,
          label: field_key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase()),
          value,
          status: status || 'USER_CORRECTION',
          reason: reason || 'User manual edit',
          user_attributed,
        };
      }
    },
    setHighlightedFieldKey: (state, action) => {
      state.highlightedFieldKey = action.payload;
    },
    clearDraftPatches: (state) => {
      state.draftPatches = {};
      state.riskAssessment = null;
      state.missingGaps = [];
    },
  },
  extraReducers: (builder) => {
    builder
      // parseIncidentFile
      .addCase(parseIncidentFile.pending, (state) => {
        state.isExtracting = true;
        state.extractionError = null;
      })
      .addCase(parseIncidentFile.fulfilled, (state, action) => {
        state.isExtracting = false;
        state.intakeExtraction = action.payload;
      })
      .addCase(parseIncidentFile.rejected, (state, action) => {
        state.isExtracting = false;
        state.extractionError = action.payload;
      })

      // parseIncidentText
      .addCase(parseIncidentText.pending, (state) => {
        state.isExtracting = true;
        state.extractionError = null;
      })
      .addCase(parseIncidentText.fulfilled, (state, action) => {
        state.isExtracting = false;
        state.intakeExtraction = action.payload;
      })
      .addCase(parseIncidentText.rejected, (state, action) => {
        state.isExtracting = false;
        state.extractionError = action.payload;
      })

      // sendCopilotMessage
      .addCase(sendCopilotMessage.pending, (state) => {
        state.isChatting = true;
      })
      .addCase(sendCopilotMessage.fulfilled, (state, action) => {
        state.isChatting = false;
        state.chatMessages.push({
          role: 'assistant',
          content: action.payload.aiResponse,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          suggestedActions: action.payload.suggestedActions || [],
        });
      })
      .addCase(sendCopilotMessage.rejected, (state, action) => {
        state.isChatting = false;
        state.chatMessages.push({
          role: 'assistant',
          content: `Error: ${action.payload}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        });
      })

      // generateRcaPackage
      .addCase(generateRcaPackage.pending, (state) => {
        state.isGeneratingRca = true;
        state.rcaError = null;
      })
      .addCase(generateRcaPackage.fulfilled, (state, action) => {
        state.isGeneratingRca = false;
        state.rcaProposal = action.payload;
      })
      .addCase(generateRcaPackage.rejected, (state, action) => {
        state.isGeneratingRca = false;
        state.rcaError = action.payload;
      })

      // converseWithCopilot
      .addCase(converseWithCopilot.pending, (state) => {
        state.isChatting = true;
      })
      .addCase(converseWithCopilot.fulfilled, (state, action) => {
        state.isChatting = false;
        const payload = action.payload;
        state.chatMessages.push({
          role: 'assistant',
          content: payload.reply_text,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          classification: payload.classification,
          fieldPatches: payload.field_patches || [],
          riskAssessment: payload.risk_assessment,
          missingFields: payload.missing_fields || [],
          suggestedActions: payload.suggested_actions || [],
        });

        if (payload.field_patches && payload.field_patches.length > 0) {
          payload.field_patches.forEach((patch) => {
            if (patch.field_key) {
              state.draftPatches[patch.field_key] = patch;
            }
          });
        }
        if (payload.risk_assessment) {
          state.riskAssessment = payload.risk_assessment;
        }
        if (payload.missing_fields && payload.missing_fields.length > 0) {
          state.missingGaps = payload.missing_fields;
        }
      })
      .addCase(converseWithCopilot.rejected, (state, action) => {
        state.isChatting = false;
        state.chatMessages.push({
          role: 'assistant',
          content: `Error: ${action.payload}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        });
      })

      // fetchCopilotMessages
      .addCase(fetchCopilotMessages.fulfilled, (state, action) => {
        const backendMsgs = action.payload;
        state.draftPatches = {};
        state.riskAssessment = null;
        state.missingGaps = [];
        if (Array.isArray(backendMsgs) && backendMsgs.length > 0) {
          state.chatMessages = backendMsgs.map((m) => {
            let extra = {};
            try {
              if (m.extra_data) extra = JSON.parse(m.extra_data);
            } catch {
              // ignore invalid json
            }
            if (extra.field_patches && Array.isArray(extra.field_patches)) {
              extra.field_patches.forEach((p) => {
                if (p.field_key) state.draftPatches[p.field_key] = p;
              });
            }
            if (extra.risk_assessment) {
              state.riskAssessment = extra.risk_assessment;
            }
            if (extra.missing_fields && Array.isArray(extra.missing_fields)) {
              state.missingGaps = extra.missing_fields;
            }
            return {
              id: m.id,
              role: m.role,
              content: m.content,
              timestamp: new Date(m.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
              classification: extra.classification || m.message_type,
              fieldPatches: extra.field_patches || [],
              riskAssessment: extra.risk_assessment || null,
              missingFields: extra.missing_fields || [],
              suggestedActions: extra.suggested_actions || [],
            };
          });
        } else {
          state.chatMessages = [];
        }
      });
  },
});

export const { 
  setActiveTab, 
  clearExtraction, 
  clearRcaProposal, 
  addUserMessage,
  updateExtractedField,
  toggleFieldAccepted,
  acceptAllFields,
  rejectAllFields,
  acceptAllSourceFacts,
  setDraftPatch,
  setHighlightedFieldKey,
  clearDraftPatches
} = copilotSlice.actions;
export default copilotSlice.reducer;

