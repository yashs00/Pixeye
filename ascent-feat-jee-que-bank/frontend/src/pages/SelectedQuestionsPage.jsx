import React, { useState } from 'react';
import { useSelection } from '../context/SelectionContext';
import QuestionCard from '../components/questions/QuestionCard';
import QuestionPreviewModal from '../components/questions/QuestionPreviewModal';
import { CheckSquare, Trash2, Download, Copy, Check, ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function SelectedQuestionsPage() {
  const {
    selectedQuestions,
    selectedCount,
    toggleQuestion,
    removeQuestion,
    clearAll,
    subjectDistribution,
    chapterDistribution,
  } = useSelection();

  const [previewQuestion, setPreviewQuestion] = useState(null);
  const [copied, setCopied] = useState(false);

  const handleExportJson = () => {
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(selectedQuestions, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `ascent_selected_${selectedCount}_questions.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const handleCopyIds = () => {
    const ids = selectedQuestions.map((q) => q.externalId).join('\n');
    navigator.clipboard.writeText(ids);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (selectedCount === 0) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl p-16 text-center space-y-4">
        <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center mx-auto text-slate-400">
          <CheckSquare className="w-8 h-8 stroke-1 text-slate-300" />
        </div>
        <h2 className="text-lg font-bold text-slate-800">No questions selected yet</h2>
        <p className="text-xs text-slate-500 max-w-md mx-auto">
          Navigate to the Question Bank and select questions using the checkboxes on each card to build your test set.
        </p>
        <Link
          to="/"
          className="inline-flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg text-xs font-semibold hover:bg-brand-700 transition-colors shadow-xs"
        >
          <ArrowLeft className="w-4 h-4" /> Go to Question Bank
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">
            Selected Questions ({selectedCount})
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Teacher selection session preserved across page navigation
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleCopyIds}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-2xs"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Copied' : 'Copy Question IDs'}</span>
          </button>

          <button
            onClick={handleExportJson}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-50 border border-brand-200 rounded-lg text-xs font-semibold text-brand-700 hover:bg-brand-100 shadow-2xs"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export JSON</span>
          </button>

          <button
            onClick={clearAll}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-rose-50 border border-rose-200 rounded-lg text-xs font-semibold text-rose-700 hover:bg-rose-100 shadow-2xs"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Clear Selection</span>
          </button>
        </div>
      </div>

      {/* Distribution Summary */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
            Subject Distribution
          </h3>
          <div className="space-y-2">
            {Object.entries(subjectDistribution).map(([subj, cnt]) => (
              <div key={subj} className="flex items-center justify-between text-xs">
                <span className="font-semibold text-slate-700">{subj}</span>
                <span className="px-2 py-0.5 rounded-full font-bold bg-slate-100 text-slate-800">
                  {cnt} ({Math.round((cnt / selectedCount) * 100)}%)
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-2xs">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3">
            Chapter Distribution (Top)
          </h3>
          <div className="space-y-1.5 max-h-36 overflow-y-auto">
            {Object.entries(chapterDistribution).map(([chap, cnt]) => (
              <div key={chap} className="flex items-center justify-between text-xs py-0.5">
                <span className="text-slate-600 truncate max-w-xs">{chap}</span>
                <span className="font-bold text-slate-800">{cnt}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Questions List */}
      <div className="space-y-4">
        {selectedQuestions.map((q, idx) => (
          <QuestionCard
            key={q.id}
            question={q}
            index={idx + 1}
            isSelected={true}
            onToggleSelect={() => removeQuestion(q.id)}
            onPreview={(question) => setPreviewQuestion(question)}
          />
        ))}
      </div>

      <QuestionPreviewModal
        question={previewQuestion}
        isOpen={!!previewQuestion}
        onClose={() => setPreviewQuestion(null)}
      />
    </div>
  );
}

