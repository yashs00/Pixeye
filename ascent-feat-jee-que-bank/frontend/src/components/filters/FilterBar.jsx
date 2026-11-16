import React, { useEffect, useState } from 'react';
import { Filter, X, ChevronDown, RefreshCw, AlertCircle } from 'lucide-react';
import { filterApi } from '../../services/api';

export default function FilterBar({
  filters,
  onFilterChange,
  onClearFilters,
  totalResults,
}) {
  const [chapters, setChapters] = useState([]);
  const [topics, setTopics] = useState([]);
  const [years, setYears] = useState([]);
  const [loadingChapters, setLoadingChapters] = useState(false);
  const [loadingTopics, setLoadingTopics] = useState(false);

  // Fetch chapters when subject changes
  useEffect(() => {
    let isMounted = true;
    setLoadingChapters(true);
    filterApi
      .getChapters(filters.subject !== 'ALL' ? filters.subject : null)
      .then((res) => {
        if (isMounted && res.success) {
          setChapters(res.data);
        }
      })
      .catch(console.error)
      .finally(() => {
        if (isMounted) setLoadingChapters(false);
      });
    return () => {
      isMounted = false;
    };
  }, [filters.subject]);

  // Fetch topics when chapter or subject changes
  useEffect(() => {
    let isMounted = true;
    if (filters.chapter && filters.chapter !== 'ALL') {
      setLoadingTopics(true);
      filterApi
        .getTopics(filters.chapter, filters.subject !== 'ALL' ? filters.subject : null)
        .then((res) => {
          if (isMounted && res.success) {
            setTopics(res.data);
          }
        })
        .catch(console.error)
        .finally(() => {
          if (isMounted) setLoadingTopics(false);
        });
    } else {
      setTopics([]);
    }
    return () => {
      isMounted = false;
    };
  }, [filters.chapter, filters.subject]);

  // Fetch years
  useEffect(() => {
    let isMounted = true;
    filterApi
      .getYears()
      .then((res) => {
        if (isMounted && res.success) {
          setYears(res.data);
        }
      })
      .catch(console.error);
    return () => {
      isMounted = false;
    };
  }, []);

  const hasActiveFilters =
    filters.subject !== 'ALL' ||
    filters.chapter !== 'ALL' ||
    filters.topic !== 'ALL' ||
    filters.year !== 'ALL' ||
    filters.difficulty !== 'ALL' ||
    filters.questionType !== 'ALL' ||
    filters.exam !== 'ALL' ||
    (filters.search && filters.search.trim() !== '');

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-2xs space-y-3">
      {/* Top Filter Header */}
      <div className="flex items-center justify-between pb-3 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-brand-600" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-700">
            Interactive Filters
          </span>
          <span className="text-xs font-medium text-slate-500">
            ({totalResults?.toLocaleString() || 0} questions match)
          </span>
        </div>

        {hasActiveFilters && (
          <button
            onClick={onClearFilters}
            className="flex items-center gap-1.5 text-xs font-semibold text-rose-600 hover:text-rose-700 hover:bg-rose-50 px-2.5 py-1 rounded transition-colors"
          >
            <X className="w-3.5 h-3.5" />
            Clear All Filters
          </button>
        )}
      </div>

      {/* Primary Filter Selectors Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {/* Exam */}
        <div>
          <label className="block text-[11px] font-semibold text-slate-500 mb-1">
            Exam
          </label>
          <select
            value={filters.exam}
            onChange={(e) => onFilterChange('exam', e.target.value)}
            className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-medium text-slate-700 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
          >
            <option value="ALL">All Exams</option>
            <option value="JEE_MAIN">JEE Main</option>
            <option value="JEE_ADVANCED">JEE Advanced</option>
            <option value="NEET">NEET</option>
          </select>
        </div>

        {/* Subject */}
        <div>
          <label className="block text-[11px] font-semibold text-slate-500 mb-1">
            Subject
          </label>
          <select
            value={filters.subject}
            onChange={(e) => {
              onFilterChange('subject', e.target.value);
              onFilterChange('chapter', 'ALL');
              onFilterChange('topic', 'ALL');
            }}
            className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-medium text-slate-700 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
          >
            <option value="ALL">All Subjects</option>
            <option value="PHYSICS">Physics</option>
            <option value="CHEMISTRY">Chemistry</option>
            <option value="MATHEMATICS">Mathematics</option>
          </select>
        </div>

        {/* Chapter (Dynamic) */}
        <div>
          <label className="block text-[11px] font-semibold text-slate-500 mb-1">
            Chapter {loadingChapters && <span className="text-slate-400 font-normal">...</span>}
          </label>
          <select
            value={filters.chapter}
            onChange={(e) => {
              onFilterChange('chapter', e.target.value);
              onFilterChange('topic', 'ALL');
            }}
            className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-medium text-slate-700 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 truncate"
          >
            <option value="ALL">All Chapters ({chapters.length})</option>
            {chapters.map((c) => (
              <option key={c.name} value={c.name}>
                {c.name} ({c.count})
              </option>
            ))}
          </select>
        </div>

        {/* Topic (Dynamic) */}
        <div>
          <label className="block text-[11px] font-semibold text-slate-500 mb-1">
            Topic {loadingTopics && <span className="text-slate-400 font-normal">...</span>}
          </label>
          <select
            value={filters.topic}
            onChange={(e) => onFilterChange('topic', e.target.value)}
            disabled={!topics || topics.length === 0}
            className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-medium text-slate-700 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 disabled:opacity-50 truncate"
          >
            <option value="ALL">
              {topics.length > 0 ? `All Topics (${topics.length})` : 'Select a chapter first'}
            </option>
            {topics.map((t) => (
              <option key={t.name} value={t.name}>
                {t.name} ({t.count})
              </option>
            ))}
          </select>
        </div>

        {/* Year */}
        <div>
          <label className="block text-[11px] font-semibold text-slate-500 mb-1">
            Year
          </label>
          <select
            value={filters.year}
            onChange={(e) => onFilterChange('year', e.target.value)}
            className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-medium text-slate-700 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
          >
            <option value="ALL">All Years</option>
            {years.map((y) => (
              <option key={y.year} value={y.year}>
                {y.year} ({y.count})
              </option>
            ))}
          </select>
        </div>

        {/* Difficulty */}
        <div>
          <label className="block text-[11px] font-semibold text-slate-500 mb-1">
            Difficulty
          </label>
          <select
            value={filters.difficulty}
            onChange={(e) => onFilterChange('difficulty', e.target.value)}
            className="w-full bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs font-medium text-slate-700 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500"
          >
            <option value="ALL">All Difficulties</option>
            <option value="EASY">Easy</option>
            <option value="MEDIUM">Medium</option>
            <option value="HARD">Hard</option>
            <option value="UNKNOWN">Unknown</option>
          </select>
        </div>
      </div>

      {/* Secondary Row: Question Type & Review Filter */}
      <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-100 text-xs">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-slate-500">Type:</span>
          {['ALL', 'MCQ_SINGLE', 'MCQ_MULTIPLE', 'NUMERICAL'].map((t) => {
            const labels = {
              ALL: 'All Types',
              MCQ_SINGLE: 'Single Choice',
              MCQ_MULTIPLE: 'Multiple Choice',
              NUMERICAL: 'Numerical',
            };
            const active = filters.questionType === t;
            return (
              <button
                key={t}
                onClick={() => onFilterChange('questionType', t)}
                className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                  active
                    ? 'bg-slate-900 text-slate-50 shadow-xs'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                }`}
              >
                {labels[t]}
              </button>
            );
          })}
        </div>

        {/* Legal Disclaimer Pill */}
        <div className="flex items-center gap-1.5 text-[11px] text-slate-500 bg-slate-50 px-2.5 py-1 rounded-md border border-slate-200">
          <AlertCircle className="w-3.5 h-3.5 text-slate-400" />
          <span>Source: Verified JEE PYQs (AIEEE 2002–2025)</span>
        </div>
      </div>
    </div>
  );
}

