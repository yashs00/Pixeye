import React from 'react';
import { X, CheckCircle, HelpCircle, Calendar, BookOpen, Layers, ShieldCheck, Copy, Check } from 'lucide-react';
import { SubjectBadge, DifficultyBadge, TypeBadge, ReviewStatusBadge } from '../common/Badge';
import MathView from '../../utils/mathRenderer';

export default function QuestionPreviewModal({ question, isOpen, onClose }) {
  const [copied, setCopied] = React.useState(false);

  if (!isOpen || !question) return null;

  const qContent = question.questionContent?.content || '';
  const options = question.options || [];
  const correctAnswers = question.correctAnswers || [];
  const explanation = question.explanation?.content || question.explanation || '';
  const media = question.media || [];

  const handleCopyId = () => {
    navigator.clipboard.writeText(question.externalId);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 sm:p-6 animate-in fade-in duration-150">
      <div
        className="bg-white rounded-2xl shadow-2xl border border-slate-200 max-w-3xl w-full max-h-[90vh] flex flex-col overflow-hidden animate-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/70">
          <div className="flex items-center gap-3">
            <span className="font-mono text-xs px-2.5 py-1 rounded bg-slate-200 font-semibold text-slate-800">
              {question.externalId}
            </span>
            <button
              onClick={handleCopyId}
              className="text-xs text-slate-500 hover:text-slate-800 flex items-center gap-1 font-medium"
              title="Copy Question ID"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Copied' : 'Copy ID'}</span>
            </button>
            <SubjectBadge subject={question.subject} />
            <DifficultyBadge difficulty={question.difficulty} />
            <TypeBadge type={question.questionType} />
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1 text-slate-800">
          {/* Metadata banner */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3 bg-slate-50 rounded-xl border border-slate-200/80 text-xs">
            <div>
              <span className="block text-[11px] font-semibold text-slate-400">Chapter</span>
              <span className="font-semibold text-slate-800">{question.chapter}</span>
            </div>
            <div>
              <span className="block text-[11px] font-semibold text-slate-400">Topic</span>
              <span className="font-medium text-slate-700">{question.topic || 'General'}</span>
            </div>
            <div>
              <span className="block text-[11px] font-semibold text-slate-400">Exam / Year</span>
              <span className="font-medium text-slate-700">{question.exam} ({question.year})</span>
            </div>
            <div>
              <span className="block text-[11px] font-semibold text-slate-400">Content Status</span>
              <ReviewStatusBadge status={question.reviewStatus} />
            </div>
          </div>

          {question.paperTitle && (
            <div className="text-xs text-slate-500 italic">
              Paper: {question.paperTitle}
            </div>
          )}

          {/* Question Statement */}
          <div className="space-y-2">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Question Statement
            </h3>
            <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-2xs">
              <MathView content={qContent} />
            </div>
          </div>

          {/* Options Section */}
          {options && options.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Options
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {options.map((opt) => {
                  const isCorrect = correctAnswers.includes(opt.id);
                  return (
                    <div
                      key={opt.id}
                      className={`p-3 rounded-xl border transition-all text-xs flex items-start gap-3 ${
                        isCorrect
                          ? 'bg-emerald-50/60 border-emerald-300 ring-1 ring-emerald-400'
                          : 'bg-white border-slate-200'
                      }`}
                    >
                      <span
                        className={`w-6 h-6 rounded-md flex items-center justify-center font-bold shrink-0 ${
                          isCorrect
                            ? 'bg-emerald-600 text-white'
                            : 'bg-slate-100 text-slate-700 border border-slate-300'
                        }`}
                      >
                        {opt.id}
                      </span>
                      <div className="flex-1 overflow-x-auto text-slate-900">
                        <MathView content={opt.content} />
                      </div>
                      {isCorrect && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-emerald-100 text-emerald-800">
                          Correct
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Teacher Solution & Explanation */}
          <div className="space-y-2 pt-2">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-700 flex items-center gap-1.5">
                <CheckCircle className="w-4 h-4 text-emerald-600" />
                Teacher Key & Step-by-Step Solution
              </h3>
              {correctAnswers.length > 0 && (
                <div className="text-xs font-bold text-emerald-800 bg-emerald-100 px-2.5 py-1 rounded-md">
                  Correct Answer: {correctAnswers.join(', ')}
                </div>
              )}
            </div>

            {explanation ? (
              <div className="p-4 bg-emerald-50/30 rounded-xl border border-emerald-200/80">
                <MathView content={explanation} />
              </div>
            ) : (
              <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-500 italic">
                No formal explanation provided in the source repository for this question.
              </div>
            )}
          </div>

          {/* Legal Attribution Notice */}
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-[11px] text-slate-500 flex items-start gap-2">
            <ShieldCheck className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
            <div>
              <p className="font-semibold text-slate-700">Licensing and Attribution:</p>
              <p>
                Imported from {question.sourceName}. Unverified third-party content is maintained under
                PIXEYE's teacher review workflow. Not for public commercial redistribution without applicable rights.
              </p>
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-slate-200 bg-slate-50 flex items-center justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-900 text-slate-50 rounded-lg text-sm font-semibold hover:bg-slate-800 transition-colors shadow-2xs"
          >
            Close Preview
          </button>
        </div>
      </div>
    </div>
  );
}

