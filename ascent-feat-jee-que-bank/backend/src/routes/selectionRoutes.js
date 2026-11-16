import express from 'express';
import {
  getSelections,
  addSelections,
  removeSelection,
  clearSelections,
} from '../controllers/selectionController.js';

const router = express.Router();

router.get('/', getSelections);
router.post('/', addSelections);
router.delete('/:questionId', removeSelection);
router.delete('/', clearSelections);

export default router;

