import { useState, useEffect } from 'react';
import { useJarvis } from './hooks/useJarvis';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import InputBox from './components/InputBox';
import StatusBadge from './components/StatusBadge';
import InspectorPanel from './components/InspectorPanel';
import WorkspacePanel from './components/WorkspacePanel';
import AgentsPanel from './components/AgentsPanel';
import { AlertTriangle, WifiOff, PanelRightClose, PanelRightOpen, Sparkles, Sun, Moon } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

type ActivePanel = 'chat' | 'workspace' | 'agents';
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
  } = useJarvis();

  const [activePanel, setActivePanel] = useState<ActivePanel>('chat');
  const [inspectorOpen, setInspectorOpen] = useState(true);
  const [theme, setTheme] = useState<Theme>(() => {
    // Load theme from localStorage or default to light
    return (localStorage.getItem('jarvis-theme') as Theme) || 'light';
  });

  // Apply theme to document
  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    localStorage.setItem('jarvis-theme', theme);
    
    // Also set body class for safety
    document.body.classList.toggle('dark', theme === 'dark');
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  return (
    <div className="flex h-screen bg-[var(--color-bg)] text-[var(--color-text)] font-sans overflow-hidden">
      {/* ── SIDEBAR (260px) - Clean, minimal ────────────────────────── */}
      <Sidebar
        status={status}
        onClear={clearMessages}
        activePanel={activePanel}
        onPanelChange={setActivePanel}
      />

      {/* ── MAIN CONTENT - Focus on content ─────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header - Minimal, clean like verdent.ai */}
        <header className="flex items-center justify-between px-8 py-4 border-b border-gray-200 bg-white">
          <div className="flex items-center gap-4">
            {/* Panel Toggle */}
            <div className="flex items-center gap-2 p-1 bg-gray-100 rounded-lg">
              <button
                onClick={() => setActivePanel('chat')}
                className={`px-4 py-2 text-sm font-medium rounded-md transition-all ${
                  activePanel === 'chat'
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                💬 Chat
              </button>
              <button
                onClick={() => setActivePanel('workspace')}
                className={`px-4 py-2 text-sm font-medium rounded-md transition-all ${
                  activePanel === 'workspace'
                    ? 'bg-white text-gray-900 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                🌐 Workspace
              </button>
            </div>

            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-gray-400" />
              <h2 className="text-sm font-medium text-gray-600">
                {isStreaming ? 'Processing...' : activePanel === 'chat' ? 'Ready to assist' : 'Workspace'}
              </h2>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <StatusBadge status={status} isConnected={isConnected} />
            <button
              onClick={() => setInspectorOpen(!inspectorOpen)}
              className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
              title={inspectorOpen ? 'Close Inspector' : 'Open Inspector'}
            >
              {inspectorOpen ? <PanelRightClose className="w-5 h-5" /> : <PanelRightOpen className="w-5 h-5" />}
            </button>
          </div>
        </header>

        {/* Error banner - Subtle, non-intrusive */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mx-8 mt-4 p-4 rounded-lg bg-red-50 border border-red-200 flex items-center gap-3"
            >
              <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0" />
              <p className="text-sm text-red-700 flex-1">{error}</p>
              {!isConnected && <WifiOff className="w-4 h-4 text-red-600" />}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Panel content */}
        {activePanel === 'chat' ? (
          <>
            <ChatArea
              messages={messages}
              currentResponse={currentResponse}
              isStreaming={isStreaming}
            />
            <InputBox
              onSend={sendMessage}
              disabled={isStreaming}
              isConnected={isConnected}
            />
          </>
        ) : activePanel === 'workspace' ? (
          <WorkspacePanel />
        ) : (
          <AgentsPanel />
        )}
      </div>

      {/* ── INSPECTOR PANEL (320px) - Clean, organized ─────────────── */}
      <AnimatePresence>
        {inspectorOpen && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 320, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="border-l border-[var(--color-border)] bg-[var(--color-panel)] overflow-hidden"
          >
            <InspectorPanel status={status} providers={providers} workspace={workspace} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── THEME TOGGLE BUTTON ─────────────────────────────────────── */}
      <motion.button
        onClick={toggleTheme}
        className="fixed bottom-4 right-4 z-50 p-3 rounded-full bg-[var(--color-panel)] border border-[var(--color-border)] shadow-lg hover:scale-110 transition-transform"
        whileHover={{ scale: 1.1 }}
        whileTap={{ scale: 0.95 }}
        title={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}
      >
        <AnimatePresence mode="wait">
          {theme === 'light' ? (
            <motion.div
              key="moon"
              initial={{ rotate: -90, opacity: 0 }}
              animate={{ rotate: 0, opacity: 1 }}
              exit={{ rotate: 90, opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              <Moon className="w-5 h-5 text-[var(--color-text)]" />
            </motion.div>
          ) : (
            <motion.div
              key="sun"
              initial={{ rotate: 90, opacity: 0 }}
              animate={{ rotate: 0, opacity: 1 }}
              exit={{ rotate: -90, opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              <Sun className="w-5 h-5 text-[var(--color-text)]" />
            </motion.div>
          )}
        </AnimatePresence>
      </motion.button>
    </div>
  );
}

export default App;
