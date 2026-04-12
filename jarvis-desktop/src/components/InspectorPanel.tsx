import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/Tabs';
import { Brain, FolderGit2, Users, ScrollText, Activity } from 'lucide-react';

export default function InspectorPanel() {
  const [activeTab, setActiveTab] = useState('memory');

  return (
    <div className="h-full flex flex-col">
      <div className="p-4 border-b border-jarvis-border">
        <h3 className="text-sm font-semibold text-jarvis-text">Inspector</h3>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
        <TabsList className="grid grid-cols-5 gap-1 p-2">
          <TabsTrigger value="memory" title="Memory"><Brain className="w-4 h-4" /></TabsTrigger>
          <TabsTrigger value="workspace" title="Workspace"><FolderGit2 className="w-4 h-4" /></TabsTrigger>
          <TabsTrigger value="agents" title="Agents"><Users className="w-4 h-4" /></TabsTrigger>
          <TabsTrigger value="logs" title="Logs"><ScrollText className="w-4 h-4" /></TabsTrigger>
          <TabsTrigger value="system" title="System"><Activity className="w-4 h-4" /></TabsTrigger>
        </TabsList>

        <div className="flex-1 overflow-y-auto p-4">
          <TabsContent value="memory">
            <MemoryTab />
          </TabsContent>
          <TabsContent value="workspace">
            <WorkspaceTab />
          </TabsContent>
          <TabsContent value="agents">
            <AgentsTab />
          </TabsContent>
          <TabsContent value="logs">
            <LogsTab />
          </TabsContent>
          <TabsContent value="system">
            <SystemTab />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}

function MemoryTab() {
  return (
    <div className="space-y-3">
      <h4 className="text-xs font-medium text-jarvis-textMuted uppercase">Working Memory</h4>
      <div className="p-3 rounded-lg bg-jarvis-card border border-jarvis-border">
        <div className="flex justify-between text-xs mb-1">
          <span className="text-jarvis-textMuted">Messages</span>
          <span className="text-jarvis-primary">0 / 20</span>
        </div>
        <div className="w-full bg-jarvis-bg rounded-full h-1.5">
          <div className="bg-gradient-to-r from-jarvis-primary to-jarvis-accent h-1.5 rounded-full" style={{ width: '0%' }} />
        </div>
      </div>

      <h4 className="text-xs font-medium text-jarvis-textMuted uppercase mt-4">Long-Term Episodes</h4>
      <div className="text-xs text-jarvis-textMuted text-center py-8">
        No episodes stored yet
      </div>
    </div>
  );
}

function WorkspaceTab() {
  return (
    <div className="space-y-3">
      <h4 className="text-xs font-medium text-jarvis-textMuted uppercase">Recent Items</h4>
      <div className="text-xs text-jarvis-textMuted text-center py-8">
        No workspace items yet. Use the Workspace panel to clone sites or generate apps.
      </div>
    </div>
  );
}

function AgentsTab() {
  const agents = [
    { name: 'Coder', status: 'idle', emoji: '💻' },
    { name: 'Researcher', status: 'idle', emoji: '🔍' },
    { name: 'RPA Operator', status: 'idle', emoji: '🤖' },
    { name: 'Email', status: 'idle', emoji: '📧' },
    { name: 'SysMon', status: 'idle', emoji: '📊' },
    { name: 'Clipboard', status: 'idle', emoji: '📋' },
    { name: 'Meeting', status: 'idle', emoji: '🎙️' },
    { name: 'Files', status: 'idle', emoji: '📁' },
  ];

  return (
    <div className="space-y-2">
      {agents.map((agent) => (
        <div key={agent.name} className="flex items-center justify-between p-2 rounded-lg bg-jarvis-card border border-jarvis-border">
          <div className="flex items-center gap-2">
            <span>{agent.emoji}</span>
            <span className="text-xs">{agent.name}</span>
          </div>
          <span className={`w-2 h-2 rounded-full ${agent.status === 'active' ? 'bg-jarvis-success animate-pulse' : 'bg-jarvis-textMuted/30'}`} />
        </div>
      ))}
    </div>
  );
}

function LogsTab() {
  return (
    <div className="space-y-2">
      <div className="font-mono text-xs p-2 rounded bg-jarvis-bg border border-jarvis-border">
        <div className="text-jarvis-textMuted">// System logs will appear here</div>
        <div className="text-jarvis-success">[INFO] Jarvis API started</div>
        <div className="text-jarvis-primary">[INFO] LLM Router initialized</div>
      </div>
    </div>
  );
}

function SystemTab() {
  return (
    <div className="space-y-3">
      <div className="p-3 rounded-lg bg-jarvis-card border border-jarvis-border">
        <div className="text-xs text-jarvis-textMuted mb-1">CPU Usage</div>
        <div className="w-full bg-jarvis-bg rounded-full h-2">
          <div className="bg-jarvis-primary h-2 rounded-full" style={{ width: '15%' }} />
        </div>
        <div className="text-xs text-jarvis-text mt-1">15%</div>
      </div>

      <div className="p-3 rounded-lg bg-jarvis-card border border-jarvis-border">
        <div className="text-xs text-jarvis-textMuted mb-1">RAM Usage</div>
        <div className="w-full bg-jarvis-bg rounded-full h-2">
          <div className="bg-jarvis-accent h-2 rounded-full" style={{ width: '42%' }} />
        </div>
        <div className="text-xs text-jarvis-text mt-1">13.4 / 32 GB</div>
      </div>

      <div className="p-3 rounded-lg bg-jarvis-card border border-jarvis-border">
        <div className="text-xs text-jarvis-textMuted mb-1">GPU (RTX 4080)</div>
        <div className="w-full bg-jarvis-bg rounded-full h-2">
          <div className="bg-jarvis-success h-2 rounded-full" style={{ width: '8%' }} />
        </div>
        <div className="text-xs text-jarvis-text mt-1">8%</div>
      </div>
    </div>
  );
}
