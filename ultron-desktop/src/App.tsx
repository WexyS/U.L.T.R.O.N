import { useState, useEffect, useCallback } from 'react';
import { useUltron } from './hooks/useUltron';
import { API_URL } from './config';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import InputBox from './components/InputBox';
import StatusBadge from './components/StatusBadge';
import InspectorPanel from './components/InspectorPanel';
import WorkspacePanel from './components/WorkspacePanel';
import AgentsPanel from './components/AgentsPanel';
import TrainingPanel from './components/TrainingPanel';
import ComposerPanel from './components/ComposerPanel';
import ConversationSidebar, { Conversation } from './components/ConversationSidebar';
import SettingsPanel from './components/SettingsPanel';
import { AlertTriangle, WifiOff, PanelRightClose, PanelRightOpen, Sun, Moon, MessageSquare, Code2, Settings } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

type ActivePanel = 'chat' | 'workspace' | 'agents' | 'training' | 'composer' | 'settings';
type Theme = 'light' | 'dark';

function App() {
  const {
    messages,
    isStreaming,
    currentResponse,
    isConnected,
    error,
    status,
    providers,
    workspace,
    sendMessage,
    clearMessages,
    setMessages,
  } = useUltron();

  const [activePanel, setActivePanel] = useState<ActivePanel>('chat');
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const [conversationSidebarOpen, setConversationSidebarOpen] = useState(false);
  const [theme, setTheme] = useState<Theme>(() => {
    return (localStorage.getItem('ultron-theme') as Theme) || 'light';
  });

  // Conversation Management
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);

  // Apply theme
  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    localStorage.setItem('ultron-theme', theme);
    document.body.classList.toggle('dark', theme === 'dark');
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  // Create new conversation
  const handleNewConversation = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/conversations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: 'New Chat' })
      });
      if (res.ok) {
        const newConv = await res.json();
        setConversations(prev => [newConv, ...prev]);
        setActiveConversationId(newConv.id);
        clearMessages();
        return newConv;
      }
    } catch (err) {
      console.error('Failed to create conversation:', err);
    }
  }, [clearMessages]);

  // Initial load of conversations from backend
  useEffect(() => {
    const fetchConversations = async () => {
      try {
        const res = await fetch(`${API_URL}/api/conversations`);
        if (res.ok) {
          const data = await res.json();
          if (data.conversations && data.conversations.length > 0) {
            setConversations(data.conversations);
          } else {
            handleNewConversation();
          }
        }
      } catch (err) {
        console.error('Failed to fetch conversations:', err);
      }
    };
    fetchConversations();
  }, [handleNewConversation]);

  // Select conversation
  const handleSelectConversation = useCallback(async (id: string) => {
    setActiveConversationId(id);
    setConversationSidebarOpen(false);
    
    // Load conversation messages from backend
    try {
      const res = await fetch(`${API_URL}/api/conversations/${id}/messages`);
      if (res.ok) {
        const data = await res.json();
        if (data.messages) {
          setMessages(data.messages.map((m: any) => ({
            role: m.role,
            content: m.content,
            timestamp: m.timestamp || Date.now()
          })));
        } else {
          clearMessages();
        }
      }
    } catch (err) {
      console.error('Failed to fetch messages:', err);
      clearMessages();
    }
  }, [clearMessages, setMessages]);

  // Delete conversation
  const handleDeleteConversation = useCallback(async (id: string) => {
    try {
      const res = await fetch(`${API_URL}/api/conversations/${id}`, { method: 'DELETE' });
      if (res.ok) {
        setConversations(prev => prev.filter(c => c.id !== id));
        if (activeConversationId === id) {
          setActiveConversationId(null);
          clearMessages();
        }
      }
    } catch (err) {
      console.error('Failed to delete conversation:', err);
    }
  }, [activeConversationId, clearMessages]);

  // Rename conversation
  const handleRenameConversation = useCallback(async (id: string, newTitle: string) => {
    try {
      const res = await fetch(`${API_URL}/api/conversations/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: newTitle })
      });
      if (res.ok) {
        setConversations(prev =>
          prev.map(c => c.id === id ? { ...c, title: newTitle } : c)
        );
      }
    } catch (err) {
      console.error('Failed to rename conversation:', err);
    }
  }, []);

  // Clear all conversations
  const handleClearAllConversations = useCallback(async () => {
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
  }, [clearMessages, handleNewConversation]);

  // Update conversation metadata when messages change (optional, backend usually handles it)
  useEffect(() => {
    if (activeConversationId && messages.length > 0) {
      setConversations(prev =>
        prev.map(c => {
          if (c.id === activeConversationId) {
            return {
              ...c,
              messageCount: messages.length,
              updatedAt: Date.now()
            };
          }
          return c;
        })
      );
    }
  }, [messages, activeConversationId]);

  return (
    <div className="flex h-screen overflow-hidden font-sans bg-zinc-50 dark:bg-zinc-950 text-zinc-900 dark:text-zinc-50">
      {/* Conversation Sidebar - Modern Sliding Overlay */}
      <AnimatePresence>
        {conversationSidebarOpen && (
          <>
            <motion.div 
              initial={{ opacity: 0 }} 
              animate={{ opacity: 1 }} 
              exit={{ opacity: 0 }}
              onClick={() => setConversationSidebarOpen(false)}
              className="fixed inset-0 bg-black/20 dark:bg-black/40 backdrop-blur-sm z-40"
            />
            <motion.div 
              initial={{ x: -320 }} 
              animate={{ x: 0 }} 
              exit={{ x: -320 }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="fixed inset-y-0 left-0 w-80 z-50 glass-panel shadow-2xl border-r border-zinc-200 dark:border-zinc-800"
            >
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
            </motion.div>
          </>
        )}
      </AnimatePresence>

      <div className="relative z-30 flex-shrink-0 border-r border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">
        <Sidebar
          status={status}
          onClear={clearMessages}
          activePanel={activePanel}
          onPanelChange={setActivePanel}
          onToggleConversationSidebar={() => setConversationSidebarOpen(prev => !prev)}
        />
      </div>

      <main className="flex-1 flex flex-col min-w-0 bg-zinc-50 dark:bg-zinc-950/50" role="main">
        <header className="flex items-center justify-between px-8 py-3 bg-white/80 dark:bg-zinc-900/80 backdrop-blur-md border-b border-zinc-200 dark:border-zinc-800 sticky top-0 z-20">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-1.5 p-1 rounded-xl bg-zinc-100 dark:bg-zinc-800/80 border border-zinc-200 dark:border-zinc-700">
              <button onClick={() => setActivePanel('chat')} className={`px-4 py-1.5 text-sm font-medium rounded-lg transition-all ${activePanel === 'chat' ? 'bg-white dark:bg-zinc-700 shadow-sm text-zinc-900 dark:text-white' : 'text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300'}`}>Chat</button>
              <button onClick={() => setActivePanel('workspace')} className={`px-4 py-1.5 text-sm font-medium rounded-lg transition-all ${activePanel === 'workspace' ? 'bg-white dark:bg-zinc-700 shadow-sm text-zinc-900 dark:text-white' : 'text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300'}`}>Workspace</button>
              <button onClick={() => setActivePanel('agents')} className={`px-4 py-1.5 text-sm font-medium rounded-lg transition-all ${activePanel === 'agents' ? 'bg-white dark:bg-zinc-700 shadow-sm text-zinc-900 dark:text-white' : 'text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300'}`}>Agents</button>
              <button onClick={() => setActivePanel('composer')} className={`px-4 py-1.5 text-sm font-medium rounded-lg transition-all ${activePanel === 'composer' ? 'bg-indigo-500 text-white shadow-md' : 'text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300'}`}>Composer</button>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <StatusBadge status={status} providers={providers} isConnected={isConnected} />
            <div className="h-4 w-px bg-zinc-200 dark:bg-zinc-800 mx-1" />
            <button onClick={toggleTheme} className="p-2 rounded-xl hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors text-zinc-500 dark:text-zinc-400">
              {theme === 'light' ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5" />}
            </button>
            <button onClick={() => setInspectorOpen(!inspectorOpen)} className="p-2 rounded-xl hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors text-zinc-500 dark:text-zinc-400">
              {inspectorOpen ? <PanelRightClose className="w-5 h-5" /> : <PanelRightOpen className="w-5 h-5" />}
            </button>
            <button onClick={() => setActivePanel(activePanel === 'settings' ? 'chat' : 'settings')} className={`p-2 rounded-xl transition-colors ${activePanel === 'settings' ? 'bg-indigo-500 text-white shadow-md shadow-indigo-500/20' : 'hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-500'}`}>
              <Settings className="w-5 h-5" />
            </button>
          </div>
        </header>

        <AnimatePresence>
          {error && (
            <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="flex items-center gap-3 px-8 py-3 bg-red-500/10 border-b border-red-500/20">
              <WifiOff className="w-4 h-4 text-red-500" />
              <span className="text-sm font-medium text-red-600 dark:text-red-400">{error}</span>
            </motion.div>
          )}
        </AnimatePresence>

        <div className="flex-1 flex min-h-0 relative">
          <div className="flex-1 flex flex-col min-w-0">
            {activePanel === 'chat' && (
              <>
                <ChatArea
                  messages={messages}
                  currentResponse={currentResponse}
                  isStreaming={isStreaming}
                  isProcessing={isStreaming && !currentResponse}
                  model={providers?.current?.name || 'Ollama'}
                  latency={providers?.current?.latency_ms || 0}
                />
                <div className="px-6 pb-6 max-w-4xl mx-auto w-full">
                  <InputBox
                    onSend={(text, mode) => sendMessage(text, mode, activeConversationId || undefined)}
                    disabled={isStreaming}
                    isConnected={isConnected}
                  />
                </div>
              </>
            )}
            <div className="h-full overflow-hidden">
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
                animate={{ width: 340, opacity: 1 }} 
                exit={{ width: 0, opacity: 0 }} 
                transition={{ type: 'spring', damping: 25, stiffness: 200 }} 
                className="border-l border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/50 backdrop-blur-xl"
              >
                <InspectorPanel status={status} providers={providers} workspace={workspace} />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>
    </div>
  );
}

export default App;
