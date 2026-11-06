import React, { forwardRef, useId } from 'react';

export const Textarea = forwardRef(
  (
    {
      label,
      helperText,
      error,
      mono = false,
      required = false,
      rows = 3,
      className = '',
      id,
      ...props
    },
    ref
  ) => {
    const generatedId = useId();
    const textareaId = id || generatedId;
    const errorId = `${textareaId}-error`;
    const helperId = `${textareaId}-helper`;

    return (
      <div className="space-y-1 w-full text-left font-sans">
        {label && (
          <label
            htmlFor={textareaId}
            className="block text-xs font-bold text-slate-700 dark:text-slate-300 select-none tracking-tight"
          >
            {label} {required && <span className="text-cyan-500 font-extrabold">*</span>}
          </label>
        )}
        <div className="relative rounded-xl overflow-hidden skeuo-well">
          <textarea
            ref={ref}
            id={textareaId}
            rows={rows}
            required={required}
            aria-invalid={Boolean(error)}
            aria-describedby={error ? errorId : helperText ? helperId : undefined}
            className={`w-full text-xs font-medium rounded-xl bg-transparent p-3 transition-all duration-150 focus:outline-hidden disabled:opacity-60 disabled:cursor-not-allowed leading-relaxed ${
              mono ? 'font-mono' : 'font-sans'
            } ${
              error
                ? 'text-rose-900 dark:text-rose-200 border-b-2 border-rose-500'
                : 'text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500'
            } ${className}`}
            {...props}
          />
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

Textarea.displayName = 'Textarea';
export default Textarea;
