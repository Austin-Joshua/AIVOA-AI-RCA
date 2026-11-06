import React from 'react';

export const Tabs = ({ tabs, activeTab, onChange, className = '' }) => {
  return (
    <div
      role="tablist"
      className={`flex border-b border-slate-200 bg-slate-50 px-2 pt-2 gap-1 overflow-x-auto scrollbar-none ${className}`}
    >
      {tabs.map((tab) => {
        const Icon = tab.icon;
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            className={`flex items-center gap-1.5 py-2 px-3 text-xs font-semibold rounded-t-lg transition border-t border-x -mb-px shrink-0 select-none ${
              isActive
                ? 'bg-white text-blue-700 border-slate-200 border-b-transparent shadow-2xs'
                : 'bg-transparent text-slate-500 border-transparent hover:text-slate-800 hover:bg-slate-100/50'
            }`}
          >
            {Icon && (
              <Icon
                className={`w-3.5 h-3.5 ${isActive ? 'text-blue-600' : 'text-slate-400'}`}
              />
            )}
            <span>{tab.label}</span>
            {tab.badge !== undefined && tab.badge !== null && (
              <span
                className={`text-[10px] px-1.5 py-0.2 rounded-full font-bold ${
                  isActive
                    ? 'bg-blue-100 text-blue-800'
                    : 'bg-slate-200 text-slate-600'
                }`}
              >
                {tab.badge}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
};

export default Tabs;

