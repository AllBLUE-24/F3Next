'use client';

// src/components/implementation/shell/StepRail.tsx

import { useState } from 'react';
import { usePathname } from 'next/navigation';
import { Upload, ScanSearch, CheckSquare, Rocket, ChevronsLeft, ChevronsRight } from 'lucide-react';
import type { ImplementationStep } from '@/types/implementation';
import { DeploymentPill } from './DeploymentPill';

const STEPS: { id: ImplementationStep; label: string; sublabel: string; icon: React.ElementType }[] = [
  { id: 'upload',   label: 'Upload',   sublabel: 'Your data files',      icon: Upload },
  { id: 'analyze',  label: 'Analyze',  sublabel: 'System is thinking',   icon: ScanSearch },
  { id: 'validate', label: 'Validate', sublabel: 'Review & confirm',      icon: CheckSquare },
  { id: 'import',   label: 'Import',   sublabel: 'Live ERP',              icon: Rocket },
];

function getActiveStep(pathname: string): ImplementationStep {
  if (pathname.includes('/analyze'))  return 'analyze';
  if (pathname.includes('/validate')) return 'validate';
  if (pathname.includes('/import') || pathname.includes('/sandbox')) return 'import';
  return 'upload';
}

function stepIndex(step: ImplementationStep) {
  return STEPS.findIndex((s) => s.id === step);
}

export function StepRail() {
  const pathname = usePathname();
  const activeStep = getActiveStep(pathname);
  const activeIdx = stepIndex(activeStep);
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside className={`relative flex flex-col border-r border-[var(--border-subtle)] bg-[var(--bg-shell)] transition-all duration-300 ${collapsed ? "w-20" : "w-72"} shrink-0 self-start sticky top-0 h-full overflow-y-auto z-30`}>
      
      {/* Collapse Toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className={`absolute right-3 top-4 text-zinc-500 hover:text-white hover:bg-white/[0.05] p-1.5 rounded-lg transition-colors z-50 ${collapsed ? "inset-0 right-auto mx-auto mt-4 opacity-100" : ""}`}
      >
        {collapsed ? <ChevronsRight className="w-4 h-4" /> : <ChevronsLeft className="w-4 h-4" />}
      </button>

      {/* Deployment Status Section */}
      <div className={`p-5 border-b border-[var(--border-subtle)] ${collapsed ? "flex justify-center" : ""}`}>
         {!collapsed && <p className="text-[10px] font-bold uppercase tracking-wider text-zinc-500 mb-3">Instance</p>}
         <DeploymentPill collapsed={collapsed} />
      </div>

      {/* Pipeline Steps Section */}
      <div className="p-5 flex-1">
        {!collapsed && <p className="text-[10px] font-bold uppercase tracking-wider text-zinc-500 mb-4">Pipeline</p>}
        <div className={`flex flex-col ${collapsed ? "items-center gap-3" : "gap-1"}`}>
        {STEPS.map((step, idx) => {
          const isDone    = idx < activeIdx;
          const isActive  = idx === activeIdx;

          return (
            <div key={step.id} className="relative flex flex-col w-full">
              {/* Connector line between steps */}
              {idx < STEPS.length - 1 && !collapsed && (
                <div className={`absolute left-[22px] top-11 w-px h-6 transition-colors duration-500 ${
                  isDone ? 'bg-amber-500/40' : 'bg-[var(--border-subtle)]'
                }`} />
              )}

              <div className={`flex items-center gap-3.5 ${collapsed ? "p-2 justify-center" : "p-3"} rounded-xl transition-all duration-200 ${
                isActive  ? 'bg-white/[0.05]' : 'hover:bg-white/[0.03]'
              }`}
              title={collapsed ? step.label : undefined}
              >
                {/* Icon */}
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 transition-all duration-300 ${
                  isDone   ? 'bg-amber-500/15 border border-amber-500/25' :
                  isActive ? 'bg-amber-500 shadow-lg shadow-amber-500/20' :
                             'bg-[var(--bg-elevated)] border border-[var(--border-subtle)]'
                }`}>
                  <step.icon className={`w-4 h-4 transition-colors duration-300 ${
                    isDone   ? 'text-amber-400' :
                    isActive ? 'text-black' :
                               'text-zinc-500'
                  }`} />
                </div>

                {!collapsed && (
                  <div className="overflow-hidden">
                    <p className={`text-sm font-semibold leading-none truncate transition-colors duration-300 ${
                      isActive ? 'text-white' :
                      isDone   ? 'text-zinc-400' :
                                 'text-zinc-500'
                    }`}>
                      {step.label}
                    </p>
                    <p className={`text-[11px] mt-1.5 leading-none truncate transition-colors duration-300 ${
                      isActive ? 'text-zinc-400' : 'text-zinc-600'
                    }`}>
                      {step.sublabel}
                    </p>
                  </div>
                )}
              </div>

              {/* Spacer for connector */}
              {idx < STEPS.length - 1 && !collapsed && <div className="h-3" />}
            </div>
          );
        })}
        </div>
      </div>
    </aside>
  );
}