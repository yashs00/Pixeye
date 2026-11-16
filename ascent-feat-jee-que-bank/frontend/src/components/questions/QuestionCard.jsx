import React, { useState } from 'react';
import { Eye, ChevronDown, ChevronUp, Image as ImageIcon, Calendar, BookOpen, Sparkles } from 'lucide-react';
import { Link } from 'react-router-dom';

// chapters with verified variant patterns (CQSE engine)
export const STUDIO_CHAPTERS = new Set(['Rotational Motion', 'Permutations And Combinations', 'Redox Reactions']);
import { SubjectBadge, DifficultyBadge, TypeBadge, ReviewStatusBadge } from '../common/Badge';
import MathView from '../../utils/mathRenderer';

export default function QuestionCard({
  question,
  index,
  isSelected,
  onToggleSelect,
  onPreview,
}) {
  const [expanded, setExpanded] = useState(false);

  const qContent = question.questionContent?.content || '';
  const options = question.options || [];
  const media = question.media || [];
  const hasImages = media.length > 0;
  const isLong = qContent.length > 350;

  return (
    <div
      className={`bg-white rounded-xl border transition-all duration-200 hover:shadow-xs ${
        isSelected
          ? 'border-brand-500 ring-2 ring-brand-500/15 bg-brand-50/10'
          : 'border-slate-200/80 hover:border-slate-300'
      }`}
    >
      {/* Top Card Bar */}
      <div className="p-4 pb-3 border-b border-slate-100 flex flex-wrap items-center justify-between gap-2 bg-slate-50/50 rounded-t-xl">
        <div className="flex items-center gap-3">
          {/* Checkbox */}
          <input
            type="checkbox"
            checked={isSelected}
            onChange={() => onToggleSelect(question)}
            className="w-4 h-4 rounded text-brand-600 border-slate-300 focus:ring-brand-500 cursor-pointer"
          />

          <span className="text-xs font-bold text-slate-500 font-mono">
            #{index}
          </span>

          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-200/60 text-slate-700 font-medium">
            {question.externalId}
          </span>

          <SubjectBadge subject={question.subject} />
          <DifficultyBadge difficulty={question.difficulty} />
          <TypeBadge type={question.questionType} />
        </div>

        <div className="flex items-center gap-2 text-xs text-slate-500">
          {question.year > 0 && (
            <span className="flex items-center gap-1 font-semibold text-slate-700 bg-white px-2 py-0.5 rounded border border-slate-200">
              <Calendar className="w-3 h-3 text-slate-400" />
              {question.year}
            </span>
          )}
          {hasImages && (
            <span className="flex items-center gap-1 text-[11px] font-medium text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200">
              <ImageIcon className="w-3 h-3" />
              Diagram
            </span>
          )}
        </div>
      </div>

      {/* Body: Chapter, Paper title & Question content */}
      <div className="p-4 space-y-3">
        {/* Meta Context Line */}
        <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
          <span className="font-medium text-slate-800">
            {question.chapter}
          </span>
          {question.topic && (
            <>
              <span className="text-slate-300">•</span>
              <span className="text-slate-600">{question.topic}</span>
            </>
          )}
          {question.paperTitle && (
            <>
              <span className="text-slate-300">•</span>
              <span className="text-slate-500 italic truncate max-w-xs">{question.paperTitle}</span>
            </>
          )}
        </div>

        {/* Question Statement with KaTeX */}
        <div className="relative">
          <div
            className={`text-sm text-slate-900 transition-all ${
              !expanded && isLong ? 'max-h-28 overflow-hidden' : ''
            }`}
          >
            <MathView content={qContent} />
          </div>

          {!expanded && isLong && (
            <div className="absolute inset-x-0 bottom-0 h-10 bg-gradient-to-t from-slate-100 to-transparent pointer-events-none" />
          )}
        </div>

        {/* Expand / Collapse toggle */}
        {isLong && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-xs font-semibold text-brand-600 hover:text-brand-700 pt-1"
          >
            {expanded ? (
              <>
                <ChevronUp className="w-3.5 h-3.5" /> Show less
              </>
            ) : (
              <>
                <ChevronDown className="w-3.5 h-3.5" /> Show full statement
              </>
            )}
          </button>
        )}

        {/* Options Grid (for MCQs) */}
        {options && options.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-2">
            {options.map((opt) => (
              <div
                key={opt.id}
                className="flex items-start gap-2.5 p-2.5 rounded-lg border border-slate-200/80 bg-slate-50/40 text-xs"
              >
                <span className="w-5 h-5 rounded-md bg-white border border-slate-300 flex items-center justify-center font-bold text-slate-700 shrink-0 text-[11px]">
                  {opt.id}
                </span>
                <div className="flex-1 overflow-x-auto text-slate-800">
                  <MathView content={opt.content} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer Card Actions */}
      <div className="px-4 py-3 border-t border-slate-100 flex items-center justify-between text-xs bg-slate-50/30 rounded-b-xl">
        <div className="text-[11px] text-slate-400">
          Source: {question.sourceName}
        </div>

        <div className="flex items-center gap-2">
          {STUDIO_CHAPTERS.has(question.chapter) ? (
            <Link
              to={`/studio/${question.id}`}
              className="neon-btn flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-white font-semibold"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Make variants</span>
            </Link>
          ) : (
            <span
              title="Variants are available for Rotational Motion, Permutations And Combinations and Redox Reactions so far"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-dashed border-slate-200 text-slate-400 font-medium cursor-not-allowed select-none"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Variants soon</span>
            </span>
          )}
          <button
            onClick={() => onPreview(question)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-700 font-semibold hover:bg-slate-50 hover:border-slate-300 transition-colors shadow-2xs"
          >
            <Eye className="w-3.5 h-3.5 text-slate-500" />
            <span>Preview & Solution</span>
          </button>
        </div>
      </div>
    </div>
  );
}

