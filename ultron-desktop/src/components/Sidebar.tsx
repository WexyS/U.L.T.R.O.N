import { Settings, Trash2, MessageSquare, Globe, Activity, Zap, Bot, MessageCircle, Mic } from 'lucide-react';
import { API_URL } from '../config';

type ActivePanel = 'chat' | 'workspace' | 'agents' | 'training' | 'composer';

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
  const handleLaunchVoice = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v2/voice/launch`, { method: 'POST' });
      if (!res.ok) throw new Error('Failed to launch voice mode');
      const data = await res.json();
      console.log('Voice mode launched:', data);
    } catch (err) {
      console.error('Error launching voice mode:', err);
      alert('Ses modu başlatılamadı. Lütfen backend\'in çalıştığından emin olun.');
    }
  };

  return (
    <div className="w-64 flex flex-col relative z-20 border-r border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">
      {/* Logo / Brand */}
      <div className="px-6 py-8">
        <div className="flex items-center gap-3">
          <motion.div 
            whileHover={{ rotate: 180 }}
            transition={{ duration: 0.5 }}
            className="w-10 h-10 rounded-xl flex items-center justify-center bg-indigo-600 shadow-lg shadow-indigo-500/20"
          >
            <Zap className="w-6 h-6 text-white" />
          </motion.div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-zinc-900 dark:text-white">Ultron</h1>
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-500">Autonomous AGI</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 space-y-1">
        {[
          { id: 'chat', label: 'Chat', icon: MessageSquare },
          { id: 'workspace', label: 'Workspace', icon: Globe },
          { id: 'agents', label: 'Agents', icon: Bot },
        ].map((item) => (
          <button
            key={item.id}
            onClick={() => onPanelChange(item.id as ActivePanel)}
            className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-xl transition-all duration-200 group ${
              activePanel === item.id
                ? 'bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400 shadow-sm'
                : 'text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800/50 hover:text-zinc-900 dark:hover:text-zinc-100'
            }`}
          >
            <item.icon className={`w-5 h-5 transition-transform group-hover:scale-110 ${activePanel === item.id ? 'text-indigo-600 dark:text-indigo-400' : ''}`} />
            <span className="font-semibold text-sm">{item.label}</span>
          </button>
        ))}
      </nav>

      {/* Bottom Section */}
      <div className="p-4 space-y-4">
        {/* Status indicator */}
        <div className="px-4 py-3 rounded-xl bg-zinc-50 dark:bg-zinc-800/30 border border-zinc-100 dark:border-zinc-800">
          <div className="flex items-center gap-2 mb-1">
            <div className={`w-2 h-2 rounded-full ${getStatusLabel(status) === 'Online' ? 'bg-green-500 animate-pulse' : 'bg-zinc-400'}`} />
            <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-400">System Status</span>
          </div>
          <p className="text-xs font-semibold text-zinc-700 dark:text-zinc-300">{getStatusLabel(status)}</p>
        </div>

        <div className="space-y-1">
          <button
            onClick={handleLaunchVoice}
            className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl transition-all hover:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 group"
          >
            <Mic className="w-5 h-5 group-hover:scale-110 transition-transform" />
            <span className="font-bold text-xs uppercase tracking-wider">Voice Mode</span>
          </button>

          <button
            onClick={onClear}
            className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl transition-all hover:bg-red-500/10 text-zinc-500 hover:text-red-600 dark:hover:text-red-400 group"
          >
            <Trash2 className="w-5 h-5 group-hover:scale-110 transition-transform" />
            <span className="font-semibold text-sm">Clear History</span>
          </button>

          <button
            onClick={() => onPanelChange('settings')}
            className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-xl transition-all group ${
              activePanel === 'settings'
                ? 'bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400 shadow-sm'
                : 'text-zinc-500 hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-500 hover:text-zinc-900'
            }`}
          >
            <Settings className={`w-5 h-5 transition-transform group-hover:rotate-45 ${activePanel === 'settings' ? 'text-indigo-600 dark:text-indigo-400' : ''}`} />
            <span className="font-semibold text-sm">Settings</span>
          </button>
        </div>
      </div>
    </div>
  );
}
