import { Activity, Cpu, Database, Layers } from 'lucide-react';

interface StatusBadgeProps {
  status: any;
  providers?: any;
  isConnected: boolean;
}

export default function StatusBadge({ status, providers, isConnected }: StatusBadgeProps) {
  if (!status) {
    return (
      <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-ultron-panel border border-ultron-border">
        <div className="w-2 h-2 rounded-full animate-pulse bg-ultron-warning" />
        <span className="text-xs text-ultron-textMuted">Connecting...</span>
      </div>
    );
  }

  const activeProvidersFromState = Array.isArray(providers?.available) ? providers.available : [];
  const activeProvidersFromStatus = Object.entries(status.llm_providers || {})
    .filter(([_, v]: [string, any]) => v.available)
    .map(([k]) => k);
  const activeProviders = activeProvidersFromState.length > 0
    ? activeProvidersFromState
    : activeProvidersFromStatus;

  const agents = status.agents || {};
  const activeAgents = Object.values(agents).filter((a: any) => a.status === 'idle').length;

  return (
    <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-ultron-panel border border-ultron-border">
      {/* Connection status */}
      <div className="flex items-center gap-2">
        <Activity className={`w-4 h-4 ${isConnected ? 'text-ultron-accent' : 'text-ultron-danger'}`} />
        <span className={`text-xs font-medium ${isConnected ? 'text-ultron-accent' : 'text-ultron-danger'}`}>
          {isConnected ? 'Online' : 'Offline'}
        </span>
      </div>

      <div className="w-px h-4 bg-ultron-border" />

      {/* Agents */}
      <div className="flex items-center gap-1.5 text-ultron-textMuted" title={`${activeAgents} agents ready`}>
        <Layers className="w-3.5 h-3.5" />
        <span className="text-xs">{activeAgents}</span>
      </div>

      {/* Providers */}
      <div className="flex items-center gap-1.5 text-ultron-textMuted" title={`Providers: ${activeProviders.join(', ') || 'None'}`}>
        <Cpu className="w-3.5 h-3.5" />
        <span className="text-xs">{activeProviders.length}</span>
      </div>

      {/* Brain Status */}
      {activeProviders.includes('brain') && (
        <div className="flex items-center gap-1.5 text-ultron-accent animate-pulse" title="Ultron Brain is Active">
          <Activity className="w-3.5 h-3.5" />
          <span className="text-[10px] font-bold uppercase tracking-tighter">Brain</span>
        </div>
      )}

      {/* Memory */}
      {status.memory && (
        <div className="flex items-center gap-1.5 text-ultron-textMuted" title={`${status.memory.vector_entries || 0} vector entries`}>
          <Database className="w-3.5 h-3.5" />
          <span className="text-xs">{status.memory.vector_entries || 0}</span>
        </div>
      )}
    </div>
  );
}
