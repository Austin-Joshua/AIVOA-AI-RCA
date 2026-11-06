import React, { useEffect, useRef } from 'react';
import { X } from 'lucide-react';

export const Modal = ({
  isOpen,
  onClose,
  title,
  description = null,
  icon = null,
  children,
  footer = null,
  maxWidth = 'md',
  className = '',
}) => {
  const modalRef = useRef(null);

  // Close on ESC
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const maxWidths = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
    '2xl': 'max-w-2xl',
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 overflow-y-auto animate-fade-in font-sans"
      role="dialog"
      aria-modal="true"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={modalRef}
        className={`skeuo-surface-raised rounded-3xl w-full ${
          maxWidths[maxWidth] || maxWidths.md
        } overflow-hidden transition-all duration-200 border border-slate-200 dark:border-zinc-800 bg-white dark:bg-black text-slate-900 dark:text-zinc-100 shadow-2xl ${className}`}
      >
        {/* Header */}
        <div className="bg-gradient-to-b from-slate-50 to-white dark:from-zinc-900 dark:to-black px-5 py-3.5 text-slate-900 dark:text-white flex items-center justify-between border-b border-slate-200 dark:border-zinc-800">
          <div className="flex items-center gap-2.5 min-w-0">
            {icon && (
              <div className="w-7 h-7 rounded-lg bg-cyan-50 dark:bg-zinc-900 border border-cyan-500/30 dark:border-cyan-500/40 flex items-center justify-center shrink-0 text-cyan-600 dark:text-cyan-400">
                {icon}
              </div>
            )}
            <div className="min-w-0">
              <h3 className="font-extrabold text-sm tracking-tight truncate text-slate-900 dark:text-white">{title}</h3>
              {description && (
                <p className="text-[11px] text-slate-500 dark:text-zinc-400 truncate mt-0.5">{description}</p>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-700 dark:hover:text-white p-1.5 rounded-xl hover:bg-slate-100 dark:hover:bg-zinc-800 transition cursor-pointer"
            aria-label="Close modal"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6">{children}</div>

        {/* Optional Footer */}
        {footer && (
          <div className="px-6 py-3.5 bg-slate-50 dark:bg-zinc-950 border-t border-slate-200 dark:border-zinc-800 flex items-center justify-end gap-3">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
};

export default Modal;
