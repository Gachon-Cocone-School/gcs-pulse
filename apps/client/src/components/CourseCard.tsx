import React from 'react';
import { Card } from './Card';
import { Badge } from './Badge';
import { ProgressBar } from './ProgressBar';
import { Clock, Users, Star } from 'lucide-react';

interface CourseCardProps {
  title: string;
  instructor: string;
  thumbnail: string;
  category: string;
  duration: string;
  students: number;
  rating: number;
  progress?: number;
  price?: string;
  className?: string;
}

export function CourseCard({ 
  title, 
  instructor, 
  thumbnail, 
  category, 
  duration, 
  students, 
  rating,
  progress,
  price,
  className = '' 
}: CourseCardProps) {
  return (
    <Card variant="default" padding="none" className={`overflow-hidden group cursor-pointer ${className}`}>
      <div className="relative overflow-hidden aspect-video">
        <img 
          src={thumbnail} 
          alt={title}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
        />
        <div className="absolute top-3 left-3">
          <Badge variant="accent" size="sm">{category}</Badge>
        </div>
        {price && (
          <div className="absolute top-3 right-3">
            <div className="bg-slate-900/80 backdrop-blur-sm text-white px-3 py-1.5 rounded-lg">
              {price}
            </div>
          </div>
        )}
      </div>
      
      <div className="p-5">
        <h3 className="mb-2 line-clamp-2 group-hover:text-primary-600 transition-colors">
          {title}
        </h3>
        <p className="text-sm text-slate-600 mb-4">{instructor}</p>
        
        <div className="flex items-center gap-4 mb-4 text-sm text-slate-600">
          <div className="flex items-center gap-1.5">
            <Clock className="w-4 h-4" />
            <span>{duration}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Users className="w-4 h-4" />
            <span>{students.toLocaleString()}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Star className="w-4 h-4 fill-amber-400 text-amber-400" />
            <span>{rating}</span>
          </div>
        </div>
        
        {progress !== undefined && (
          <ProgressBar 
            progress={progress} 
            size="sm" 
            variant="gradient"
          />
        )}
      </div>
    </Card>
  );
}
