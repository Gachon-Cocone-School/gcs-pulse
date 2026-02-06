import React from 'react';

interface CardProps {
  children: React.ReactNode;
  variant?: 'default' | 'elevated' | 'bordered' | 'flat';
  padding?: 'none' | 'sm' | 'md' | 'lg';
  className?: string;
  onClick?: () => void;
}

export function Card({ 
  children, 
  variant = 'default', 
  padding = 'md',
  className = '',
  onClick
}: CardProps) {
  const variants = {
    default: "bg-white shadow-sm hover:shadow-md transition-shadow duration-200",
    elevated: "bg-white shadow-lg hover:shadow-xl transition-shadow duration-200",
    bordered: "bg-white border-2 border-slate-200 hover:border-primary-300 transition-colors duration-200",
    flat: "bg-slate-100"
  };
  
  const paddings = {
    none: "",
    sm: "p-4",
    md: "p-6",
    lg: "p-8"
  };

  return (
    <div 
      className={`rounded-xl ${variants[variant]} ${paddings[padding]} ${className}`}
      onClick={onClick}
    >
      {children}
    </div>
  );
}
