import { SelectionService } from '../services/selectionService.js';

export const getSelections = async (req, res, next) => {
  try {
    const sessionId = req.query.sessionId || 'default-session';
    const selections = await SelectionService.getSelections(sessionId);
    res.json({
      success: true,
      data: selections,
    });
  } catch (error) {
    next(error);
  }
};

export const addSelections = async (req, res, next) => {
  try {
    const { sessionId = 'default-session', questionIds, questionId, metadata } = req.body;
    const ids = questionIds || (questionId ? [questionId] : []);
    const updated = await SelectionService.addSelections(sessionId, ids, metadata);
    res.json({
      success: true,
      data: updated,
    });
  } catch (error) {
    next(error);
  }
};

export const removeSelection = async (req, res, next) => {
  try {
    const { questionId } = req.params;
    const sessionId = req.query.sessionId || 'default-session';
    const updated = await SelectionService.removeSelection(sessionId, questionId);
    res.json({
      success: true,
      data: updated,
    });
  } catch (error) {
    next(error);
  }
};

export const clearSelections = async (req, res, next) => {
  try {
    const sessionId = req.query.sessionId || 'default-session';
    const updated = await SelectionService.clearSelections(sessionId);
    res.json({
      success: true,
      data: updated,
    });
  } catch (error) {
    next(error);
  }
};

