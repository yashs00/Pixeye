import express from 'express';
import cors from 'cors';
import morgan from 'morgan';
import dotenv from 'dotenv';

import questionRoutes from './routes/questionRoutes.js';
import filterRoutes from './routes/filterRoutes.js';
import statsRoutes from './routes/statsRoutes.js';
import selectionRoutes from './routes/selectionRoutes.js';
import importRoutes from './routes/importRoutes.js';
import variantRoutes from './routes/variantRoutes.js';
import { errorHandler } from './middleware/errorHandler.js';
import prisma from './prisma/client.js';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
app.use(cors({
  origin: '*', // Allow frontend dev server
  credentials: true,
}));
app.use(express.json({ limit: '10mb' }));
app.use(morgan('dev'));

// Health check
app.get('/api/health', async (req, res) => {
  try {
    const questionCount = await prisma.question.count();
    res.json({
      status: 'healthy',
      service: 'PIXEYE Question Bank API',
      database: 'connected',
      totalQuestions: questionCount,
      timestamp: new Date().toISOString(),
    });
  } catch (err) {
    res.status(500).json({
      status: 'unhealthy',
      database: 'disconnected',
      error: err.message,
    });
  }
});

// API Routes
app.use('/api/questions/statistics', statsRoutes);
app.use('/api/questions', questionRoutes);
app.use('/api/filters', filterRoutes);
app.use('/api/selections', selectionRoutes);
app.use('/api/admin/imports', importRoutes);
app.use('/api/variants', variantRoutes);

// Error Handler
app.use(errorHandler);

// Start server
const server = app.listen(PORT, () => {
  console.log(`===============================================`);
  console.log(` PIXEYE Backend API running on port ${PORT}`);
  console.log(` Health check: http://localhost:${PORT}/api/health`);
  console.log(`===============================================`);
});

// Graceful shutdown
process.on('SIGINT', async () => {
  console.log('Shutting down server...');
  await prisma.$disconnect();
  server.close(() => {
    console.log('Server terminated.');
    process.exit(0);
  });
});

export default app;

