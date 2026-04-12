import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/Tabs';
import { Brain, FolderGit2, Users, ScrollText, Activity, Zap, Wifi, WifiOff } from 'lucide-react';

interface InspectorPanelProps {
  status: any;
  providers: any;
  workspace: any;
}

export default function InspectorPanel({ status, providers, workspace }: InspectorPanelProps) {
  const [activeTab, setActiveTab] = useState('memory');

  const agents = status?.agents || {};
  const llmProviders = providers || status?.llm_providers || {};
  const memory = status?.memory || {};
  const workspaceItems = workspace?.items || [];
  const isRunning = status?.running ?? false;

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-jarvis-border">
        <h3 className="text-sm font-semibold text-jarvis-text">Inspector</h3>
        <div className="flex items-center gap-2 mt-1">
          {isRunning ? (
            <Zap className="w-3 h-3 text-jarvis-success" />
          ) : (
            <WifiOff className="w-3 h-3 text-jarvis-danger" />
          )}
          <span className="text-xs text-jarvis-textMuted">
            {isRunning ? 'Orchestrator running' : 'Orchestrator not started'}
          </span>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
        <TabsList className="grid grid-cols-5 gap-1 p-2">
          <TabsTrigger value="memory" title="Memory"><Brain className="w-4 h-4" /></TabsTrigger>
          <TabsTrigger value="workspace" title="Workspace"><FolderGit2 className="w-4 h-4" /></TabsTrigger>
          <TabsTrigger value="agents" title="Agents"><Users className="w-4 h-4" /></TabsTrigger>
          <TabsTrigger value="logs" title="Providers"><ScrollText className="w-4 h-4" /></TabsTrigger>
          <TabsTrigger value="system" title="System"><Activity className="w-4 h-4" /></TabsTrigger>
        </TabsList>

        <div className="flex-1 overflow-y-auto p-4">
          <TabsContent value="memory">
            <MemoryTab memory={memory} />
          </TabsContent>
          <TabsContent value="workspace">
            <WorkspaceTab items={workspaceItems} />
          </TabsContent>
          <TabsContent value="agents">
            <AgentsTab agents={agents} />
          </TabsContent>
          <TabsContent value="logs">
            <ProvidersTab providers={llmProviders} />
          </TabsContent>
          <TabsContent value="system">
            <SystemTab status={status} />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}

function MemoryTab({ memory }: { memory: any }) {
  const vectorEntries = memory?.vector_entries || 0;
  const graphNodes = memory?.graph_nodes || 0;
  const workingMessages = memory?.working_messages || 0;

  return (
    <div className="space-y-3">
      <h4 className="text-xs font-medium text-jarvis-textMuted uppercase">Working Memory</h4>
      <div className="p-3 rounded-lg bg-jarvis-card border border-jarvis-border">
        <div className="flex justify-between text-xs mb-1">
          <span className="text-jarvis-textMuted">Messages</span>
          <span className="text-jarvis-primary">{workingMessages} / 20</span>
        </div>
        <div className="w-full bg-jarvis-bg rounded-full h-1.5">
          <div
            className="bg-gradient-to-r from-jarvis-primary to-jarvis-accent h-1.5 rounded-full transition-all"
            style={{ width: `${Math.min((workingMessages / 20) * 100, 100)}%` }}
          />
        </div>
      </div>

      <h4 className="text-xs font-medium text-jarvis-textMuted uppercase mt-4">Long-Term Memory</h4>
      <div className="space-y-2">
        <div className="flex items-center justify-between p-2 rounded bg-jarvis-card border border-jarvis-border text-xs">
          <span className="text-jarvis-textMuted">Vector entries</span>
          <span className="text-jarvis-text font-mono">{vectorEntries}</span>
        </div>
        <div className="flex items-center justify-between p-2 rounded bg-jarvis-card border border-jarvis-border text-xs">
          <span className="text-jarvis-textMuted">Graph nodes</span>
          <span className="text-jarvis-text font-mono">{graphNodes}</span>
        </div>
      </div>

      {vectorEntries === 0 && graphNodes === 0 && (
        <div className="text-xs text-jarvis-textMuted text-center py-8">
          No memories stored yet. Interact with Jarvis to build memory.
        </div>
      )}
    </div>
  );
}

function WorkspaceTab({ items }: { items: any[] }) {
  if (!items.length) {
    return (
      <div className="text-xs text-jarvis-textMuted text-center py-8">
        No workspace items yet. Use the Workspace panel to clone sites or generate apps.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {items.map((item: any) => (
        <div key={item.id} className="p-2 rounded-lg bg-jarvis-card border border-jarvis-border text-xs">
          <div className="flex items-center justify-between">
            <span className="text-jarvis-text font-medium">{item.name}</span>
            <span className={`px-1.5 py-0.5 rounded text-xs ${
              item.type === 'cloned' ? 'bg-jarvis-primary/10 text-jarvis-primary' :
              item.type === 'generated' ? 'bg-jarvis-accent/10 text-jarvis-accent' :
              'bg-jarvis-success/10 text-jarvis-success'
            }`}>
              {item.type}
            </span>
          </div>
          {item.description && (
            <p className="text-jarvis-textMuted mt-1 truncate">{item.description}</p>
          )}
        </div>
      ))}
    </div>
  );
}

function AgentsTab({ agents }: { agents: Record<string, any> }) {
  const allAgents = [
    { key: 'coder', name: 'Coder', emoji: '💻' },
    { key: 'researcher', name: 'Researcher', emoji: '🔍' },
    { key: 'rpa_operator', name: 'RPA Operator', emoji: '🤖' },
    { key: 'email', name: 'Email', emoji: '📧' },
    { key: 'sysmon', name: 'SysMon', emoji: '📊' },
    { key: 'clipboard', name: 'Clipboard', emoji: '📋' },
    { key: 'meeting', name: 'Meeting', emoji: '🎙️' },
    { key: 'files', name: 'Files', emoji: '📁' },
  ];

  if (!Object.keys(agents).length) {
    return (
      <div className="text-xs text-jarvis-textMuted text-center py-8">
        Agent status unavailable. Check if orchestrator is running.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {allAgents.map((a) => {
        const agent = agents[a.key];
        const isActive = agent?.status === 'busy';
        const isReady = agent?.status === 'idle';
        const completed = agent?.tasks_completed || 0;
        const failed = agent?.tasks_failed || 0;

        return (
          <div key={a.key} className="flex items-center justify-between p-2 rounded-lg bg-jarvis-card border border-jarvis-border text-xs">
            <div className="flex items-center gap-2">
              <span>{a.emoji}</span>
              <div>
                <span className="text-jarvis-text font-medium">{a.name}</span>
                {completed > 0 && (
                  <span className="text-jarvis-textMuted ml-1">({completed}✓{failed > 0 ? ` ${failed}✗` : ''})</span>
                )}
              </div>
            </div>
            <span className={`w-2 h-2 rounded-full ${
              isActive ? 'bg-jarvis-success animate-pulse' :
              isReady ? 'bg-jarvis-primary/50' :
              'bg-jarvis-textMuted/30'
            }`} title={agent?.status || 'unknown'} />
          </div>
        );
      })}
    </div>
  );
}

function ProvidersTab({ providers }: { providers: Record<string, any> }) {
  const entries = Object.entries(providers);

  if (!entries.length) {
    return (
      <div className="text-xs text-jarvis-textMuted text-center py-8">
        Provider data unavailable. Check API keys in .env.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {entries.map(([key, val]: [string, any]) => {
        const available = val?.available ?? false;
        const latency = val?.latency_ms ?? val?.stats?.avg_latency_ms ?? '—';
        const score = val?.stats?.health_score ?? '—';

        return (
          <div key={key} className="p-2 rounded-lg bg-jarvis-card border border-jarvis-border text-xs">
            <div className="flex items-center justify-between mb-1">
              <span className="text-jarvis-text font-medium capitalize">{key}</span>
              {available ? (
                <span className="flex items-center gap-1 text-jarvis-success">
                  <Wifi className="w-3 h-3" /> OK
                </span>
              ) : (
                <span className="flex items-center gap-1 text-jarvis-danger">
                  <WifiOff className="w-3 h-3" /> OFF
                </span>
              )}
            </div>
            <div className="flex gap-3 text-jarvis-textMuted">
              <span>Latency: {latency}</span>
              <span>Health: {score}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function SystemTab({ status }: { status: any }) {
  const uptime = status?.uptime_seconds ?? 0;
  const running = status?.running ?? false;
  const events = status?.event_bus_events ?? 0;

  const fmtUptime = uptime < 60 ? `${Math.floor(uptime)}s` :
                    uptime < 3600 ? `${Math.floor(uptime / 60)}m` :
                    `${Math.floor(uptime / 3600)}h ${Math.floor((uptime % 3600) / 60)}m`;

  return (
    <div className="space-y-3">
      <div className="p-3 rounded-lg bg-jarvis-card border border-jarvis-border">
        <div className="text-xs text-jarvis-textMuted mb-1">Status</div>
        <div className="flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${running ? 'bg-jarvis-success animate-pulse' : 'bg-jarvis-danger'}`} />
          <span className="text-xs text-jarvis-text">{running ? 'Running' : 'Not Started'}</span>
        </div>
      </div>

      <div className="p-3 rounded-lg bg-jarvis-card border border-jarvis-border">
        <div className="text-xs text-jarvis-textMuted mb-1">Uptime</div>
        <div className="text-sm text-jarvis-text font-mono">{fmtUptime}</div>
      </div>

      <div className="p-3 rounded-lg bg-jarvis-card border border-jarvis-border">
        <div className="text-xs text-jarvis-textMuted mb-1">Event Bus</div>
        <div className="text-sm text-jarvis-text font-mono">{events} recent events</div>
      </div>
    </div>
  );
}
