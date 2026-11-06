import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  PlusCircle,
  History,
  AlertTriangle,
  CheckCircle2,
  FlaskConical,
  User,
  LogOut,
  Sun,
  Moon,
} from 'lucide-react';
import { setShowNewModal, setShowAuditModal, setShowLoginModal } from '../../store/uiSlice';
import { logoutUser } from '../../store/authSlice';
import InvestigationDropdown from './InvestigationDropdown';

export const Header = ({ isDark, onToggleTheme }) => {
  const dispatch = useDispatch();
  const { currentInvestigation } = useSelector((state) => state.investigation);
  const { user } = useSelector((state) => state.auth);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const userMenuRef = useRef(null);

  // Close dropdown on outside click or Escape key
  const handleOutsideClick = useCallback((e) => {
    if (userMenuRef.current && !userMenuRef.current.contains(e.target)) {
      setShowUserMenu(false);
    }
  }, []);

  useEffect(() => {
    const handleEscKey = (e) => {
      if (e.key === 'Escape') setShowUserMenu(false);
    };

    if (showUserMenu) {
      document.addEventListener('mousedown', handleOutsideClick);
      document.addEventListener('keydown', handleEscKey);
    }
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
      document.removeEventListener('keydown', handleEscKey);
    };
  }, [showUserMenu, handleOutsideClick]);

  // Clickable Logo redirects to home / top of workspace
  const handleLogoClick = (e) => {
    e.preventDefault();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <header className="skeuo-header-bar sticky top-0 z-30 shadow-md backdrop-blur-md">
      <div className="max-w-[1720px] mx-auto px-4 sm:px-6 lg:px-8 xl:px-10 h-16 flex items-center justify-between gap-3">
        {/* ── Brand / Logo (Clickable redirect to Home) ────────────────── */}
        <button
          onClick={handleLogoClick}
          aria-label="AIVOA.AI Home - Return to workspace"
          className="flex items-center gap-3 group focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500 rounded-xl py-1 px-1.5 transition-all cursor-pointer text-left shrink-0 active:scale-95"
        >
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-800 via-blue-700 to-indigo-800 p-[1.5px] shadow-md shadow-blue-900/20 group-hover:shadow-blue-800/40 transition-all">
            <div className="w-full h-full bg-blue-950 dark:bg-[#060814] rounded-xl flex items-center justify-center">
              <FlaskConical className="w-5 h-5 text-amber-400 group-hover:scale-110 transition-transform" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-black text-lg tracking-tight bg-gradient-to-r from-blue-800 via-blue-700 to-indigo-800 dark:from-blue-400 dark:via-blue-300 dark:to-indigo-400 bg-clip-text text-transparent">
                AIVOA.AI
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-50 dark:bg-amber-950/50 text-amber-800 dark:text-amber-300 font-mono border border-amber-300 dark:border-amber-700/60 font-bold shadow-2xs">
                RCA Intelligence
              </span>
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 hidden sm:block font-medium">
              Pharma API Manufacturing Quality Suite
            </p>
          </div>
        </button>

        {/* ── Right Section Controls ───────────────────────────────────── */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Document Dropdown beside Audit — only when authenticated */}
          {user && <InvestigationDropdown />}

          {/* Current Approval Status Banner (Pill format) */}
          {user && currentInvestigation && (
            <div className="hidden lg:flex items-center">
              {currentInvestigation.is_approved ? (
                <span className="flex items-center gap-1.5 text-xs font-bold px-3 py-1 rounded-full bg-emerald-100 dark:bg-emerald-950/80 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800 shadow-2xs font-mono">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                  QA Approved
                </span>
              ) : (
                <span className="flex items-center gap-1.5 text-xs font-bold px-3 py-1 rounded-full bg-amber-100 dark:bg-amber-950/80 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-800 shadow-2xs font-mono">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
                  Active Investigation
                </span>
              )}
            </div>
          )}

          {/* Audit Trail Icon Button */}
          {user && (
            <button
              onClick={() => dispatch(setShowAuditModal(true))}
              className="skeuo-btn-secondary flex items-center justify-center w-9 h-9 rounded-xl transition border border-slate-300 dark:border-zinc-800 text-slate-800 dark:text-zinc-200 hover:text-slate-900 dark:hover:text-white shadow-xs active:translate-y-0.5 cursor-pointer shrink-0"
              title="Audit Trail Dossier (21 CFR Part 11)"
              aria-label="View audit trail"
            >
              <History className="w-4 h-4 text-blue-700 dark:text-blue-400" />
              <span className="sr-only">Audit</span>
            </button>
          )}

          {/* New RCA Icon Button */}
          {user && (
            <button
              onClick={() => dispatch(setShowNewModal(true))}
              className="skeuo-btn-primary flex items-center justify-center w-9 h-9 rounded-xl shadow-xs transition active:translate-y-0.5 cursor-pointer shrink-0"
              title="Initiate New RCA Investigation"
              aria-label="Create new RCA investigation"
            >
              <PlusCircle className="w-4 h-4" />
              <span className="sr-only">New RCA</span>
            </button>
          )}

          {/* Light / Dark Mode Toggle Icon Button */}
          <button
            onClick={onToggleTheme}
            aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            className="skeuo-btn-secondary flex items-center justify-center w-9 h-9 rounded-xl border border-slate-300 dark:border-zinc-800 text-slate-700 dark:text-zinc-200 hover:text-slate-900 dark:hover:text-white transition active:scale-95 cursor-pointer shadow-xs shrink-0"
          >
            {isDark ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-blue-700" />}
          </button>

          {/* User Account Avatar Button or Sign In Button */}
          {user ? (
            <div className="relative" ref={userMenuRef}>
              <button
                onClick={() => setShowUserMenu((v) => !v)}
                aria-haspopup="true"
                aria-expanded={showUserMenu}
                aria-label={`User account: ${user.full_name}, role ${user.role}. Open account menu.`}
                title={`${user.full_name} (${user.role})`}
                className="skeuo-btn-secondary flex items-center justify-center w-9 h-9 rounded-xl border border-slate-300 dark:border-zinc-800 transition active:translate-y-0.5 cursor-pointer shadow-xs shrink-0 relative group"
              >
                <div className="w-7 h-7 rounded-lg bg-blue-100 dark:bg-blue-950/60 border border-blue-300 dark:border-blue-500/40 flex items-center justify-center text-blue-800 dark:text-blue-300 shrink-0 font-bold text-[11px] group-hover:scale-105 transition-transform">
                  {user.full_name
                    ?.split(' ')
                    .map((n) => n[0])
                    .slice(0, 2)
                    .join('')
                    .toUpperCase() || <User className="w-3.5 h-3.5" />}
                </div>
                <span className="sr-only">{user.full_name} ({user.role})</span>
              </button>

              {/* User Dropdown Menu */}
              {showUserMenu && (
                <div
                  role="menu"
                  aria-label="Account menu"
                  className="skeuo-surface-raised absolute right-0 mt-2 w-64 rounded-2xl shadow-2xl py-2 z-50 text-slate-900 dark:text-slate-100 border border-slate-300 dark:border-[#1e2236] bg-white dark:bg-[#080a14] animate-fade-in backdrop-blur-xl"
                >
                  <div className="px-3.5 py-3 border-b border-slate-200 dark:border-[#1e2236]">
                    <p className="text-[10px] text-slate-500 dark:text-slate-400 uppercase font-mono font-bold tracking-wider mb-1">
                      Active cGMP Identity
                    </p>
                    <p className="text-xs font-bold text-slate-900 dark:text-white truncate">{user.full_name}</p>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400 font-mono truncate">@{user.username}</p>
                    <div className="mt-2 flex items-center gap-1.5">
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-950/50 text-blue-800 dark:text-blue-300 border border-blue-300 dark:border-blue-800/60 font-semibold">
                        Role: {user.role}
                      </span>
                    </div>
                    {user.department && (
                      <p className="text-[10px] text-slate-500 dark:text-zinc-400 mt-1.5">{user.department}</p>
                    )}
                  </div>

                  <div className="pt-1 px-1">
                    <button
                      role="menuitem"
                      onClick={() => {
                        dispatch(logoutUser());
                        setShowUserMenu(false);
                      }}
                      className="w-full text-left px-3 py-2 text-xs text-rose-700 dark:text-rose-300 hover:bg-rose-50 dark:hover:bg-rose-950/40 rounded-xl flex items-center gap-2 transition cursor-pointer font-semibold"
                    >
                      <LogOut className="w-3.5 h-3.5 shrink-0" />
                      Sign Out
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <button
              onClick={() => dispatch(setShowLoginModal(true))}
              className="skeuo-btn-primary flex items-center gap-1.5 text-xs font-bold px-3.5 py-1.5 rounded-xl shadow-xs transition active:translate-y-0.5 cursor-pointer"
              aria-label="Sign in to your quality system account"
            >
              <User className="w-3.5 h-3.5" />
              <span>Sign In</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
};

export default Header;
