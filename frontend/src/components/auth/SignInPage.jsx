import React, { useState } from 'react';
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
  CheckCircle2,
  Cpu,
  Layers,
  Sparkles,
  ArrowRight,
  Eye,
  EyeOff,
  GitFork,
  FileSearch,
  FileCheck,
  Crown,
} from 'lucide-react';
import { loginUser } from '../../store/authSlice';
import { fetchInvestigations, fetchInvestigationById } from '../../store/investigationSlice';
import { setNotification } from '../../store/uiSlice';

export const SignInPage = ({ onToggleTheme, isDark }) => {
  const dispatch = useDispatch();
  const { status } = useSelector((state) => state.auth);

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [localError, setLocalError] = useState('');

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

  const handleSelectDemoPersona = (demoUser, demoPass) => {
    setUsername(demoUser);
    setPassword(demoPass);
    setLocalError('');
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
                  AIVO.AI
                </span>
                <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-amber-50 dark:bg-amber-950/40 text-amber-800 dark:text-amber-300 font-mono border border-amber-300 dark:border-amber-700/60 font-bold shadow-2xs">
                  cGMP Enterprise Platform
                </span>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">
                Autonomous Root Cause Analysis &amp; CAPA Intelligence for API Manufacturing
              </p>
            </div>
          </div>

          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight leading-tight max-w-2xl">
            Autonomous Deviation Triage &amp;{' '}
            <span className="bg-gradient-to-r from-blue-700 to-indigo-700 dark:from-blue-400 dark:to-indigo-400 bg-clip-text text-transparent">
              Regulatory-Grade
            </span>{' '}
            Root Cause Analysis
          </h1>
          <p className="text-sm text-slate-600 dark:text-slate-300 mt-3 max-w-2xl leading-relaxed">
            AIVO.AI combines multi-agent causality reasoning, verbatim-cited evidence grounding, and dual-methodology synthesis (5-Whys causal chaining and Ishikawa 6Ms) to accelerate deviation investigations from weeks to hours while ensuring strict compliance with ICH Q9, ICH Q10, and FDA 21 CFR Part 11.
          </p>

          {/* Key Value Metrics Bar — Gold Accented Numbers */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 my-6">
            <div className="skeuo-card rounded-2xl p-3 border border-slate-300 dark:border-[#1e2236] text-center">
              <span className="text-xl font-extrabold text-amber-700 dark:text-amber-400 font-mono">70%</span>
              <p className="text-[10px] text-slate-500 dark:text-slate-400 font-bold uppercase mt-0.5">RCA Cycle Time Reduction</p>
            </div>
            <div className="skeuo-card rounded-2xl p-3 border border-slate-300 dark:border-[#1e2236] text-center">
              <span className="text-xl font-extrabold text-emerald-700 dark:text-emerald-400 font-mono">100%</span>
              <p className="text-[10px] text-slate-500 dark:text-slate-400 font-bold uppercase mt-0.5">Verbatim Citation Grounding</p>
            </div>
            <div className="skeuo-card rounded-2xl p-3 border border-slate-300 dark:border-[#1e2236] text-center">
              <span className="text-xl font-extrabold text-blue-800 dark:text-blue-400 font-mono">0</span>
              <p className="text-[10px] text-slate-500 dark:text-slate-400 font-bold uppercase mt-0.5">Silent Hallucinations</p>
            </div>
            <div className="skeuo-card rounded-2xl p-3 border border-slate-300 dark:border-[#1e2236] text-center">
              <span className="text-xl font-extrabold text-blue-900 dark:text-blue-300 font-mono">Part 11</span>
              <p className="text-[10px] text-slate-500 dark:text-slate-400 font-bold uppercase mt-0.5">Immutable SHA-256 Logs</p>
            </div>
          </div>
        </div>

        {/* ── Core Platform Architecture Grid ─────────────────────────── */}
        <div className="my-4 max-w-2xl w-full space-y-3.5">
          <p className="text-xs uppercase font-extrabold text-slate-500 dark:text-slate-400 tracking-wider font-mono flex items-center gap-1.5">
            <Crown className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
            Core Investigation Capabilities
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="skeuo-card rounded-2xl p-4 border border-slate-300 dark:border-[#1e2236] space-y-1.5">
              <div className="flex items-center gap-2 text-blue-800 dark:text-blue-400">
                <FileSearch className="w-4 h-4" />
                <h4 className="text-xs font-extrabold text-slate-900 dark:text-white">Multimodal Incident Ingestion</h4>
              </div>
              <p className="text-[11px] text-slate-600 dark:text-slate-300 leading-relaxed">
                Ingests multipage batch records (BPRs), shift handover notes, SCADA telemetry alarms, and analytical deviation memos with verbatim citation mapping.
              </p>
            </div>

            <div className="skeuo-card rounded-2xl p-4 border border-slate-300 dark:border-[#1e2236] space-y-1.5">
              <div className="flex items-center gap-2 text-indigo-700 dark:text-indigo-400">
                <GitFork className="w-4 h-4" />
                <h4 className="text-xs font-extrabold text-slate-900 dark:text-white">Dual-Engine Causality Mapping</h4>
              </div>
              <p className="text-[11px] text-slate-600 dark:text-slate-300 leading-relaxed">
                Synthesizes 5-Whys causal chains and Ishikawa 6Ms (Machine, Method, Material, Measurement, Man, Milieu) to isolate confirmed root causes from contributing factors.
              </p>
            </div>

            <div className="skeuo-card rounded-2xl p-4 border border-slate-300 dark:border-[#1e2236] space-y-1.5">
              <div className="flex items-center gap-2 text-amber-700 dark:text-amber-400">
                <AlertTriangle className="w-4 h-4" />
                <h4 className="text-xs font-extrabold text-slate-900 dark:text-white">Evidence Gap &amp; Risk Detection</h4>
              </div>
              <p className="text-[11px] text-slate-600 dark:text-slate-300 leading-relaxed">
                Proactively detects missing calibration logs, unattached work orders, and unresolved discrepancies before QA dossier sign-off.
              </p>
            </div>

            <div className="skeuo-card rounded-2xl p-4 border border-slate-300 dark:border-[#1e2236] space-y-1.5">
              <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-400">
                <FileCheck className="w-4 h-4" />
                <h4 className="text-xs font-extrabold text-slate-900 dark:text-white">Closed-Loop CAPA &amp; QA Sign-Off</h4>
              </div>
              <p className="text-[11px] text-slate-600 dark:text-slate-300 leading-relaxed">
                Generates preventive actions with assignees and quantitative effectiveness criteria. Enforces Separation of Duties with 21 CFR Part 11 electronic sign-off.
              </p>
            </div>
          </div>
        </div>

        {/* Regulatory & Enterprise Compliance Badges */}
        <div className="flex items-center gap-4 sm:gap-6 flex-wrap pt-4 border-t border-slate-300 dark:border-[#1e2236]/80 text-[11px] text-slate-600 dark:text-slate-400 font-semibold">
          <div className="flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
            <span>ALCOA+ Data Integrity</span>
          </div>
          <div className="flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4 text-blue-700 dark:text-blue-400 shrink-0" />
            <span>21 CFR Part 11 Compliant</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Layers className="w-4 h-4 text-blue-800 dark:text-blue-300 shrink-0" />
            <span>ICH Q9 / Q10 Quality System</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Cpu className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0" />
            <span>Cryptographic SHA-256 Audit Trail</span>
          </div>
        </div>
      </div>

      {/* ── RIGHT PANEL: Royal Authentication Vault ───────────────────── */}
      <div className="lg:w-[42%] xl:w-[38%] p-6 sm:p-10 lg:p-12 flex flex-col justify-center items-center relative z-10 bg-slate-50 dark:bg-[#020308]">
        <div className="w-full max-w-md">
          {/* Vault Card */}
          <div className="skeuo-surface-raised rounded-3xl p-7 sm:p-8 border border-slate-300 dark:border-[#1e2236] shadow-2xl relative">
            <div className="flex items-center justify-between mb-6">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-blue-800 to-indigo-800 flex items-center justify-center text-amber-400 shadow-lg shadow-blue-900/25 border border-blue-600/30">
                <Lock className="w-6 h-6" />
              </div>
              <span className="text-[10px] font-mono uppercase px-3 py-1 rounded-full bg-blue-50 dark:bg-blue-950/40 border border-blue-200 dark:border-blue-800/50 text-blue-800 dark:text-blue-300 font-bold">
                Quality System Portal v2.4
              </span>
            </div>

            <h2 className="text-xl font-extrabold text-slate-900 dark:text-white tracking-tight">
              Quality System Authentication
            </h2>
            <p className="text-xs text-slate-600 dark:text-slate-400 mt-1 mb-6 font-medium">
              Sign in with your verified cGMP investigator or approver credentials.
            </p>

            {/* Quick Demo Persona Shortcuts */}
            <div className="mb-6 p-3.5 rounded-2xl bg-blue-50/50 dark:bg-[#0c0e1a] border border-blue-200 dark:border-[#1e2236]">
              <p className="text-[10px] uppercase font-bold text-slate-600 dark:text-slate-400 tracking-wider mb-2.5 flex items-center gap-1 font-mono">
                <Sparkles className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
                Quick-Select Test Personas:
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                <button
                  type="button"
                  onClick={() => handleSelectDemoPersona('lead_investigator', 'AivoaPass2026!')}
                  className="skeuo-btn-secondary text-left p-2.5 rounded-xl text-xs flex flex-col transition border-blue-200 dark:border-blue-800/40 hover:border-blue-400 cursor-pointer"
                >
                  <span className="font-bold text-slate-900 dark:text-slate-100 flex items-center justify-between">
                    Dr. Sarah Lin
                    <ArrowRight className="w-3 h-3 text-blue-700 dark:text-blue-400" />
                  </span>
                  <span className="text-[10px] text-blue-800 dark:text-blue-300 font-mono mt-0.5 font-bold">
                    Role: INVESTIGATOR
                  </span>
                </button>
                <button
                  type="button"
                  onClick={() => handleSelectDemoPersona('qa_director', 'AivoaPass2026!')}
                  className="skeuo-btn-secondary text-left p-2.5 rounded-xl text-xs flex flex-col transition border-amber-200 dark:border-amber-800/40 hover:border-amber-400 cursor-pointer"
                >
                  <span className="font-bold text-slate-900 dark:text-slate-100 flex items-center justify-between">
                    Dr. Elena Rostova
                    <ArrowRight className="w-3 h-3 text-amber-600 dark:text-amber-400" />
                  </span>
                  <span className="text-[10px] text-amber-800 dark:text-amber-300 font-mono mt-0.5 font-bold">
                    Role: QA_APPROVER
                  </span>
                </button>
              </div>
            </div>

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
              Authorized access only. Every data modification and workflow transition is cryptographically logged under 21 CFR Part 11.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SignInPage;
