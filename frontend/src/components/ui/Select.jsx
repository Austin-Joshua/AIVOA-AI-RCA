import React, { forwardRef, useId } from 'react';
import { ChevronDown } from 'lucide-react';

export const Select = forwardRef(
  (
    {
      label,
      helperText,
      error,
      options = null,
      children,
      required = false,
      className = '',
      id,
      ...props
    },
    ref
  ) => {
    const generatedId = useId();
    const selectId = id || generatedId;
    const errorId = `${selectId}-error`;
    const helperId = `${selectId}-helper`;

    return (
      <div className="space-y-1 w-full text-left font-sans">
        {label && (
          <label
            htmlFor={selectId}
            className="block text-xs font-bold text-slate-700 dark:text-slate-300 select-none tracking-tight"
          >
            {label} {required && <span className="text-cyan-500 font-extrabold">*</span>}
          </label>
        )}
        <div className="relative rounded-xl overflow-hidden skeuo-well">
          <select
            ref={ref}
            id={selectId}
            required={required}
            aria-invalid={Boolean(error)}
            aria-describedby={error ? errorId : helperText ? helperId : undefined}
            className={`w-full appearance-none text-xs rounded-xl bg-transparent pl-3.5 pr-9 py-2.5 transition-all duration-150 focus:outline-hidden disabled:opacity-60 disabled:cursor-not-allowed font-medium cursor-pointer ${
              error
                ? 'text-rose-900 dark:text-rose-200 border-b-2 border-rose-500'
                : 'text-slate-900 dark:text-slate-100'
            } ${className}`}
            {...props}
          >
            {options
              ? options.map((opt) => (
                  <option key={opt.value} value={opt.value} className="bg-white dark:bg-black text-slate-800 dark:text-zinc-100">
                    {opt.label}
                  </option>
                ))
              : children}
          </select>
          <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none text-slate-400 dark:text-slate-500">
            <ChevronDown className="w-4 h-4" />
          </div>
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

Select.displayName = 'Select';
export default Select;
