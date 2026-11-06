import { configureStore } from '@reduxjs/toolkit';
import investigationReducer from './investigationSlice';
import copilotReducer from './copilotSlice';
import uiReducer from './uiSlice';
import authReducer from './authSlice';

export const store = configureStore({
  reducer: {
    investigation: investigationReducer,
    copilot: copilotReducer,
    ui: uiReducer,
    auth: authReducer,
  },
});

export default store;
