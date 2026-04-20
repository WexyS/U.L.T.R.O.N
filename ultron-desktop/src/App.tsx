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
import { 
  Settings, PanelRightOpen, PanelRightClose, 
  WifiOff, Sun, Moon, PanelLeftClose, PanelLeftOpen 
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { API_URL } from './config';

type ActivePanel = 'chat' | 'workspace' | 'agents' | 'training' | 'composer' | 'settings';
type Theme = 'light' | 'dark';

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
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  // Apply theme
  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(theme);
    localStorage.setItem('ultron-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev: Theme) => prev === 'light' ? 'dark' : 'light');
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
        <header className="flex items-center justify-between px-6 py-4 sticky top-0 z-20 bg-zinc-50/80 dark:bg-[#121212]/80 backdrop-blur-md border-b border-zinc-200 dark:border-zinc-800/50">
          <div className="flex items-center gap-4">
            <button 
              onClick={() => setConversationSidebarOpen(!conversationSidebarOpen)}
              className="p-2 hover:bg-zinc-200 dark:hover:bg-zinc-800 rounded-xl transition-colors text-zinc-500"
            >
              {conversationSidebarOpen ? <PanelLeftClose className="w-5 h-5" /> : <PanelLeftOpen className="w-5 h-5" />}
            </button>
            
            <div className="flex items-center gap-1 p-1 rounded-2xl bg-zinc-200/50 dark:bg-zinc-800/50">
              <button onClick={() => setActivePanel('chat')} className={`px-5 py-2 text-xs lg:text-sm font-semibold rounded-xl transition-all ${activePanel === 'chat' ? 'bg-white dark:bg-zinc-700 shadow-sm text-zinc-900 dark:text-zinc-100' : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100'}`}>CHAT</button>
              <button onClick={() => setActivePanel('workspace')} className={`px-5 py-2 text-xs lg:text-sm font-semibold rounded-xl transition-all ${activePanel === 'workspace' ? 'bg-white dark:bg-zinc-700 shadow-sm text-zinc-900 dark:text-zinc-100' : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100'}`}>WORK</button>
              <button onClick={() => setActivePanel('agents')} className={`px-5 py-2 text-xs lg:text-sm font-semibold rounded-xl transition-all ${activePanel === 'agents' ? 'bg-white dark:bg-zinc-700 shadow-sm text-zinc-900 dark:text-zinc-100' : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100'}`}>AGENTS</button>
              <button onClick={() => setActivePanel('composer')} className={`px-5 py-2 text-xs lg:text-sm font-semibold rounded-xl transition-all ${activePanel === 'composer' ? 'bg-purple-600 text-white shadow-md' : 'text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100'}`}>COMPOSER</button>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <StatusBadge status={status} providers={providers} isConnected={isConnected} />
            <div className="h-6 w-px bg-zinc-200 dark:bg-zinc-800 mx-2" />
            <button onClick={toggleTheme} className="p-2.5 rounded-xl hover:bg-zinc-200 dark:hover:bg-zinc-800 transition-all text-zinc-500">
              {theme === 'light' ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5" />}
            </button>
            <button onClick={() => setInspectorOpen(!inspectorOpen)} className="p-2.5 rounded-xl hover:bg-zinc-200 dark:hover:bg-zinc-800 transition-all text-zinc-500">
              {inspectorOpen ? <PanelRightClose className="w-5 h-5" /> : <PanelRightOpen className="w-5 h-5" />}
            </button>
            <button onClick={() => setActivePanel(activePanel === 'settings' ? 'chat' : 'settings')} className={`p-2.5 rounded-xl transition-all ${activePanel === 'settings' ? 'bg-purple-600 text-white' : 'hover:bg-zinc-200 dark:hover:bg-zinc-800 text-zinc-500'}`}>
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

        <div className="flex-1 flex min-h-0 relative h-full">
          <div className="flex-1 flex flex-col min-w-0 h-full">
            {activePanel === 'chat' && (
              <div className="flex-1 flex flex-col min-h-0">
                <ChatArea
                  messages={messages}
                  currentResponse={currentResponse}
                  isStreaming={isStreaming}
                  isProcessing={isStreaming && !currentResponse}
                />
                <div className="px-6 pb-12 max-w-5xl mx-auto w-full">
                  <InputBox
                    onSend={sendMessage}
                    disabled={isStreaming}
                    isConnected={isConnected}
                  />
                </div>
              </div>
            )}

            <div className="flex-1 overflow-hidden">
              {activePanel === 'workspace' && <WorkspacePanel />}
              {activePanel === 'agents' && <AgentsPanel />}
              {activePanel === 'training' && <TrainingPanel />}
              {activePanel === 'composer' && <ComposerPanel />}
              {activePanel === 'settings' && <SettingsPanel />}
            </div>
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
                  <InspectorPanel status={status} />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}

const InspectorPanel = ({ status }: { status: any }) => (
  <div className="h-full flex flex-col p-6 scrollbar-premium overflow-y-auto">
    <div className="flex items-center gap-3 mb-8">
      <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
      <h3 className="font-bold text-zinc-900 dark:text-zinc-100">Inspector</h3>
      <span className="text-[10px] bg-zinc-200 dark:bg-zinc-800 px-2 py-0.5 rounded-full text-zinc-500 uppercase tracking-widest font-bold">Live</span>
    </div>
    
    <div className="space-y-8">
       <div className="space-y-4">
         <h4 className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">Working Memory</h4>
         <div className="p-4 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-100 dark:border-zinc-800 shadow-sm">
           <div className="flex justify-between items-center mb-2">
             <span className="text-sm text-zinc-500">Messages</span>
             <span className="text-sm font-bold">{(status?.memory?.messages || 0)} / 20</span>
           </div>
           <div className="w-full h-1.5 bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
             <div className="h-full bg-purple-500 rounded-full" style={{ width: `${((status?.memory?.messages || 0) / 20) * 100}%` }} />
           </div>
         </div>
       </div>

       <div className="space-y-4">
         <h4 className="text-[10px] font-bold text-zinc-400 uppercase tracking-widest">Long-Term Memory</h4>
         <div className="p-4 rounded-2xl bg-white dark:bg-zinc-900 border border-zinc-100 dark:border-zinc-800 shadow-sm space-y-3">
           <div className="flex justify-between text-sm">
             <span className="text-zinc-500">Vector entries</span>
             <span className="font-bold">{status?.memory?.vector_count || 688}</span>
           </div>
           <div className="flex justify-between text-sm">
             <span className="text-zinc-500">Graph nodes</span>
             <span className="font-bold">{status?.memory?.graph_nodes || 6}</span>
           </div>
         </div>
       </div>
    </div>
  </div>
);

export default App;
