import React, { useState, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  FlaskConical,
  Lock,
  User,
  ShieldCheck,
  AlertTriangle,
  LogIn,
  Sun,
  Moon,
  Sparkles,
  ArrowRight,
  Eye,
  EyeOff,
  GitFork,
  FileSearch,
  FileCheck,
} from 'lucide-react';
import { loginUser, demoLoginUser } from '../../store/authSlice';
import { fetchInvestigations, fetchInvestigationById } from '../../store/investigationSlice';
import { setNotification } from '../../store/uiSlice';
import api from '../../services/api';

export const SignInPage = ({ onToggleTheme, isDark }) => {
  const dispatch = useDispatch();
  const { status } = useSelector((state) => state.auth);

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [localError, setLocalError] = useState('');
  const [demoLoginEnabled, setDemoLoginEnabled] = useState(false);

  useEffect(() => {
    let isMounted = true;
    api.get('/auth/config')
      .then((res) => {
        if (isMounted && res.data?.demo_login_enabled) {
          setDemoLoginEnabled(true);
        }
      })
      .catch(() => {
        if (isMounted) setDemoLoginEnabled(false);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setLocalError('Please enter both username and password.');
      return;
    }
    setLocalError('');

    const res = await dispatch(loginUser({ username: username.trim(), password }));
    if (!res.error) {
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

  const handleDemoLogin = async (persona) => {
    setLocalError('');
    const res = await dispatch(demoLoginUser({ persona }));
    if (!res.error) {
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
      setLocalError(res.payload || 'Demo authentication failed. Demo login may be disabled.');
    }
  };

  return (
    <div className="min-h-screen w-full flex flex-col lg:flex-row bg-slate-100 dark:bg-[#020308] text-slate-900 dark:text-slate-100 overflow-x-hidden relative font-sans transition-colors duration-200">
      {/* ── Top Bar Controls ──────────────────────────────────────────── */}
      <div className="absolute top-4 right-4 z-20 flex items-center gap-2.5">
        <button
          onClick={onToggleTheme}
          aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
          title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
          className="skeuo-btn-secondary flex items-center justify-center w-10 h-10 rounded-2xl border border-slate-300 dark:border-[#1e2236] shadow-md backdrop-blur-md transition-all active:scale-95 cursor-pointer text-slate-700 dark:text-slate-200 hover:text-blue-700 dark:hover:text-blue-400"
        >
          {isDark ? (
            <Sun className="w-5 h-5 text-amber-400" />
          ) : (
            <Moon className="w-5 h-5 text-blue-700" />
          )}
        </button>
      </div>

      {/* ── LEFT PANEL: Pharma Platform Architecture ─────────────────── */}
      <div className="lg:w-[58%] xl:w-[62%] p-6 sm:p-10 lg:p-14 flex flex-col justify-between border-b lg:border-b-0 lg:border-r border-slate-300 dark:border-[#1e2236]/80 relative z-10 bg-white dark:bg-[#060814]">
        {/* Brand Header */}
        <div>
          <div className="flex items-center gap-3.5 mb-6">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-blue-800 via-blue-700 to-indigo-800 p-[1.5px] shadow-lg shadow-blue-900/25">
              <div className="w-full h-full bg-blue-950 dark:bg-[#060814] rounded-2xl flex items-center justify-center">
                <FlaskConical className="w-7 h-7 text-amber-400" />
              </div>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-black text-2xl tracking-tight bg-gradient-to-r from-blue-800 via-blue-700 to-indigo-800 dark:from-blue-400 dark:via-blue-300 dark:to-indigo-400 bg-clip-text text-transparent">
                  AIVOA.AI
                </span>
                <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800/80 text-slate-700 dark:text-slate-300 font-mono border border-slate-300 dark:border-slate-700 font-medium">
                  Decision-support prototype
                </span>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 font-medium mt-0.5">
                RCA Intelligence Suite for Active Pharmaceutical Ingredient (API) Manufacturing
              </p>
            </div>
          </div>

          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight leading-tight max-w-2xl">
            AI-assisted root cause investigation for{' '}
            <span className="bg-gradient-to-r from-blue-700 to-indigo-700 dark:from-blue-400 dark:to-indigo-400 bg-clip-text text-transparent">
              API manufacturing deviations
            </span>
          </h1>
          <p className="text-sm font-semibold text-blue-900 dark:text-blue-300 mt-2 max-w-2xl">
            AI suggests; qualified people decide.
          </p>

          {/* Three Honest Core Capabilities */}
          <div className="my-6 max-w-2xl w-full space-y-3">
            <div className="skeuo-card rounded-2xl p-4 border border-slate-300 dark:border-[#1e2236] flex items-start gap-3">
              <div className="w-8 h-8 rounded-xl bg-blue-50 dark:bg-blue-950/50 flex items-center justify-center text-blue-700 dark:text-blue-400 shrink-0 border border-blue-200 dark:border-blue-800/50">
                <FileSearch className="w-4 h-4" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-900 dark:text-white">
                  1. Extract from documents with cited sources
                </h4>
                <p className="text-[11px] text-slate-600 dark:text-slate-300 mt-0.5 leading-relaxed">
                  Ingests batch production records (BPRs), shift handover notes, and analytical records with verbatim source excerpts and page citations.
                </p>
              </div>
            </div>

            <div className="skeuo-card rounded-2xl p-4 border border-slate-300 dark:border-[#1e2236] flex items-start gap-3">
              <div className="w-8 h-8 rounded-xl bg-indigo-50 dark:bg-indigo-950/50 flex items-center justify-center text-indigo-700 dark:text-indigo-400 shrink-0 border border-indigo-200 dark:border-indigo-800/50">
                <GitFork className="w-4 h-4" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-900 dark:text-white">
                  2. 5 Whys and fishbone suggestions
                </h4>
                <p className="text-[11px] text-slate-600 dark:text-slate-300 mt-0.5 leading-relaxed">
                  Generates structured 5-Whys causal chains and Ishikawa 6M diagrams. All AI causes remain suggestions until verified by a qualified investigator.
                </p>
              </div>
            </div>

            <div className="skeuo-card rounded-2xl p-4 border border-slate-300 dark:border-[#1e2236] flex items-start gap-3">
              <div className="w-8 h-8 rounded-xl bg-amber-50 dark:bg-amber-950/50 flex items-center justify-center text-amber-700 dark:text-amber-400 shrink-0 border border-amber-200 dark:border-amber-800/50">
                <FileCheck className="w-4 h-4" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-slate-900 dark:text-white">
                  3. CAPA drafts with rationale
                </h4>
                <p className="text-[11px] text-slate-600 dark:text-slate-300 mt-0.5 leading-relaxed">
                  Formulates preventive action proposals with explicit regulatory rationales and measurable effectiveness verification criteria.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Regulatory & Scientific Methodology Footnote */}
        <div className="flex items-center gap-4 sm:gap-6 flex-wrap pt-4 border-t border-slate-300 dark:border-[#1e2236]/80 text-[11px] text-slate-600 dark:text-slate-400 font-semibold">
          <div className="flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
            <span>ALCOA+ Data Integrity Principles</span>
          </div>
          <div className="flex items-center gap-1.5">
            <FlaskConical className="w-4 h-4 text-blue-700 dark:text-blue-400 shrink-0" />
            <span>ICH Q9 / Q10 Quality Risk Management</span>
          </div>
        </div>
      </div>

      {/* ── RIGHT PANEL: Authentication Vault ─────────────────────────── */}
      <div className="lg:w-[42%] xl:w-[38%] p-6 sm:p-10 lg:p-12 flex flex-col justify-center items-center relative z-10 bg-slate-50 dark:bg-[#020308]">
        <div className="w-full max-w-md">
          {/* Vault Card */}
          <div className="skeuo-surface-raised rounded-3xl p-7 sm:p-8 border border-slate-300 dark:border-[#1e2236] shadow-2xl relative">
            <div className="flex items-center justify-between mb-6">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-blue-800 to-indigo-800 flex items-center justify-center text-amber-400 shadow-lg shadow-blue-900/25 border border-blue-600/30">
                <Lock className="w-6 h-6" />
              </div>
              <span className="text-[10px] font-mono uppercase px-3 py-1 rounded-full bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800/50 text-blue-800 dark:text-blue-300 font-bold">
                Quality System Portal
              </span>
            </div>

            <h2 className="text-xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              Quality System Authentication
            </h2>
            <p className="text-xs text-slate-600 dark:text-slate-400 mt-1 mb-6 font-medium">
              Sign in with your verified cGMP investigator or approver credentials.
            </p>

            {/* Quick Demo Persona Shortcuts — Neutral names, server-side env auth only */}
            {demoLoginEnabled && (
              <div className="mb-6 p-3.5 rounded-2xl bg-blue-50/50 dark:bg-[#0c0e1a] border border-blue-200 dark:border-[#1e2236]">
                <p className="text-[10px] uppercase font-bold text-slate-600 dark:text-slate-400 tracking-wider mb-2.5 flex items-center gap-1 font-mono">
                  <Sparkles className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
                  Recording / Demo Shortcuts:
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  <button
                    type="button"
                    onClick={() => handleDemoLogin('investigator')}
                    disabled={status === 'loading'}
                    className="skeuo-btn-secondary text-left p-2.5 rounded-xl text-xs flex flex-col transition border-blue-200 dark:border-blue-800/40 hover:border-blue-400 cursor-pointer disabled:opacity-50"
                  >
                    <span className="font-bold text-slate-900 dark:text-slate-100 flex items-center justify-between">
                      Demo Investigator
                      <ArrowRight className="w-3 h-3 text-blue-700 dark:text-blue-400" />
                    </span>
                    <span className="text-[10px] text-blue-800 dark:text-blue-300 font-mono mt-0.5 font-bold">
                      Role: INVESTIGATOR
                    </span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDemoLogin('qa')}
                    disabled={status === 'loading'}
                    className="skeuo-btn-secondary text-left p-2.5 rounded-xl text-xs flex flex-col transition border-amber-200 dark:border-amber-800/40 hover:border-amber-400 cursor-pointer disabled:opacity-50"
                  >
                    <span className="font-bold text-slate-900 dark:text-slate-100 flex items-center justify-between">
                      Demo QA Reviewer
                      <ArrowRight className="w-3 h-3 text-amber-600 dark:text-amber-400" />
                    </span>
                    <span className="text-[10px] text-amber-800 dark:text-amber-300 font-mono mt-0.5 font-bold">
                      Role: QA_APPROVER
                    </span>
                  </button>
                </div>
              </div>
            )}

            {/* Login Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              {localError && (
                <div className="flex items-start gap-2.5 p-3.5 bg-rose-50 dark:bg-rose-950/30 border border-rose-300 dark:border-rose-800/60 rounded-xl text-rose-800 dark:text-rose-200 text-xs font-medium animate-fade-in shadow-inner">
                  <AlertTriangle className="w-4 h-4 text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" />
                  <span>{localError}</span>
                </div>
              )}

              {/* Username Input */}
              <div className="space-y-1.5 text-left">
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-200">
                  cGMP Username <span className="text-blue-700 dark:text-blue-400">*</span>
                </label>
                <div className="relative rounded-xl skeuo-well overflow-hidden">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <User className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="Enter cGMP username"
                    className="w-full text-xs font-semibold bg-transparent text-slate-900 dark:text-white px-3.5 py-3 pl-10 focus:outline-none placeholder:text-slate-400 dark:placeholder:text-slate-500"
                  />
                </div>
              </div>

              {/* Password Input */}
              <div className="space-y-1.5 text-left">
                <label className="block text-xs font-bold text-slate-700 dark:text-slate-200">
                  Password <span className="text-blue-700 dark:text-blue-400">*</span>
                </label>
                <div className="relative rounded-xl skeuo-well overflow-hidden">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter password"
                    className="w-full text-xs font-semibold bg-transparent text-slate-900 dark:text-white px-3.5 py-3 pl-10 pr-10 focus:outline-none placeholder:text-slate-400 dark:placeholder:text-slate-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Submit Button */}
              <div className="pt-2">
                <button
                  type="submit"
                  disabled={status === 'loading'}
                  className="skeuo-btn-primary w-full py-3 px-4 rounded-xl font-bold text-xs flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed shadow-md"
                >
                  <LogIn className="w-4 h-4" />
                  {status === 'loading' ? 'Authenticating with cGMP Vault...' : 'Sign In to Investigation Portal'}
                </button>
              </div>
            </form>

            {/* Footer Trust / Notice */}
            <div className="mt-6 pt-4 border-t border-slate-200 dark:border-[#1e2236]/80 text-center text-[10px] text-slate-500 dark:text-slate-400 font-medium leading-relaxed">
              Decision-support prototype. Aligned with ICH Q9/Q10 principles; not a validated GxP system. AI output must be reviewed by qualified personnel.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SignInPage;
