import { FilterService } from '../services/filterService.js';

export const getStatistics = async (req, res, next) => {
  try {
    const stats = await FilterService.getStatistics();
    res.json({
      success: true,
      data: stats,
    });
  } catch (error) {
    next(error);
  }
};

