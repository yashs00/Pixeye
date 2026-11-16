import express from 'express';
import {
  getSubjects,
  getChapters,
  getTopics,
  getYears,
  getDifficulties,
  getQuestionTypes,
} from '../controllers/filterController.js';

const router = express.Router();

router.get('/subjects', getSubjects);
router.get('/chapters', getChapters);
router.get('/topics', getTopics);
router.get('/years', getYears);
router.get('/difficulties', getDifficulties);
router.get('/types', getQuestionTypes);

export default router;

