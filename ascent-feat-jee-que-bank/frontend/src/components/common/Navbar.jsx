import React from 'react';
import { Search, CheckSquare, Bell, User } from 'lucide-react';
import { useSelection } from '../../context/SelectionContext';

export default function Navbar({
  searchTerm,
  onSearchChange,
  onOpenSelectionDrawer,
  totalQuestions,
}) {
  const { selectedCount } = useSelection();

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between sticky top-0 z-10">
      {/* Title / Description */}
      <div className="flex items-center gap-4">
        <div>
          <h1 className="text-lg font-bold text-slate-900 leading-tight">Question Bank</h1>
          <p className="text-xs text-slate-500">
            Browse, preview and curate authentic JEE/NEET previous year questions
          </p>
        </div>
      </div>

      {/* Global Search Bar */}
      <div className="flex-1 max-w-lg mx-6">
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search questions by statement, formula, topic, ID..."
            className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-900 placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 transition-all"
          />
          {searchTerm && (
            <button
              onClick={() => onSearchChange('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-400 hover:text-slate-600"
            >
              Clear
            </button>
          )}
        </div>
      </div>

      {/* Action items */}
      <div className="flex items-center gap-3">
        {/* Selection Pill */}
        <button
          onClick={onOpenSelectionDrawer}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-sm font-semibold transition-all ${
            selectedCount > 0
              ? 'bg-brand-50 border-brand-300 text-brand-700 shadow-xs hover:bg-brand-100'
              : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
          }`}
        >
          <CheckSquare className="w-4 h-4 text-brand-600" />
          <span>Selected</span>
          <span className="px-1.5 py-0.2 rounded-full text-xs bg-brand-600 text-white font-bold">
            {selectedCount}
          </span>
        </button>

        <div className="h-5 w-px bg-slate-200 mx-1"></div>

        {/* Teacher profile badge */}
        <div className="flex items-center gap-2 pl-1">
          <div className="w-8 h-8 rounded-full bg-slate-100 border border-slate-300 flex items-center justify-center text-slate-600">
            <User className="w-4 h-4" />
          </div>
          <div className="hidden md:block text-left text-xs">
            <span className="block font-semibold text-slate-800">Faculty Reviewer</span>
            <span className="block text-[11px] text-slate-400">JEE Physics & Math</span>
          </div>
        </div>
      </div>
    </header>
  );
}

