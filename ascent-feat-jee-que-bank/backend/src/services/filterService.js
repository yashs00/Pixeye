import prisma from '../prisma/client.js';

export class FilterService {
  /**
   * Get distinct subjects with question counts
   */
  static async getSubjects() {
    const subjects = await prisma.question.groupBy({
      by: ['subject'],
      _count: {
        id: true,
      },
      orderBy: {
        subject: 'asc',
      },
    });

    return subjects.map((s) => ({
      name: s.subject,
      code: s.subject,
      count: s._count.id,
    }));
  }

  /**
   * Get distinct chapters with question counts, optionally filtered by subject
   */
  static async getChapters(subject = null) {
    const where = {};
    if (subject && subject !== 'ALL') {
      where.subject = subject.toUpperCase();
    }

    const chapters = await prisma.question.groupBy({
      by: ['chapter', 'subject'],
      where,
      _count: {
        id: true,
      },
      orderBy: {
        chapter: 'asc',
      },
    });

    return chapters.map((c) => ({
      name: c.chapter,
      subject: c.subject,
      count: c._count.id,
    }));
  }

  /**
   * Get distinct topics with question counts, optionally filtered by chapter and subject
   */
  static async getTopics(chapter = null, subject = null) {
    const where = {};
    if (subject && subject !== 'ALL') {
      where.subject = subject.toUpperCase();
    }
    if (chapter && chapter !== 'ALL') {
      where.chapter = chapter;
    }

    const topics = await prisma.question.groupBy({
      by: ['topic', 'chapter'],
      where,
      _count: {
        id: true,
      },
      orderBy: {
        topic: 'asc',
      },
    });

    return topics
      .filter((t) => t.topic)
      .map((t) => ({
        name: t.topic,
        chapter: t.chapter,
        count: t._count.id,
      }));
  }

  /**
   * Get distinct years
   */
  static async getYears(subject = null) {
    const where = {};
    if (subject && subject !== 'ALL') {
      where.subject = subject.toUpperCase();
    }

    const years = await prisma.question.groupBy({
      by: ['year'],
      where,
      _count: {
        id: true,
      },
      orderBy: {
        year: 'desc',
      },
    });

    return years
      .filter((y) => y.year > 0)
      .map((y) => ({
        year: y.year,
        count: y._count.id,
      }));
  }

  /**
   * Get distinct difficulties
   */
  static async getDifficulties() {
    const difficulties = await prisma.question.groupBy({
      by: ['difficulty'],
      _count: {
        id: true,
      },
      orderBy: {
        difficulty: 'asc',
      },
    });

    return difficulties.map((d) => ({
      name: d.difficulty,
      count: d._count.id,
    }));
  }

  /**
   * Get distinct question types
   */
  static async getQuestionTypes() {
    const types = await prisma.question.groupBy({
      by: ['questionType'],
      _count: {
        id: true,
      },
      orderBy: {
        questionType: 'asc',
      },
    });

    return types.map((t) => ({
      name: t.questionType,
      count: t._count.id,
    }));
  }

  /**
   * Get comprehensive question statistics
   */
  static async getStatistics() {
    const [
      totalQuestions,
      bySubject,
      byDifficulty,
      byType,
      byYear,
      byReviewStatus,
      topChapters,
    ] = await Promise.all([
      prisma.question.count(),
      prisma.question.groupBy({
        by: ['subject'],
        _count: { id: true },
      }),
      prisma.question.groupBy({
        by: ['difficulty'],
        _count: { id: true },
      }),
      prisma.question.groupBy({
        by: ['questionType'],
        _count: { id: true },
      }),
      prisma.question.groupBy({
        by: ['year'],
        _count: { id: true },
        orderBy: { year: 'desc' },
      }),
      prisma.question.groupBy({
        by: ['reviewStatus'],
        _count: { id: true },
      }),
      prisma.question.groupBy({
        by: ['chapter', 'subject'],
        _count: { id: true },
        orderBy: { _count: { id: 'desc' } },
        take: 10,
      }),
    ]);

    const subjectCounts = {};
    bySubject.forEach((s) => {
      subjectCounts[s.subject] = s._count.id;
    });

    const difficultyCounts = {};
    byDifficulty.forEach((d) => {
      difficultyCounts[d.difficulty] = d._count.id;
    });

    const typeCounts = {};
    byType.forEach((t) => {
      typeCounts[t.questionType] = t._count.id;
    });

    const yearCounts = {};
    byYear.filter((y) => y.year > 0).forEach((y) => {
      yearCounts[y.year] = y._count.id;
    });

    const reviewStatusCounts = {};
    byReviewStatus.forEach((r) => {
      reviewStatusCounts[r.reviewStatus] = r._count.id;
    });

    return {
      totalQuestions,
      bySubject: subjectCounts,
      byDifficulty: difficultyCounts,
      byType: typeCounts,
      byYear: yearCounts,
      byReviewStatus: reviewStatusCounts,
      topChapters: topChapters.map((c) => ({
        chapter: c.chapter,
        subject: c.subject,
        count: c._count.id,
      })),
    };
  }
}

