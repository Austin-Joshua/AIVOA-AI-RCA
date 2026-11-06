import React, { forwardRef, useId } from 'react';

export const Input = forwardRef(
  (
    {
      label,
      helperText,
      error,
      icon = null,
      iconRight = null,
      mono = false,
      required = false,
      className = '',
      id,
      ...props
    },
    ref
  ) => {
    const generatedId = useId();
    const inputId = id || generatedId;
    const errorId = `${inputId}-error`;
    const helperId = `${inputId}-helper`;

    return (
      <div className="space-y-1 w-full text-left font-sans">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-xs font-bold text-slate-700 dark:text-slate-300 select-none tracking-tight"
          >
            {label} {required && <span className="text-cyan-500 font-extrabold">*</span>}
          </label>
        )}
        <div className="relative rounded-xl overflow-hidden skeuo-well">
          {icon && (
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400 dark:text-slate-500">
              {icon}
            </div>
          )}
          <input
            ref={ref}
            type="text"
            id={inputId}
            required={required}
            aria-invalid={Boolean(error)}
            aria-describedby={error ? errorId : helperText ? helperId : undefined}
            className={`w-full text-xs font-medium rounded-xl bg-transparent px-3 py-2.5 transition-all duration-150 focus:outline-hidden disabled:opacity-60 disabled:cursor-not-allowed ${
              icon ? 'pl-9' : ''
            } ${iconRight ? 'pr-9' : ''} ${mono ? 'font-mono' : 'font-sans'} ${
              error
                ? 'text-rose-900 dark:text-rose-200 border-b-2 border-rose-500'
                : 'text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500'
            } ${className}`}
            {...props}
          />
          {iconRight && (
            <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none text-slate-400 dark:text-slate-500">
              {iconRight}
            </div>
          )}
        </div>
        {error && (
          <p id={errorId} className="text-[11px] font-semibold text-rose-600 dark:text-rose-400 mt-1">
            {error}
          </p>
        )}
        {helperText && !error && (
          <p id={helperId} className="text-[11px] font-medium text-slate-500 dark:text-slate-400 mt-1">
            {helperText}
          </p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';
export default Input;
