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
];

// --- COMPONENT: Renders the list of questions ---
interface QuestionsListProps {
  answers: Record<string, string>;
  handleSelect: (key: string, value: string) => void;
}

export default function QuestionsList({ answers, handleSelect }: QuestionsListProps) {
  return (
    <div className="space-y-6">
      {QUESTIONS_DATA.map((q) => (
        <div key={q.key} className="bg-white shadow-sm rounded-lg p-6 border border-gray-100 transition-all hover:shadow-md">
          <h3 className="text-lg font-medium text-gray-900 mb-4">{q.question}</h3>
          <div className="space-y-2">
            {q.options.map((option) => (
              <label
                key={option}
                className={`flex items-center p-3 rounded-md cursor-pointer border transition-colors ${
                  answers[q.key] === option
                    ? 'bg-indigo-50 border-indigo-500 ring-1 ring-indigo-500'
                    : 'border-gray-200 hover:bg-gray-50'
                }`}
              >
                <input
                  type="radio"
                  name={q.key}
                  value={option}
                  checked={answers[q.key] === option}
                  onChange={() => handleSelect(q.key, option)}
                  className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300"
                />
                <span className="ml-3 block text-sm font-medium text-gray-700">
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