import express from 'express';
import { Readable } from 'node:stream';
import prisma from '../prisma/client.js';

/**
 * Variant Studio API — proxies the CQSE engine service (Python, see pixeye/cqse/service.py).
 *
 *   GET  /api/variants/health
 *   POST /api/variants/match     { questionId }                       -> patterns for this bank question
 *   POST /api/variants/generate  { family, n, seed, exclude }         -> NDJSON stream of verified variants
 *   POST /api/variants/accept    { parentId, items: [{family, params, seed}] }
 *
 * Accept never trusts what the browser sends back: each variant is rebuilt and re-verified by the engine
 * from (family, params, seed), and the engine's copy is stored with reviewStatus PENDING_REVIEW.
 */
const router = express.Router();
const CQSE_URL = process.env.CQSE_URL || 'http://127.0.0.1:8765';

const engineDown = (res) =>
  res.status(503).json({
    success: false,
    message: 'Variant engine is not running. Start it with: python -m cqse.service',
  });

async function engine(path, body) {
  const r = await fetch(`${CQSE_URL}${path}`, {
    method: body ? 'POST' : 'GET',
    headers: { 'content-type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  return r;
}

router.get('/health', async (req, res) => {
  try {
    const r = await engine('/health');
    res.json({ success: true, ...(await r.json()) });
  } catch {
    engineDown(res);
  }
});

router.post('/match', async (req, res, next) => {
  try {
    const q = await prisma.question.findUnique({ where: { id: String(req.body.questionId || '') } });
    if (!q) return res.status(404).json({ success: false, message: 'Question not found' });
    let r;
    try {
      r = await engine('/match', {
        externalId: q.externalId,
        chapter: q.chapter,
        stem: q.questionContent?.content || '',
      });
    } catch {
      return engineDown(res);
    }
    res.json({ success: true, question: q, ...(await r.json()) });
  } catch (e) {
    next(e);
  }
});

router.post('/generate', async (req, res) => {
  const { family, n = 5, seed = 0, exclude = [] } = req.body || {};
  let r;
  try {
    r = await engine('/variants', { family, n: Math.min(Number(n) || 5, 12), seed: Number(seed) || 0, exclude });
  } catch {
    return engineDown(res);
  }
  res.setHeader('Content-Type', 'application/x-ndjson; charset=utf-8');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('X-Accel-Buffering', 'no');
  const stream = Readable.fromWeb(r.body);
  req.on('close', () => stream.destroy());
  stream.pipe(res);
});

const toPrisma = (row, parentId) => ({
  externalId: row.externalId,
  sourceName: row.sourceName,
  exam: row.exam,
  subject: row.subject,
  chapter: row.chapter,
  topic: row.topic ?? null,
  year: row.year,
  paperTitle: row.paperTitle ?? null,
  difficulty: row.difficulty,
  questionType: row.questionType,
  questionContent: row.questionContent,
  options: row.options ?? [],
  correctAnswers: row.correctAnswers ?? [],
  ...(row.answer ? { answer: row.answer } : {}),
  ...(row.explanation ? { explanation: row.explanation } : {}),
  media: row.media ?? [],
  sourceMetadata: { ...row.sourceMetadata, parentQuestionId: parentId, acceptedAt: new Date().toISOString() },
  reviewStatus: 'PENDING_REVIEW',
});

router.post('/accept', async (req, res, next) => {
  try {
    const { parentId = null, items = [] } = req.body || {};
    if (!Array.isArray(items) || items.length === 0 || items.length > 50) {
      return res.status(400).json({ success: false, message: 'Send 1–50 variants' });
    }
    const saved = [];
    const failed = [];
    for (const it of items) {
      let v;
      try {
        const r = await engine('/build', { family: it.family, params: it.params, seed: it.seed });
        v = await r.json();
      } catch {
        return engineDown(res);
      }
      if (!v || v.error) {
        failed.push({ family: it.family, reason: v?.error || 'engine error' });
        continue;
      }
      const data = toPrisma(v.row, parentId);
      const q = await prisma.question.upsert({
        where: { sourceName_externalId: { sourceName: data.sourceName, externalId: data.externalId } },
        create: data,
        update: data,
      });
      saved.push({ id: q.id, externalId: q.externalId });
    }
    res.json({ success: true, saved, failed });
  } catch (e) {
    next(e);
  }
});

export default router;
