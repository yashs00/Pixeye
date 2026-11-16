import React from 'react';

export function SubjectBadge({ subject }) {
  const s = (subject || '').toUpperCase();
  const styles = {
    PHYSICS: 'bg-blue-50 text-blue-700 border-blue-200',
    CHEMISTRY: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    MATHEMATICS: 'bg-amber-50 text-amber-700 border-amber-200',
    BIOLOGY: 'bg-purple-50 text-purple-700 border-purple-200',
  };

  const style = styles[s] || 'bg-slate-100 text-slate-700 border-slate-200';

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border ${style}`}>
      {subject}
    </span>
  );
}

export function DifficultyBadge({ difficulty }) {
  const d = (difficulty || '').toUpperCase();
  const styles = {
    EASY: 'bg-green-50 text-green-700 border-green-200',
    MEDIUM: 'bg-yellow-50 text-yellow-800 border-yellow-200',
    HARD: 'bg-rose-50 text-rose-700 border-rose-200',
    UNKNOWN: 'bg-slate-100 text-slate-600 border-slate-200',
  };

  const style = styles[d] || styles.UNKNOWN;

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${style}`}>
      {difficulty}
    </span>
  );
}

export function TypeBadge({ type }) {
  const labelMap = {
    MCQ_SINGLE: 'Single Choice',
    MCQ_MULTIPLE: 'Multiple Choice',
    NUMERICAL: 'Numerical',
    INTEGER: 'Integer',
    OTHER: 'Other',
  };

  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
      {labelMap[type] || type}
    </span>
  );
}

export function ReviewStatusBadge({ status }) {
  const s = (status || '').toUpperCase();
  if (s === 'VERIFIED') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
        Verified
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
      <span className="w-1.5 h-1.5 rounded-full bg-amber-500"></span>
      Pending Review
    </span>
  );
}

