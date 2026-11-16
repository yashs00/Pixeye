import React from 'react';
import { Settings, Database, Server, Shield, Globe, Terminal } from 'lucide-react';

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-2xs">
        <h2 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
          <Settings className="w-5 h-5 text-brand-600" />
          Platform Settings & Infrastructure
        </h2>
        <p className="text-xs text-slate-500 mt-1">
          Technical specifications, database parameters, and content governance
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Database Configuration Card */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-4">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-800">
            <Database className="w-4 h-4 text-emerald-600" />
            PostgreSQL Database & Prisma
          </div>
          <div className="space-y-2 text-xs">
            <div className="flex justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Database Name</span>
              <span className="font-mono font-semibold text-slate-800">que_bank</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Host / Port</span>
              <span className="font-mono font-semibold text-slate-800">localhost:5432</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">ORM</span>
              <span className="font-semibold text-slate-800">Prisma Client 5.22.0</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-slate-500">Connection Mode</span>
              <span className="font-semibold text-emerald-600 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Active Pooled
              </span>
            </div>
          </div>
        </div>

        {/* Question Ingestion Pipeline */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-4">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-800">
            <Terminal className="w-4 h-4 text-brand-600" />
            Python Extraction Pipeline
          </div>
          <div className="space-y-2 text-xs">
            <div className="flex justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Source Package</span>
              <span className="font-mono font-semibold text-slate-800">jee_data_base (v0.2.2)</span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Repository</span>
              <span className="font-mono font-semibold text-brand-600 truncate max-w-xs">
                HostServer001/jee_mains_pyqs_data_base
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-slate-100">
              <span className="text-slate-500">Runtime Architecture</span>
              <span className="font-semibold text-slate-800">Independent Python CLI Utility</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-slate-500">Production Node Backend</span>
              <span className="font-semibold text-slate-800">Zero Python runtime dependency</span>
            </div>
          </div>
        </div>

        {/* Legal & Governance */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-2xs space-y-4 md:col-span-2">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-800">
            <Shield className="w-4 h-4 text-indigo-600" />
            Content Licensing & Attribution Policy
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            The PIXEYE question bank maintains an auditable provenance chain. Ingested questions preserve raw metadata and are assigned a review lifecycle status (<code className="px-1 py-0.5 bg-slate-100 rounded text-slate-800">PENDING_REVIEW</code>, <code className="px-1 py-0.5 bg-slate-100 rounded text-slate-800">VERIFIED</code>, <code className="px-1 py-0.5 bg-slate-100 rounded text-slate-800">UNPUBLISHED</code>).
            Unverified content remains restricted from student-facing assessments until authorized by faculty administration.
          </p>
        </div>
      </div>
    </div>
  );
}

