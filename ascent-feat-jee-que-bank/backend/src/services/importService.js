import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import prisma from '../prisma/client.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export class ImportService {
  /**
   * Run the import process from the canonical questions.json export
   * @param {Object} options 
   * @param {string} [options.jsonPath] Custom path to questions.json
   * @param {number} [options.batchSize] Batch size for DB insert
   * @param {boolean} [options.autoVerify] Whether to auto-verify imported questions
   */
  static async executeImport(options = {}) {
    const defaultJsonPath = path.resolve(
      __dirname,
      '../../../question-importer/exports/questions.json'
    );
    const jsonPath = options.jsonPath || defaultJsonPath;
    const batchSize = options.batchSize || 500;
    const autoVerify = options.autoVerify || false;

    if (!fs.existsSync(jsonPath)) {
      throw new Error(`Questions export file not found at: ${jsonPath}`);
    }

    console.log(`[ImportService] Starting import from ${jsonPath}...`);
    const rawData = fs.readFileSync(jsonPath, 'utf-8');
    const questions = JSON.parse(rawData);

    // Create ImportJob record
    const job = await prisma.importJob.create({
      data: {
        source: 'HostServer001 JEE Database',
        status: 'RUNNING',
        totalDiscovered: questions.length,
        startedAt: new Date(),
      },
    });

    let totalImported = 0;
    let totalFailed = 0;
    const errors = [];

    try {
      // 1. Sync Subjects, Chapters, and Topics
      console.log(`[ImportService] Syncing Subjects, Chapters, and Topics metadata...`);
      const subjectMap = new Map();
      const chapterMap = new Map();
      const topicMap = new Map();

      for (const q of questions) {
        const subjCode = q.subject;
        if (!subjectMap.has(subjCode)) {
          const subject = await prisma.subject.upsert({
            where: { code: subjCode },
            update: {},
            create: {
              code: subjCode,
              name: subjCode.charAt(0) + subjCode.slice(1).toLowerCase(),
            },
          });
          subjectMap.set(subjCode, subject.id);
        }

        const subjectId = subjectMap.get(subjCode);
        const chapterName = q.chapter || 'General';
        const chapKey = `${subjectId}::${chapterName}`;

        if (!chapterMap.has(chapKey)) {
          const slug = chapterName.toLowerCase().replace(/[^a-z0-9]+/g, '-');
          const chapter = await prisma.chapter.upsert({
            where: {
              subjectId_name: {
                subjectId,
                name: chapterName,
              },
            },
            update: {},
            create: {
              subjectId,
              name: chapterName,
              slug,
            },
          });
          chapterMap.set(chapKey, chapter.id);
        }

        const chapterId = chapterMap.get(chapKey);
        const topicName = q.topic || 'General';
        const topicKey = `${chapterId}::${topicName}`;

        if (!topicMap.has(topicKey)) {
          const topicSlug = topicName.toLowerCase().replace(/[^a-z0-9]+/g, '-');
          await prisma.topic.upsert({
            where: {
              chapterId_name: {
                chapterId,
                name: topicName,
              },
            },
            update: {},
            create: {
              chapterId,
              name: topicName,
              slug: topicSlug,
            },
          });
          topicMap.set(topicKey, true);
        }
      }

      console.log(`[ImportService] Metadata synced. Processing ${questions.length} questions in batches of ${batchSize}...`);

      // 2. Insert questions in batches using createMany with skipDuplicates
      for (let i = 0; i < questions.length; i += batchSize) {
        const batch = questions.slice(i, i + batchSize);
        const formattedBatch = batch.map((q) => ({
          externalId: q.external_id,
          sourceName: q.source?.name || 'HostServer001 JEE Database',
          exam: q.exam || 'JEE_MAIN',
          subject: q.subject,
          chapter: q.chapter,
          topic: q.topic,
          year: q.year || 0,
          paperTitle: q.paper_title || null,
          difficulty: q.difficulty || 'UNKNOWN',
          questionType: q.type || 'MCQ_SINGLE',
          questionContent: q.question,
          options: q.options || [],
          correctAnswers: q.correct_answers || [],
          answer: q.answer || null,
          explanation: q.explanation ? { content: q.explanation } : null,
          media: q.media || [],
          sourceMetadata: q.source || {},
          reviewStatus: autoVerify ? 'VERIFIED' : 'PENDING_REVIEW',
        }));

        try {
          const result = await prisma.question.createMany({
            data: formattedBatch,
            skipDuplicates: true,
          });
          totalImported += result.count;
          console.log(`[ImportService] Batch ${Math.floor(i / batchSize) + 1} processed: +${result.count} questions (Total: ${totalImported})`);
        } catch (batchErr) {
          console.error(`[ImportService] Error in batch ${i}:`, batchErr.message);
          totalFailed += batch.length;
          errors.push({ batchIndex: i, error: batchErr.message });
        }
      }

      // Complete job
      const completedJob = await prisma.importJob.update({
        where: { id: job.id },
        data: {
          status: 'COMPLETED',
          completedAt: new Date(),
          totalImported,
          totalFailed,
          errorLog: errors.length > 0 ? errors : null,
        },
      });

      console.log(`[ImportService] Import job finished! Total Imported: ${totalImported}, Discovered: ${questions.length}`);
      return completedJob;
    } catch (err) {
      console.error(`[ImportService] Fatal import error:`, err);
      await prisma.importJob.update({
        where: { id: job.id },
        data: {
          status: 'FAILED',
          completedAt: new Date(),
          totalImported,
          totalFailed: questions.length - totalImported,
          errorLog: [{ error: err.message, stack: err.stack }],
        },
      });
      throw err;
    }
  }

  /**
   * Verify all pending review questions or a specific list
   */
  static async verifyQuestions(questionIds = null) {
    if (questionIds && questionIds.length > 0) {
      return await prisma.question.updateMany({
        where: { id: { in: questionIds } },
        data: { reviewStatus: 'VERIFIED' },
      });
    }
    return await prisma.question.updateMany({
      where: { reviewStatus: 'PENDING_REVIEW' },
      data: { reviewStatus: 'VERIFIED' },
    });
  }

  /**
   * Get list of import jobs
   */
  static async getImportJobs() {
    return await prisma.importJob.findMany({
      orderBy: { createdAt: 'desc' },
      take: 50,
    });
  }

  /**
   * Get details of a single import job
   */
  static async getImportJobById(id) {
    return await prisma.importJob.findUnique({
      where: { id },
    });
  }
}

