import React from 'react';
import { X, Trash2, CheckSquare, Layers, BookOpen, Atom, FlaskConical, Calculator } from 'lucide-react';
import { useSelection } from '../../context/SelectionContext';
import { SubjectBadge } from '../common/Badge';

export default function SelectedQuestionsDrawer({ isOpen, onClose, onPreviewQuestion }) {
  const {
    selectedQuestions,
    selectedCount,
    removeQuestion,
    clearAll,
    subjectDistribution,
    chapterDistribution,
  } = useSelection();

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-slate-900/40 backdrop-blur-xs flex justify-end animate-in fade-in duration-150">
      <div
        className="w-full max-w-md bg-white h-full shadow-2xl border-l border-slate-200 flex flex-col justify-between animate-in slide-in-from-right duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Drawer Header */}
        <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
          <div className="flex items-center gap-2">
            <CheckSquare className="w-5 h-5 text-brand-600" />
            <div>
              <h2 className="text-sm font-bold text-slate-900">Selected Questions</h2>
              <p className="text-xs text-slate-500">
                {selectedCount} question{selectedCount !== 1 ? 's' : ''} in current session
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {selectedCount > 0 && (
              <button
                onClick={clearAll}
                className="text-xs font-semibold text-rose-600 hover:text-rose-700 hover:bg-rose-50 px-2 py-1 rounded transition-colors"
                title="Clear all selected"
              >
                Clear All
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Drawer Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {selectedCount === 0 ? (
            <div className="h-64 flex flex-col items-center justify-center text-center p-6 text-slate-400">
              <CheckSquare className="w-12 h-12 stroke-1 text-slate-300 mb-2" />
              <p className="text-sm font-semibold text-slate-700">No questions selected</p>
              <p className="text-xs text-slate-400 mt-1 max-w-xs">
                Check the boxes on any question cards to assemble your question batch.
              </p>
            </div>
          ) : (
            <>
              {/* Subject Breakdown Card */}
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                <span className="block text-[11px] font-bold uppercase tracking-wider text-slate-500 mb-2">
                  Subject Breakdown
                </span>
                <div className="grid grid-cols-3 gap-2">
                  <div className="p-2 bg-white rounded-lg border border-slate-200 text-center">
                    <span className="block text-xs font-semibold text-blue-700">Physics</span>
                    <span className="text-base font-extrabold text-slate-900">
                      {subjectDistribution.PHYSICS || 0}
                    </span>
                  </div>
                  <div className="p-2 bg-white rounded-lg border border-slate-200 text-center">
                    <span className="block text-xs font-semibold text-emerald-700">Chemistry</span>
                    <span className="text-base font-extrabold text-slate-900">
                      {subjectDistribution.CHEMISTRY || 0}
                    </span>
                  </div>
                  <div className="p-2 bg-white rounded-lg border border-slate-200 text-center">
                    <span className="block text-xs font-semibold text-amber-700">Math</span>
                    <span className="text-base font-extrabold text-slate-900">
                      {subjectDistribution.MATHEMATICS || 0}
                    </span>
                  </div>
                </div>
              </div>

              {/* Selected List */}
              <div className="space-y-2">
                <span className="block text-[11px] font-bold uppercase tracking-wider text-slate-500">
                  Question Items ({selectedCount})
                </span>

                <div className="space-y-2">
                  {selectedQuestions.map((q, idx) => (
                    <div
                      key={q.id}
                      className="p-3 bg-white rounded-xl border border-slate-200 flex items-start justify-between gap-3 shadow-2xs hover:border-slate-300 transition-colors"
                    >
                      <div className="space-y-1 flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-[11px] font-mono font-bold text-slate-600">
                            #{idx + 1}
                          </span>
                          <SubjectBadge subject={q.subject} />
                          <span className="text-xs text-slate-500 font-medium">
                            {q.year}
                          </span>
                        </div>
                        <p className="text-xs font-semibold text-slate-800 truncate">
                          {q.chapter}
                        </p>
                        <p className="text-[11px] text-slate-500 line-clamp-2">
                          {q.questionContent?.content?.replace(/<[^>]+>/g, '') || ''}
                        </p>
                      </div>

                      <div className="flex flex-col items-end gap-1">
                        <button
                          onClick={() => removeQuestion(q.id)}
                          className="p-1 text-slate-400 hover:text-rose-600 rounded hover:bg-rose-50 transition-colors"
                          title="Remove from selection"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => onPreviewQuestion(q)}
                          className="text-[11px] font-semibold text-brand-600 hover:text-brand-700"
                        >
                          View
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Drawer Footer */}
        <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
          <span className="text-xs font-medium text-slate-600">
            Selection persists across page navigation
          </span>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-900 text-slate-50 rounded-lg text-xs font-semibold hover:bg-slate-800 transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}

