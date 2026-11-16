import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { importApi } from '../services/api';
import { History, Play, ShieldCheck, CheckCircle2, Clock, AlertTriangle, RefreshCw, FileText } from 'lucide-react';

export default function ImportHistoryPage() {
  const queryClient = useQueryClient();
  const [msg, setMsg] = useState(null);

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['imports'],
    queryFn: importApi.getImports,
  });

  const importMutation = useMutation({
    mutationFn: (payload) => importApi.triggerImport(payload),
    onSuccess: (res) => {
      queryClient.invalidateQueries(['imports']);
      queryClient.invalidateQueries(['questions']);
      queryClient.invalidateQueries(['statistics']);
      setMsg({ type: 'success', text: `Import completed! Added ${res.data?.totalImported || 0} questions.` });
      setTimeout(() => setMsg(null), 5000);
    },
    onError: (err) => {
      setMsg({ type: 'error', text: err.response?.data?.message || err.message });
    },
  });

  const verifyMutation = useMutation({
    mutationFn: () => importApi.verifyAll(),
    onSuccess: (res) => {
      queryClient.invalidateQueries(['questions']);
      queryClient.invalidateQueries(['statistics']);
      setMsg({ type: 'success', text: res.message || 'All pending questions verified!' });
      setTimeout(() => setMsg(null), 5000);
    },
  });

  const jobs = data?.data || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <History className="w-5 h-5 text-brand-600" />
            Data Import & Provenance Management
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Track previous year question extraction pipelines and legal verification status
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => verifyMutation.mutate()}
            disabled={verifyMutation.isPending}
            className="flex items-center gap-1.5 px-3 py-2 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs font-semibold hover:bg-emerald-100 disabled:opacity-50 transition-colors shadow-2xs"
          >
            <ShieldCheck className="w-4 h-4 text-emerald-600" />
            <span>{verifyMutation.isPending ? 'Verifying...' : 'Verify All Questions'}</span>
          </button>

          <button
            onClick={() => importMutation.mutate({ autoVerify: true })}
            disabled={importMutation.isPending}
            className="flex items-center gap-1.5 px-4 py-2 bg-slate-900 text-slate-50 rounded-lg text-xs font-semibold hover:bg-slate-800 disabled:opacity-50 transition-colors shadow-2xs"
          >
            {importMutation.isPending ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            <span>{importMutation.isPending ? 'Import In Progress...' : 'Run Incremental Import'}</span>
          </button>
        </div>
      </div>

      {msg && (
        <div
          className={`p-4 rounded-xl text-xs font-semibold border ${
            msg.type === 'success'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
              : 'bg-rose-50 border-rose-200 text-rose-800'
          }`}
        >
          {msg.text}
        </div>
      )}

      {/* Legal Provenance Banner */}
      <div className="p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-600 space-y-1">
        <div className="flex items-center gap-2 font-bold text-slate-800">
          <ShieldCheck className="w-4 h-4 text-brand-600" />
          Content Licensing and Attribution Architecture
        </div>
        <p className="text-[11px] text-slate-500 leading-relaxed">
          In compliance with legal requirements, raw extracted questions are cataloged with original metadata from
          <code className="mx-1 px-1 py-0.5 bg-slate-200 rounded font-mono text-slate-800">jee_mains_pyqs_data_base</code>.
          Import jobs enforce duplicate prevention through composite keys <code className="font-mono text-slate-800">(sourceName, externalId)</code>,
          ensuring re-running imports never corrupt existing teacher records or create duplicates.
        </p>
      </div>

      {/* Import History Table */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
            Import Job Logs ({jobs.length})
          </span>
          <button
            onClick={() => refetch()}
            className="text-xs font-semibold text-slate-500 hover:text-slate-800 flex items-center gap-1"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Refresh
          </button>
        </div>

        {isLoading ? (
          <div className="p-8 text-center text-xs text-slate-400">Loading import logs...</div>
        ) : jobs.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-400">No import jobs recorded yet.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-700">
              <thead className="bg-slate-50/80 border-b border-slate-200 text-[11px] font-bold uppercase text-slate-500 tracking-wider">
                <tr>
                  <th className="py-3 px-6">Job ID / Source</th>
                  <th className="py-3 px-6">Status</th>
                  <th className="py-3 px-6">Discovered</th>
                  <th className="py-3 px-6">Imported</th>
                  <th className="py-3 px-6">Failed</th>
                  <th className="py-3 px-6">Started</th>
                  <th className="py-3 px-6">Duration</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {jobs.map((job) => {
                  const startTime = new Date(job.startedAt);
                  const endTime = job.completedAt ? new Date(job.completedAt) : null;
                  const durationSec = endTime ? Math.round((endTime - startTime) / 1000) : '-';

                  return (
                    <tr key={job.id} className="hover:bg-slate-50/60 transition-colors">
                      <td className="py-3.5 px-6 font-medium">
                        <div className="font-bold text-slate-900">{job.source}</div>
                        <div className="font-mono text-[10px] text-slate-400">{job.id}</div>
                      </td>
                      <td className="py-3.5 px-6">
                        {job.status === 'COMPLETED' ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                            <CheckCircle2 className="w-3 h-3" /> Completed
                          </span>
                        ) : job.status === 'RUNNING' ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                            <RefreshCw className="w-3 h-3 animate-spin" /> Running
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-200">
                            <AlertTriangle className="w-3 h-3" /> Failed
                          </span>
                        )}
                      </td>
                      <td className="py-3.5 px-6 font-semibold text-slate-900">
                        {job.totalDiscovered.toLocaleString()}
                      </td>
                      <td className="py-3.5 px-6 font-semibold text-emerald-700">
                        +{job.totalImported.toLocaleString()}
                      </td>
                      <td className="py-3.5 px-6 font-medium text-slate-500">
                        {job.totalFailed}
                      </td>
                      <td className="py-3.5 px-6 text-slate-500">
                        {startTime.toLocaleString()}
                      </td>
                      <td className="py-3.5 px-6 font-mono text-slate-600">
                        {durationSec !== '-' ? `${durationSec}s` : 'In progress'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

