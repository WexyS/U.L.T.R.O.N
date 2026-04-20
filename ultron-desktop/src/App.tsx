import { useState, useEffect, useCallback } from 'react';
import { useUltron, ChatMessage, Conversation } from './hooks/useUltron';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import InputBox from './components/InputBox';
import SettingsPanel from './components/SettingsPanel';
import WorkspacePanel from './components/WorkspacePanel';
import AgentsPanel from './components/AgentsPanel';
import ComposerPanel from './components/ComposerPanel';
import TrainingPanel from './components/TrainingPanel';
import StatusBadge from './components/StatusBadge';
import ConversationSidebar from './components/ConversationSidebar';
import InspectorPanel from './components/InspectorPanel';
import { 
  Settings, PanelRightOpen, PanelRightClose, 
  WifiOff, Sun, Moon, PanelLeftClose, PanelLeftOpen, Type
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { API_URL } from './config';

type ActivePanel = 'chat' | 'workspace' | 'agents' | 'training' | 'composer' | 'settings';
type Theme = 'light' | 'dark';
type FontSize = 'sm' | 'md' | 'lg' | 'xl';

function App() {
  const {
    messages,
    sendMessage,
    isStreaming,
    currentResponse,
    status,
    isConnected,
    error,
    providers,
    clearMessages,
    conversations,
    activeConversationId,
    setActiveConversationId,
    setConversations,
    loadConversationMessages
  } = useUltron();

  const [activePanel, setActivePanel] = useState<ActivePanel>('chat');
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [conversationSidebarOpen, setConversationSidebarOpen] = useState(true);
  const [theme, setTheme] = useState<Theme>(() => {
    let t = localStorage.getItem('ultron-theme') as string;
    if (t === 'space' || !t) t = 'dark'; 
    return (t as Theme);
  });
  const [fontSize, setFontSize] = useState<FontSize>(() => {
    return (localStorage.getItem('ultron-font-size') as FontSize) || 'md';
  });
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  // Apply theme & font size
  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(theme);
    localStorage.setItem('ultron-theme', theme);

    root.classList.remove('font-size-sm', 'font-size-md', 'font-size-lg', 'font-size-xl');
    root.classList.add(`font-size-${fontSize}`);
    localStorage.setItem('ultron-font-size', fontSize);
  }, [theme, fontSize]);

  const toggleTheme = () => {
    setTheme((prev: Theme) => prev === 'light' ? 'dark' : 'light');
  };

  const toggleFontSize = () => {
    setFontSize((prev: FontSize) => {
      if (prev === 'sm') return 'md';
      if (prev === 'md') return 'lg';
      if (prev === 'lg') return 'xl';
      return 'sm';
    });
  };

  const handleNewConversation = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/conversations`, { method: 'POST' });
      const data = await res.json();
      if (data && data.id) {
        setConversations((prev: Conversation[]) => [data, ...prev]);
        setActiveConversationId(data.id);
        clearMessages();
      }
    } catch (err) {
      console.error('Failed to create conversation:', err);
    }
  }, [clearMessages, setActiveConversationId, setConversations]);

  const handleSelectConversation = useCallback(async (id: string) => {
    setActiveConversationId(id);
    await loadConversationMessages(id);
    if (window.innerWidth < 1024) {
      setConversationSidebarOpen(false);
    }
  }, [loadConversationMessages, setActiveConversationId]);

  const handleDeleteConversation = useCallback(async (id: string) => {
    try {
      const res = await fetch(`${API_URL}/api/conversations/${id}`, { method: 'DELETE' });
      if (res.ok) {
        setConversations((prev: Conversation[]) => prev.filter((c: Conversation) => c.id !== id));
        if (activeConversationId === id) {
          setActiveConversationId(null);
          clearMessages();
        }
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    }
  }, [activeConversationId, clearMessages, setActiveConversationId, setConversations]);

  const handleRenameConversation = useCallback(async (id: string, newTitle: string) => {
    try {
      const res = await fetch(`${API_URL}/api/conversations/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: newTitle })
      });
      if (res.ok) {
        setConversations((prev: Conversation[]) =>
          prev.map((c: Conversation) => c.id === id ? { ...c, title: newTitle } : c)
        );
      }
    } catch (err) {
      console.error('Failed to rename conversation:', err);
    }
  }, [setConversations]);

  const handleClearAllConversations = useCallback(async () => {
    if (!confirm('Are you sure you want to clear all history?')) return;
    try {
      const res = await fetch(`${API_URL}/api/conversations/all`, { method: 'DELETE' });
      if (res.ok) {
        setConversations([]);
        setActiveConversationId(null);
        clearMessages();
        handleNewConversation();
      }
    } catch (err) {
      console.error('Failed to clear all conversations:', err);
    }
  }, [clearMessages, handleNewConversation, setActiveConversationId, setConversations]);

  return (
    <div className="flex h-screen overflow-hidden font-sans bg-zinc-50 dark:bg-[#121212] text-zinc-900 dark:text-zinc-50 selection:bg-purple-500/30">
      
      {/* Navigation Rail */}
      <div className="hidden lg:flex flex-col w-16 bg-zinc-100 dark:bg-[#1A1A1A] border-r border-zinc-200 dark:border-zinc-800/50">
        <Sidebar
          status={status}
          onClear={handleClearAllConversations}
          activePanel={activePanel}
          onPanelChange={setActivePanel}
          onToggleConversationSidebar={() => setConversationSidebarOpen(prev => !prev)}
          isCollapsed={true}
        />
      </div>

      {/* Conversation Sidebar */}
      <AnimatePresence initial={false}>
        {conversationSidebarOpen && (
          <motion.div 
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 300, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="hidden lg:block h-full border-r border-zinc-200 dark:border-zinc-800/50 bg-zinc-50/50 dark:bg-[#1E1E1E]/50 overflow-hidden"
          >
            <div className="w-[300px] h-full">
              <ConversationSidebar
                conversations={conversations}
                activeConversationId={activeConversationId}
                onSelectConversation={handleSelectConversation}
                onNewConversation={handleNewConversation}
                onDeleteConversation={handleDeleteConversation}
                onRenameConversation={handleRenameConversation}
                onClearAllConversations={handleClearAllConversations}
                isOpen={true}
                onClose={() => setConversationSidebarOpen(false)}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <main className="flex-1 flex flex-col min-w-0 bg-transparent" role="main">
        {/* Header */}
        <header className="flex-shrink-0 flex flex-wrap gap-2 items-center justify-between px-3 lg:px-6 py-3 lg:py-4 bg-zinc-50/80 dark:bg-[#121212]/80 backdrop-blur-md border-b border-zinc-200 dark:border-zinc-800/50">
          <div className="flex items-center gap-2 lg:gap-4 overflow-x-auto no-scrollbar flex-1 lg:flex-none">
            <button 
              onClick={() => setConversationSidebarOpen(!conversationSidebarOpen)}
              className="p-2 hover:bg-zinc-200 dark:hover:bg-zinc-800 rounded-xl transition-colors text-zinc-500"
            >
              {conversationSidebarOpen ? <PanelLeftClose className="w-5 h-5" /> : <PanelLeftOpen className="w-5 h-5" />}
            </button>
            
            <div className="flex items-center gap-1 p-1 rounded-2xl bg-zinc-200/50 dark:bg-zinc-800/50 shrink-0">
              <button onClick={() => setActivePanel('chat')} className={`px-3 lg:px-5 py-1.5 lg:py-2 text-xs lg:text-sm font-semibold rounded-xl transition-all ${activePanel === 'chat' ? 'bg-white dark:bg-zinc-700 shadow-sm text-zinc-900 dark:text-zinc-100' : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100'}`}>CHAT</button>
              <button onClick={() => setActivePanel('workspace')} className={`px-3 lg:px-5 py-1.5 lg:py-2 text-xs lg:text-sm font-semibold rounded-xl transition-all ${activePanel === 'workspace' ? 'bg-white dark:bg-zinc-700 shadow-sm text-zinc-900 dark:text-zinc-100' : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100'}`}>WORK</button>
              <button onClick={() => setActivePanel('agents')} className={`px-3 lg:px-5 py-1.5 lg:py-2 text-xs lg:text-sm font-semibold rounded-xl transition-all ${activePanel === 'agents' ? 'bg-white dark:bg-zinc-700 shadow-sm text-zinc-900 dark:text-zinc-100' : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100'}`}>AGENTS</button>
              <button onClick={() => setActivePanel('composer')} className={`px-3 lg:px-5 py-1.5 lg:py-2 text-xs lg:text-sm font-semibold rounded-xl transition-all ${activePanel === 'composer' ? 'bg-purple-600 text-white shadow-md' : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100'}`}>COMPOSER</button>
            </div>
          </div>

          <div className="flex items-center gap-1 lg:gap-3 shrink-0">
            <div className="hidden sm:block">
              <StatusBadge status={status} providers={providers} isConnected={isConnected} />
            </div>
            <div className="hidden sm:block h-6 w-px bg-zinc-200 dark:bg-zinc-800 mx-1 lg:mx-2" />
            
            <button 
              onClick={toggleFontSize} 
              className="p-1.5 lg:p-2.5 rounded-xl hover:bg-zinc-200 dark:hover:bg-zinc-800 transition-all text-zinc-500 relative group"
              title={`Yazı Boyutu: ${fontSize.toUpperCase()}`}
            >
              <Type className="w-5 h-5" />
              <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-purple-500 text-[10px] font-bold text-white uppercase">
                {fontSize}
              </span>
            </button>

            <button onClick={toggleTheme} className="p-1.5 lg:p-2.5 rounded-xl hover:bg-zinc-200 dark:hover:bg-zinc-800 transition-all text-zinc-500">
              {theme === 'light' ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5" />}
            </button>
            <button onClick={() => setInspectorOpen(!inspectorOpen)} className="hidden sm:block p-1.5 lg:p-2.5 rounded-xl hover:bg-zinc-200 dark:hover:bg-zinc-800 transition-all text-zinc-500">
              {inspectorOpen ? <PanelRightClose className="w-5 h-5" /> : <PanelRightOpen className="w-5 h-5" />}
            </button>
            <button onClick={() => setActivePanel(activePanel === 'settings' ? 'chat' : 'settings')} className={`p-1.5 lg:p-2.5 rounded-xl transition-all ${activePanel === 'settings' ? 'bg-purple-600 text-white' : 'hover:bg-zinc-200 dark:hover:bg-zinc-800 text-zinc-500'}`}>
              <Settings className="w-5 h-5" />
            </button>
          </div>
        </header>

        <AnimatePresence>
          {error && (
            <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="flex items-center gap-3 px-8 py-3 bg-red-500/10 border-b border-red-500/20">
              <WifiOff className="w-4 h-4 text-red-500" />
              <span className="text-sm font-semibold text-red-600 dark:text-red-400">{error}</span>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="flex-1 flex min-h-0 relative">
          <div className="flex-1 flex flex-col min-w-0">
            {activePanel === 'chat' && (
              <div className="flex-1 flex flex-col min-h-0 overflow-hidden relative">
                {/* Messages — scrollable, fills remaining space */}
                <ChatArea
                  messages={messages}
                  currentResponse={currentResponse}
                  isStreaming={isStreaming}
                  isProcessing={isStreaming && !currentResponse}
                />
                
                {/* Input Area — Integrated look with subtle separator */}
                <div className="flex-shrink-0 bg-zinc-50/50 dark:bg-[#121212]/50 backdrop-blur-sm border-t border-zinc-200 dark:border-zinc-800/50">
                  <div className="max-w-4xl mx-auto px-4 py-4 lg:px-8">
                    <InputBox
                      onSend={sendMessage}
                      disabled={isStreaming}
                      isConnected={isConnected}
                    />
                  </div>
                </div>
              </div>
            )}

            {activePanel !== 'chat' && (
              <div className="flex-1 overflow-y-auto">
                {activePanel === 'workspace' && <WorkspacePanel />}
                {activePanel === 'agents' && <AgentsPanel />}
                {activePanel === 'training' && <TrainingPanel />}
                {activePanel === 'composer' && <ComposerPanel />}
                {activePanel === 'settings' && <SettingsPanel />}
              </div>
            )}
          </div>

          <AnimatePresence>
            {inspectorOpen && (
              <motion.div 
                initial={{ width: 0, opacity: 0 }}
                animate={{ width: 350, opacity: 1 }}
                exit={{ width: 0, opacity: 0 }}
                className="h-full border-l border-zinc-200 dark:border-zinc-800/50 bg-zinc-50/50 dark:bg-[#1A1A1A]/50 overflow-hidden"
              >
                <div className="w-[350px] h-full">
                  <InspectorPanel status={status} providers={providers} workspace={undefined} />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}

export default App;
