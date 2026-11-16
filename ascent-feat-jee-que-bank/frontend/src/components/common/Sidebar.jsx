import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  BookOpen,
  CheckSquare,
  History,
  LayoutDashboard,
  Settings,
  Layers,
  Database,
  ShieldCheck, Eye } from 'lucide-react';
import PixeyeLogo from './PixeyeLogo';
import { useSelection } from '../../context/SelectionContext';

export default function Sidebar() {
  const { selectedCount } = useSelection();

  const navItems = [
    {
      to: '/',
      label: 'Question Bank',
      icon: BookOpen,
      badge: null,
      primary: true,
    },
    {
      to: '/selected',
      label: 'Selected Questions',
      icon: CheckSquare,
      badge: selectedCount > 0 ? selectedCount : null,
    },
    {
      to: '/imports',
      label: 'Import History',
      icon: History,
      badge: null,
    },
    {
      to: '/overview',
      label: 'Overview & Stats',
      icon: LayoutDashboard,
      badge: null,
    },
    {
      to: '/settings',
      label: 'Settings',
      icon: Settings,
      badge: null,
    },
  ];

  return (
    <aside className="w-64 bg-white border-r border-slate-200 flex flex-col justify-between h-screen sticky top-0 shrink-0 z-20">
      <div>
        {/* Brand Header */}
        <div className="h-16 px-6 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <PixeyeLogo size={40} />
            <div className="leading-none">
              <span className="block text-[19px] font-extrabold tracking-[0.12em] neon-text">PIXEYE</span>
              <span className="block mt-1 text-[10px] font-semibold tracking-[0.18em] text-slate-400 uppercase">Question Bank</span>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <div className="p-4 space-y-1">
          <div className="px-3 py-2 text-[11px] font-bold uppercase tracking-wider text-slate-400">
            Teacher Workspace
          </div>

          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center justify-between px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-brand-50 text-brand-700 font-semibold shadow-xs'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                  }`
                }
              >
                <div className="flex items-center gap-3">
                  <Icon className="w-4 h-4 text-slate-400 group-hover:text-slate-600" />
                  <span>{item.label}</span>
                </div>
                {item.badge !== null && (
                  <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-brand-600 text-white">
                    {item.badge}
                  </span>
                )}
              </NavLink>
            );
          })}
        </div>
      </div>

      {/* System Status Footnote */}
      <div className="p-4 border-t border-slate-100">
        <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/60 text-xs">
          <div className="flex items-center justify-between font-semibold text-slate-700 mb-1">
            <span className="flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5 text-emerald-600" />
              PostgreSQL Connected
            </span>
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          </div>
          <p className="text-slate-500 text-[11px] leading-tight">
            JEE Mains PYQ Ingestion Pipeline v1.0
          </p>
          <div className="mt-2 flex items-center gap-1 text-[10px] text-slate-400">
            <ShieldCheck className="w-3 h-3 text-slate-400" />
            <span>Verified Content Engine</span>
          </div>
        </div>
      </div>
    </aside>
  );
}

