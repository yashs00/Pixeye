import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

export const questionApi = {
  getQuestions: async (params) => {
    const res = await api.get('/questions', { params });
    return res.data;
  },

  getQuestionById: async (id) => {
    const res = await api.get(`/questions/${id}`);
    return res.data;
  },

  getStatistics: async () => {
    const res = await api.get('/questions/statistics');
    return res.data;
  },
};

export const filterApi = {
  getSubjects: async () => {
    const res = await api.get('/filters/subjects');
    return res.data;
  },

  getChapters: async (subject) => {
    const res = await api.get('/filters/chapters', { params: { subject } });
    return res.data;
  },

  getTopics: async (chapter, subject) => {
    const res = await api.get('/filters/topics', { params: { chapter, subject } });
    return res.data;
  },

  getYears: async (subject) => {
    const res = await api.get('/filters/years', { params: { subject } });
    return res.data;
  },

  getDifficulties: async () => {
    const res = await api.get('/filters/difficulties');
    return res.data;
  },

  getTypes: async () => {
    const res = await api.get('/filters/types');
    return res.data;
  },
};

export const selectionApi = {
  getSelections: async (sessionId = 'teacher-session') => {
    const res = await api.get('/selections', { params: { sessionId } });
    return res.data;
  },

  addSelections: async (sessionId = 'teacher-session', questionIds) => {
    const res = await api.post('/selections', { sessionId, questionIds });
    return res.data;
  },

  removeSelection: async (sessionId = 'teacher-session', questionId) => {
    const res = await api.delete(`/selections/${questionId}`, { params: { sessionId } });
    return res.data;
  },

  clearSelections: async (sessionId = 'teacher-session') => {
    const res = await api.delete('/selections', { params: { sessionId } });
    return res.data;
  },
};

export const importApi = {
  getImports: async () => {
    const res = await api.get('/admin/imports');
    return res.data;
  },

  getImportById: async (id) => {
    const res = await api.get(`/admin/imports/${id}`);
    return res.data;
  },

  triggerImport: async (payload) => {
    const res = await api.post('/admin/imports', payload);
    return res.data;
  },

  verifyAll: async (questionIds) => {
    const res = await api.post('/admin/imports/verify-all', { questionIds });
    return res.data;
  },
};

export const variantApi = {
  match: async (questionId) => {
    const res = await api.post('/variants/match', { questionId });
    return res.data;
  },

  accept: async (parentId, items) => {
    const res = await api.post('/variants/accept', { parentId, items }, { timeout: 120000 });
    return res.data;
  },

  /** Streams verified variants one by one (NDJSON). onVariant(v) per variant; resolves with the final summary. */
  generate: async ({ family, n, seed, exclude }, onVariant, signal) => {
    const res = await fetch('/api/variants/generate', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ family, n, seed, exclude }),
      signal,
    });
    if (!res.ok) {
      let msg = 'Variant engine unavailable';
      try { msg = (await res.json()).message || msg; } catch { /* ignore */ }
      throw new Error(msg);
    }
    const reader = res.body.getReader();
    const dec = new TextDecoder();
    let buf = '';
    let summary = null;
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let i;
      while ((i = buf.indexOf('\n')) >= 0) {
        const line = buf.slice(0, i).trim();
        buf = buf.slice(i + 1);
        if (!line) continue;
        const msg = JSON.parse(line);
        if (msg.error) throw new Error(msg.error);
        if (msg.done) summary = msg;
        else onVariant(msg);
      }
    }
    return summary;
  },
};

export default api;

