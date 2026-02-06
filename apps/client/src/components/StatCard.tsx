import React from 'react';
import { Card } from './Card';
import { LucideIcon } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  change?: string;
  icon: LucideIcon;
  trend?: 'up' | 'down' | 'neutral';
  className?: string;
}

export function StatCard({ 
  title, 
  value, 
  change, 
  icon: Icon, 
  trend = 'neutral',
  className = '' 
}: StatCardProps) {
  const trendColors = {
    up: 'text-teal-600',
    down: 'text-coral-600',
    neutral: 'text-slate-600'
  };

  return (
    <Card variant="default" className={className}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm text-slate-600 mb-1">{title}</p>
          <h3 className="mb-2">{value}</h3>
          {change && (
            <p className={`text-sm ${trendColors[trend]}`}>
              {change}
            </p>
          )}
        </div>
        <div className="p-3 bg-primary-100 rounded-xl">
          <Icon className="w-6 h-6 text-primary-700" />
        </div>
      </div>
    </Card>
  );
}
