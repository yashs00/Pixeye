import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { questionApi } from '../services/api';
import StatsCards from '../components/dashboard/StatsCards';
import FilterBar from '../components/filters/FilterBar';
import QuestionCard from '../components/questions/QuestionCard';
import QuestionPreviewModal from '../components/questions/QuestionPreviewModal';
import SelectedQuestionsDrawer from '../components/questions/SelectedQuestionsDrawer';
import Pagination from '../components/questions/Pagination';
import { useSelection } from '../context/SelectionContext';
import { CheckSquare, Square, RefreshCw, AlertCircle, ArrowUpDown, Sparkles } from 'lucide-react';

const STUDIO_LINKS = [
  { subject: 'PHYSICS', chapter: 'Rotational Motion' },
  { subject: 'MATHEMATICS', chapter: 'Permutations And Combinations' },
  { subject: 'CHEMISTRY', chapter: 'Redox Reactions' },
];

export default function QuestionBankPage({ searchTerm, onOpenDrawer, isDrawerOpen, onCloseDrawer }) {
  const { isSelected, toggleQuestion, selectMultiple, deselectMultiple } = useSelection();

  // Filters state
  const [filters, setFilters] = useState({
    exam: 'ALL',
    subject: 'ALL',
    chapter: 'ALL',
    topic: 'ALL',
    year: 'ALL',
    difficulty: 'ALL',
    questionType: 'ALL',
    reviewStatus: 'ALL',
    sortBy: 'year',
    sortOrder: 'desc',
    page: 1,
    limit: 20,
  });

  // Debounced search query
  const [debouncedSearch, setDebouncedSearch] = useState(searchTerm);
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchTerm);
      setFilters((prev) => ({ ...prev, page: 1 }));
    }, 350);
    return () => clearTimeout(handler);
  }, [searchTerm]);

  // Preview modal state
  const [previewQuestion, setPreviewQuestion] = useState(null);

  // Fetch statistics
  const { data: statsData, isLoading: loadingStats } = useQuery({
    queryKey: ['statistics'],
    queryFn: questionApi.getStatistics,
    staleTime: 60000,
  });

  // Fetch questions query
  const queryParams = {
    ...filters,
    search: debouncedSearch,
  };

  const {
    data: questionsData,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['questions', queryParams],
    queryFn: () => questionApi.getQuestions(queryParams),
    keepPreviousData: true,
  });

  const questions = questionsData?.data || [];
  const pagination = questionsData?.pagination || { page: 1, totalPages: 1, total: 0, limit: 20 };

  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value,
      page: 1, // Reset page on filter change
    }));
  };

  const handleClearFilters = () => {
    setFilters({
      exam: 'ALL',
      subject: 'ALL',
      chapter: 'ALL',
      topic: 'ALL',
      year: 'ALL',
      difficulty: 'ALL',
      questionType: 'ALL',
      reviewStatus: 'ALL',
      sortBy: 'year',
      sortOrder: 'desc',
      page: 1,
      limit: filters.limit,
    });
  };

  // Select all on current page logic
  const allPageSelected = questions.length > 0 && questions.every((q) => isSelected(q.id));
  const somePageSelected = questions.some((q) => isSelected(q.id));

  const handleToggleSelectAllPage = () => {
    if (allPageSelected) {
      deselectMultiple(questions.map((q) => q.id));
    } else {
      selectMultiple(questions);
    }
  };

  return (
    <div className="space-y-6">
      {/* 1. Statistics Cards */}
      <StatsCards
        stats={statsData?.data}
        loading={loadingStats}
        activeSubject={filters.subject}
        onSelectSubject={(subj) => handleFilterChange('subject', subj)}
      />

      {/* Variant Studio entry point */}
      <div className="relative overflow-hidden flex flex-wrap items-center gap-3 rounded-xl bg-[#0d0f17] px-5 py-4 neon-border">
        <div aria-hidden className="absolute -top-16 -left-10 w-60 h-40 rounded-full bg-[#22e4ff]/25 blur-3xl" />
        <div aria-hidden className="absolute -bottom-16 right-10 w-72 h-40 rounded-full bg-[#8257ff]/35 blur-3xl" />
        <span className="relative flex items-center gap-2 text-sm font-semibold text-white">
          <Sparkles className="w-4 h-4 text-[#22e4ff]" /> Variant <span className="neon-text">Studio</span>
        </span>
        <span className="relative text-xs text-ink-300">Make verified variants of a question. Open a chapter, then click <b className="text-white">Make variants</b>:</span>
        <div className="relative flex flex-wrap gap-2">
          {STUDIO_LINKS.map((l) => (
            <button
              key={l.chapter}
              onClick={() => setFilters((prev) => ({ ...prev, subject: l.subject, chapter: l.chapter, topic: 'ALL', page: 1 }))}
              className={`rounded-full px-3 py-1 text-xs font-semibold transition ${
                filters.chapter === l.chapter
                  ? 'neon-btn text-white'
                  : 'border border-white/15 bg-ink-100/5 text-ink-200 hover:border-[#22e4ff]/60 hover:text-white'
              }`}
            >
              {l.chapter}
            </button>
          ))}
        </div>
      </div>

      {/* 2. Interactive Filter Bar */}
      <FilterBar
        filters={{ ...filters, search: debouncedSearch }}
        onFilterChange={handleFilterChange}
        onClearFilters={handleClearFilters}
        totalResults={pagination.total}
      />

      {/* 3. Action Toolbar: Select All on page, Sort order */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-white px-4 py-2.5 rounded-xl border border-slate-200 text-xs">
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 cursor-pointer font-semibold text-slate-700 select-none">
            <input
              type="checkbox"
              checked={allPageSelected}
              ref={(el) => {
                if (el) el.indeterminate = !allPageSelected && somePageSelected;
              }}
              onChange={handleToggleSelectAllPage}
              className="w-4 h-4 rounded text-brand-600 border-slate-300 focus:ring-brand-500 cursor-pointer"
            />
            <span>Select all on page ({questions.length})</span>
          </label>
        </div>

        {/* Sorting controls */}
        <div className="flex items-center gap-2 text-slate-600">
          <ArrowUpDown className="w-3.5 h-3.5 text-slate-400" />
          <span>Sort by:</span>
          <select
            value={filters.sortBy}
            onChange={(e) => handleFilterChange('sortBy', e.target.value)}
            className="bg-slate-50 border border-slate-200 rounded px-2 py-1 font-semibold text-slate-800 focus:outline-none"
          >
            <option value="year">Exam Year</option>
            <option value="chapter">Chapter</option>
            <option value="difficulty">Difficulty</option>
            <option value="createdAt">Date Imported</option>
          </select>

          <select
            value={filters.sortOrder}
            onChange={(e) => handleFilterChange('sortOrder', e.target.value)}
            className="bg-slate-50 border border-slate-200 rounded px-2 py-1 font-semibold text-slate-800 focus:outline-none"
          >
            <option value="desc">Descending</option>
            <option value="asc">Ascending</option>
          </select>
        </div>
      </div>

      {/* 4. Question Cards List / Skeleton / Empty States */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-44 bg-white rounded-xl border border-slate-200 p-6 animate-pulse space-y-3">
              <div className="flex gap-2">
                <div className="w-16 h-5 bg-slate-200 rounded" />
                <div className="w-20 h-5 bg-slate-200 rounded" />
                <div className="w-16 h-5 bg-slate-200 rounded" />
              </div>
              <div className="h-4 bg-slate-200 rounded w-5/6" />
              <div className="h-4 bg-slate-200 rounded w-2/3" />
            </div>
          ))}
        </div>
      ) : isError ? (
        <div className="bg-rose-50 border border-rose-200 rounded-xl p-8 text-center space-y-3">
          <AlertCircle className="w-10 h-10 text-rose-500 mx-auto" />
          <h3 className="text-sm font-bold text-rose-900">Failed to load questions from database</h3>
          <p className="text-xs text-rose-700 max-w-md mx-auto">{error?.message || 'Check your PostgreSQL connection'}</p>
          <button
            onClick={() => refetch()}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-rose-600 text-white rounded-lg text-xs font-semibold hover:bg-rose-700"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Retry Request
          </button>
        </div>
      ) : questions.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center space-y-3">
          <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto text-slate-400">
            <Square className="w-6 h-6 stroke-1" />
          </div>
          <h3 className="text-base font-bold text-slate-800">No matching questions found</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            Try adjusting your search criteria or clearing active filters to see more questions.
          </p>
          <button
            onClick={handleClearFilters}
            className="px-4 py-2 bg-slate-900 text-slate-50 rounded-lg text-xs font-semibold hover:bg-slate-800 transition-colors shadow-2xs"
          >
            Clear All Active Filters
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {questions.map((q, idx) => {
            const displayIndex = (pagination.page - 1) * pagination.limit + idx + 1;
            return (
              <QuestionCard
                key={q.id}
                question={q}
                index={displayIndex}
                isSelected={isSelected(q.id)}
                onToggleSelect={toggleQuestion}
                onPreview={(question) => setPreviewQuestion(question)}
              />
            );
          })}
        </div>
      )}

      {/* 5. Pagination */}
      <Pagination
        currentPage={pagination.page}
        totalPages={pagination.totalPages}
        pageSize={pagination.limit}
        totalResults={pagination.total}
        onPageChange={(page) => setFilters((prev) => ({ ...prev, page }))}
        onPageSizeChange={(limit) => setFilters((prev) => ({ ...prev, limit, page: 1 }))}
      />

      {/* 6. Preview Modal */}
      <QuestionPreviewModal
        question={previewQuestion}
        isOpen={!!previewQuestion}
        onClose={() => setPreviewQuestion(null)}
      />

      {/* 7. Selected Questions Drawer */}
      <SelectedQuestionsDrawer
        isOpen={isDrawerOpen}
        onClose={onCloseDrawer}
        onPreviewQuestion={(q) => {
          onCloseDrawer();
          setPreviewQuestion(q);
        }}
      />
    </div>
  );
}

