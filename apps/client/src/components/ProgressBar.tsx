import React from 'react';

interface ProgressBarProps {
  progress: number;
  label?: string;
  showPercentage?: boolean;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'primary' | 'accent' | 'gradient';
  className?: string;
}

export function ProgressBar({ 
  progress, 
  label, 
  showPercentage = true,
  size = 'md',
  variant = 'primary',
  className = '' 
}: ProgressBarProps) {
  const clampedProgress = Math.min(100, Math.max(0, progress));
  
  const sizes = {
    sm: "h-1.5",
    md: "h-2.5",
    lg: "h-3.5"
  };
  
  const variants = {
    primary: "bg-primary-600",
    accent: "bg-accent-500",
    gradient: "bg-gradient-to-r from-primary-600 to-accent-500"
  };

  return (
    <div className={`w-full ${className}`}>
      {(label || showPercentage) && (
        <div className="flex items-center justify-between mb-2">
          {label && <span className="text-sm text-slate-700">{label}</span>}
          {showPercentage && <span className="text-sm text-slate-600">{Math.round(clampedProgress)}%</span>}
        </div>
      )}
      <div className={`w-full bg-slate-200 rounded-full overflow-hidden ${sizes[size]}`}>
        <div 
          className={`${sizes[size]} ${variants[variant]} rounded-full transition-all duration-500 ease-out`}
          style={{ width: `${clampedProgress}%` }}
        />
      </div>
    </div>
  );
}
