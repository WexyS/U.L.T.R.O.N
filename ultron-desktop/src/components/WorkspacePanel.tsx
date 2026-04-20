import { useState, useEffect } from 'react';
import { Globe, Code, Layers, Loader2, CheckCircle, AlertCircle, FolderOpen, ExternalLink } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { API_URL } from '../config';

interface WorkspaceItem {
  id: string;
  type: 'clone' | 'generated' | 'synthesized';
  name: string;
  url?: string;
  description: string;
  components: string[];
  tech_stack: string;
  path: string;
  created_at: string;
}

export default function WorkspacePanel() {
  const [activeTab, setActiveTab] = useState<'clone' | 'generate' | 'synthesize'>('clone');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [workspace, setWorkspace] = useState<WorkspaceItem[]>([]);

  // Form states
  const [cloneUrl, setCloneUrl] = useState('');
  const [generateIdea, setGenerateIdea] = useState('');
  const [synthesizeCommand, setSynthesizeCommand] = useState('');

  // Load workspace items
  useEffect(() => {
    loadWorkspace();
  }, []);

  const loadWorkspace = async () => {
    try {
      const resp = await fetch(`${API_URL}/api/v2/workspace/list`);
      const data = await resp.json();
      setWorkspace(data.items || []);
    } catch (err) {
      console.error('Failed to load workspace:', err);
    }
  };

  const handleClone = async () => {
    if (!cloneUrl.trim()) return;
    
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const resp = await fetch(`${API_URL}/api/v2/workspace/clone`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: cloneUrl,
          extract_components: true,
        }),
      });

      const data = await resp.json();
      
      if (data.success) {
        setResult(`✅ Successfully cloned: ${data.item.name}`);
        setCloneUrl('');
        loadWorkspace();
      } else {
        setError(`❌ Clone failed: ${data.error}`);
      }
    } catch (err: any) {
      setError(`❌ Network error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    if (!generateIdea.trim()) return;
    
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const resp = await fetch(`${API_URL}/api/v2/workspace/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          idea: generateIdea,
          tech_stack: 'html-css-js',
        }),
      });

      const data = await resp.json();
      
      if (data.success) {
        setResult(`✅ Generated app: ${data.item.name}`);
        setGenerateIdea('');
        loadWorkspace();
      } else {
        setError(`❌ Generation failed: ${data.error}`);
      }
    } catch (err: any) {
      setError(`❌ Network error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSynthesize = async () => {
    if (!synthesizeCommand.trim()) return;
    
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const resp = await fetch(`${API_URL}/api/v2/workspace/synthesize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_command: synthesizeCommand,
          target_project: 'synthesized-app',
        }),
      });

      const data = await resp.json();
      
      if (data.success) {
        setResult(`✅ Synthesized: ${data.item.name}`);
        setSynthesizeCommand('');
        loadWorkspace();
      } else {
        setError(`❌ Synthesis failed: ${data.error}`);
      }
    } catch (err: any) {
      setError(`❌ Network error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const openInExplorer = (path: string) => {
    // Open folder in file explorer
    fetch(`${API_URL}/api/v2/workspace/open-folder`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path }),
    }).catch(console.error);
  };

  return (
    <div className="workspace-panel flex-1 overflow-y-auto p-6" style={{ backgroundColor: 'var(--color-bg)', color: 'var(--color-text)' }}>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2" style={{ color: 'var(--color-text)' }}>Workspace</h1>
        <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>Clone websites, generate apps, or synthesize new projects from templates</p>
      </div>

      {/* Tab Navigation */}
      <div className="flex items-center gap-2 mb-6 p-1 rounded-lg w-fit" style={{ backgroundColor: 'var(--color-bg-tertiary)' }}>
        <button
          onClick={() => setActiveTab('clone')}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-all ${
            activeTab === 'clone'
              ? 'shadow-sm'
              : 'hover:opacity-80'
          }`}
          style={{
            backgroundColor: activeTab === 'clone' ? 'var(--color-bg)' : 'transparent',
            color: activeTab === 'clone' ? 'var(--color-text)' : 'var(--color-text-secondary)',
          }}
        >
          <Globe className="w-4 h-4" />
          Clone Site
        </button>
        <button
          onClick={() => setActiveTab('generate')}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-all ${
            activeTab === 'generate'
              ? 'shadow-sm'
              : 'hover:opacity-80'
          }`}
          style={{
            backgroundColor: activeTab === 'generate' ? 'var(--color-bg)' : 'transparent',
            color: activeTab === 'generate' ? 'var(--color-text)' : 'var(--color-text-secondary)',
          }}
        >
          <Code className="w-4 h-4" />
          Generate App
        </button>
        <button
          onClick={() => setActiveTab('synthesize')}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-all ${
            activeTab === 'synthesize'
              ? 'shadow-sm'
              : 'hover:opacity-80'
          }`}
          style={{
            backgroundColor: activeTab === 'synthesize' ? 'var(--color-bg)' : 'transparent',
            color: activeTab === 'synthesize' ? 'var(--color-text)' : 'var(--color-text-secondary)',
          }}
        >
          <Layers className="w-4 h-4" />
          Synthesize
        </button>
      </div>

      {/* Content */}
      <div className="space-y-6">
        {/* CLONE TAB */}
        {activeTab === 'clone' && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4"
          >
            <div className="p-6 rounded-xl border" style={{ backgroundColor: 'var(--color-bg-secondary)', borderColor: 'var(--color-border)' }}>
              <h3 className="text-lg font-semibold mb-3" style={{ color: 'var(--color-text)' }}>Clone a Website</h3>
              <p className="text-sm mb-4" style={{ color: 'var(--color-text-secondary)' }}>
                Enter a URL to clone the website. Playwright will render it, extract components, and save the structure.
              </p>
              <div className="flex gap-3">
                <input
                  type="url"
                  value={cloneUrl}
                  onChange={(e) => setCloneUrl(e.target.value)}
                  placeholder="https://example.com"
                  className="flex-1 rounded-lg border px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-accent"
                  style={{
                    backgroundColor: 'var(--color-bg)',
                    borderColor: 'var(--color-border)',
                    color: 'var(--color-text)',
                  }}
                  disabled={loading}
                />
                <button
                  onClick={handleClone}
                  disabled={loading || !cloneUrl.trim()}
                  className="px-6 py-2.5 font-medium rounded-lg transition-all disabled:cursor-not-allowed flex items-center gap-2 text-white"
                  style={{
                    backgroundColor: loading || !cloneUrl.trim() ? 'var(--color-border)' : 'var(--color-accent)',
                  }}
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Globe className="w-4 h-4" />}
                  {loading ? 'Cloning...' : 'Clone'}
                </button>
              </div>
            </div>

            {/* Features */}
            <div className="grid grid-cols-3 gap-4">
              <div className="p-4 border rounded-lg" style={{ backgroundColor: 'var(--color-card)', borderColor: 'var(--color-border)' }}>
                <Globe className="w-6 h-6 mb-2" style={{ color: 'var(--color-accent)' }} />
                <h4 className="font-medium mb-1" style={{ color: 'var(--color-text)' }}>Full Rendering</h4>
                <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>Playwright renders JS-heavy sites</p>
              </div>
              <div className="p-4 border rounded-lg" style={{ backgroundColor: 'var(--color-card)', borderColor: 'var(--color-border)' }}>
                <Layers className="w-6 h-6 mb-2" style={{ color: '#a855f7' }} />
                <h4 className="font-medium mb-1" style={{ color: 'var(--color-text)' }}>Component Extraction</h4>
                <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>Detects navbar, hero, cards, etc.</p>
              </div>
              <div className="p-4 border rounded-lg" style={{ backgroundColor: 'var(--color-card)', borderColor: 'var(--color-border)' }}>
                <FolderOpen className="w-6 h-6 mb-2" style={{ color: 'var(--color-success)' }} />
                <h4 className="font-medium mb-1" style={{ color: 'var(--color-text)' }}>Saved Structure</h4>
                <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>Metadata and components stored</p>
              </div>
            </div>
          </motion.div>
        )}

        {/* GENERATE TAB */}
        {activeTab === 'generate' && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4"
          >
            <div className="p-6 rounded-xl border" style={{ backgroundColor: 'var(--color-bg-secondary)', borderColor: 'var(--color-border)' }}>
              <h3 className="text-lg font-semibold mb-3" style={{ color: 'var(--color-text)' }}>Generate an App from Idea</h3>
              <p className="text-sm mb-4" style={{ color: 'var(--color-text-secondary)' }}>
                Describe your app idea and AI will generate a complete, working application.
              </p>
              <textarea
                value={generateIdea}
                onChange={(e) => setGenerateIdea(e.target.value)}
                placeholder="A todo list application with dark mode and local storage..."
                rows={3}
                className="w-full mb-4 rounded-lg border px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-accent"
                style={{
                  backgroundColor: 'var(--color-bg)',
                  borderColor: 'var(--color-border)',
                  color: 'var(--color-text)',
                }}
                disabled={loading}
              />
              <button
                onClick={handleGenerate}
                disabled={loading || !generateIdea.trim()}
                className="w-full px-6 py-2.5 font-medium rounded-lg transition-all disabled:cursor-not-allowed flex items-center justify-center gap-2 text-white"
                style={{
                  backgroundColor: loading || !generateIdea.trim() ? 'var(--color-border)' : '#9333ea',
                }}
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Code className="w-4 h-4" />}
                {loading ? 'Generating...' : 'Generate App'}
              </button>
            </div>

            {/* Tips */}
            <div className="p-4 border rounded-lg" style={{ backgroundColor: 'rgba(var(--color-accent), 0.1)', borderColor: 'rgb(var(--color-accent))' }}>
              <h4 className="font-medium mb-2" style={{ color: 'var(--color-accent)' }}>💡 Tips for better results:</h4>
              <ul className="text-sm space-y-1" style={{ color: 'var(--color-accent)' }}>
                <li>• Be specific about features</li>
                <li>• Mention the tech stack you prefer</li>
                <li>• Include design preferences</li>
              </ul>
            </div>
          </motion.div>
        )}

        {/* SYNTHESIZE TAB */}
        {activeTab === 'synthesize' && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-4"
          >
            <div className="p-6 rounded-xl border" style={{ backgroundColor: 'var(--color-bg-secondary)', borderColor: 'var(--color-border)' }}>
              <h3 className="text-lg font-semibold mb-3" style={{ color: 'var(--color-text)' }}>Synthesize from Templates</h3>
              <p className="text-sm mb-4" style={{ color: 'var(--color-text-secondary)' }}>
                Combine existing cloned templates to create a new application using RAG.
              </p>
              <textarea
                value={synthesizeCommand}
                onChange={(e) => setSynthesizeCommand(e.target.value)}
                placeholder="Create a dashboard with the navbar from site A and the cards from site B..."
                rows={3}
                className="w-full mb-4 rounded-lg border px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-accent"
                style={{
                  backgroundColor: 'var(--color-bg)',
                  borderColor: 'var(--color-border)',
                  color: 'var(--color-text)',
                }}
                disabled={loading}
              />
              <button
                onClick={handleSynthesize}
                disabled={loading || !synthesizeCommand.trim()}
                className="w-full px-6 py-2.5 font-medium rounded-lg transition-all disabled:cursor-not-allowed flex items-center justify-center gap-2 text-white"
                style={{
                  backgroundColor: loading || !synthesizeCommand.trim() ? 'var(--color-border)' : '#4f46e5',
                }}
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Layers className="w-4 h-4" />}
                {loading ? 'Synthesizing...' : 'Synthesize'}
              </button>
            </div>
          </motion.div>
        )}

        {/* Result/Error */}
        <AnimatePresence>
          {result && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="p-4 border rounded-lg flex items-center gap-3"
              style={{ backgroundColor: 'rgba(var(--color-success), 0.1)', borderColor: 'rgb(var(--color-success))' }}
            >
              <CheckCircle className="w-5 h-5 flex-shrink-0" style={{ color: 'var(--color-success)' }} />
              <p className="text-sm flex-1" style={{ color: 'var(--color-success)' }}>{result}</p>
            </motion.div>
          )}

          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="p-4 border rounded-lg flex items-center gap-3"
              style={{ backgroundColor: 'rgba(var(--color-danger), 0.1)', borderColor: 'rgb(var(--color-danger))' }}
            >
              <AlertCircle className="w-5 h-5 flex-shrink-0" style={{ color: 'var(--color-danger)' }} />
              <p className="text-sm flex-1" style={{ color: 'var(--color-danger)' }}>{error}</p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Workspace Items */}
        {workspace.length > 0 && (
          <div className="mt-8">
            <h3 className="text-lg font-semibold mb-4" style={{ color: 'var(--color-text)' }}>Recent Projects ({workspace.length})</h3>
            <div className="space-y-3">
              {workspace.slice(0, 10).map((item) => (
                <div
                  key={item.id}
                  className="p-4 border rounded-lg hover:shadow-md transition-shadow"
                  style={{ backgroundColor: 'var(--color-card)', borderColor: 'var(--color-border)' }}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">
                        {item.type === 'clone' ? '🌐' : item.type === 'generated' ? '💻' : '🔄'}
                      </span>
                      <h4 className="font-medium" style={{ color: 'var(--color-text)' }}>{item.name}</h4>
                    </div>
                    <button
                      onClick={() => openInExplorer(item.path)}
                      className="p-1 rounded transition-colors hover:opacity-80"
                      style={{ backgroundColor: 'var(--color-bg-tertiary)' }}
                      title="Open in Explorer"
                    >
                      <ExternalLink className="w-4 h-4" style={{ color: 'var(--color-text-secondary)' }} />
                    </button>
                  </div>
                  <p className="text-sm mb-2" style={{ color: 'var(--color-text-secondary)' }}>{item.description}</p>
                  <div className="flex items-center gap-2 flex-wrap">
                    {item.components.slice(0, 5).map((comp) => (
                      <span key={comp} className="px-2 py-0.5 text-xs rounded" style={{ backgroundColor: 'var(--color-bg-tertiary)', color: 'var(--color-text-secondary)' }}>
                        {comp}
                      </span>
                    ))}
                    <span className="text-xs" style={{ color: 'var(--color-text-tertiary)' }}>
                      {new Date(item.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
