import { Settings, Trash2, MessageSquare, Globe, Activity, Zap, Bot, Mic, LayoutGrid } from 'lucide-react';
import { motion } from 'framer-motion';
import { API_URL } from '../config';

type ActivePanel = 'chat' | 'workspace' | 'agents' | 'training' | 'composer' | 'settings';

interface SidebarProps {
  status: any;
  onClear: () => void;
  activePanel: ActivePanel;
  onPanelChange: (panel: ActivePanel) => void;
  onToggleConversationSidebar?: () => void;
  isCollapsed?: boolean;
}

export default function Sidebar({ 
  status, 
  onClear, 
  activePanel, 
  onPanelChange, 
  onToggleConversationSidebar,
  isCollapsed = false
}: SidebarProps) {
  
  const navItems = [
    { id: 'chat', label: 'Chat', icon: MessageSquare },
    { id: 'workspace', label: 'Workspace', icon: Globe },
    { id: 'agents', label: 'Agents', icon: LayoutGrid },
  ];

  if (isCollapsed) {
    return (
      <div className="h-full flex flex-col items-center py-6 gap-6">
        <motion.div 
          whileHover={{ scale: 1.1 }}
          className="w-10 h-10 rounded-2xl flex items-center justify-center bg-purple-600 text-white shadow-lg shadow-purple-500/20"
        >
          <Bot className="w-6 h-6" />
        </motion.div>

        <div className="flex-1 flex flex-col gap-2">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => onPanelChange(item.id as ActivePanel)}
              className={`p-3 rounded-2xl transition-all ${
                activePanel === item.id
                  ? 'bg-purple-600 text-white shadow-lg'
                  : 'text-zinc-500 hover:bg-zinc-200 dark:hover:bg-zinc-800'
              }`}
              title={item.label}
            >
              <item.icon className="w-5 h-5" />
            </button>
          ))}
        </div>

        <div className="flex flex-col gap-2">
          <button
            onClick={() => onPanelChange('settings')}
            className={`p-3 rounded-2xl transition-all ${
              activePanel === 'settings'
                ? 'bg-purple-600 text-white shadow-lg'
                : 'text-zinc-500 hover:bg-zinc-200 dark:hover:bg-zinc-800'
            }`}
            title="Settings"
          >
            <Settings className="w-5 h-5" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-zinc-50 dark:bg-[#1A1A1A] border-r border-zinc-200 dark:border-zinc-800/50">
      <div className="px-6 py-8">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl flex items-center justify-center bg-purple-600 text-white shadow-lg shadow-purple-500/20">
            <Bot className="w-6 h-6" />
          </div>
          <h1 className="text-xl font-bold tracking-tight text-zinc-900 dark:text-white font-serif">Ultron</h1>
        </div>
      </div>

      <nav className="flex-1 px-4 space-y-2">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => onPanelChange(item.id as ActivePanel)}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-2xl transition-all font-semibold ${
              activePanel === item.id
                ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/20'
                : 'text-zinc-500 hover:bg-zinc-200 dark:hover:bg-zinc-800'
            }`}
          >
            <item.icon className="w-5 h-5" />
            <span>{item.label}</span>
          </button>
        ))}
      </nav>

      <div className="p-4 mt-auto">
        <button
          onClick={() => onPanelChange('settings')}
          className={`w-full flex items-center gap-3 px-4 py-3 rounded-2xl transition-all font-semibold ${
            activePanel === 'settings'
              ? 'bg-purple-600 text-white shadow-lg'
              : 'text-zinc-500 hover:bg-zinc-200 dark:hover:bg-zinc-800'
          }`}
        >
          <Settings className="w-5 h-5" />
          <span>Settings</span>
        </button>
      </div>
    </div>
  );
}
