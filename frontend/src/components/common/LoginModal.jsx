import React, { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { Lock, User, X, LogIn, AlertCircle, Sparkles, Eye, EyeOff } from 'lucide-react';
import { loginUser } from '../../store/authSlice';
import { setShowLoginModal, setNotification } from '../../store/uiSlice';
import { fetchInvestigations, fetchInvestigationById } from '../../store/investigationSlice';
import { Button, Input } from '../ui';

export const LoginModal = () => {
  const dispatch = useDispatch();
  const { showLoginModal } = useSelector((state) => state.ui);
  const { status } = useSelector((state) => state.auth);

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [localError, setLocalError] = useState('');

  if (!showLoginModal) return null;

  const handleClose = () => {
    setLocalError('');
    dispatch(setShowLoginModal(false));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setLocalError('Please enter both username and password.');
      return;
    }
    setLocalError('');

    const res = await dispatch(loginUser({ username: username.trim(), password }));
    if (!res.error) {
      dispatch(setShowLoginModal(false));
      setUsername('');
      setPassword('');
      dispatch(
        setNotification({
          type: 'success',
          message: `Authenticated as ${res.payload.user.full_name} (${res.payload.user.role})`,
        })
      );
      const invAction = await dispatch(fetchInvestigations());
      if (invAction.payload && invAction.payload.length > 0) {
        dispatch(fetchInvestigationById(invAction.payload[0].id));
      }
    } else {
      setLocalError(res.payload || 'Authentication failed. Please verify your cGMP credentials.');
    }
  };

  const handleSelectPersona = (u, p) => {
    setUsername(u);
    setPassword(p);
    setLocalError('');
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-md p-4 animate-fade-in font-sans"
      role="dialog"
      aria-modal="true"
    >
      <div className="skeuo-surface-raised rounded-3xl max-w-md w-full shadow-2xl border border-slate-300 dark:border-[#1e2236] overflow-hidden bg-white dark:bg-[#080a14] text-slate-900 dark:text-slate-100">
        {/* Header */}
        <div className="px-5 py-4 bg-gradient-to-b from-blue-50/80 to-white dark:from-[#0c0e1a] dark:to-[#080a14] text-slate-900 dark:text-white flex items-center justify-between border-b border-slate-200 dark:border-[#1e2236]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-blue-100 dark:bg-blue-950/60 border border-blue-300 dark:border-blue-700/50 flex items-center justify-center text-blue-800 dark:text-blue-300 shadow-xs">
              <Lock className="w-5 h-5 text-amber-500" />
            </div>
            <div>
              <h3 className="font-extrabold text-sm tracking-tight text-slate-900 dark:text-white">Quality System Authentication</h3>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">API Manufacturing Quality &amp; CAPA Portal</p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="text-slate-400 hover:text-slate-700 dark:hover:text-white p-1.5 rounded-xl hover:bg-slate-100 dark:hover:bg-zinc-800 transition cursor-pointer"
            aria-label="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Quick Persona Selector */}
          <div className="p-3 rounded-2xl bg-blue-50/50 dark:bg-[#0c0e1a] border border-blue-200 dark:border-[#1e2236]">
            <p className="text-[10px] uppercase font-bold text-slate-600 dark:text-slate-400 tracking-wider mb-2 flex items-center gap-1 font-mono">
              <Sparkles className="w-3 h-3 text-amber-600 dark:text-amber-400" />
              Quick Select Test Credentials:
            </p>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => handleSelectPersona('lead_investigator', 'AivoaPass2026!')}
                className="skeuo-btn-secondary text-left p-2 rounded-xl text-xs flex flex-col transition border border-blue-200 dark:border-[#1e2236] hover:border-blue-400"
              >
                <span className="font-bold text-slate-900 dark:text-slate-100 text-[11px]">Dr. Sarah Lin</span>
                <span className="text-[10px] text-blue-800 dark:text-blue-300 font-mono font-bold">Lead Investigator</span>
              </button>
              <button
                type="button"
                onClick={() => handleSelectPersona('qa_director', 'AivoaPass2026!')}
                className="skeuo-btn-secondary text-left p-2 rounded-xl text-xs flex flex-col transition border border-amber-200 dark:border-[#1e2236] hover:border-amber-400"
              >
                <span className="font-bold text-slate-900 dark:text-slate-100 text-[11px]">Dr. Elena Rostova</span>
                <span className="text-[10px] text-amber-800 dark:text-amber-300 font-mono font-bold">QA Director</span>
              </button>
            </div>
          </div>

          {localError && (
            <div className="flex items-start gap-2.5 p-3.5 bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 rounded-xl text-rose-700 dark:text-rose-200 text-xs font-medium">
              <AlertCircle className="w-4 h-4 text-rose-500 dark:text-rose-400 shrink-0 mt-0.5" />
              <span>{localError}</span>
            </div>
          )}

          <Input
            label="Username"
            required
            autoFocus
            icon={<User className="w-4 h-4" />}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="Enter cGMP username"
          />

          <div className="relative">
            <Input
              label="Password"
              type={showPassword ? 'text' : 'password'}
              required
              icon={<Lock className="w-4 h-4" />}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute top-7 right-3 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
            >
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>

          <div className="pt-2 flex items-center justify-end gap-3 border-t border-slate-200 dark:border-zinc-800">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleClose}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              loading={status === 'loading'}
              icon={<LogIn className="w-3.5 h-3.5" />}
            >
              Sign In
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default LoginModal;
