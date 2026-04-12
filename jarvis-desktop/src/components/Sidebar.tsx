import { Bot, Code2, Search, Monitor, Zap, MemoryStick, Shield, MessageSquare, FolderOpen } from 'lucide-react';

interface SidebarProps {
  status: any;
  onClear: () => void;
  activePanel: 'chat' | 'workspace';
  onPanelChange: (panel: 'chat' | 'workspace') => void;
}

const AGENT_INFO: Record<string, { icon: React.ReactNode; desc: string; color: string }> = {
  coder: {
    icon: <Code2 className="w-5 h-5" />,
    desc: 'Writes, executes & self-heals code',
    color: 'text-purple-400'
  },
  researcher: {
    icon: <Search className="w-5 h-5" />,
    desc: 'Multi-hop web research with citations',
    color: 'text-blue-400'
  },
  rpa_operator: {
    icon: <Monitor className="w-5 h-5" />,
    desc: 'Screen control, OCR & automation',
    color: 'text-orange-400'
  }
};

export default function Sidebar({ status, onClear, activePanel, onPanelChange }: SidebarProps) {
  const agents = status?.agents || {};
  const providers = status?.llm_providers || {};
  const memory = status?.memory || {};

  return (
    <div className="w-60 bg-jarvis-panel border-r border-jarvis-border flex flex-col">
      {/* Logo */}
      <div className="p-4 border-b border-jarvis-border">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="w-10 h-10 rounded-full bg-jarvis-primary/10 border-2 border-jarvis-primary/30 flex items-center justify-center">
              <Bot className="w-5 h-5 text-jarvis-primary" />
            </div>
            <div className="absolute -inset-1 rounded-full border border-jarvis-primary/20 animate-pulse-slow" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white tracking-wider">J.A.R.V.I.S</h1>
            <p className="text-xs text-jarvis-textMuted">v2.0 Multi-Agent</p>
          </div>
        </div>
      </div>

      {/* Panel Switcher */}
      <div className="flex gap-2 p-3 border-b border-jarvis-border">
        <button
          onClick={() => onPanelChange('chat')}
          className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-md text-xs font-medium transition-colors ${
            activePanel === 'chat'
              ? 'bg-jarvis-primary/10 text-jarvis-primary border border-jarvis-primary/30'
              : 'text-jarvis-textMuted hover:text-jarvis-text hover:bg-jarvis-card'
          }`}
        >
          <MessageSquare className="w-3.5 h-3.5" />
          Chat
        </button>
        <button
          onClick={() => onPanelChange('workspace')}
          className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-md text-xs font-medium transition-colors ${
            activePanel === 'workspace'
              ? 'bg-jarvis-accent/10 text-jarvis-accent border border-jarvis-accent/30'
              : 'text-jarvis-textMuted hover:text-jarvis-text hover:bg-jarvis-card'
          }`}
        >
          <FolderOpen className="w-3.5 h-3.5" />
          Workspace
        </button>
      </div>

      {/* Agents */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        <h2 className="text-xs font-semibold text-jarvis-textMuted uppercase tracking-wider">Agents</h2>
        {Object.entries(AGENT_INFO).map(([key, info]) => {
          const agent = agents[key] as any;
          const isActive = agent?.status === 'busy';
          const isReady = agent?.status === 'idle';

          return (
            <div
              key={key}
              className={`p-3 rounded-lg border transition-all ${
                isActive
                  ? 'bg-jarvis-primary/5 border-jarvis-primary/30'
                  : isReady
                    ? 'bg-jarvis-bg border-jarvis-border/50'
                    : 'bg-jarvis-bg/50 border-jarvis-border/30 opacity-60'
              }`}
            >
              <div className="flex items-center gap-2 mb-1">
                <span className={info.color}>{info.icon}</span>
                <span className="text-sm font-medium text-white capitalize">
                  {key.replace('_', ' ')}
                </span>
                <div className={`ml-auto w-2 h-2 rounded-full ${
                  isActive ? 'bg-jarvis-primary animate-pulse' :
                  isReady ? 'bg-jarvis-success' : 'bg-jarvis-textMuted'
                }`} />
              </div>
              <p className="text-xs text-jarvis-textMuted">{info.desc}</p>
              {agent?.tasks_completed > 0 && (
                <p className="text-xs text-jarvis-textMuted mt-1">
                  ✓ {agent.tasks_completed} tasks
                </p>
              )}
            </div>
          );
        })}

        {/* LLM Providers */}
        <div className="pt-3 border-t border-jarvis-border">
          <h2 className="text-xs font-semibold text-jarvis-textMuted uppercase tracking-wider mb-2">Providers</h2>
          <div className="space-y-1">
            {Object.entries(providers).map(([key, val]: [string, any]) => (
              <div key={key} className="flex items-center justify-between py-1 text-xs">
                <span className="text-jarvis-textMuted capitalize">{key}</span>
                <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                  val.available
                    ? 'bg-jarvis-success/10 text-jarvis-success'
                    : 'bg-jarvis-danger/10 text-jarvis-danger'
                }`}>
                  {val.available ? 'OK' : 'OFF'}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Memory */}
        {memory.vector_entries > 0 && (
          <div className="pt-3 border-t border-jarvis-border">
            <h2 className="text-xs font-semibold text-jarvis-textMuted uppercase tracking-wider mb-2">Memory</h2>
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-xs text-jarvis-textMuted">
                <MemoryStick className="w-4 h-4" />
                <span>{memory.vector_entries} vectors</span>
              </div>
              {memory.graph_nodes > 0 && (
                <div className="flex items-center gap-2 text-xs text-jarvis-textMuted">
                  <Shield className="w-4 h-4" />
                  <span>{memory.graph_nodes} graph nodes</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="p-3 border-t border-jarvis-border">
        <button
          onClick={onClear}
          className="w-full px-3 py-2 rounded-lg bg-jarvis-bg border border-jarvis-border text-jarvis-textMuted hover:text-white hover:border-jarvis-primary/50 transition-all text-sm"
        >
          Clear Chat
        </button>
      </div>
    </div>
  );
}
