import React from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export function Input({ label, error, helperText, className = '', ...props }: InputProps) {
  return (
    <div className="w-full">
      {label && (
        <label className="block mb-2 text-slate-700">
          {label}
        </label>
      )}
      <input
        className={`w-full px-4 py-2.5 bg-white border-2 rounded-lg transition-all duration-200
          ${error 
            ? 'border-coral-500 focus:border-coral-600 focus:ring-4 focus:ring-coral-100' 
            : 'border-slate-200 focus:border-primary-500 focus:ring-4 focus:ring-primary-100'
          }
          outline-none text-slate-800 placeholder:text-slate-400
          disabled:bg-slate-100 disabled:cursor-not-allowed
          ${className}`}
        {...props}
      />
      {error && (
        <p className="mt-1.5 text-sm text-coral-600">{error}</p>
      )}
      {helperText && !error && (
        <p className="mt-1.5 text-sm text-slate-500">{helperText}</p>
      )}
    </div>
  );
}
