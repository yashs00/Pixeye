import React from 'react';
import katex from 'katex';
import DOMPurify from 'dompurify';

/**
 * Replace LaTeX markers in a string with KaTeX rendered HTML
 */
export function renderMathContent(rawText) {
  if (!rawText || typeof rawText !== 'string') return '';

  let processed = rawText;

  // 1. Replace double-dollar math $$ ... $$
  processed = processed.replace(/\$\$([\s\S]+?)\$\$/g, (match, equation) => {
    try {
      const cleanEq = equation
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&amp;/g, '&');
      return katex.renderToString(cleanEq.trim(), {
        displayMode: true,
        throwOnError: false,
      });
    } catch (e) {
      return `<span class="text-rose-500 font-mono text-xs">${equation}</span>`;
    }
  });

  // 2. Replace single-dollar math $ ... $ (ensuring not already inside HTML tag)
  processed = processed.replace(/\$([^\$\n]+?)\$/g, (match, equation) => {
    try {
      const cleanEq = equation
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&amp;/g, '&');
      return katex.renderToString(cleanEq.trim(), {
        displayMode: false,
        throwOnError: false,
      });
    } catch (e) {
      return `<span class="text-rose-500 font-mono text-xs">${equation}</span>`;
    }
  });

  // 3. Sanitize with DOMPurify allowing KaTeX and image markup
  const cleanHtml = DOMPurify.sanitize(processed, {
    ADD_TAGS: [
      'math', 'mrow', 'mi', 'mo', 'mn', 'ms', 'mtext', 'mfrac',
      'msqrt', 'mroot', 'msub', 'msup', 'msubsup', 'munder',
      'mover', 'munderover', 'mtable', 'mtr', 'mtd', 'semantics', 'annotation',
    ],
    ADD_ATTR: [
      'aria-hidden', 'encoding', 'display', 'class', 'style', 'src', 'alt', 'loading',
    ],
  });

  return cleanHtml;
}

/**
 * React Component to render sanitized math + HTML
 */
export default function MathView({ content, className = '' }) {
  if (!content) return null;
  const html = renderMathContent(content);

  return (
    <div
      className={`prose prose-slate max-w-none text-slate-800 leading-relaxed break-words overflow-x-auto ${className}`}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

