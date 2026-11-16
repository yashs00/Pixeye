import express from 'express';
import {
  getImports,
  getImportById,
  triggerImport,
  verifyAllQuestions,
} from '../controllers/importController.js';

const router = express.Router();

router.get('/', getImports);
router.get('/:id', getImportById);
router.post('/', triggerImport);
router.post('/verify-all', verifyAllQuestions);

export default router;

