import { ImportService } from '../services/importService.js';

export const getImports = async (req, res, next) => {
  try {
    const jobs = await ImportService.getImportJobs();
    res.json({ success: true, data: jobs });
  } catch (error) {
    next(error);
  }
};

export const getImportById = async (req, res, next) => {
  try {
    const { id } = req.params;
    const job = await ImportService.getImportJobById(id);
    if (!job) {
      return res.status(404).json({ success: false, message: 'Import job not found' });
    }
    res.json({ success: true, data: job });
  } catch (error) {
    next(error);
  }
};

export const triggerImport = async (req, res, next) => {
  try {
    const { autoVerify = false, batchSize = 500 } = req.body || {};
    // Trigger import asynchronously or synchronously depending on preference
    // For transparent status, we start it and return job or wait
    const job = await ImportService.executeImport({ autoVerify, batchSize });
    res.json({
      success: true,
      message: 'Import completed successfully',
      data: job,
    });
  } catch (error) {
    next(error);
  }
};

export const verifyAllQuestions = async (req, res, next) => {
  try {
    const { questionIds } = req.body || {};
    const result = await ImportService.verifyQuestions(questionIds);
    res.json({
      success: true,
      message: `Successfully updated ${result.count} questions to VERIFIED`,
      data: result,
    });
  } catch (error) {
    next(error);
  }
};

