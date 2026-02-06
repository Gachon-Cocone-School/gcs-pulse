import React from 'react';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'primary' | 'accent' | 'success' | 'warning' | 'neutral';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function Badge({ 
  children, 
  variant = 'neutral', 
  size = 'md',
  className = '' 
}: BadgeProps) {
  const variants = {
    primary: "bg-primary-100 text-primary-800 border border-primary-200",
    accent: "bg-accent-100 text-accent-800 border border-accent-200",
    success: "bg-teal-100 text-teal-800 border border-teal-200",
    warning: "bg-coral-100 text-coral-800 border border-coral-200",
    neutral: "bg-slate-100 text-slate-700 border border-slate-200"
  };
  
  const sizes = {
    sm: "px-2 py-0.5 text-xs",
    md: "px-2.5 py-1 text-sm",
    lg: "px-3 py-1.5 text-base"
  };

  return (
    <span className={`inline-flex items-center rounded-full ${variants[variant]} ${sizes[size]} ${className}`}>
      {children}
    </span>
  );
}
