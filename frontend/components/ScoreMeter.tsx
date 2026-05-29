import { cn } from '@/lib/utils';
import React from 'react';

type ScoreLevel = {
  min: number;
  max: number;
  label: string;
  color: string;
};

const levels: ScoreLevel[] = [
  { min: 0, max: 15, label: 'Very Poor', color: 'bg-red-600' },
  { min: 16, max: 30, label: 'Poor', color: 'bg-red-400' },
  { min: 31, max: 50, label: 'Fair', color: 'bg-orange-400' },
  { min: 51, max: 70, label: 'Good', color: 'bg-blue-500' },
  { min: 71, max: 85, label: 'Very Good', color: 'bg-green-500' },
  { min: 86, max: 100, label: 'Excellent', color: 'bg-emerald-600' },
];

export default function ScoreMeter({ score }: { score: number }) {
  const level =
    levels.find((l) => score >= l.min && score <= l.max) ?? levels[0];

  return (
    <div className="w-full space-y-2">
      <div className="flex items-center justify-between">
        <span className={cn('px-1 text-sm font-semibold')}>
          {score > levels[levels.length - 1].min ? '🏆 ' : ''}
          {level.label}
        </span>
        <span className="text-sm font-medium text-gray-700">{score}/100</span>
      </div>
      <div className="h-3 w-full overflow-hidden rounded bg-gray-200">
        <div
          className={cn('h-full transition-all duration-300', level.color)}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );
}
