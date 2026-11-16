import prisma from '../prisma/client.js';

export class SelectionService {
  /**
   * Get selected questions for a session with full details and distribution stats
   */
  static async getSelections(sessionId = 'default-session') {
    const selections = await prisma.questionSelection.findMany({
      where: { sessionId },
      orderBy: { createdAt: 'desc' },
    });

    const questionIds = selections.map((s) => s.questionId);
    if (questionIds.length === 0) {
      return {
        total: 0,
        questions: [],
        subjectDistribution: {},
        chapterDistribution: {},
      };
    }

    const questions = await prisma.question.findMany({
      where: { id: { in: questionIds } },
    });

    // Compute subject and chapter distributions
    const subjectDistribution = {};
    const chapterDistribution = {};

    questions.forEach((q) => {
      subjectDistribution[q.subject] = (subjectDistribution[q.subject] || 0) + 1;
      chapterDistribution[q.chapter] = (chapterDistribution[q.chapter] || 0) + 1;
    });

    return {
      total: questions.length,
      questions,
      subjectDistribution,
      chapterDistribution,
    };
  }

  /**
   * Add a question or multiple questions to selection
   */
  static async addSelections(sessionId = 'default-session', questionIds = [], metadata = {}) {
    const ids = Array.isArray(questionIds) ? questionIds : [questionIds];
    const data = ids.map((id) => ({
      sessionId,
      questionId: id,
      metadata: metadata || {},
    }));

    await prisma.questionSelection.createMany({
      data,
      skipDuplicates: true,
    });

    return await this.getSelections(sessionId);
  }

  /**
   * Remove a single question from selection
   */
  static async removeSelection(sessionId = 'default-session', questionId) {
    await prisma.questionSelection.deleteMany({
      where: {
        sessionId,
        questionId,
      },
    });
    return await this.getSelections(sessionId);
  }

  /**
   * Clear all selections for session
   */
  static async clearSelections(sessionId = 'default-session') {
    await prisma.questionSelection.deleteMany({
      where: { sessionId },
    });
    return {
      total: 0,
      questions: [],
      subjectDistribution: {},
      chapterDistribution: {},
    };
  }
}

