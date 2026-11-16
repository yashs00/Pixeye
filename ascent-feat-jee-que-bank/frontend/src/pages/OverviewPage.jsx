import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { questionApi } from '../services/api';
import { BookOpen, Atom, FlaskConical, Calculator, Layers, TrendingUp, BarChart3 } from 'lucide-react';

export default function OverviewPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['statistics'],
    queryFn: questionApi.getStatistics,
  });

  const stats = data?.data;
  const total = stats?.totalQuestions || 0;

  if (isLoading) {
    return <div className="p-8 text-center text-slate-400 text-sm">Loading analytics overview...</div>;
  }

  const subjects = [
    { name: 'Physics', code: 'PHYSICS', count: stats?.bySubject?.PHYSICS || 0, color: 'bg-blue-500' },
    { name: 'Chemistry', code: 'CHEMISTRY', count: stats?.bySubject?.CHEMISTRY || 0, color: 'bg-emerald-500' },
    { name: 'Mathematics', code: 'MATHEMATICS', count: stats?.bySubject?.MATHEMATICS || 0, color: 'bg-amber-500' },
  ];

  const types = [
    { label: 'Single Choice (MCQ)', count: stats?.byType?.MCQ_SINGLE || 0, color: 'bg-indigo-500' },
    { label: 'Numerical / Integer', count: stats?.byType?.NUMERICAL || 0, color: 'bg-violet-500' },
    { label: 'Multiple Choice (MCQM)', count: stats?.byType?.MCQ_MULTIPLE || 0, color: 'bg-sky-500' },
  ];

  const difficulties = [
    { label: 'Easy', count: stats?.byDifficulty?.EASY || 0, color: 'bg-green-500' },
    { label: 'Medium', count: stats?.byDifficulty?.MEDIUM || 0, color: 'bg-yellow-500' },
    { label: 'Hard', count: stats?.byDifficulty?.HARD || 0, color: 'bg-rose-500' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs">
        <h2 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-brand-600" />
          Question Bank Distribution & Coverage
        </h2>
        <p className="text-xs text-slate-500 mt-1">
          Detailed metrics across 14,973 verified JEE Main Previous Year Questions (2002–2025)
        </p>
      </div>

      {/* Grid of breakdowns */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Subject Breakdown */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-4">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
            Subject Coverage
          </h3>
          <div className="space-y-3">
            {subjects.map((s) => {
              const pct = Math.round((s.count / (total || 1)) * 100);
              return (
                <div key={s.code} className="space-y-1">
                  <div className="flex justify-between text-xs font-semibold">
                    <span className="text-slate-700">{s.name}</span>
                    <span className="text-slate-900">{s.count.toLocaleString()} ({pct}%)</span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
                    <div className={`h-full ${s.color}`} style={{ width: `${pct}%` }}></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Question Type Breakdown */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-4">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
            Question Formats
          </h3>
          <div className="space-y-3">
            {types.map((t) => {
              const pct = Math.round((t.count / (total || 1)) * 100);
              return (
                <div key={t.label} className="space-y-1">
                  <div className="flex justify-between text-xs font-semibold">
                    <span className="text-slate-700">{t.label}</span>
                    <span className="text-slate-900">{t.count.toLocaleString()} ({pct}%)</span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
                    <div className={`h-full ${t.color}`} style={{ width: `${pct}%` }}></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Difficulty Breakdown */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-4">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
            Difficulty Distribution
          </h3>
          <div className="space-y-3">
            {difficulties.map((d) => {
              const pct = Math.round((d.count / (total || 1)) * 100);
              return (
                <div key={d.label} className="space-y-1">
                  <div className="flex justify-between text-xs font-semibold">
                    <span className="text-slate-700">{d.label}</span>
                    <span className="text-slate-900">{d.count.toLocaleString()} ({pct}%)</span>
                  </div>
                  <div className="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
                    <div className={`h-full ${d.color}`} style={{ width: `${pct}%` }}></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Top Chapters */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs space-y-3">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
          Top 10 Chapters by Question Volume
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          {(stats?.topChapters || []).map((c, i) => (
            <div key={c.chapter} className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs">
              <span className="text-[10px] font-mono font-bold text-slate-400">#{i + 1}</span>
              <p className="font-bold text-slate-800 truncate mt-0.5">{c.chapter}</p>
              <div className="mt-1 flex items-center justify-between text-[11px] text-slate-500">
                <span>{c.subject}</span>
                <span className="font-semibold text-brand-600">{c.count} Qs</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

