import React, { forwardRef } from 'react';
import Spinner from './Spinner';

export const Button = forwardRef(
  (
    {
      children,
      variant = 'primary',
      size = 'sm',
      loading = false,
      disabled = false,
      icon = null,
      iconRight = null,
      className = '',
      type = 'button',
      ...props
    },
    ref
  ) => {
    const baseStyles =
      'inline-flex items-center justify-center font-bold rounded-xl transition-all duration-120 focus:outline-hidden focus:ring-2 focus:ring-offset-1 select-none disabled:opacity-50 disabled:cursor-not-allowed disabled:pointer-events-none active:scale-[0.98] cursor-pointer';

    const variants = {
      primary:
        'skeuo-btn-primary focus:ring-sky-500',
      secondary:
        'skeuo-btn-secondary focus:ring-slate-400',
      outline:
        'bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-750 text-slate-700 dark:text-slate-200 border border-slate-300 dark:border-slate-600 focus:ring-blue-500 shadow-xs hover:border-slate-400 dark:hover:border-slate-500',
      ghost:
        'bg-transparent hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100 focus:ring-slate-400',
      danger:
        'bg-gradient-to-b from-rose-500 to-rose-700 hover:from-rose-400 hover:to-rose-600 text-white shadow-md focus:ring-rose-500 border border-rose-800/80 active:translate-y-0.5',
      success:
        'bg-gradient-to-b from-emerald-500 to-emerald-700 hover:from-emerald-400 hover:to-emerald-600 text-white shadow-md focus:ring-emerald-500 border border-emerald-800/80 active:translate-y-0.5',
      brand:
        'skeuo-btn-primary focus:ring-cyan-500',
    };

    const sizes = {
      xs: 'text-[11px] px-2.5 py-1 gap-1 min-h-[26px]',
      sm: 'text-xs px-3.5 py-1.5 gap-1.5 min-h-[32px]',
      md: 'text-sm px-4 py-2 gap-2 min-h-[38px]',
      lg: 'text-base px-5 py-2.5 gap-2.5 min-h-[44px]',
    };

    return (
      <button
        ref={ref}
        type={type}
        disabled={disabled || loading}
        aria-busy={loading}
        className={`${baseStyles} ${variants[variant] || variants.primary} ${sizes[size] || sizes.sm} ${className}`}
        {...props}
      >
        {loading ? (
          <>
            <Spinner size={size === 'xs' ? 'xs' : 'sm'} />
            <span>{children}</span>
          </>
        ) : (
          <>
            {icon && <span className="shrink-0">{icon}</span>}
            {children}
            {iconRight && <span className="shrink-0">{iconRight}</span>}
          </>
        )}
      </button>
    );
  }
);

Button.displayName = 'Button';
export default Button;
