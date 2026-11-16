import { ImportService } from './importService.js';
import prisma from '../prisma/client.js';

async function run() {
  console.log('--- Ascent Question Ingestion Runner ---');
  try {
    const job = await ImportService.executeImport({
      autoVerify: true // For initial ingestion, set to VERIFIED so questions are instantly accessible in the teacher dashboard, while preserving full audit trail!
    });
    console.log('Import completed successfully:', job);
  } catch (err) {
    console.error('Import failed:', err);
    process.exit(1);
  } finally {
    await prisma.$disconnect();
  }
}

run();

