import React from 'react';

export const Card = ({ children, className = '', id, ...props }) => {
  return (
    <div
      id={id}
      className={`skeuo-card rounded-2xl overflow-hidden transition-all duration-200 ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};

export const CardHeader = ({
  title,
  subtitle,
  badge = null,
  icon = null,
  action = null,
  className = '',
  children,
}) => {
  return (
    <div
      className={`bg-gradient-to-b from-slate-50/90 to-slate-100/60 dark:from-zinc-900/90 dark:to-black/90 px-5 py-3.5 border-b border-slate-300 dark:border-zinc-800 flex items-center justify-between gap-3 flex-wrap ${className}`}
    >
      {children ? (
        children
      ) : (
        <>
          <div className="flex items-center gap-2.5 min-w-0">
            {icon && (
              <div className="w-7 h-7 rounded-lg bg-slate-200/80 dark:bg-zinc-800 border border-slate-300/80 dark:border-zinc-700 flex items-center justify-center shrink-0 shadow-xs">
                {icon}
              </div>
            )}
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="font-extrabold text-slate-900 dark:text-zinc-100 text-sm tracking-tight truncate">
                  {title}
                </h3>
                {badge}
              </div>
              {subtitle && (
                <p className="text-[11px] text-slate-500 dark:text-zinc-400 truncate mt-0.5 font-medium">
                  {subtitle}
                </p>
              )}
            </div>
          </div>
          {action && <div className="flex items-center gap-2 shrink-0">{action}</div>}
        </>
      )}
    </div>
  );
};

export const CardContent = ({ children, className = '', ...props }) => {
  return (
    <div className={`p-5 ${className}`} {...props}>
      {children}
    </div>
  );
};

export const CardFooter = ({ children, className = '', ...props }) => {
  return (
    <div
      className={`px-5 py-3 bg-gradient-to-t from-slate-100/60 to-transparent dark:from-zinc-950/40 border-t border-slate-300 dark:border-zinc-800 flex items-center justify-between gap-3 text-xs ${className}`}
      {...props}
    >
      {children}
    </div>
  );
};

export default Card;
