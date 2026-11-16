import React from 'react';
import { BookOpen, Atom, FlaskConical, Calculator, TrendingUp } from 'lucide-react';

export default function StatsCards({ stats, loading, activeSubject, onSelectSubject }) {
  if (loading && !stats) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-24 bg-white rounded-xl border border-slate-200 animate-pulse p-4" />
        ))}
      </div>
    );
  }

  const total = stats?.totalQuestions || 0;
  const physics = stats?.bySubject?.PHYSICS || 0;
  const chemistry = stats?.bySubject?.CHEMISTRY || 0;
  const math = stats?.bySubject?.MATHEMATICS || 0;

  const cards = [
    {
      id: 'ALL',
      title: 'Total Questions',
      count: total,
      label: 'Verified JEE PYQs',
      icon: BookOpen,
      iconColor: 'text-indigo-600',
      bgColor: 'bg-indigo-50',
      borderColor: activeSubject === 'ALL' ? 'border-brand-500 ring-2 ring-brand-500/20' : 'border-slate-200',
    },
    {
      id: 'PHYSICS',
      title: 'Physics',
      count: physics,
      label: `${Math.round((physics / (total || 1)) * 100)}% of Bank`,
      icon: Atom,
      iconColor: 'text-blue-600',
      bgColor: 'bg-blue-50',
      borderColor: activeSubject === 'PHYSICS' ? 'border-blue-500 ring-2 ring-blue-500/20' : 'border-slate-200',
    },
    {
      id: 'CHEMISTRY',
      title: 'Chemistry',
      count: chemistry,
      label: `${Math.round((chemistry / (total || 1)) * 100)}% of Bank`,
      icon: FlaskConical,
      iconColor: 'text-emerald-600',
      bgColor: 'bg-emerald-50',
      borderColor: activeSubject === 'CHEMISTRY' ? 'border-emerald-500 ring-2 ring-emerald-500/20' : 'border-slate-200',
    },
    {
      id: 'MATHEMATICS',
      title: 'Mathematics',
      count: math,
      label: `${Math.round((math / (total || 1)) * 100)}% of Bank`,
      icon: Calculator,
      iconColor: 'text-amber-600',
      bgColor: 'bg-amber-50',
      borderColor: activeSubject === 'MATHEMATICS' ? 'border-amber-500 ring-2 ring-amber-500/20' : 'border-slate-200',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((card) => {
        const Icon = card.icon;
        const isActive = activeSubject === card.id;

        return (
          <button
            key={card.id}
            onClick={() => onSelectSubject(card.id)}
            className={`text-left bg-white p-4 rounded-xl border transition-all duration-150 hover:shadow-xs hover:border-slate-300 ${card.borderColor}`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                {card.title}
              </span>
              <div className={`w-8 h-8 rounded-lg ${card.bgColor} flex items-center justify-center`}>
                <Icon className={`w-4 h-4 ${card.iconColor}`} />
              </div>
            </div>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-2xl font-extrabold text-slate-900 tracking-tight">
                {card.count.toLocaleString()}
              </span>
              <span className="text-xs text-slate-500 font-medium">
                {card.label}
              </span>
            </div>
          </button>
        );
      })}
    </div>
  );
}

