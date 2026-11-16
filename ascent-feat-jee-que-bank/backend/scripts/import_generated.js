// Import CQSE-generated, verified questions into the question bank (status PENDING_REVIEW for teacher sign-off).
// Usage (from backend/):  node scripts/import_generated.js ../../out/generated/import_ready.json
import path from 'path';
import { ImportService } from '../src/services/importService.js';

const file = process.argv[2];
if (!file) {
  console.error('usage: node scripts/import_generated.js <path to import_ready.json>');
  process.exit(1);
}
const job = await ImportService.executeImport({ jsonPath: path.resolve(file), autoVerify: false });
console.log(`imported ${job.totalImported} of ${job.totalDiscovered} generated questions (job ${job.id})`);
process.exit(0);
