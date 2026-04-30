'use client';

import React from 'react';

// --- DATA: The 10 Questions ---
export const QUESTIONS_DATA = [
  {
    key: 'q1_business_model',
    question: '1. What is your exact business model?',
    options: [
      'Make-to-Order (Job Work / Custom fabrication)',
      'Make-to-Stock (Own Brand / Standard Products)',
      'Assembly Only (Buying parts, assembling)',
      'Trading & Distribution',
    ],
  },
  {
    key: 'q2_annual_turnover',
    question: '2. What is your approximate Annual Turnover?',
    options: ['₹50L - ₹2 Cr', '₹2 Cr - ₹10 Cr', '₹10 Cr - ₹50 Cr', '₹50 Cr+'],
  },
  {
    key: 'q3_cost_calculation_method',
    question: '3. How do you calculate the "Final Cost" of your product?',
    options: [
      'Mental Math (Rough estimate based on material)',
      'Excel Sheet (Updated sometimes)',
      'Tally (Purchase cost only)',
      'ERP / Real-time (Automated)',
    ],
  },
  {
    key: 'q4_inventory_value',
    question: '4. What is the approximate value of Inventory sitting in your factory right now?',
    options: [
      '< ₹10 Lakhs',
      '₹10 Lakhs - ₹50 Lakhs',
      '₹50 Lakhs - ₹2 Crores',
      'I honestly don\'t know (No live record)',
    ],
  },
  {
    key: 'q5_bom_management',
    question: '5. How do you handle "Bill of Materials" (BOM)?',
    options: [
      'We don\'t have formal BOMs',
      'We have Excel BOMs, but production often changes',
      'We use strict BOMs with revisions',
    ],
  },
  {
    key: 'q6_line_stoppages_freq',
    question: '6. How often do you face "Line Stoppages" because a material was missing?',
    options: ['Never', 'Once or twice a month', 'Weekly occurrence'],
  },
  {
    key: 'q7_invoice_vs_payment_tracking',
    question: '7. Who creates the Invoices vs. Who tracks the Payment?',
    options: [
      'I do both (Owner)',
      'Accountant does both',
      'Sales team invoices, Accounts team tracks',
    ],
  },
  {
    key: 'q8_return_rate',
    question: '8. How many "Returns" or "Rejections" do you get from customers?',
    options: ['< 1% (Rare)', '2-5% (Manageable)', '> 5% (Serious issue)'],
  },
  {
    key: 'q9_store_manager_dependency',
    question: '9. If your Store Manager leaves tomorrow, what happens?',
    options: [
      'Nothing, data is in the system',
      'Minor headache, but we have Excel backups',
      'Disaster. He knows where everything is kept',
    ],
  },
  {
    key: 'q10_dream_fix',
    question: '10. What is your "Dream Fix"?',
    options: [
      'I want to know my stock levels on my phone',
      'I want to stop leakage/theft',
      'I want accurate production costing',
      'I want to reduce manual data entry',
    ],
  },
  {
    key: 'q11_owner_firefighting',
    question: '11. How much time does the Owner/MD spend on daily production "firefighting"?',
    options: [
      '< 1 hour (Systems run themselves)',
      '2-4 hours (Coordination & follow-ups)',
      'Full Day (Nothing moves without my approval)',
    ],
  },
  {
    key: 'q12_delivery_reliability',
    question: '12. How often do you delay customer deliveries due to "Internal Chaos"?',
    options: [
      'Rarely (We are on time)',
      'Sometimes (10-20% of orders)',
      'Frequently (Customers are constantly calling)',
    ],
  },
  {
    key: 'q13_scrap_tracking',
    question: '13. How do you track "Scrap" or "Wastage" during production?',
    options: [
      'Strictly weighed and recorded',
      'Mental estimate by supervisor',
      'No formal tracking (Part of the process)',
    ],
  },
];

// --- COMPONENT: Renders the list of questions ---
interface QuestionsListProps {
  answers: Record<string, string>;
  handleSelect: (key: string, value: string) => void;
}

export default function QuestionsList({ answers, handleSelect }: QuestionsListProps) {
  return (
    <div className="space-y-5">
      {QUESTIONS_DATA.map((q) => (
        <div key={q.key} className="surface-card p-5 transition-all hover:border-[var(--border-default)]" style={{ borderRadius: 'var(--radius-lg)' }}>
          <h3 className="text-sm font-bold text-zinc-200 mb-3">{q.question}</h3>
          <div className="space-y-1.5">
            {q.options.map((option) => (
              <label
                key={option}
                className={`flex items-center p-2.5 rounded-xl cursor-pointer border transition-all duration-150 ${
                  answers[q.key] === option
                    ? 'bg-amber-500/10 border-amber-500/30 ring-1 ring-amber-500/30'
                    : 'border-transparent hover:bg-white/[0.03]'
                }`}
              >
                <input
                  type="radio"
                  name={q.key}
                  value={option}
                  checked={answers[q.key] === option}
                  onChange={() => handleSelect(q.key, option)}
                  className="h-3.5 w-3.5 text-amber-500 focus:ring-amber-500/30 border-zinc-700 bg-[var(--bg-void)] accent-amber-500"
                />
                <span className="ml-3 block text-xs font-medium text-zinc-400">
                  {option}
                </span>
              </label>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}