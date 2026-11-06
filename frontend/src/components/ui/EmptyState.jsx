import React from 'react';

export const EmptyState = ({
  icon,
  title,
  description,
  action = null,
  secondaryAction = null,
  className = '',
}) => {
  return (
    <div
      className={`skeuo-card rounded-3xl p-8 sm:p-12 text-center max-w-lg mx-auto shadow-xl font-sans ${className}`}
    >
      {icon && (
        <div className="w-14 h-14 rounded-2xl bg-cyan-950/80 border border-cyan-500/50 text-cyan-400 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-cyan-500/20">
          {icon}
        </div>
      )}
      <h3 className="text-base font-extrabold text-slate-900 dark:text-slate-50 tracking-tight">{title}</h3>
      {description && (
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-2 mb-6 leading-relaxed max-w-sm mx-auto font-medium">
          {description}
        </p>
      )}
      {(action || secondaryAction) && (
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          {action}
          {secondaryAction}
        </div>
      )}
    </div>
  );
};

export default EmptyState;
