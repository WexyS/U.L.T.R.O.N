import { useState } from 'react';
import { useJarvis } from './hooks/useJarvis';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import InputBox from './components/InputBox';
import StatusBadge from './components/StatusBadge';
import InspectorPanel from './components/InspectorPanel';
import WorkspacePanel from './components/WorkspacePanel';
import { AlertTriangle, WifiOff, PanelRightClose, PanelRightOpen } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

type ActivePanel = 'chat' | 'workspace';

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

  return (
    <div className="flex h-screen bg-jarvis-bg text-jarvis-text font-sans overflow-hidden">
      {/* ── SIDEBAR (240px) ─────────────────────────────────────── */}
      <Sidebar
        status={status}
        onClear={clearMessages}
        activePanel={activePanel}
        onPanelChange={setActivePanel}
      />

      {/* ── MAIN CONTENT (flexible) ─────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="flex items-center justify-between px-6 py-3 border-b border-jarvis-border bg-jarvis-panel/80 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setActivePanel(activePanel === 'chat' ? 'workspace' : 'chat')}
              className="px-3 py-1.5 text-xs rounded-md bg-jarvis-card hover:bg-jarvis-border transition-colors"
            >
              {activePanel === 'chat' ? '🌐 Workspace' : '💬 Chat'}
            </button>
            <h2 className="text-sm font-medium text-jarvis-textMuted">
              {isStreaming ? 'Processing...' : activePanel === 'chat' ? 'Ready' : 'Workspace'}
            </h2>
          </div>
          <div className="flex items-center gap-3">
            <StatusBadge status={status} isConnected={isConnected} />
            <button
              onClick={() => setInspectorOpen(!inspectorOpen)}
              className="p-1.5 rounded-md hover:bg-jarvis-card transition-colors"
              title={inspectorOpen ? 'Close Inspector' : 'Open Inspector'}
            >
              {inspectorOpen ? <PanelRightClose className="w-4 h-4" /> : <PanelRightOpen className="w-4 h-4" />}
            </button>
          </div>
        </header>

        {/* Error banner */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mx-6 mt-3 p-3 rounded-lg bg-jarvis-danger/10 border border-jarvis-danger/30 flex items-center gap-3"
            >
              <AlertTriangle className="w-4 h-4 text-jarvis-danger flex-shrink-0" />
              <p className="text-sm text-jarvis-danger flex-1">{error}</p>
              {!isConnected && <WifiOff className="w-4 h-4 text-jarvis-danger" />}
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
        ) : (
          <WorkspacePanel />
        )}
      </div>

      {/* ── INSPECTOR PANEL (300px) ─────────────────────────────── */}
      <AnimatePresence>
        {inspectorOpen && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 300, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="border-l border-jarvis-border bg-jarvis-panel/80 backdrop-blur-sm overflow-hidden"
          >
            <InspectorPanel status={status} providers={providers} workspace={workspace} />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default App;
