import { FilterService } from '../services/filterService.js';

export const getSubjects = async (req, res, next) => {
  try {
    const subjects = await FilterService.getSubjects();
    res.json({ success: true, data: subjects });
  } catch (error) {
    next(error);
  }
};

export const getChapters = async (req, res, next) => {
  try {
    const { subject } = req.query;
    const chapters = await FilterService.getChapters(subject);
    res.json({ success: true, data: chapters });
  } catch (error) {
    next(error);
  }
};

export const getTopics = async (req, res, next) => {
  try {
    const { chapter, subject } = req.query;
    const topics = await FilterService.getTopics(chapter, subject);
    res.json({ success: true, data: topics });
  } catch (error) {
    next(error);
  }
};

export const getYears = async (req, res, next) => {
  try {
    const { subject } = req.query;
    const years = await FilterService.getYears(subject);
    res.json({ success: true, data: years });
  } catch (error) {
    next(error);
  }
};

export const getDifficulties = async (req, res, next) => {
  try {
    const difficulties = await FilterService.getDifficulties();
    res.json({ success: true, data: difficulties });
  } catch (error) {
    next(error);
  }
};

export const getQuestionTypes = async (req, res, next) => {
  try {
    const types = await FilterService.getQuestionTypes();
    res.json({ success: true, data: types });
  } catch (error) {
    next(error);
  }
};

