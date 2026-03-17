'use client';

// src/components/implementation/shell/StepRail.tsx

import { usePathname } from 'next/navigation';
import { Upload, ScanSearch, CheckSquare, FlaskConical } from 'lucide-react';
import type { ImplementationStep } from '@/types/implementation';

const STEPS: { id: ImplementationStep; label: string; sublabel: string; icon: React.ElementType }[] = [
  { id: 'upload',   label: 'Upload',   sublabel: 'Your data files',      icon: Upload },
  { id: 'analyze',  label: 'Analyze',  sublabel: 'System is thinking',   icon: ScanSearch },
  { id: 'validate', label: 'Validate', sublabel: 'Review & confirm',      icon: CheckSquare },
  { id: 'sandbox',  label: 'Sandbox',  sublabel: 'Test & approve',        icon: FlaskConical },
];

function getActiveStep(pathname: string): ImplementationStep {
  if (pathname.includes('/analyze'))  return 'analyze';
  if (pathname.includes('/validate')) return 'validate';
  if (pathname.includes('/sandbox'))  return 'sandbox';
  return 'upload';
}

function stepIndex(step: ImplementationStep) {
  return STEPS.findIndex((s) => s.id === step);
}

export function StepRail() {
  const pathname = usePathname();
  const activeStep = getActiveStep(pathname);
  const activeIdx = stepIndex(activeStep);

  return (
    <aside className="hidden lg:flex flex-col w-56 flex-shrink-0 border-r border-white/[0.06] py-10 px-5 gap-1">
      {STEPS.map((step, idx) => {
        const isDone    = idx < activeIdx;
        const isActive  = idx === activeIdx;
        const isLocked  = idx > activeIdx;

        return (
          <div key={step.id} className="relative flex flex-col">
            {/* Connector line between steps */}
            {idx < STEPS.length - 1 && (
              <div className={`absolute left-[18px] top-10 w-px h-6 transition-colors duration-500 ${
                isDone ? 'bg-amber-500/50' : 'bg-white/[0.06]'
              }`} />
            )}

            <div className={`flex items-center gap-3 p-2.5 rounded-xl transition-all duration-300 ${
              isActive  ? 'bg-white/[0.04]' : 'hover:bg-white/[0.02]'
            }`}>
              {/* Icon / check */}
              <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 transition-all duration-300 ${
                isDone   ? 'bg-amber-500/20 border border-amber-500/30' :
                isActive ? 'bg-amber-500 shadow-lg shadow-amber-500/20' :
                           'bg-white/[0.04] border border-white/[0.08]'
              }`}>
                <step.icon className={`w-4 h-4 transition-colors duration-300 ${
                  isDone   ? 'text-amber-400' :
                  isActive ? 'text-black' :
                             'text-gray-700'
                }`} />
              </div>

              <div>
                <p className={`text-xs font-bold leading-none transition-colors duration-300 ${
                  isActive ? 'text-white' :
                  isDone   ? 'text-gray-500' :
                             'text-gray-700'
                }`}>
                  {step.label}
                </p>
                <p className={`text-[10px] mt-1 leading-none transition-colors duration-300 ${
                  isActive ? 'text-gray-500' : 'text-gray-800'
                }`}>
                  {step.sublabel}
                </p>
              </div>
            </div>

            {/* Spacer for connector */}
            {idx < STEPS.length - 1 && <div className="h-4" />}
          </div>
        );
      })}
    </aside>
  );
}