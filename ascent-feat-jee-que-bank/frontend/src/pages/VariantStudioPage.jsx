import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ArrowLeft, Sparkles, Check, X, Plus, ChevronRight, ChevronUp, FlaskConical, FileText,
  Loader2, AlertTriangle, ShieldCheck, ShieldAlert, Save, Command, Keyboard,
} from 'lucide-react';
import MathView from '../utils/mathRenderer';
import { variantApi } from '../services/api';
import PixeyeLogo from '../components/common/PixeyeLogo';

/* Variant Studio — full-screen dark workspace. Every variant shown has passed the CQSE engine's checks. */

const BATCH = 5;

const TIER = {
  source: 'Made from this question',
  same: 'Same kind of question',
  related: 'Related pattern',
  none: 'Closest available pattern',
};

const DIFF = { EASY: 1, MEDIUM: 2, HARD: 3 };
const titleCase = (s) => s.charAt(0).toUpperCase() + s.slice(1);
const prettyFamily = (id) => titleCase(id.split('.').slice(1).join(' ').replace(/_/g, ' '));
const trapText = (label) => titleCase(label.toLowerCase());
const examLine = (q) => [q.exam?.replace('_', ' ').replace(/\bMAIN\b/, 'Main').replace(/\bJEE\b/, 'JEE'), q.year > 0 ? q.year : null]
  .filter(Boolean).join(' · ');

/* ------------------------------------------------------------------ atoms */

function Kbd({ children, tone = 'dark' }) {
  const cls = tone === 'light'
    ? 'border-white/30 text-white/80'
    : 'border-ink-600 text-ink-400';
  return (
    <kbd className={`inline-flex items-center justify-center min-w-[20px] h-5 px-1 rounded-md border text-[10.5px] font-medium leading-none ${cls}`}>
      {children}
    </kbd>
  );
}

function Dots({ level }) {
  const n = DIFF[level] || 0;
  return (
    <span className="inline-flex items-center gap-1" aria-hidden>
      {[1, 2, 3].map((i) => (
        <span key={i} className={`w-1.5 h-1.5 rounded-full ${i <= n ? 'bg-amber-700' : 'bg-ink-600'}`} />
      ))}
    </span>
  );
}

function Verified({ status }) {
  const ok = status === 'VERIFIED';
  return (
    <span
      title={ok
        ? 'Answer derived by two independent methods; every option checked'
        : 'Answer and every option verified; a teacher signs this pattern off once'}
      className={`vs-pop inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[12.5px] font-medium ${
        ok ? 'border-emerald-500/30 bg-emerald-500/[0.08] text-emerald-700'
          : 'border-amber-600/30 bg-amber-600/[0.08] text-amber-800'
      }`}
    >
      {ok ? <Check className="w-3.5 h-3.5" /> : <ShieldAlert className="w-3.5 h-3.5" />}
      {ok ? 'Verified' : 'Verified · sign-off pending'}
    </span>
  );
}

function Skeleton({ delay = 0 }) {
  return (
    <div className="vs-rise rounded-2xl border border-white/[0.07] bg-ink-900 p-6 space-y-5" style={{ animationDelay: `${delay}ms` }}>
      <div className="flex justify-between"><div className="vs-skel h-4 w-32 rounded" /><div className="vs-skel h-7 w-24 rounded-full" /></div>
      <div className="space-y-2.5"><div className="vs-skel h-4 w-11/12 rounded" /><div className="vs-skel h-4 w-2/3 rounded" /></div>
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">{[0, 1, 2, 3].map((i) => <div key={i} className="vs-skel h-14 rounded-xl" />)}</div>
      <p className="flex items-center gap-2 text-xs text-ink-500"><Loader2 className="w-3.5 h-3.5 animate-spin" /> Solving two ways and checking every option…</p>
    </div>
  );
}

/* ------------------------------------------------------------------ option */

function Option({ opt, correct, trap }) {
  const [open, setOpen] = useState(false);
  return (
    <div className={`rounded-xl border transition-colors ${
      correct
        ? 'border-emerald-600/50 bg-emerald-600/[0.07] neon-correct'
        : 'border-white/[0.07] bg-ink-100/[0.02] hover:border-white/[0.16]'
    }`}>
      <button
        type="button"
        onClick={() => trap && setOpen((o) => !o)}
        aria-expanded={trap ? open : undefined}
        className={`w-full flex items-center gap-3.5 px-3.5 py-3 text-left ${trap ? 'cursor-pointer' : 'cursor-default'}`}
      >
        <span className={`w-8 h-8 shrink-0 rounded-lg flex items-center justify-center text-[13px] font-semibold ${
          correct ? 'bg-emerald-500/15 text-emerald-700' : 'bg-ink-100/[0.06] text-ink-200'
        }`}>{opt.id}</span>
        <div className="flex-1 min-w-0 overflow-x-auto text-[17px] text-ink-100"><MathView content={opt.content} /></div>
        {correct && (
          <span className="shrink-0 inline-flex items-center gap-1 text-[13.5px] text-emerald-700"><Check className="w-4 h-4" />Correct</span>
        )}
        {trap && (
          <span title={trap.why} className="shrink-0 max-w-[58%] truncate rounded-md bg-amber-600/[0.09] px-2.5 py-1 text-[13px] text-amber-800/90">
            Trap · {trapText(trap.label)}
          </span>
        )}
      </button>
      {trap && (
        <div className="vs-collapse" data-open={open}>
          <div>
            <div className="mx-3.5 mb-3.5 rounded-lg border border-amber-600/15 bg-amber-600/[0.04] px-3.5 py-3 text-[13px] leading-relaxed space-y-1.5">
              <p><span className="text-amber-800">Why students pick it · </span><span className="text-ink-300">{trap.why}</span></p>
              <p><span className="text-ink-100">Why it's wrong · </span><span className="text-ink-400">{trap.wrong}</span></p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ variant card */

function VariantCard({ v, n, index, focused, accepted, leaving, solution, onSolution, onAccept, onReject, onMore, refCb }) {
  const row = v.row;
  const correct = new Set(row.correctAnswers || []);
  const numerical = row.questionType === 'NUMERICAL';
  const sim = row.sourceMetadata?.originality?.max_similarity_to_bank;
  const diff = row.difficulty || 'UNKNOWN';
  return (
    <article
      ref={refCb}
      className={`vs-rise rounded-2xl border bg-ink-900/80 backdrop-blur transition-[border-color,box-shadow] duration-200 ${leaving ? 'vs-out' : ''} ${
        accepted ? 'border-emerald-500/50 shadow-[0_0_0_1px_rgba(16,185,129,0.25)]'
          : focused ? 'border-transparent neon-border neon-ring'
            : 'border-white/[0.07] hover:border-white/[0.12]'
      }`}
      style={{ animationDelay: `${Math.min(index, 5) * 70}ms` }}
    >
      <header className="flex flex-wrap items-center justify-between gap-3 px-6 sm:px-8 py-5 border-b border-white/[0.06]">
        <div className="flex items-center gap-3 text-[14.5px] text-ink-400">
          <span className="font-medium tracking-wide">VAR-{String(n).padStart(2, '0')}</span>
          <span className="h-4 w-px bg-ink-700" />
          <Dots level={diff} />
          <span>{titleCase(diff.toLowerCase())}</span>
          {numerical && <span className="rounded-md bg-ink-100/[0.05] px-2 py-0.5 text-xs text-ink-300">Numerical</span>}
        </div>
        <Verified status={v.status} />
      </header>

      <div className="px-6 sm:px-8 pt-6 pb-5 space-y-6">
        <div className="text-[18px] leading-[1.75] text-ink-100 max-w-[78ch]"><MathView content={row.questionContent?.content} /></div>

        {numerical ? (
          <div className="inline-flex items-center gap-3 rounded-xl border border-emerald-500/40 bg-emerald-500/[0.06] px-4 py-3">
            <span className="text-ink-400 text-sm">Answer</span>
            <span className="text-[18px] font-semibold text-emerald-700 tabular-nums">{row.answer?.value}</span>
            <Check className="w-4 h-4 text-emerald-700" />
          </div>
        ) : (
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
            {(row.options || []).map((o) => (
              <Option key={o.id} opt={o} correct={correct.has(o.id)} trap={!correct.has(o.id) ? v.traps?.[o.id] : null} />
            ))}
          </div>
        )}

        <div>
          <button type="button" onClick={onSolution} aria-expanded={solution}
            className="inline-flex items-center gap-2.5 py-1 text-[16px] text-ink-300 hover:text-white transition-colors">
            <ChevronRight className={`w-4 h-4 transition-transform duration-200 ${solution ? 'rotate-90' : ''}`} />
            Worked solution
          </button>
          <div className="vs-collapse" data-open={solution}>
            <div>
              <div className="mt-3 ml-6 border-l border-iris-400/30 pl-5 text-[15.5px] leading-[1.8] text-ink-300 max-w-[80ch]">
                <MathView content={row.explanation?.content} />
              </div>
            </div>
          </div>
        </div>
      </div>

      <footer className="flex flex-wrap items-center justify-between gap-3 px-6 sm:px-8 py-4 border-t border-white/[0.06]">
        <span className="inline-flex items-center gap-2 text-[13.5px] text-ink-500" title="Word overlap with the closest question already in the bank">
          <Command className="w-3.5 h-3.5" />
          {typeof sim === 'number' ? `${Math.round((1 - sim) * 100)}% new wording vs. bank` : 'Select for review'}
        </span>
        <div className="flex items-center gap-2.5">
          <button onClick={onReject}
            className="inline-flex items-center gap-2 rounded-xl px-3.5 py-2.5 text-[15px] text-ink-300 hover:text-rose-700 hover:bg-rose-500/[0.06] transition">
            <X className="w-4 h-4" /> Reject <Kbd>R</Kbd>
          </button>
          <button onClick={onAccept}
            className={`inline-flex items-center gap-2 rounded-xl px-5 py-2.5 text-[15px] font-medium text-white active:scale-[0.98] transition ${
              accepted ? 'bg-emerald-500 hover:bg-emerald-600 neon-correct' : 'neon-btn'
            }`}>
            <Check className="w-4 h-4" /> {accepted ? 'Accepted' : 'Accept'} <Kbd tone="light">A</Kbd>
          </button>
          <button onClick={onMore}
            className="inline-flex items-center gap-2 rounded-xl border border-white/[0.1] px-4 py-2.5 text-[15px] text-ink-200 hover:bg-ink-100/[0.04] hover:border-white/[0.18] transition">
            <Plus className="w-4 h-4" /> More like this
          </button>
        </div>
      </footer>
    </article>
  );
}

/* ------------------------------------------------------------------ page */

export default function VariantStudioPage() {
  const { questionId } = useParams();
  const { data, isLoading, error } = useQuery({
    queryKey: ['variant-match', questionId],
    queryFn: () => variantApi.match(questionId),
    retry: 0,
  });

  const [family, setFamily] = useState(null);
  const [variants, setVariants] = useState([]);
  const [pending, setPending] = useState(0);
  const [genError, setGenError] = useState(null);
  const [exhausted, setExhausted] = useState(false);
  const [accepted, setAccepted] = useState({});
  const [leaving, setLeaving] = useState({});
  const [solutions, setSolutions] = useState({});
  const [focus, setFocus] = useState(0);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState(null);
  const [bump, setBump] = useState(0);
  const [origOpen, setOrigOpen] = useState(true);
  const [pickOpen, setPickOpen] = useState(false);
  const [keysOpen, setKeysOpen] = useState(false);
  const seedRef = useRef(1);
  const abortRef = useRef(null);
  const cardRefs = useRef([]);
  const variantsRef = useRef([]);
  variantsRef.current = variants;

  const question = data?.question;
  const patterns = data?.patterns || [];
  const current = patterns.find((p) => p.id === family);

  useEffect(() => { if (patterns.length && !family) setFamily(patterns[0].id); }, [patterns, family]);

  const generate = useCallback(async (fam, n, { append = true } = {}) => {
    if (!fam) return;
    abortRef.current?.abort();
    const ctl = new AbortController();
    abortRef.current = ctl;
    setGenError(null);
    setExhausted(false);
    if (!append) { setVariants([]); setFocus(0); setAccepted({}); setLeaving({}); }
    setPending(n);
    try {
      const summary = await variantApi.generate(
        { family: fam, n, seed: seedRef.current++, exclude: append ? variantsRef.current.map((v) => v.key) : [] },
        (v) => {
          setVariants((prev) => (prev.some((p) => p.key === v.key) ? prev : [...prev, v]));
          setPending((p) => Math.max(0, p - 1));
        },
        ctl.signal,
      );
      if (summary?.exhausted) setExhausted(true);
    } catch (e) {
      if (e.name !== 'AbortError') setGenError(e.message);
    } finally {
      if (abortRef.current === ctl) setPending(0);
    }
  }, []);

  const lastFam = useRef(null);
  useEffect(() => {
    if (family && lastFam.current !== family) {
      lastFam.current = family;
      generate(family, BATCH, { append: false });
    }
  }, [family, generate]);

  const visible = variants.filter((v) => leaving[v.key] !== 'gone');
  const acceptedList = variants.filter((v) => accepted[v.key]);

  const toggleAccept = useCallback((key) => {
    setAccepted((a) => { const n = { ...a }; if (n[key]) delete n[key]; else n[key] = true; return n; });
    setBump((b) => b + 1);
  }, []);

  const reject = useCallback((key) => {
    setLeaving((l) => ({ ...l, [key]: 'anim' }));
    setAccepted((a) => { const n = { ...a }; delete n[key]; return n; });
    setTimeout(() => setLeaving((l) => ({ ...l, [key]: 'gone' })), 200);
  }, []);

  const save = async () => {
    if (!acceptedList.length) return;
    setSaving(true);
    try {
      const r = await variantApi.accept(questionId, acceptedList.map((v) => ({ family: v.family, params: v.params, seed: v.seed })));
      const savedKeys = new Set(r.saved.map((s) => s.externalId));
      setToast({
        ok: r.failed.length === 0,
        text: `${r.saved.length} variant${r.saved.length === 1 ? '' : 's'} saved as Pending review`
          + (r.failed.length ? ` · ${r.failed.length} failed re-verification and were not saved` : ''),
      });
      setAccepted({});
      setLeaving((l) => { const n = { ...l }; acceptedList.forEach((v) => { if (savedKeys.has(v.key)) n[v.key] = 'gone'; }); return n; });
    } catch (e) {
      setToast({ ok: false, text: e.response?.data?.message || e.message });
    } finally {
      setSaving(false);
      setTimeout(() => setToast(null), 4200);
    }
  };

  useEffect(() => {
    const onKey = (e) => {
      if (e.metaKey || e.ctrlKey || e.altKey || ['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;
      const v = visible[focus];
      const k = e.key.toLowerCase();
      if (k === 'j' || e.key === 'ArrowDown') { e.preventDefault(); setFocus((f) => Math.min(f + 1, visible.length - 1)); }
      else if (k === 'k' || e.key === 'ArrowUp') { e.preventDefault(); setFocus((f) => Math.max(f - 1, 0)); }
      else if (k === 'a' && v) toggleAccept(v.key);
      else if (k === 'r' && v) reject(v.key);
      else if (k === 's' && v) setSolutions((s) => ({ ...s, [v.key]: !s[v.key] }));
      else if (k === 'm' && family) generate(family, 3);
      else if (k === 'g' && family) generate(family, BATCH);
      else if (e.key === '?') setKeysOpen((o) => !o);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [visible, focus, family, generate, toggleAccept, reject]);

  useEffect(() => { cardRefs.current[focus]?.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); }, [focus]);

  const origCorrect = useMemo(() => new Set(question?.correctAnswers || []), [question]);

  const shell = (children) => (
    <div className="vs-dark relative min-h-screen bg-ink-950 text-ink-100 antialiased overflow-x-hidden">
      <div aria-hidden className="vs-bloom w-[520px] h-[520px] -top-48 -left-40 bg-[#22e4ff]/30" />
      <div aria-hidden className="vs-bloom w-[620px] h-[620px] -top-64 right-[-10rem] bg-[#8257ff]/40" />
      <div aria-hidden className="vs-bloom w-[480px] h-[480px] bottom-[-14rem] left-1/3 bg-[#ff3ec9]/20" />
      <div className="relative z-10 mx-auto max-w-[1440px] px-4 sm:px-8 lg:px-12 py-8 lg:py-12">{children}</div>
    </div>
  );

  if (isLoading) {
    return shell(
      <div className="grid grid-cols-1 lg:grid-cols-[minmax(300px,420px)_minmax(0,1fr)] gap-8 mt-28">
        <div className="vs-skel h-96 rounded-2xl" />
        <div className="space-y-6"><Skeleton /><Skeleton delay={90} /></div>
      </div>,
    );
  }

  if (error || data?.success === false) {
    const msg = error?.response?.data?.message || error?.message || data?.message;
    return shell(
      <div className="max-w-lg mx-auto mt-24 rounded-2xl border border-white/[0.08] bg-ink-900 p-8 text-center space-y-4">
        <AlertTriangle className="w-8 h-8 text-amber-700 mx-auto" />
        <h2 className="text-xl font-semibold">Variant engine unavailable</h2>
        <p className="text-sm text-ink-400">{msg}</p>
        <code className="block rounded-lg bg-black/40 px-3 py-2 text-xs text-ink-200">.venv/bin/python -m cqse.service</code>
        <Link to="/" className="inline-flex items-center gap-1.5 text-sm text-iris-300 hover:text-white"><ArrowLeft className="w-4 h-4" /> Back to question bank</Link>
      </div>,
    );
  }

  return shell(
    <>
      {/* ---------------- header */}
      <header className="flex flex-wrap items-end justify-between gap-6 mb-10">
        <div className="space-y-4">
          <div className="flex items-center gap-4">
            <Link to="/" aria-label="Back to question bank"
              className="inline-flex items-center justify-center w-8 h-8 rounded-lg border border-white/[0.08] text-ink-400 hover:text-white hover:border-white/20 transition">
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <span className="inline-flex items-center gap-2.5 text-[13px] font-medium tracking-[0.22em] text-ink-400">
              <span className="inline-flex items-center gap-2 text-ink-200"><PixeyeLogo size={22} /><span className="neon-text font-semibold">PIXEYE</span></span><span className="text-ink-600">/</span>QUESTION VARIATIONS
            </span>
          </div>
          <h1 className="text-[40px] sm:text-[52px] leading-none font-semibold tracking-[-0.03em] text-white">Variant <span className="neon-text">studio</span></h1>
          <p className="text-[17px] sm:text-[19px] text-ink-300">Generate verified question variants, then choose what belongs in your bank.</p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={() => setKeysOpen((o) => !o)}
            className="hidden md:inline-flex items-center gap-2 rounded-xl px-3 py-2.5 text-sm text-ink-400 hover:text-white transition">
            <Keyboard className="w-4 h-4" /> <Kbd>?</Kbd>
          </button>
          <button
            onClick={() => generate(family, BATCH)}
            disabled={!family || pending > 0}
            className="neon-btn inline-flex items-center gap-3 rounded-2xl px-6 py-4 text-[17px] sm:text-[19px] font-medium text-white active:scale-[0.98] transition disabled:opacity-70 disabled:cursor-wait"
          >
            {pending > 0 ? <Loader2 className="w-5 h-5 animate-spin" /> : <Sparkles className="w-5 h-5" />}
            {pending > 0 ? 'Generating…' : `Generate ${BATCH} more`}
            <Kbd tone="light">G</Kbd>
          </button>
        </div>
      </header>

      {keysOpen && (
        <div className="vs-rise mb-8 flex flex-wrap gap-x-6 gap-y-2 rounded-xl border border-white/[0.07] bg-ink-900 px-5 py-3 text-[13px] text-ink-400">
          <span><Kbd>J</Kbd> <Kbd>K</Kbd> next / previous</span><span><Kbd>A</Kbd> accept</span><span><Kbd>R</Kbd> reject</span>
          <span><Kbd>S</Kbd> solution</span><span><Kbd>M</Kbd> 3 more like this</span><span><Kbd>G</Kbd> generate 5 more</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-[minmax(300px,420px)_minmax(0,1fr)] gap-8 items-start">
        {/* ---------------- original */}
        <aside className="lg:sticky lg:top-8 rounded-2xl border border-white/[0.07] bg-ink-900/80 backdrop-blur overflow-hidden">
          <button onClick={() => setOrigOpen((o) => !o)}
            className="w-full flex items-center justify-between px-7 py-5 border-b border-white/[0.06] text-left">
            <span className="flex items-center gap-3 text-[19px] font-semibold text-white"><FileText className="w-5 h-5 text-ink-300" />Original question</span>
            <ChevronUp className={`w-5 h-5 text-ink-400 transition-transform duration-200 ${origOpen ? '' : 'rotate-180'}`} />
          </button>
          <div className="vs-collapse" data-open={origOpen}>
            <div>
              <div className="px-7 pt-6 pb-7 space-y-6 lg:max-h-[calc(100vh-14rem)] overflow-y-auto">
                <div className="flex flex-wrap items-center gap-3 text-[15px] text-ink-400">
                  <span className="max-w-[12rem] truncate rounded-lg border border-white/[0.1] px-3 py-1.5 text-[13.5px] text-ink-200" title={question.externalId}>
                    {question.externalId}
                  </span>
                  <span>{examLine(question)}</span>
                </div>
                <div className="vs-orig text-[17px] leading-[1.75] text-ink-100"><MathView content={question.questionContent?.content} /></div>
                {(question.options || []).length > 0 && (
                  <ul className="space-y-2.5 pl-3">
                    {question.options.map((o) => (
                      <li key={o.id} className={`flex items-start gap-2 text-[16px] ${origCorrect.has(o.id) ? 'text-emerald-700' : 'text-ink-300'}`}>
                        <span className="shrink-0">({o.id})</span>
                        <div className="min-w-0 overflow-x-auto"><MathView content={o.content} /></div>
                        {origCorrect.has(o.id) && <Check className="w-4 h-4 mt-1 shrink-0" />}
                      </li>
                    ))}
                  </ul>
                )}

                <div className="border-t border-white/[0.07] pt-6 space-y-4">
                  <p className="text-[13px] font-medium tracking-[0.2em] text-ink-400">VERIFIED PATTERN</p>
                  {!data.supported ? (
                    <p className="text-sm text-ink-400">{data.message}</p>
                  ) : (
                    <>
                      {current && (
                        <div className="flex flex-wrap gap-2.5">
                          <span className="rounded-lg border border-iris-400/30 bg-iris-500/[0.12] px-3 py-1.5 text-[15px] text-iris-300">{prettyFamily(current.id)}</span>
                          <span className="rounded-lg border border-white/[0.1] px-3 py-1.5 text-[15px] text-ink-300">{current.topic}</span>
                        </div>
                      )}
                      <p className="text-[13px] text-ink-500">
                        {current ? TIER[current.tier] : ''}
                        {!data.close && ' · no close pattern for this exact question yet'}
                      </p>
                      <button onClick={() => setPickOpen((o) => !o)}
                        className="inline-flex items-center gap-1.5 text-[14px] text-ink-300 hover:text-white transition-colors">
                        <ChevronRight className={`w-4 h-4 transition-transform duration-200 ${pickOpen ? 'rotate-90' : ''}`} />
                        Change pattern ({patterns.length})
                      </button>
                      <div className="vs-collapse" data-open={pickOpen}>
                        <div>
                          <div className="space-y-1.5 pt-1">
                            {patterns.map((p) => (
                              <button key={p.id}
                                onClick={() => { setFamily(p.id); setPickOpen(false); }}
                                className={`w-full flex items-center justify-between gap-3 rounded-lg px-3 py-2.5 text-left transition-colors ${
                                  p.id === family ? 'bg-iris-500/[0.12] text-iris-300' : 'text-ink-300 hover:bg-ink-100/[0.04] hover:text-white'
                                }`}>
                                <span className="min-w-0">
                                  <span className="block truncate text-[14.5px]">{prettyFamily(p.id)}</span>
                                  <span className="block truncate text-[12.5px] text-ink-500">{p.topic} · {p.numerical ? 'Numerical' : 'MCQ'}</span>
                                </span>
                                {p.tier !== 'none' && <span className="shrink-0 text-[11px] text-ink-500">{p.tier === 'source' ? 'source' : p.tier}</span>}
                              </button>
                            ))}
                          </div>
                        </div>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        </aside>

        {/* ---------------- variants */}
        <section className="space-y-6 min-w-0" aria-live="polite">
          {genError && (
            <div className="vs-rise flex items-start gap-2.5 rounded-2xl border border-rose-500/30 bg-rose-500/[0.07] p-5 text-sm text-rose-800">
              <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" /> {genError}
            </div>
          )}

          {visible.map((v, i) => (
            <VariantCard
              key={v.key} v={v} n={i + 1} index={i}
              focused={i === focus} accepted={!!accepted[v.key]} leaving={leaving[v.key] === 'anim'}
              solution={!!solutions[v.key]}
              onSolution={() => setSolutions((s) => ({ ...s, [v.key]: !s[v.key] }))}
              onAccept={() => { setFocus(i); toggleAccept(v.key); }}
              onReject={() => reject(v.key)}
              onMore={() => generate(v.family, 3)}
              refCb={(el) => { cardRefs.current[i] = el; }}
            />
          ))}

          {Array.from({ length: Math.min(pending, 3) }).map((_, i) => <Skeleton key={`s${i}`} delay={i * 90} />)}

          {exhausted && pending === 0 && (
            <p className="text-center text-sm text-ink-500 py-2">This pattern has no more distinct verified variants. Try another pattern.</p>
          )}
          {!pending && visible.length === 0 && !genError && data.supported && (
            <div className="rounded-2xl border border-dashed border-white/[0.1] py-20 text-center text-ink-400">
              All variants reviewed. Press <Kbd>G</Kbd> to generate more.
            </div>
          )}
        </section>
      </div>

      {/* ---------------- tray */}
      {acceptedList.length > 0 && (
        <div className="vs-tray fixed bottom-6 left-1/2 z-40 w-[min(620px,calc(100vw-32px))]">
          <div className="flex items-center gap-3 rounded-2xl border border-white/[0.1] bg-ink-800/95 backdrop-blur pl-4 pr-2 py-2 shadow-2xl shadow-black/50">
            <span key={bump} className="vs-bump flex items-center justify-center w-8 h-8 rounded-full bg-emerald-500 text-sm font-semibold text-white">{acceptedList.length}</span>
            <span className="flex-1 truncate text-[15px] text-ink-200">accepted · saved as <span className="text-amber-800">Pending review</span></span>
            <button onClick={() => setAccepted({})} className="px-3 py-2 text-sm text-ink-400 hover:text-white">Clear</button>
            <button onClick={save} disabled={saving}
              className="neon-btn inline-flex items-center gap-2 rounded-xl px-4 py-2.5 text-[15px] font-medium text-white disabled:opacity-70">
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />} Save to bank
            </button>
          </div>
        </div>
      )}

      {toast && (
        <div className={`vs-rise fixed top-6 right-6 z-50 max-w-sm rounded-xl border bg-ink-800 px-4 py-3 text-sm shadow-2xl shadow-black/40 ${
          toast.ok ? 'border-emerald-500/30 text-emerald-800' : 'border-rose-500/30 text-rose-800'
        }`}>
          <div className="flex items-start gap-2">
            {toast.ok ? <ShieldCheck className="w-4 h-4 mt-0.5 shrink-0" /> : <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />}
            {toast.text}
          </div>
        </div>
      )}
    </>,
  );
}
