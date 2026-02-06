import React from 'react';
import { Loader2 } from 'lucide-react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'accent' | 'ghost' | 'outline';
  size?: 'sm' | 'md' | 'lg';
  isLoading?: boolean;
  children: React.ReactNode;
}

export function Button({ 
  variant = 'primary', 
  size = 'md', 
  isLoading = false,
  children, 
  className = '',
  disabled,
  ...props 
}: ButtonProps) {
  const baseStyles = "inline-flex items-center justify-center gap-2 rounded-lg transition-all duration-200 font-medium disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2";
  
  const variants = {
    primary: "bg-primary-600 text-white hover:bg-primary-700 active:bg-primary-800 shadow-sm hover:shadow-md focus-visible:ring-primary-600",
    secondary: "bg-slate-700 text-white hover:bg-slate-800 active:bg-slate-900 shadow-sm hover:shadow-md focus-visible:ring-slate-700",
    accent: "bg-accent-500 text-slate-900 hover:bg-accent-600 active:bg-accent-700 shadow-sm hover:shadow-md focus-visible:ring-accent-500",
    ghost: "bg-transparent text-slate-700 hover:bg-slate-100 active:bg-slate-200 focus-visible:ring-slate-500",
    outline: "bg-transparent border-2 border-slate-300 text-slate-700 hover:border-primary-600 hover:text-primary-600 hover:bg-primary-50 active:bg-primary-100 focus-visible:ring-primary-600"
  };
  
  const sizes = {
    sm: "px-3 py-1.5 text-sm",
    md: "px-4 py-2.5 text-base",
    lg: "px-6 py-3.5 text-lg"
  };

  return (
    <button 
      className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${isLoading ? 'opacity-80 cursor-wait' : ''} ${className}`}
      disabled={disabled}
      aria-disabled={isLoading || disabled}
      data-loading={isLoading}
      onClick={(e) => {
        if (isLoading) {
          e.preventDefault();
          return;
        }
        props.onClick?.(e);
      }}
      {...props}
    >
      {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
      {children}
    </button>
  );
}
