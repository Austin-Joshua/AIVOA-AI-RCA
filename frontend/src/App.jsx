import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { fetchInvestigations, fetchInvestigationById, seedParacetamolDemo } from './store/investigationSlice';
import { fetchCurrentUser } from './store/authSlice';
import { setShowNewModal } from './store/uiSlice';
import { Sparkles, Plus, ShieldCheck, CheckCircle2, Cpu } from 'lucide-react';
import Header from './components/layout/Header';
import WorkflowSidebar from './components/layout/WorkflowSidebar';
import DeviationSection from './components/form/DeviationSection';
import EvidenceSection from './components/form/EvidenceSection';
import FiveWhysSection from './components/form/FiveWhysSection';
import FishboneSection from './components/form/FishboneSection';
import RootCauseSection from './components/form/RootCauseSection';
import CapaSection from './components/form/CapaSection';
import ApprovalSection from './components/form/ApprovalSection';
import CopilotPanel from './components/copilot/CopilotPanel';
import NewInvestigationModal from './components/common/NewInvestigationModal';
import AuditModal from './components/common/AuditModal';
import LoginModal from './components/common/LoginModal';
import NotificationBanner from './components/common/NotificationBanner';
import SignInPage from './components/auth/SignInPage';

export function App() {
  const dispatch = useDispatch();
  const token = useSelector((state) => state.auth.token);
  const currentUser = useSelector((state) => state.auth.user);
  const currentInvestigation = useSelector((state) => state.investigation.currentInvestigation);
  const loading = useSelector((state) => state.investigation.loading);

  const isAuthenticated = Boolean(token && currentUser);

  // ── Theme State Management ────────────────────────────────────────────────
  const [isDark, setIsDark] = useState(() => {
    const saved = localStorage.getItem('aivoa_theme');
    if (saved) return saved === 'dark';
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    const root = document.documentElement;
    if (isDark) {
      root.classList.add('dark');
      localStorage.setItem('aivoa_theme', 'dark');
    } else {
      root.classList.remove('dark');
      localStorage.setItem('aivoa_theme', 'light');
    }
  }, [isDark]);

  const toggleTheme = () => setIsDark((prev) => !prev);

  // ── Initialize Auth & Investigation Dossier ──────────────────────────────
  useEffect(() => {
    const initAuthAndData = async () => {
      if (token) {
        const userAction = await dispatch(fetchCurrentUser());
        if (fetchCurrentUser.fulfilled.match(userAction)) {
          const action = await dispatch(fetchInvestigations());
          if (action.payload && action.payload.length > 0) {
            dispatch(fetchInvestigationById(action.payload[0].id));
          }
        }
      }
    };

    initAuthAndData();
  }, [dispatch, token]);

  const handleStartParacetamolDemo = async () => {
    const res = await dispatch(seedParacetamolDemo());
    if (res.payload?.id) {
      dispatch(fetchInvestigationById(res.payload.id));
    }
  };

  // If user is not signed in, show the dedicated, premium Split-Screen Authentication Experience
  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-slate-100 dark:bg-[#020308] font-sans transition-colors duration-150">
        <SignInPage isDark={isDark} onToggleTheme={toggleTheme} />
        <LoginModal />
        <NotificationBanner />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-100 dark:bg-[#020308] flex flex-col font-sans text-slate-800 dark:text-slate-100 transition-colors duration-150">
      {/* ── Top Header ─────────────────────────────────────────────────────── */}
      <Header isDark={isDark} onToggleTheme={toggleTheme} />

      {/* ── Main Workspace ─────────────────────────────────────────────────── */}
      <main className="flex-1 max-w-[1780px] w-full mx-auto p-3 sm:p-5 lg:p-6 xl:p-8">
        {!currentInvestigation && !loading ? (
          /* ── Authenticated but no investigation selected ─────────────── */
          <div className="my-10">
            <div className="skeuo-surface-raised rounded-3xl p-8 sm:p-12 text-center max-w-xl mx-auto shadow-xl border border-slate-300 dark:border-zinc-800">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center mx-auto mb-5 shadow-lg shadow-cyan-500/20 text-white">
                <Sparkles className="w-7 h-7" />
              </div>
              <h2 className="text-xl font-extrabold text-slate-900 dark:text-white tracking-tight">
                No Active RCA Investigation
              </h2>
              <p className="text-xs text-slate-600 dark:text-zinc-400 mt-2 mb-6 leading-relaxed max-w-md mx-auto">
                Select an existing pharmaceutical deviation dossier from the registry dropdown above, or initialize a new cGMP investigation to begin automated intake, 5-Whys causal mapping, and CAPA generation.
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
                <button
                  type="button"
                  onClick={() => dispatch(setShowNewModal(true))}
                  className="skeuo-btn-primary py-2.5 px-4 rounded-xl text-xs font-bold flex items-center justify-center gap-2 cursor-pointer w-full sm:w-auto"
                >
                  <Plus className="w-4 h-4" />
                  <span>Create New Investigation</span>
                </button>
                <button
                  type="button"
                  onClick={handleStartParacetamolDemo}
                  className="skeuo-btn-secondary py-2.5 px-4 rounded-xl text-xs font-bold flex items-center justify-center gap-2 cursor-pointer w-full sm:w-auto"
                >
                  <Sparkles className="w-4 h-4 text-amber-500" />
                  <span>Start Paracetamol Demo Scenario</span>
                </button>
              </div>
            </div>
          </div>
        ) : (
          /* ── Full Investigation Workspace (3-Column Layout with Vertical Workflow Sidebar) ─ */
          <div className="flex flex-col lg:flex-row gap-6 items-start">
            {/* LEFT SIDEBAR: Vertical cGMP Workflow Stages (Sticky) */}
            <aside className="w-full lg:w-64 xl:w-72 shrink-0 lg:sticky lg:top-20 z-10">
              <WorkflowSidebar />
            </aside>

            {/* CENTER PANEL: Structured RCA Investigation Form */}
            <div className="flex-1 min-w-0 space-y-6">
              <DeviationSection />
              <EvidenceSection />
              <FiveWhysSection />
              <FishboneSection />
              <RootCauseSection />
              <CapaSection />
              <ApprovalSection />
            </div>

            {/* RIGHT PANEL: AI Investigation Copilot (Sticky) */}
            <aside className="w-full lg:w-[440px] xl:w-[480px] shrink-0 lg:sticky lg:top-20 h-[calc(100vh-6.5rem)]">
              <CopilotPanel />
            </aside>
          </div>
        )}
      </main>

      {/* ── cGMP Regulatory Disclaimer Footer ──────────────────────────── */}
      <footer className="mt-auto border-t border-slate-200/90 dark:border-[#1e2236]/90 bg-white/80 dark:bg-[#060814]/90 backdrop-blur-md py-3.5 px-6 text-center text-[11px] text-slate-500 dark:text-slate-400">
        <div className="max-w-[1780px] mx-auto flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-blue-700 dark:text-blue-400 shrink-0" />
            <span>
              <strong>cGMP / Decision-Support Notice:</strong> AI Copilot provides probabilistic decision-support aligned with ICH Q9 &amp; ICH Q10.
            </span>
          </div>
          <div className="flex items-center gap-3 text-[10px] font-mono text-slate-500 dark:text-slate-400">
            <span className="flex items-center gap-1">
              <CheckCircle2 className="w-3 h-3 text-emerald-600 dark:text-emerald-400" /> 21 CFR Part 11
            </span>
            <span className="flex items-center gap-1">
              <Cpu className="w-3 h-3 text-amber-600 dark:text-amber-400" /> ALCOA+ Audit
            </span>
          </div>
        </div>
      </footer>

      {/* ── Modals & Banners ───────────────────────────────────────────── */}
      <NewInvestigationModal />
      <AuditModal />
      <LoginModal />
      <NotificationBanner />
    </div>
  );
}

export default App;
