import { Settings, Trash2, MessageSquare, Globe, Activity, Zap, Bot, MessageCircle } from 'lucide-react';

type ActivePanel = 'chat' | 'workspace' | 'agents' | 'training';

interface SidebarProps {
  status: unknown;
  onClear: () => void;
  activePanel: ActivePanel;
  onPanelChange: (panel: ActivePanel) => void;
  onToggleConversationSidebar?: () => void;
}

function getStatusLabel(status: unknown): string {
  if (!status) return 'Ready';
  if (typeof status === 'string') return status;
  if (status && typeof status === 'object' && 'running' in status && (status as Record<string, unknown>).running) return 'Online';
  if (status && typeof status === 'object' && 'error' in status && (status as Record<string, unknown>).error) return 'Error';
  return 'Ready';
}

export default function Sidebar({ status, onClear, activePanel, onPanelChange, onToggleConversationSidebar }: SidebarProps) {
  return (
    <div className="w-64 border-r flex flex-col relative z-20" style={{ backgroundColor: 'var(--color-panel)', borderColor: 'var(--color-border)' }}>
      {/* Logo / Brand */}
      <div className="px-6 py-5 border-b" style={{ borderColor: 'var(--color-border)' }}>
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: 'linear-gradient(135deg, rgb(var(--color-accent)), #4f46e5)' }}>
            <Zap className="w-6 h-6" style={{ color: 'white' }} />
          </div>
          <div>
            <h1 className="text-lg font-bold" style={{ color: 'var(--color-text)' }}>Ultron</h1>
            <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>AI Assistant v2.1</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        <button
          onClick={() => onPanelChange('chat')}
          className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all ${
            activePanel === 'chat'
              ? 'shadow-sm'
              : 'hover:opacity-80'
          }`}
          style={{
            backgroundColor: activePanel === 'chat' ? 'rgba(var(--color-accent), 0.1)' : 'transparent',
            color: activePanel === 'chat' ? 'var(--color-accent)' : 'var(--color-text-secondary)',
          }}
        >
          <MessageSquare className="w-5 h-5" />
          <span className="font-medium">Chat</span>
        </button>

        <button
          onClick={() => onPanelChange('workspace')}
          className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all ${
            activePanel === 'workspace'
              ? 'shadow-sm'
              : 'hover:opacity-80'
          }`}
          style={{
            backgroundColor: activePanel === 'workspace' ? 'rgba(var(--color-accent), 0.1)' : 'transparent',
            color: activePanel === 'workspace' ? 'var(--color-accent)' : 'var(--color-text-secondary)',
          }}
        >
          <Globe className="w-5 h-5" />
          <span className="font-medium">Workspace</span>
        </button>

        <button
          onClick={() => onPanelChange('agents')}
          className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all ${
            activePanel === 'agents'
              ? 'shadow-sm'
              : 'hover:opacity-80'
          }`}
          style={{
            backgroundColor: activePanel === 'agents' ? 'rgba(var(--color-accent), 0.1)' : 'transparent',
            color: activePanel === 'agents' ? 'var(--color-accent)' : 'var(--color-text-secondary)',
          }}
        >
          <Bot className="w-5 h-5" />
          <span className="font-medium">Agents</span>
        </button>
      </nav>

      {/* Status */}
      <div className="px-3 py-4 border-t" style={{ borderColor: 'var(--color-border)' }}>
        <div className="px-3 py-2 rounded-lg" style={{ backgroundColor: 'var(--color-bg-tertiary)' }}>
          <p className="text-xs mb-1" style={{ color: 'var(--color-text-secondary)' }}>Status</p>
          <p className="text-sm font-medium capitalize" style={{ color: 'var(--color-text)' }}>{getStatusLabel(status)}</p>
        </div>
      </div>

      {/* Actions */}
      <div className="px-3 py-4 border-t space-y-2" style={{ borderColor: 'var(--color-border)' }}>
        {/* Conversations Toggle */}
        {onToggleConversationSidebar && (
          <button
            onClick={onToggleConversationSidebar}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all hover:opacity-80"
            style={{ color: 'var(--color-text-secondary)' }}
          >
            <MessageCircle className="w-5 h-5" />
            <span className="font-medium">Conversations</span>
          </button>
        )}

        <button
          onClick={onClear}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all hover:opacity-80"
          style={{ color: 'var(--color-text-secondary)' }}
        >
          <Trash2 className="w-5 h-5" />
          <span className="font-medium">Clear Chat</span>
        </button>

        <button
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all hover:opacity-80"
          style={{ color: 'var(--color-text-secondary)' }}
          aria-label="Settings (coming soon)"
          title="Settings (coming soon)"
          aria-disabled
          onClick={() => alert('Settings panel coming soon!')}
        >
          <Settings className="w-5 h-5" />
          <span className="font-medium">Settings</span>
        </button>
      </div>
    </div>
  );
}
