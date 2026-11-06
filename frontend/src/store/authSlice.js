import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import api from '../services/api';

const TOKEN_KEY = 'aivoa_token';
const USER_KEY = 'aivoa_user';

export const loginUser = createAsyncThunk(
  'auth/loginUser',
  async ({ username, password }, { rejectWithValue }) => {
    try {
      const res = await api.post('/auth/login', { username, password });
      const data = res.data;
      const access_token = data.access_token;
      const user = data.user || {
        id: data.user_id,
        username: data.username,
        full_name: data.full_name,
        role: data.role,
        department: data.department,
      };
      localStorage.setItem(TOKEN_KEY, access_token);
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      return { token: access_token, user };
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Authentication failed');
    }
  }
);

export const demoLoginUser = createAsyncThunk(
  'auth/demoLoginUser',
  async ({ persona }, { rejectWithValue }) => {
    try {
      const res = await api.post('/auth/demo-login', { persona });
      const data = res.data;
      const access_token = data.access_token;
      const user = data.user || {
        id: data.user_id,
        username: data.username,
        full_name: data.full_name,
        role: data.role,
        department: data.department,
      };
      localStorage.setItem(TOKEN_KEY, access_token);
      localStorage.setItem(USER_KEY, JSON.stringify(user));
      return { token: access_token, user };
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Demo login failed');
    }
  }
);

export const fetchCurrentUser = createAsyncThunk(
  'auth/fetchCurrentUser',
  async (_, { rejectWithValue }) => {
    try {
      const res = await api.get('/auth/me');
      localStorage.setItem(USER_KEY, JSON.stringify(res.data));
      return res.data;
    } catch (err) {
      return rejectWithValue(err.response?.data?.detail || 'Failed to fetch current user');
    }
  }
);

let initialUser = null;
try {
  const saved = localStorage.getItem(USER_KEY);
  if (saved) initialUser = JSON.parse(saved);
} catch {
  initialUser = null;
}

const authSlice = createSlice({
  name: 'auth',
  initialState: {
    token: localStorage.getItem(TOKEN_KEY) || null,
    user: initialUser,
    status: 'idle',
    error: null,
  },
  reducers: {
    logoutUser: (state) => {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      state.token = null;
      state.user = null;
      state.status = 'idle';
      state.error = null;
    },
    clearAuthError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(loginUser.pending, (state) => {
        state.status = 'loading';
        state.error = null;
      })
      .addCase(loginUser.fulfilled, (state, action) => {
        state.status = 'succeeded';
        state.token = action.payload.token;
        state.user = action.payload.user;
        state.error = null;
      })
      .addCase(loginUser.rejected, (state, action) => {
        state.status = 'failed';
        state.error = action.payload;
        state.token = null;
        state.user = null;
      })
      .addCase(demoLoginUser.pending, (state) => {
        state.status = 'loading';
        state.error = null;
      })
      .addCase(demoLoginUser.fulfilled, (state, action) => {
        state.status = 'succeeded';
        state.token = action.payload.token;
        state.user = action.payload.user;
        state.error = null;
      })
      .addCase(demoLoginUser.rejected, (state, action) => {
        state.status = 'failed';
        state.error = action.payload;
        state.token = null;
        state.user = null;
      })
      .addCase(fetchCurrentUser.fulfilled, (state, action) => {
        state.user = action.payload;
      })
      .addCase(fetchCurrentUser.rejected, (state) => {
        state.token = null;
        state.user = null;
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
      });
  },
});

export const { logoutUser, clearAuthError } = authSlice.actions;
export default authSlice.reducer;
