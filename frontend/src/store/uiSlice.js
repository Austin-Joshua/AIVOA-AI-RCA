import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  notification: null, // { type: 'success' | 'error' | 'info', message: '' }
  showNewModal: false,
  showAuditModal: false,
  showDiffPreview: false,
  showLoginModal: false,
};

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    setNotification: (state, action) => {
      state.notification = action.payload;
    },
    clearNotification: (state) => {
      state.notification = null;
    },
    setShowNewModal: (state, action) => {
      state.showNewModal = action.payload;
    },
    setShowAuditModal: (state, action) => {
      state.showAuditModal = action.payload;
    },
    setShowDiffPreview: (state, action) => {
      state.showDiffPreview = action.payload;
    },
    setShowLoginModal: (state, action) => {
      state.showLoginModal = action.payload;
    },
  },
});

export const {
  setNotification,
  clearNotification,
  setShowNewModal,
  setShowAuditModal,
  setShowDiffPreview,
  setShowLoginModal,
} = uiSlice.actions;

export default uiSlice.reducer;

