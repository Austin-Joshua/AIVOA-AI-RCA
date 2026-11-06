import React, { useState, useRef, useEffect, useMemo } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import {
  FileText,
  ChevronDown,
  Search,
  Check,
  PlusCircle,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Filter,
} from 'lucide-react';
import { fetchInvestigationById } from '../../store/investigationSlice';
import { setShowNewModal } from '../../store/uiSlice';

export const InvestigationDropdown = () => {
  const dispatch = useDispatch();
  const { currentInvestigation, investigationsList } = useSelector((state) => state.investigation);

  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL'); // ALL, ACTIVE, APPROVED
  const dropdownRef = useRef(null);
  const searchInputRef = useRef(null);

  // Close on outside click or Escape key
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') setIsOpen(false);
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
      setTimeout(() => searchInputRef.current?.focus(), 50);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen]);

  // Filter investigations
  const filteredInvestigations = useMemo(() => {
    return (investigationsList || []).filter((inv) => {
      const matchesSearch =
        (inv.investigation_number || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        (inv.title || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
        (inv.lead_investigator || '').toLowerCase().includes(searchQuery.toLowerCase());

      if (!matchesSearch) return false;

      if (statusFilter === 'APPROVED') return inv.is_approved;
      if (statusFilter === 'ACTIVE') return !inv.is_approved;
      return true;
    });
  }, [investigationsList, searchQuery, statusFilter]);

  const handleSelectInvestigation = (id) => {
    dispatch(fetchInvestigationById(id));
    setIsOpen(false);
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* ── Tactile Skeuomorphic Trigger Button ─────────────────────── */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-label={
          currentInvestigation
            ? `Active Dossier: ${currentInvestigation.investigation_number} - ${currentInvestigation.title}`
            : 'Select investigation dossier'
        }
        className="skeuo-btn-secondary flex items-center gap-2.5 px-3 py-1.5 rounded-xl text-xs font-semibold max-w-[200px] sm:max-w-[280px] md:max-w-[380px] transition-all cursor-pointer select-none group border border-slate-300 dark:border-[#1e2236] shadow-xs"
      >
        <div className="w-5 h-5 rounded-lg bg-blue-100 dark:bg-blue-950/60 border border-blue-300 dark:border-blue-700/50 flex items-center justify-center shrink-0">
          <FileText className="w-3.5 h-3.5 text-blue-800 dark:text-blue-300" />
        </div>

        {currentInvestigation ? (
          <div className="flex items-center gap-2 min-w-0 text-left truncate">
            <span className="font-mono text-[10px] text-amber-900 dark:text-amber-300 font-extrabold shrink-0 px-1.5 py-0.5 rounded-md bg-amber-50 dark:bg-amber-950/50 border border-amber-300 dark:border-amber-700/60 shadow-2xs">
              {currentInvestigation.investigation_number}
            </span>
            <span className="truncate text-slate-900 dark:text-slate-100 text-xs font-bold">
              {currentInvestigation.title}
            </span>
          </div>
        ) : (
          <span className="text-slate-500 dark:text-slate-400 font-medium">Select Dossier...</span>
        )}

        <ChevronDown
          className={`w-3.5 h-3.5 text-slate-400 dark:text-slate-400 shrink-0 ml-auto transition-transform duration-200 ${
            isOpen ? 'rotate-180 text-blue-700 dark:text-blue-400' : 'group-hover:text-slate-700 dark:group-hover:text-slate-200'
          }`}
        />
      </button>

      {/* ── Hidden Synced Native Select for Assistive / Automated Tools ── */}
      <select
        aria-label="Switch investigation"
        value={currentInvestigation?.id || ''}
        onChange={(e) => {
          if (e.target.value) {
            handleSelectInvestigation(Number(e.target.value));
          }
        }}
        className="sr-only"
        tabIndex={-1}
      >
        {investigationsList.map((inv) => (
          <option key={inv.id} value={inv.id}>
            [{inv.is_approved ? 'APPROVED' : inv.status || 'OPEN'}] {inv.investigation_number} — {inv.title}
          </option>
        ))}
      </select>

      {/* ── Rich Skeuomorphic Floating Dropdown Panel ─────────────────── */}
      {isOpen && (
        <div
          role="listbox"
          aria-label="Investigation dossiers"
          className="skeuo-surface-raised absolute left-0 mt-2 w-[340px] sm:w-[460px] rounded-2xl p-3.5 z-50 shadow-2xl border border-slate-300 dark:border-[#1e2236] bg-white dark:bg-[#080a14] text-slate-900 dark:text-slate-100 animate-fade-in backdrop-blur-xl"
        >
          {/* Header */}
          <div className="flex items-center justify-between pb-2.5 mb-2.5 border-b border-slate-200 dark:border-[#1e2236]/80 px-1">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-blue-700 dark:text-blue-400" />
              <span className="text-xs font-extrabold text-slate-900 dark:text-white tracking-tight">Dossier Registry</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-100 dark:bg-[#12152a] text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-[#1e2236] font-semibold">
                {investigationsList.length} total
              </span>
            </div>
            <button
              onClick={() => {
                setIsOpen(false);
                dispatch(setShowNewModal(true));
              }}
              className="text-[11px] font-extrabold text-blue-700 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 flex items-center gap-1 transition cursor-pointer"
            >
              <PlusCircle className="w-3.5 h-3.5" />
              New Dossier
            </button>
          </div>

          {/* Search Box */}
          <div className="relative mb-2.5">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400 dark:text-slate-500">
              <Search className="w-3.5 h-3.5" />
            </div>
            <input
              ref={searchInputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by dossier ID, product, batch, or lead..."
              className="skeuo-well w-full text-xs text-slate-900 dark:text-white bg-slate-50 dark:bg-[#060814] border border-slate-300 dark:border-[#1e2236] rounded-xl py-2 pl-9 pr-3 focus:outline-none placeholder:text-slate-400 dark:placeholder:text-slate-600 font-sans"
            />
          </div>

          {/* Filter Chips */}
          <div className="flex items-center gap-1.5 mb-2.5 px-1">
            <Filter className="w-3 h-3 text-slate-400 dark:text-slate-500" />
            <button
              onClick={() => setStatusFilter('ALL')}
              className={`text-[10px] px-2 py-0.5 rounded-lg font-bold transition cursor-pointer ${
                statusFilter === 'ALL'
                  ? 'bg-blue-100 dark:bg-blue-950/80 text-blue-800 dark:text-blue-300 border border-blue-300 dark:border-blue-700/60'
                  : 'bg-slate-100 dark:bg-[#12152a]/60 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 border border-transparent'
              }`}
            >
              All ({investigationsList.length})
            </button>
            <button
              onClick={() => setStatusFilter('ACTIVE')}
              className={`text-[10px] px-2 py-0.5 rounded-lg font-bold transition cursor-pointer ${
                statusFilter === 'ACTIVE'
                  ? 'bg-amber-100 dark:bg-amber-950/80 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-700/60'
                  : 'bg-slate-100 dark:bg-[#12152a]/60 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 border border-transparent'
              }`}
            >
              Active ({investigationsList.filter((i) => !i.is_approved).length})
            </button>
            <button
              onClick={() => setStatusFilter('APPROVED')}
              className={`text-[10px] px-2 py-0.5 rounded-lg font-bold transition cursor-pointer ${
                statusFilter === 'APPROVED'
                  ? 'bg-emerald-100 dark:bg-emerald-950/80 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700/60'
                  : 'bg-slate-100 dark:bg-[#12152a]/60 text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 border border-transparent'
              }`}
            >
              QA Approved ({investigationsList.filter((i) => i.is_approved).length})
            </button>
          </div>

          {/* Scrollable Dossier List */}
          <div className="max-h-[300px] overflow-y-auto space-y-1.5 pr-1">
            {filteredInvestigations.length === 0 ? (
              <div className="text-center py-6 text-xs text-slate-400 dark:text-zinc-500">
                No matching investigation dossiers found.
              </div>
            ) : (
              filteredInvestigations.map((inv) => {
                const isSelected = currentInvestigation?.id === inv.id;
                return (
                  <button
                    key={inv.id}
                    onClick={() => handleSelectInvestigation(inv.id)}
                    role="option"
                    aria-selected={isSelected}
                    className={`w-full text-left p-2.5 rounded-xl transition flex items-start gap-2.5 border cursor-pointer ${
                      isSelected
                        ? 'bg-blue-50 dark:bg-blue-950/60 border-blue-400 dark:border-blue-500/60 text-slate-900 dark:text-white shadow-xs ring-1 ring-blue-500/40'
                        : 'bg-slate-50/70 hover:bg-slate-100 dark:bg-[#0c0e1a]/60 dark:hover:bg-[#12152a] border-slate-200 dark:border-[#1e2236] hover:border-slate-300 dark:hover:border-[#2a3050] text-slate-700 dark:text-slate-300'
                    }`}
                  >
                    <div className="mt-0.5 shrink-0">
                      {isSelected ? (
                        <div className="w-4 h-4 rounded-full bg-blue-700 dark:bg-blue-600 text-white flex items-center justify-center font-bold">
                          <Check className="w-3 h-3 stroke-[3]" />
                        </div>
                      ) : (
                        <div className="w-4 h-4 rounded-full border border-slate-300 dark:border-[#1e2236]" />
                      )}
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <span className="font-mono text-[11px] font-extrabold text-blue-800 dark:text-blue-300">
                          {inv.investigation_number}
                        </span>
                        {inv.is_approved ? (
                          <span className="flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-950/80 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800/60">
                            <CheckCircle2 className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
                            QA Approved
                          </span>
                        ) : (
                          <span className="flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-950/80 text-amber-800 dark:text-amber-300 border border-amber-300 dark:border-amber-800/60">
                            <AlertTriangle className="w-3 h-3 text-amber-600 dark:text-amber-400" />
                            Active
                          </span>
                        )}
                        {inv.stage && (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 dark:bg-zinc-800 text-slate-600 dark:text-zinc-400 border border-slate-300 dark:border-zinc-700">
                            {inv.stage}
                          </span>
                        )}
                      </div>

                      <p className="text-xs font-semibold text-slate-900 dark:text-zinc-200 line-clamp-1">
                        {inv.title}
                      </p>

                      <div className="flex items-center gap-3 mt-1 text-[10px] text-slate-500 dark:text-zinc-400 font-mono">
                        <span>Lead: {inv.lead_investigator || 'Unassigned'}</span>
                        {inv.created_at && (
                          <span className="flex items-center gap-1">
                            <Clock className="w-3 h-3" />
                            {new Date(inv.created_at).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default InvestigationDropdown;
