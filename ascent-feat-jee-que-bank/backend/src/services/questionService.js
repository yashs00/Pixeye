import prisma from '../prisma/client.js';

export class QuestionService {
  /**
   * Get paginated and filtered list of questions
   */
  static async getQuestions(query = {}) {
    const {
      search,
      exam,
      subject,
      chapter,
      topic,
      year,
      difficulty,
      questionType,
      reviewStatus,
      page = 1,
      limit = 20,
      sortBy = 'year',
      sortOrder = 'desc',
    } = query;

    const pageNum = Math.max(1, parseInt(page, 10) || 1);
    const limitNum = Math.min(100, Math.max(1, parseInt(limit, 10) || 20));
    const skip = (pageNum - 1) * limitNum;

    const where = {};

    if (exam && exam !== 'ALL') {
      where.exam = exam.toUpperCase();
    }

    if (subject && subject !== 'ALL') {
      where.subject = subject.toUpperCase();
    }

    if (chapter && chapter !== 'ALL') {
      where.chapter = chapter;
    }

    if (topic && topic !== 'ALL') {
      where.topic = topic;
    }

    if (year && year !== 'ALL') {
      const parsedYear = parseInt(year, 10);
      if (!isNaN(parsedYear)) {
        where.year = parsedYear;
      }
    }

    if (difficulty && difficulty !== 'ALL') {
      where.difficulty = difficulty.toUpperCase();
    }

    if (questionType && questionType !== 'ALL') {
      where.questionType = questionType.toUpperCase();
    }

    if (reviewStatus && reviewStatus !== 'ALL') {
      where.reviewStatus = reviewStatus.toUpperCase();
    }

    // Search filter across statement, chapter, topic, externalId, paperTitle
    if (search && search.trim()) {
      const searchStr = search.trim();
      where.OR = [
        { externalId: { contains: searchStr, mode: 'insensitive' } },
        { chapter: { contains: searchStr, mode: 'insensitive' } },
        { topic: { contains: searchStr, mode: 'insensitive' } },
        { paperTitle: { contains: searchStr, mode: 'insensitive' } },
        // Raw questionContent text search via JSON filter or string
        {
          questionContent: {
            path: ['content'],
            string_contains: searchStr,
          },
        },
      ];
    }

    // Sort order
    const validSortFields = ['year', 'createdAt', 'difficulty', 'subject', 'chapter'];
    const sortField = validSortFields.includes(sortBy) ? sortBy : 'year';
    const direction = sortOrder.toLowerCase() === 'asc' ? 'asc' : 'desc';

    const orderBy = [{ [sortField]: direction }, { createdAt: 'desc' }];

    const [total, questions] = await Promise.all([
      prisma.question.count({ where }),
      prisma.question.findMany({
        where,
        skip,
        take: limitNum,
        orderBy,
      }),
    ]);

    const totalPages = Math.ceil(total / limitNum);

    return {
      data: questions,
      pagination: {
        page: pageNum,
        limit: limitNum,
        total,
        totalPages,
        hasNextPage: pageNum < totalPages,
        hasPrevPage: pageNum > 1,
      },
    };
  }

  /**
   * Get single question by ID
   */
  static async getQuestionById(id) {
    const question = await prisma.question.findUnique({
      where: { id },
    });
    if (!question) {
      throw new Error(`Question with id '${id}' not found`);
    }
    return question;
  }
}

