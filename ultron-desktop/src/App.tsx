import { useState, useEffect, useCallback } from 'react';
import { useUltron } from './hooks/useUltron';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import InputBox from './components/InputBox';
import StatusBadge from './components/StatusBadge';
import InspectorPanel from './components/InspectorPanel';
import WorkspacePanel from './components/WorkspacePanel';
import AgentsPanel from './components/AgentsPanel';
import TrainingPanel from './components/TrainingPanel';
import ConversationSidebar, { Conversation } from './components/ConversationSidebar';
import { AlertTriangle, WifiOff, PanelRightClose, PanelRightOpen, Sparkles, Sun, Moon, MessageSquare } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

type ActivePanel = 'chat' | 'workspace' | 'agents' | 'training';
type Theme = 'light' | 'dark';

// Generate unique ID
const generateId = () => `conv-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

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
  } = useUltron();

  const [activePanel, setActivePanel] = useState<ActivePanel>('chat');
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const [conversationSidebarOpen, setConversationSidebarOpen] = useState(false);
  const [theme, setTheme] = useState<Theme>(() => {
    return (localStorage.getItem('ultron-theme') as Theme) || 'light';
  });

  // Conversation Management
  const [conversations, setConversations] = useState<Conversation[]>(() => {
    const saved = localStorage.getItem('ultron-conversations');
    return saved ? JSON.parse(saved) : [];
  });
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);

  // Save conversations to localStorage
  useEffect(() => {
    localStorage.setItem('ultron-conversations', JSON.stringify(conversations));
  }, [conversations]);

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
  const handleNewConversation = useCallback(() => {
    const newConv: Conversation = {
      id: generateId(),
      title: 'New Chat',
      messageCount: 0,
      createdAt: Date.now(),
      updatedAt: Date.now(),
      model: 'Ollama',
      mode: 'chat'
    };
    setConversations(prev => [newConv, ...prev]);
    setActiveConversationId(newConv.id);
    clearMessages();
  }, [clearMessages]);

  // Select conversation
  const handleSelectConversation = useCallback((id: string) => {
    setActiveConversationId(id);
    setConversationSidebarOpen(false);
    // In a real implementation, load conversation messages from storage
    clearMessages();
  }, [clearMessages]);

  // Delete conversation
  const handleDeleteConversation = useCallback((id: string) => {
    setConversations(prev => prev.filter(c => c.id !== id));
    if (activeConversationId === id) {
      setActiveConversationId(null);
      clearMessages();
    }
  }, [activeConversationId, clearMessages]);

  // Rename conversation
  const handleRenameConversation = useCallback((id: string, newTitle: string) => {
    setConversations(prev =>
      prev.map(c => c.id === id ? { ...c, title: newTitle } : c)
    );
  }, []);

  // Update conversation when messages change
  useEffect(() => {
    if (activeConversationId && messages.length > 0) {
      setConversations(prev =>
        prev.map(c => {
          if (c.id === activeConversationId) {
            // Auto-generate title from first message
            const firstUserMessage = messages.find(m => m.role === 'user');
            const title = firstUserMessage
              ? firstUserMessage.content.substring(0, 50) + (firstUserMessage.content.length > 50 ? '...' : '')
              : c.title;

            return {
              ...c,
              title: c.title === 'New Chat' ? title : c.title,
              messageCount: messages.length,
              updatedAt: Date.now()
            };
          }
          return c;
        })
      );
    }
  }, [messages, activeConversationId]);

  // Create first conversation if none exist
  useEffect(() => {
    if (conversations.length === 0 && messages.length === 0) {
      handleNewConversation();
    }
  }, []);

  return (
    <div className="flex h-screen overflow-hidden font-sans bg-white dark:bg-gray-950 text-gray-900 dark:text-gray-100">
      {/* Conversation Sidebar */}
      <ConversationSidebar
        conversations={conversations}
        activeConversationId={activeConversationId}
        onSelectConversation={handleSelectConversation}
        onNewConversation={handleNewConversation}
        onDeleteConversation={handleDeleteConversation}
        onRenameConversation={handleRenameConversation}
        isOpen={conversationSidebarOpen}
        onClose={() => setConversationSidebarOpen(false)}
      />

      {/* ── SIDEBAR (260px) ────────────────────────── */}
      <Sidebar
        status={status}
        onClear={clearMessages}
        activePanel={activePanel}
        onPanelChange={setActivePanel}
        onToggleConversationSidebar={() => setConversationSidebarOpen(prev => !prev)}
      />

      {/* ── MAIN CONTENT ─────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="flex items-center justify-between px-8 py-4 border-b border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900">
          <div className="flex items-center gap-4">
            {/* Conversation Toggle */}
            <button
              onClick={() => setConversationSidebarOpen(prev => !prev)}
              className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-200/50 dark:hover:bg-gray-800/50 transition-colors"
              title="Toggle conversations"
            >
              <MessageSquare className="w-5 h-5" />
              <span className="text-sm font-medium">{conversations.length}</span>
            </button>

            {/* Panel Toggle */}
            <div className="flex items-center gap-2 p-1 rounded-lg bg-gray-200/50 dark:bg-gray-800/50">
              <button
                onClick={() => setActivePanel('chat')}
                className={`px-4 py-2 text-sm font-medium rounded-md transition-all ${
                  activePanel === 'chat'
                    ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                💬 Chat
              </button>
              <button
                onClick={() => setActivePanel('workspace')}
                className={`px-4 py-2 text-sm font-medium rounded-md transition-all ${
                  activePanel === 'workspace'
                    ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                🗂️ Workspace
              </button>
              <button
                onClick={() => setActivePanel('agents')}
                className={`px-4 py-2 text-sm font-medium rounded-md transition-all ${
                  activePanel === 'agents'
                    ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                🤖 Agents
              </button>
              <button
                onClick={() => setActivePanel('training')}
                className={`px-4 py-2 text-sm font-medium rounded-md transition-all ${
                  activePanel === 'training'
                    ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                    : 'text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                }`}
              >
                🎓 Training
              </button>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <StatusBadge status={status} isConnected={isConnected} />
            <button
              onClick={toggleTheme}
              className="p-2 rounded-lg hover:bg-gray-200/50 dark:hover:bg-gray-800/50 transition-colors"
              title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
            >
              {theme === 'light' ? <Moon className="w-5 h-5" /> : <Sun className="w-5 h-5" />}
            </button>
            <button
              onClick={() => setInspectorOpen(!inspectorOpen)}
              className="p-2 rounded-lg hover:bg-gray-200/50 dark:hover:bg-gray-800/50 transition-colors"
              title="Toggle inspector"
            >
              {inspectorOpen ? <PanelRightClose className="w-5 h-5" /> : <PanelRightOpen className="w-5 h-5" />}
            </button>
          </div>
        </header>

        {/* Connection Error */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="flex items-center gap-2 px-8 py-3 bg-red-50 dark:bg-red-900/20 border-b border-red-200 dark:border-red-800"
            >
              <WifiOff className="w-4 h-4 text-red-600" />
              <AlertTriangle className="w-4 h-4 text-red-600" />
              <span className="text-sm text-red-600 dark:text-red-400">{error}</span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Content Panel */}
        <div className="flex-1 flex min-h-0">
          {/* Main Content */}
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
                <InputBox
                  onSend={sendMessage}
                  disabled={isStreaming}
                  isConnected={isConnected}
                />
              </>
            )}
            {activePanel === 'workspace' && <WorkspacePanel />}
            {activePanel === 'agents' && <AgentsPanel />}
            {activePanel === 'training' && <TrainingPanel />}
          </div>

          {/* Inspector Panel */}
          <AnimatePresence>
            {inspectorOpen && (
              <motion.div
                initial={{ width: 0, opacity: 0 }}
                animate={{ width: 320, opacity: 1 }}
                exit={{ width: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="border-l border-gray-200 dark:border-gray-800 overflow-hidden"
              >
                <InspectorPanel status={status} providers={providers} workspace={workspace} />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

export default App;
