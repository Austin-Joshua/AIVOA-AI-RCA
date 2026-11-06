import React from 'react';

export const Badge = ({
  children,
  variant = 'neutral',
  size = 'sm',
  dot = false,
  icon = null,
  className = '',
}) => {
  const variants = {
    verified: 'bg-emerald-50 text-emerald-800 border-emerald-300/80',
    inference: 'bg-amber-50 text-amber-800 border-amber-300/80',
    edited: 'bg-blue-50 text-blue-800 border-blue-300/80',
    missing: 'bg-rose-50 text-rose-800 border-rose-300/80',
    neutral: 'bg-slate-100 text-slate-700 border-slate-200',
    info: 'bg-cyan-50 text-cyan-800 border-cyan-300/80',
    warning: 'bg-amber-100 text-amber-900 border-amber-300',
    danger: 'bg-rose-100 text-rose-900 border-rose-300',
    purple: 'bg-purple-50 text-purple-800 border-purple-200',
  };

  const dotColors = {
    verified: 'bg-emerald-500',
    inference: 'bg-amber-500',
    edited: 'bg-blue-500',
    missing: 'bg-rose-500',
    neutral: 'bg-slate-400',
    info: 'bg-cyan-500',
    warning: 'bg-amber-500',
    danger: 'bg-rose-500',
    purple: 'bg-purple-500',
  };

  const sizes = {
    xs: 'text-[10px] px-1.5 py-0.2 font-semibold',
    sm: 'text-[11px] px-2 py-0.5 font-bold',
    md: 'text-xs px-2.5 py-0.5 font-bold',
  };

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border tracking-wide uppercase ${
        variants[variant] || variants.neutral
      } ${sizes[size] || sizes.sm} ${className}`}
    >
      {dot && (
        <span
          className={`w-1.5 h-1.5 rounded-full ${dotColors[variant] || dotColors.neutral} shrink-0`}
        />
      )}
      {icon && <span className="shrink-0">{icon}</span>}
      <span>{children}</span>
    </span>
  );
};

export default Badge;

