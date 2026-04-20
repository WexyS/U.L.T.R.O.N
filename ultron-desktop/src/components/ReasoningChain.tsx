import React from 'react';

export interface ReActStep {
  type: 'think' | 'plan' | 'act' | 'observe' | 'reflect';
  content: string;
  timestamp: string;
}

interface ReasoningChainProps {
  steps: ReActStep[];
}

const ReasoningChain: React.FC<ReasoningChainProps> = ({ steps }) => {
  if (steps.length === 0) return null;

  return (
    <div className="flex flex-col gap-4 p-4 my-4 bg-slate-900/50 rounded-xl border border-blue-500/20 backdrop-blur-md animate-in fade-in slide-in-from-bottom-4">
      <div className="flex items-center gap-2 mb-2 text-blue-400 font-semibold uppercase tracking-wider text-xs">
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
        </span>
        Ultron Reasoning Process
      </div>
      
      <div className="flex flex-col gap-3">
        {steps.map((step, idx) => (
          <div key={idx} className="flex gap-3 group">
            <div className="flex flex-col items-center">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold ${getTypeStyles(step.type)}`}>
                {step.type[0].toUpperCase()}
              </div>
              {idx !== steps.length - 1 && <div className="w-0.5 h-full bg-slate-700 my-1"></div>}
            </div>
            
            <div className="flex-1 pt-1">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-slate-400 uppercase">{step.type}</span>
                <span className="text-[10px] text-slate-600">{new Date(step.timestamp).toLocaleTimeString()}</span>
              </div>
              <p className="text-sm text-slate-300 mt-1 leading-relaxed whitespace-pre-wrap">
                {step.content}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const getTypeStyles = (type: string) => {
  switch (type) {
    case 'think': return 'bg-purple-500/20 text-purple-400 border border-purple-500/30';
    case 'plan': return 'bg-blue-500/20 text-blue-400 border border-blue-500/30';
    case 'act': return 'bg-amber-500/20 text-amber-400 border border-amber-500/30';
    case 'observe': return 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30';
    case 'reflect': return 'bg-rose-500/20 text-rose-400 border border-rose-500/30';
    default: return 'bg-slate-500/20 text-slate-400 border border-slate-500/30';
  }
};

export default ReasoningChain;
