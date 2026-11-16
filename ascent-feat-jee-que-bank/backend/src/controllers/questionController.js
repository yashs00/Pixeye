import { QuestionService } from '../services/questionService.js';

export const getQuestions = async (req, res, next) => {
  try {
    const result = await QuestionService.getQuestions(req.query);
    res.json({
      success: true,
      ...result,
    });
  } catch (error) {
    next(error);
  }
};

export const getQuestionById = async (req, res, next) => {
  try {
    const { id } = req.params;
    const question = await QuestionService.getQuestionById(id);
    res.json({
      success: true,
      data: question,
    });
  } catch (error) {
    next(error);
  }
};

