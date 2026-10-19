/**
 * TechSift AI - Knowledge Journey Workflow Stepper.
 * Visual technical learning progression: Understand -> Listen -> Practice -> Master.
 * In Phase 3, only 'Understand' is active; others are marked Coming Soon.
 */

import React from 'react';
import { BookOpen, Headphones, PenTool, Award, Lock, ArrowRight, ArrowLeft } from 'lucide-react';
import { useLanguage } from '../../context/LanguageContext';

export const KnowledgeJourney: React.FC<{ compact?: boolean }> = ({ compact = false }) => {
  const { t, direction } = useLanguage();
  const ArrowIcon = direction === 'rtl' ? ArrowLeft : ArrowRight;

  const stages = [
    {
      id: 'understand',
      title: t.stageUnderstand,
      desc: t.stageUnderstandDesc,
      icon: BookOpen,
      status: 'active',
      badge: t.currentStage,
      badgeColor: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300',
    },
    {
      id: 'listen',
      title: t.stageListen,
      desc: t.stageListenDesc,
      icon: Headphones,
      status: 'active', // Active in Phase 4B
      badge: 'Active ($0)',
      badgeColor: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300',
    },
    {
      id: 'practice',
      title: t.stagePractice,
      desc: t.stagePracticeDesc,
      icon: PenTool,
      status: 'active', // Active in Phase 5A
      badge: 'Active ($0)',
      badgeColor: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300',
    },
    {
      id: 'master',
      title: t.stageMaster,
      desc: t.stageMasterDesc,
      icon: Award,
      status: 'active', // Active in Phase 5C
      badge: 'Active ($0)',
      badgeColor: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300',
    },
  ];

  if (compact) {
    return (
      <div className="flex items-center gap-2 overflow-x-auto py-1">
        {stages.map((stage, idx) => {
          const Icon = stage.icon;
          const isActive = stage.status === 'active';
          return (
            <React.Fragment key={stage.id}>
              <div
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-500/20'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 opacity-60'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{stage.title}</span>
                {!isActive && <Lock className="w-3 h-3 text-slate-400" />}
              </div>
              {idx < stages.length - 1 && (
                <ArrowIcon className="w-3 h-3 text-slate-300 dark:text-slate-700 shrink-0" />
              )}
            </React.Fragment>
          );
        })}
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            {t.journeyTitle}
          </h3>
          <p className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">
            Phase 5C: Technical Summaries, Audio Studio, Interactive Curricula, Assessments & Progress Mastery
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 relative">
        {stages.map((stage, idx) => {
          const Icon = stage.icon;
          const isActive = stage.status === 'active';

          return (
            <div
              key={stage.id}
              className={`relative rounded-xl p-4 border transition-all ${
                isActive
                  ? 'border-indigo-500 bg-indigo-50/50 dark:bg-indigo-950/20 shadow-sm'
                  : 'border-slate-200 dark:border-slate-800 bg-slate-50/40 dark:bg-slate-900/40 opacity-75'
              }`}
            >
              <div className="flex items-center justify-between mb-3">
                <div
                  className={`p-2 rounded-lg ${
                    isActive
                      ? 'bg-indigo-600 text-white'
                      : 'bg-slate-200 dark:bg-slate-800 text-slate-500 dark:text-slate-400'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                </div>
                <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${stage.badgeColor}`}>
                  {stage.badge}
                </span>
              </div>

              <div className="flex items-center gap-1.5 font-semibold text-slate-900 dark:text-white text-sm mb-1">
                <span>{stage.title}</span>
                {!isActive && <Lock className="w-3.5 h-3.5 text-slate-400 inline" />}
              </div>

              <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                {stage.desc}
              </p>

              {/* Connecting arrow for larger screens */}
              {idx < stages.length - 1 && (
                <div className="hidden md:block absolute -right-3.5 top-1/2 -translate-y-1/2 z-10">
                  <div className="w-7 h-7 rounded-full bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex items-center justify-center">
                    <ArrowIcon className="w-3.5 h-3.5 text-slate-400" />
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
