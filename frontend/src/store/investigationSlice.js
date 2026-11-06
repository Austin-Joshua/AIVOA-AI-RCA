import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import api from '../services/api';
import { converseWithCopilot } from './copilotSlice';

// ==========================================
// Async Thunks
// ==========================================

export const fetchInvestigations = createAsyncThunk(
  'investigation/fetchInvestigations',
  async (_, { rejectWithValue }) => {
    try {
      const res = await api.get('/investigations/');
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to fetch investigations');
    }
  }
);

export const fetchInvestigationById = createAsyncThunk(
  'investigation/fetchInvestigationById',
  async (id, { rejectWithValue }) => {
    try {
      const res = await api.get(`/investigations/${id}`);
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to load investigation');
    }
  }
);

export const createInvestigation = createAsyncThunk(
  'investigation/createInvestigation',
  async (data, { rejectWithValue }) => {
    try {
      const res = await api.post('/investigations/', data);
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to create investigation');
    }
  }
);

export const seedParacetamolDemo = createAsyncThunk(
  'investigation/seedParacetamolDemo',
  async (_, { rejectWithValue }) => {
    try {
      const res = await api.post('/investigations/seed-demo-scenario');
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to seed demo scenario');
    }
  }
);

export const updateDeviation = createAsyncThunk(
  'investigation/updateDeviation',
  async ({ id, data }, { rejectWithValue }) => {
    try {
      const res = await api.put(`/deviations/${id}`, data);
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to update deviation');
    }
  }
);

export const verifyDeviation = createAsyncThunk(
  'investigation/verifyDeviation',
  async (deviationId, { rejectWithValue }) => {
    try {
      const res = await api.post(`/deviations/${deviationId}/verify`);
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to verify deviation');
    }
  }
);

export const saveInvestigationDeviation = createAsyncThunk(
  'investigation/saveInvestigationDeviation',
  async ({ investigationId, deviationData }, { dispatch, rejectWithValue }) => {
    try {
      const res = await api.post(`/deviations/?investigation_id=${investigationId}`, deviationData);
      dispatch(fetchInvestigationById(investigationId));
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to save deviation details');
    }
  }
);

// Evidence Management Thunks
export const uploadEvidence = createAsyncThunk(
  'investigation/uploadEvidence',
  async ({ investigationId, formData }, { dispatch, rejectWithValue }) => {
    try {
      const res = await api.post(`/investigations/${investigationId}/evidences/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      dispatch(fetchInvestigationById(investigationId));
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to upload evidence');
    }
  }
);

export const verifyEvidence = createAsyncThunk(
  'investigation/verifyEvidence',
  async ({ evidenceId, investigatorName, notes }, { rejectWithValue }) => {
    try {
      const res = await api.post(`/evidences/${evidenceId}/verify`, {
        investigator_name: investigatorName,
        verification_notes: notes,
      });
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to verify evidence');
    }
  }
);

export const deleteEvidence = createAsyncThunk(
  'investigation/deleteEvidence',
  async (evidenceId, { rejectWithValue }) => {
    try {
      await api.delete(`/evidences/${evidenceId}`);
      return evidenceId;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to delete evidence');
    }
  }
);

// Evidence Gap Thunks
export const fetchEvidenceGaps = createAsyncThunk(
  'investigation/fetchEvidenceGaps',
  async (investigationId, { rejectWithValue }) => {
    try {
      const res = await api.get(`/investigations/${investigationId}/evidence-gaps`);
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to fetch evidence gaps');
    }
  }
);

export const respondToEvidenceGap = createAsyncThunk(
  'investigation/respondToEvidenceGap',
  async ({ gapId, response, responderName }, { rejectWithValue }) => {
    try {
      const res = await api.post(`/evidence-gaps/${gapId}/respond`, {
        response,
        responder_name: responderName,
      });
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to record gap response');
    }
  }
);

export const resolveEvidenceGap = createAsyncThunk(
  'investigation/resolveEvidenceGap',
  async ({ gapId, resolverName, resolvingEvidenceId, resolutionNotes }, { rejectWithValue }) => {
    try {
      const res = await api.post(`/evidence-gaps/${gapId}/resolve`, {
        resolver_name: resolverName,
        resolving_evidence_id: resolvingEvidenceId,
        resolution_notes: resolutionNotes,
      });
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to resolve evidence gap');
    }
  }
);

// Root Cause Evidence Linking & Confirmation Thunks
export const linkRootCauseEvidence = createAsyncThunk(
  'investigation/linkRootCauseEvidence',
  async ({ rootCauseId, evidenceId, relationshipType, explanation }, { rejectWithValue }) => {
    try {
      const res = await api.post(`/root-causes/${rootCauseId}/evidence-links`, {
        evidence_id: evidenceId,
        relationship_type: relationshipType,
        relevance_explanation: explanation,
      });
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to link evidence');
    }
  }
);

export const unlinkRootCauseEvidence = createAsyncThunk(
  'investigation/unlinkRootCauseEvidence',
  async ({ rootCauseId, linkId, dispositionRationale, investigatorName }, { rejectWithValue }) => {
    try {
      const params = {};
      if (dispositionRationale) params.disposition_rationale = dispositionRationale;
      if (investigatorName) params.investigator_name = investigatorName;
      await api.delete(`/root-causes/${rootCauseId}/evidence-links/${linkId}`, { params });
      return { rootCauseId, linkId, dispositionRationale, dismissedBy: investigatorName };
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to unlink evidence');
    }
  }
);

export const confirmRootCause = createAsyncThunk(
  'investigation/confirmRootCause',
  async ({ rootCauseId, investigatorName, justification }, { rejectWithValue }) => {
    try {
      const res = await api.post(`/root-causes/${rootCauseId}/confirm`, {
        investigator_name: investigatorName,
        justification,
      });
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to confirm root cause');
    }
  }
);

export const rejectRootCause = createAsyncThunk(
  'investigation/rejectRootCause',
  async ({ rootCauseId, investigatorName, rationale }, { rejectWithValue }) => {
    try {
      const res = await api.post(`/root-causes/${rootCauseId}/reject`, {
        investigator_name: investigatorName,
        rationale,
      });
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to reject root cause');
    }
  }
);

// 5-Whys, Fishbone, CAPA, Approval
export const addFiveWhyStep = createAsyncThunk(
  'investigation/addFiveWhyStep',
  async ({ investigationId, data }, { rejectWithValue }) => {
    try {
      const res = await api.post(`/investigations/${investigationId}/five-whys`, data);
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to add Five Whys step');
    }
  }
);

export const updateFiveWhyStep = createAsyncThunk(
  'investigation/updateFiveWhyStep',
  async ({ stepId, data }, { rejectWithValue }) => {
    try {
      const res = await api.put(`/five-whys/${stepId}`, data);
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to update Five Whys step');
    }
  }
);

export const deleteFiveWhyStep = createAsyncThunk(
  'investigation/deleteFiveWhyStep',
  async (stepId, { rejectWithValue }) => {
    try {
      await api.delete(`/five-whys/${stepId}`);
      return stepId;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to delete Five Whys step');
    }
  }
);

export const addFishboneCause = createAsyncThunk(
  'investigation/addFishboneCause',
  async ({ investigationId, data }, { rejectWithValue }) => {
    try {
      const res = await api.post(`/investigations/${investigationId}/fishbone`, data);
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to add Fishbone cause');
    }
  }
);

export const updateFishboneCause = createAsyncThunk(
  'investigation/updateFishboneCause',
  async ({ causeId, data }, { rejectWithValue }) => {
    try {
      const res = await api.put(`/fishbone/${causeId}`, data);
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to update Fishbone cause');
    }
  }
);

export const deleteFishboneCause = createAsyncThunk(
  'investigation/deleteFishboneCause',
  async (causeId, { rejectWithValue }) => {
    try {
      await api.delete(`/fishbone/${causeId}`);
      return causeId;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to delete Fishbone cause');
    }
  }
);

// Evidence Linking for 5-Whys
export const linkFiveWhysEvidence = createAsyncThunk(
  'investigation/linkFiveWhysEvidence',
  async ({ stepId, evidenceId, relationshipType, explanation, confidence }, { rejectWithValue }) => {
    try {
      const res = await api.post(`/five-whys/${stepId}/evidence`, {
        evidence_id: evidenceId,
        relationship_type: relationshipType,
        relevance_explanation: explanation,
        confidence_rating: confidence || 'HIGH',
      });
      return { stepId, link: res.data };
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to link evidence to Five Whys step');
    }
  }
);

export const unlinkFiveWhysEvidence = createAsyncThunk(
  'investigation/unlinkFiveWhysEvidence',
  async ({ stepId, evidenceId }, { rejectWithValue }) => {
    try {
      await api.delete(`/five-whys/${stepId}/evidence/${evidenceId}`);
      return { stepId, evidenceId };
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to unlink evidence from Five Whys step');
    }
  }
);

export const verifyFiveWhysStep = createAsyncThunk(
  'investigation/verifyFiveWhysStep',
  async ({ stepId, isVerified, notes }, { rejectWithValue }) => {
    try {
      const res = await api.post(`/five-whys/${stepId}/verify`, {
        is_verified: isVerified,
        verification_notes: notes,
      });
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to verify Five Whys step');
    }
  }
);

// Evidence Linking & Promotion for Fishbone
export const linkFishboneEvidence = createAsyncThunk(
  'investigation/linkFishboneEvidence',
  async ({ causeId, evidenceId, relationshipType, explanation, confidence }, { rejectWithValue }) => {
    try {
      const res = await api.post(`/fishbone/${causeId}/evidence`, {
        evidence_id: evidenceId,
        relationship_type: relationshipType,
        relevance_explanation: explanation,
        confidence_rating: confidence || 'HIGH',
      });
      return { causeId, link: res.data };
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to link evidence to Fishbone cause');
    }
  }
);

export const unlinkFishboneEvidence = createAsyncThunk(
  'investigation/unlinkFishboneEvidence',
  async ({ causeId, evidenceId }, { rejectWithValue }) => {
    try {
      await api.delete(`/fishbone/${causeId}/evidence/${evidenceId}`);
      return { causeId, evidenceId };
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to unlink evidence from Fishbone cause');
    }
  }
);

export const verifyFishboneCause = createAsyncThunk(
  'investigation/verifyFishboneCause',
  async ({ causeId, status, notes }, { rejectWithValue }) => {
    try {
      const res = await api.post(`/fishbone/${causeId}/verify`, {
        status,
        verification_notes: notes,
      });
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to verify Fishbone cause');
    }
  }
);

export const promoteFishboneCause = createAsyncThunk(
  'investigation/promoteFishboneCause',
  async ({ causeId, isPrimary, category, notes }, { rejectWithValue }) => {
    try {
      const res = await api.post(`/fishbone/${causeId}/promote`, {
        is_primary: isPrimary || false,
        category,
        investigator_notes: notes,
      });
      return { causeId, rootCause: res.data };
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to promote Fishbone cause to Root Cause proposal');
    }
  }
);

// Root Cause CRUD
export const addRootCause = createAsyncThunk(
  'investigation/addRootCause',
  async ({ investigationId, data }, { rejectWithValue }) => {
    try {
      const res = await api.post(`/investigations/${investigationId}/root-causes`, data);
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to add Root Cause proposal');
    }
  }
);

export const updateRootCause = createAsyncThunk(
  'investigation/updateRootCause',
  async ({ rootCauseId, data }, { rejectWithValue }) => {
    try {
      const res = await api.put(`/root-causes/${rootCauseId}`, data);
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to update Root Cause proposal');
    }
  }
);

export const deleteRootCause = createAsyncThunk(
  'investigation/deleteRootCause',
  async (rootCauseId, { rejectWithValue }) => {
    try {
      await api.delete(`/root-causes/${rootCauseId}`);
      return rootCauseId;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to delete Root Cause proposal');
    }
  }
);

export const addCapaAction = createAsyncThunk(
  'investigation/addCapaAction',
  async ({ investigationId, data }, { rejectWithValue }) => {
    try {
      const res = await api.post(`/investigations/${investigationId}/capas`, data);
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to add CAPA action');
    }
  }
);

export const updateCapaAction = createAsyncThunk(
  'investigation/updateCapaAction',
  async ({ capaId, data }, { rejectWithValue }) => {
    try {
      const res = await api.put(`/capas/${capaId}`, data);
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to update CAPA action');
    }
  }
);

export const verifyCapaAction = createAsyncThunk(
  'investigation/verifyCapaAction',
  async (capaId, { rejectWithValue }) => {
    try {
      const res = await api.post(`/capas/${capaId}/verify`);
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to verify CAPA action');
    }
  }
);

export const approveCapaAction = createAsyncThunk(
  'investigation/approveCapaAction',
  async ({ capaId, approvalNotes }, { rejectWithValue }) => {
    try {
      const res = await api.post(`/capas/${capaId}/approve`, {
        approval_notes: approvalNotes || null,
      });
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to approve CAPA action');
    }
  }
);

export const completeCapaAction = createAsyncThunk(
  'investigation/completeCapaAction',
  async ({ capaId, completionNotes }, { rejectWithValue }) => {
    try {
      const res = await api.post(`/capas/${capaId}/complete`, {
        completion_notes: completionNotes,
      });
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to complete CAPA action');
    }
  }
);

export const verifyCapaEffectiveness = createAsyncThunk(
  'investigation/verifyCapaEffectiveness',
  async ({ capaId, verificationNotes }, { rejectWithValue }) => {
    try {
      const res = await api.post(`/capas/${capaId}/verify-effectiveness`, {
        verification_notes: verificationNotes || null,
      });
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to verify CAPA effectiveness');
    }
  }
);

export const deleteCapaAction = createAsyncThunk(
  'investigation/deleteCapaAction',
  async (capaId, { rejectWithValue }) => {
    try {
      await api.delete(`/capas/${capaId}`);
      return capaId;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to delete CAPA action');
    }
  }
);

export const approveInvestigation = createAsyncThunk(
  'investigation/approveInvestigation',
  async ({ investigationId, approverName, comments }, { rejectWithValue }) => {
    try {
      const res = await api.post(`/investigations/${investigationId}/approve`, null, {
        params: { approver_name: approverName, comments },
      });
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to approve investigation');
    }
  }
);

export const fetchAuditLogs = createAsyncThunk(
  'investigation/fetchAuditLogs',
  async (investigationId, { rejectWithValue }) => {
    try {
      const res = await api.get(`/investigations/${investigationId}/audit-logs`);
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to fetch audit logs');
    }
  }
);

// ==========================================
// Slice Definition
// ==========================================

const initialState = {
  investigationsList: [],
  currentInvestigation: null,
  activeStage: 'INTAKE', // INTAKE, INVESTIGATION, ROOT_CAUSE, CAPA, APPROVAL
  loading: false,
  error: null,
  auditLogs: [],
  evidenceGaps: [],
};

const investigationSlice = createSlice({
  name: 'investigation',
  initialState,
  reducers: {
    setActiveStage: (state, action) => {
      state.activeStage = action.payload;
    },
    setCurrentInvestigation: (state, action) => {
      state.currentInvestigation = action.payload;
      if (action.payload?.stage) {
        state.activeStage = action.payload.stage;
      }
    },
    clearError: (state) => {
      state.error = null;
    },
    updateDeviationFieldInMemory: (state, action) => {
      const { field, value } = action.payload;
      if (state.currentInvestigation) {
        if (!state.currentInvestigation.deviation) {
          state.currentInvestigation.deviation = {
            deviation_number: state.currentInvestigation.id
              ? `DEV-2026-${String(state.currentInvestigation.id).padStart(4, '0')}`
              : null,
            deviation_number_source: 'SYSTEM',
            deviation_type: 'MAJOR',
            severity: 'Major',
            batch_number: '',
            product_name: '',
            unit_operation: '',
            equipment_id: '',
            bpr_number: '',
            target_yield_kg: null,
            actual_yield_kg: null,
            description: '',
            immediate_containment: '',
            is_ai_populated: true,
            is_verified: false,
          };
        }
        state.currentInvestigation.deviation[field] = value;
      }
    },
  },
  extraReducers: (builder) => {
    builder
      // fetchInvestigations
      .addCase(fetchInvestigations.pending, (state) => {
        state.loading = true;
      })
      .addCase(fetchInvestigations.fulfilled, (state, action) => {
        state.loading = false;
        state.investigationsList = action.payload;
      })
      .addCase(fetchInvestigations.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })

      // fetchInvestigationById
      .addCase(fetchInvestigationById.pending, (state) => {
        state.loading = true;
      })
      .addCase(fetchInvestigationById.fulfilled, (state, action) => {
        state.loading = false;
        state.currentInvestigation = action.payload;
        if (action.payload?.evidence_gaps) {
          state.evidenceGaps = action.payload.evidence_gaps;
        }
        if (action.payload?.stage) {
          state.activeStage = action.payload.stage;
        }
      })
      .addCase(fetchInvestigationById.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })

      // createInvestigation
      .addCase(createInvestigation.fulfilled, (state, action) => {
        state.currentInvestigation = action.payload;
        state.investigationsList.unshift(action.payload);
        state.activeStage = 'INTAKE';
      })

      // seedParacetamolDemo
      .addCase(seedParacetamolDemo.fulfilled, (state, action) => {
        state.currentInvestigation = action.payload;
        state.investigationsList.unshift(action.payload);
        state.activeStage = 'INVESTIGATION';
      })

      // updateDeviation
      .addCase(updateDeviation.fulfilled, (state, action) => {
        if (state.currentInvestigation) {
          state.currentInvestigation.deviation = action.payload;
        }
      })

      // verifyDeviation
      .addCase(verifyDeviation.fulfilled, (state) => {
        if (state.currentInvestigation && state.currentInvestigation.deviation) {
          state.currentInvestigation.deviation.is_verified = true;
        }
      })

      // saveInvestigationDeviation
      .addCase(saveInvestigationDeviation.fulfilled, (state, action) => {
        if (state.currentInvestigation) {
          state.currentInvestigation.deviation = action.payload;
        }
      })

      // Reactive form update from Copilot converse
      .addCase(converseWithCopilot.fulfilled, (state, action) => {
        const patches = action.payload?.field_patches;
        if (!patches || !Array.isArray(patches) || patches.length === 0) return;
        if (!state.currentInvestigation) return;
        if (!state.currentInvestigation.deviation) {
          state.currentInvestigation.deviation = {
            deviation_number: state.currentInvestigation.id
              ? `DEV-2026-${String(state.currentInvestigation.id).padStart(4, '0')}`
              : null,
            deviation_number_source: 'SYSTEM',
            deviation_type: 'MAJOR',
            severity: action.payload?.risk_assessment?.suggested_severity || 'Major',
            batch_number: '',
            product_name: '',
            unit_operation: '',
            equipment_id: '',
            bpr_number: '',
            target_yield_kg: null,
            actual_yield_kg: null,
            description: '',
            immediate_containment: action.payload?.risk_assessment?.suggested_next_action || '',
            is_ai_populated: true,
            is_verified: false,
          };
        }
        patches.forEach((p) => {
          if (p && p.field_key && p.value !== undefined && p.value !== null) {
            state.currentInvestigation.deviation[p.field_key] = p.value;
            if (p.field_key === 'deviation_title' && p.value) {
              state.currentInvestigation.title = p.value;
            }
          }
        });
        state.currentInvestigation.deviation.is_ai_populated = true;
      })

      // verifyEvidence
      .addCase(verifyEvidence.fulfilled, (state, action) => {
        if (state.currentInvestigation && state.currentInvestigation.evidences) {
          const idx = state.currentInvestigation.evidences.findIndex((e) => e.id === action.payload.id);
          if (idx !== -1) {
            state.currentInvestigation.evidences[idx] = action.payload;
          }
        }
      })

      // deleteEvidence
      .addCase(deleteEvidence.fulfilled, (state, action) => {
        if (state.currentInvestigation && state.currentInvestigation.evidences) {
          state.currentInvestigation.evidences = state.currentInvestigation.evidences.filter(
            (e) => e.id !== action.payload
          );
        }
      })

      // fetchEvidenceGaps
      .addCase(fetchEvidenceGaps.fulfilled, (state, action) => {
        state.evidenceGaps = action.payload;
        if (state.currentInvestigation) {
          state.currentInvestigation.evidence_gaps = action.payload;
        }
      })

      // respondToEvidenceGap
      .addCase(respondToEvidenceGap.fulfilled, (state, action) => {
        const updateGap = (gaps) => {
          const idx = gaps.findIndex((g) => g.id === action.payload.id);
          if (idx !== -1) gaps[idx] = action.payload;
        };
        updateGap(state.evidenceGaps);
        if (state.currentInvestigation?.evidence_gaps) {
          updateGap(state.currentInvestigation.evidence_gaps);
        }
      })

      // resolveEvidenceGap
      .addCase(resolveEvidenceGap.fulfilled, (state, action) => {
        const updateGap = (gaps) => {
          const idx = gaps.findIndex((g) => g.id === action.payload.id);
          if (idx !== -1) gaps[idx] = action.payload;
        };
        updateGap(state.evidenceGaps);
        if (state.currentInvestigation?.evidence_gaps) {
          updateGap(state.currentInvestigation.evidence_gaps);
        }
      })

      // confirmRootCause & rejectRootCause
      .addCase(confirmRootCause.fulfilled, (state, action) => {
        if (state.currentInvestigation?.root_causes) {
          const idx = state.currentInvestigation.root_causes.findIndex((rc) => rc.id === action.payload.id);
          if (idx !== -1) state.currentInvestigation.root_causes[idx] = action.payload;
        }
      })
      .addCase(rejectRootCause.fulfilled, (state, action) => {
        if (state.currentInvestigation?.root_causes) {
          const idx = state.currentInvestigation.root_causes.findIndex((rc) => rc.id === action.payload.id);
          if (idx !== -1) state.currentInvestigation.root_causes[idx] = action.payload;
        }
      })

      // linkRootCauseEvidence
      .addCase(linkRootCauseEvidence.fulfilled, (state, action) => {
        if (state.currentInvestigation?.root_causes) {
          const rc = state.currentInvestigation.root_causes.find((r) => r.id === action.payload.root_cause_id);
          if (rc) {
            if (!rc.evidence_links) rc.evidence_links = [];
            rc.evidence_links.push(action.payload);
          }
        }
      })

      // unlinkRootCauseEvidence
      .addCase(unlinkRootCauseEvidence.fulfilled, (state, action) => {
        if (state.currentInvestigation?.root_causes) {
          const rc = state.currentInvestigation.root_causes.find((r) => r.id === action.payload.rootCauseId);
          if (rc && rc.evidence_links) {
            const removed = rc.evidence_links.find((l) => l.id === action.payload.linkId);
            rc.evidence_links = rc.evidence_links.filter((l) => l.id !== action.payload.linkId);
            if (action.payload.dispositionRationale && removed) {
              if (!rc.dispositions) rc.dispositions = [];
              rc.dispositions.push({
                id: Date.now(),
                root_cause_id: action.payload.rootCauseId,
                evidence_id: removed.evidence_id,
                relationship_type: 'CONTRADICTORY',
                disposition_rationale: action.payload.dispositionRationale,
                dismissed_by: action.payload.dismissedBy || 'Investigator',
                dismissed_at: new Date().toISOString(),
              });
            }
          }
        }
      })

      // addFiveWhyStep
      .addCase(addFiveWhyStep.fulfilled, (state, action) => {
        if (state.currentInvestigation) {
          state.currentInvestigation.five_whys.push(action.payload);
        }
      })

      // updateFiveWhyStep
      .addCase(updateFiveWhyStep.fulfilled, (state, action) => {
        if (state.currentInvestigation) {
          const idx = state.currentInvestigation.five_whys.findIndex((s) => s.id === action.payload.id);
          if (idx !== -1) {
            state.currentInvestigation.five_whys[idx] = action.payload;
          }
        }
      })

      // deleteFiveWhyStep
      .addCase(deleteFiveWhyStep.fulfilled, (state, action) => {
        if (state.currentInvestigation) {
          state.currentInvestigation.five_whys = state.currentInvestigation.five_whys.filter(
            (s) => s.id !== action.payload
          );
        }
      })

      // addFishboneCause
      .addCase(addFishboneCause.fulfilled, (state, action) => {
        if (state.currentInvestigation) {
          state.currentInvestigation.fishbone_causes.push(action.payload);
        }
      })

      // updateFishboneCause
      .addCase(updateFishboneCause.fulfilled, (state, action) => {
        if (state.currentInvestigation) {
          const idx = state.currentInvestigation.fishbone_causes.findIndex((c) => c.id === action.payload.id);
          if (idx !== -1) {
            state.currentInvestigation.fishbone_causes[idx] = action.payload;
          }
        }
      })

      // deleteFishboneCause
      .addCase(deleteFishboneCause.fulfilled, (state, action) => {
        if (state.currentInvestigation) {
          state.currentInvestigation.fishbone_causes = state.currentInvestigation.fishbone_causes.filter(
            (c) => c.id !== action.payload
          );
        }
      })

      // addCapaAction
      .addCase(addCapaAction.fulfilled, (state, action) => {
        if (state.currentInvestigation) {
          state.currentInvestigation.capa_actions.push(action.payload);
        }
      })

      // updateCapaAction
      .addCase(updateCapaAction.fulfilled, (state, action) => {
        if (state.currentInvestigation) {
          const idx = state.currentInvestigation.capa_actions.findIndex((c) => c.id === action.payload.id);
          if (idx !== -1) {
            state.currentInvestigation.capa_actions[idx] = action.payload;
          }
        }
      })

      // verifyCapaAction
      .addCase(verifyCapaAction.fulfilled, (state, action) => {
        if (state.currentInvestigation) {
          const idx = state.currentInvestigation.capa_actions.findIndex((c) => c.id === action.payload.id);
          if (idx !== -1) {
            state.currentInvestigation.capa_actions[idx] = action.payload;
          }
        }
      })

      // approveCapaAction
      .addCase(approveCapaAction.fulfilled, (state, action) => {
        if (state.currentInvestigation) {
          const idx = state.currentInvestigation.capa_actions.findIndex((c) => c.id === action.payload.id);
          if (idx !== -1) {
            state.currentInvestigation.capa_actions[idx] = action.payload;
          }
        }
      })

      // completeCapaAction
      .addCase(completeCapaAction.fulfilled, (state, action) => {
        if (state.currentInvestigation) {
          const idx = state.currentInvestigation.capa_actions.findIndex((c) => c.id === action.payload.id);
          if (idx !== -1) {
            state.currentInvestigation.capa_actions[idx] = action.payload;
          }
        }
      })

      // verifyCapaEffectiveness
      .addCase(verifyCapaEffectiveness.fulfilled, (state, action) => {
        if (state.currentInvestigation) {
          const idx = state.currentInvestigation.capa_actions.findIndex((c) => c.id === action.payload.id);
          if (idx !== -1) {
            state.currentInvestigation.capa_actions[idx] = action.payload;
          }
        }
      })

      // deleteCapaAction
      .addCase(deleteCapaAction.fulfilled, (state, action) => {
        if (state.currentInvestigation) {
          state.currentInvestigation.capa_actions = state.currentInvestigation.capa_actions.filter(
            (c) => c.id !== action.payload
          );
        }
      })

      // approveInvestigation
      .addCase(approveInvestigation.fulfilled, (state, action) => {
        state.currentInvestigation = action.payload;
      })

      // linkFiveWhysEvidence
      .addCase(linkFiveWhysEvidence.fulfilled, (state, action) => {
        if (state.currentInvestigation) {
          const step = state.currentInvestigation.five_whys?.find((s) => s.id === action.payload.stepId);
          if (step) {
            step.evidence_links = step.evidence_links || [];
            step.evidence_links.push(action.payload.link);
          }
        }
      })

      // unlinkFiveWhysEvidence
      .addCase(unlinkFiveWhysEvidence.fulfilled, (state, action) => {
        if (state.currentInvestigation) {
          const step = state.currentInvestigation.five_whys?.find((s) => s.id === action.payload.stepId);
          if (step && step.evidence_links) {
            step.evidence_links = step.evidence_links.filter((l) => l.evidence_id !== action.payload.evidenceId);
          }
        }
      })

      // verifyFiveWhysStep
      .addCase(verifyFiveWhysStep.fulfilled, (state, action) => {
        if (state.currentInvestigation) {
          const idx = state.currentInvestigation.five_whys?.findIndex((s) => s.id === action.payload.id);
          if (idx !== -1) {
            state.currentInvestigation.five_whys[idx] = action.payload;
          }
        }
      })

      // linkFishboneEvidence
      .addCase(linkFishboneEvidence.fulfilled, (state, action) => {
        if (state.currentInvestigation) {
          const cause = state.currentInvestigation.fishbone_causes?.find((c) => c.id === action.payload.causeId);
          if (cause) {
            cause.evidence_links = cause.evidence_links || [];
            cause.evidence_links.push(action.payload.link);
          }
        }
      })

      // unlinkFishboneEvidence
      .addCase(unlinkFishboneEvidence.fulfilled, (state, action) => {
        if (state.currentInvestigation) {
          const cause = state.currentInvestigation.fishbone_causes?.find((c) => c.id === action.payload.causeId);
          if (cause && cause.evidence_links) {
            cause.evidence_links = cause.evidence_links.filter((l) => l.evidence_id !== action.payload.evidenceId);
          }
        }
      })

      // verifyFishboneCause
      .addCase(verifyFishboneCause.fulfilled, (state, action) => {
        if (state.currentInvestigation) {
          const idx = state.currentInvestigation.fishbone_causes?.findIndex((c) => c.id === action.payload.id);
          if (idx !== -1) {
            state.currentInvestigation.fishbone_causes[idx] = action.payload;
          }
        }
      })

      // promoteFishboneCause
      .addCase(promoteFishboneCause.fulfilled, (state, action) => {
        if (state.currentInvestigation) {
          state.currentInvestigation.root_causes = state.currentInvestigation.root_causes || [];
          state.currentInvestigation.root_causes.push(action.payload.rootCause);
          const cause = state.currentInvestigation.fishbone_causes?.find((c) => c.id === action.payload.causeId);
          if (cause) {
            cause.promoted_to_root_cause_id = action.payload.rootCause.id;
          }
        }
      })

      // addRootCause
      .addCase(addRootCause.fulfilled, (state, action) => {
        if (state.currentInvestigation) {
          state.currentInvestigation.root_causes = state.currentInvestigation.root_causes || [];
          state.currentInvestigation.root_causes.push(action.payload);
        }
      })

      // updateRootCause
      .addCase(updateRootCause.fulfilled, (state, action) => {
        if (state.currentInvestigation) {
          const idx = state.currentInvestigation.root_causes?.findIndex((r) => r.id === action.payload.id);
          if (idx !== -1) {
            state.currentInvestigation.root_causes[idx] = action.payload;
          }
        }
      })

      // deleteRootCause
      .addCase(deleteRootCause.fulfilled, (state, action) => {
        if (state.currentInvestigation) {
          state.currentInvestigation.root_causes = state.currentInvestigation.root_causes.filter(
            (r) => r.id !== action.payload
          );
        }
      })

      // fetchAuditLogs
      .addCase(fetchAuditLogs.fulfilled, (state, action) => {
        state.auditLogs = action.payload;
      });
  },
});

export const { setActiveStage, setCurrentInvestigation, clearError, updateDeviationFieldInMemory } = investigationSlice.actions;
export default investigationSlice.reducer;
