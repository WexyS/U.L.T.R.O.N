import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Globe, Lightbulb, Combine, X, Loader2 } from 'lucide-react';

type ActionType = 'clone' | 'generate' | 'synthesize' | null;

const API_BASE = 'http://localhost:8000';

export default function WorkspacePanel() {
  const [action, setAction] = useState<ActionType>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <h2 className="text-lg font-semibold mb-6">Workspace</h2>

      {/* Action Buttons */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <ActionButton
          icon={<Globe className="w-5 h-5" />}
          label="Site Klonla"
          color="jarvis-primary"
          onClick={() => setAction('clone')}
        />
        <ActionButton
          icon={<Lightbulb className="w-5 h-5" />}
          label="Fikir → Uygulama"
          color="jarvis-accent"
          onClick={() => setAction('generate')}
        />
        <ActionButton
          icon={<Combine className="w-5 h-5" />}
          label="RAG Sentezi"
          color="jarvis-success"
          onClick={() => setAction('synthesize')}
        />
      </div>

      {/* Modals */}
      <AnimatePresence>
        {action === 'clone' && (
          <CloneModal
            onClose={() => setAction(null)}
            onSubmit={async (url) => {
              setLoading(true);
              try {
                const res = await fetch(`${API_BASE}/api/v2/workspace/clone`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ url, extract_components: true }),
                });
                const data = await res.json();
                setResult(data.success ? `✓ Klonlandı: ${data.item.name}` : `✗ Hata: ${data.error}`);
              } catch (e: unknown) {
                setResult(`✗ Hata: ${e instanceof Error ? e.message : String(e)}`);
              } finally {
                setLoading(false);
              }
            }}
            loading={loading}
          />
        )}
        {action === 'generate' && (
          <GenerateModal
            onClose={() => setAction(null)}
            onSubmit={async (idea) => {
              setLoading(true);
              try {
                const res = await fetch(`${API_BASE}/api/v2/workspace/generate`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ idea, tech_stack: 'html-css-js' }),
                });
                const data = await res.json();
                setResult(data.success ? `✓ Üretildi: ${data.item.name}` : `✗ Hata: ${data.error}`);
              } catch (e: unknown) {
                setResult(`✗ Hata: ${e instanceof Error ? e.message : String(e)}`);
              } finally {
                setLoading(false);
              }
            }}
            loading={loading}
          />
        )}
        {action === 'synthesize' && (
          <SynthesizeModal
            onClose={() => setAction(null)}
            onSubmit={async (command, project) => {
              setLoading(true);
              try {
                const res = await fetch(`${API_BASE}/api/v2/workspace/synthesize`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ user_command: command, target_project: project }),
                });
                const data = await res.json();
                setResult(data.success ? `✓ Sentezledi: ${data.item.name}` : `✗ Hata: ${data.error}`);
              } catch (e: unknown) {
                setResult(`✗ Hata: ${e instanceof Error ? e.message : String(e)}`);
              } finally {
                setLoading(false);
              }
            }}
            loading={loading}
          />
        )}
      </AnimatePresence>

      {/* Result */}
      {result && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-6 p-4 rounded-lg bg-jarvis-card border border-jarvis-border font-mono text-sm"
        >
          {result}
        </motion.div>
      )}

      {/* Workspace Grid */}
      <WorkspaceGrid />
    </div>
  );
}

function ActionButton({ icon, label, color, onClick }: {
  icon: React.ReactNode;
  label: string;
  color: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex flex-col items-center gap-2 p-6 rounded-xl bg-jarvis-card border border-jarvis-border hover:border-jarvis-primary/50 transition-all card-hover"
    >
      <span className={`${color}`}>{icon}</span>
      <span className="text-xs font-medium">{label}</span>
    </button>
  );
}

function CloneModal({ onClose, onSubmit, loading }: {
  onClose: () => void;
  onSubmit: (url: string) => Promise<void>;
  loading: boolean;
}) {
  const [url, setUrl] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url) return;
    await onSubmit(url);
  };

  return (
    <ModalShell onClose={onClose} title="Site Klonla">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="text-xs text-jarvis-textMuted">URL</label>
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com"
            className="w-full mt-1 px-3 py-2 rounded-md bg-jarvis-bg border border-jarvis-border text-sm focus:border-jarvis-primary outline-none"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full py-2 rounded-md bg-jarvis-primary text-jarvis-bg font-medium text-sm disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Klonla'}
        </button>
      </form>
    </ModalShell>
  );
}

function GenerateModal({ onClose, onSubmit, loading }: {
  onClose: () => void;
  onSubmit: (idea: string) => Promise<void>;
  loading: boolean;
}) {
  const [idea, setIdea] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!idea) return;
    await onSubmit(idea);
  };

  return (
    <ModalShell onClose={onClose} title="Fikir → Uygulama">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="text-xs text-jarvis-textMuted">Fikir</label>
          <textarea
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            placeholder="Yapılacaklar listesi uygulaması yap"
            rows={4}
            className="w-full mt-1 px-3 py-2 rounded-md bg-jarvis-bg border border-jarvis-border text-sm focus:border-jarvis-accent outline-none resize-none"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full py-2 rounded-md bg-jarvis-accent text-white font-medium text-sm disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Üret'}
        </button>
      </form>
    </ModalShell>
  );
}

function SynthesizeModal({ onClose, onSubmit, loading }: {
  onClose: () => void;
  onSubmit: (command: string, project: string) => Promise<void>;
  loading: boolean;
}) {
  const [command, setCommand] = useState('');
  const [project, setProject] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!command || !project) return;
    await onSubmit(command, project);
  };

  return (
    <ModalShell onClose={onClose} title="RAG Sentezi">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="text-xs text-jarvis-textMuted">Komut</label>
          <textarea
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            placeholder="Karanlık temalı siteyi Glossa'ya entegre et"
            rows={3}
            className="w-full mt-1 px-3 py-2 rounded-md bg-jarvis-bg border border-jarvis-border text-sm focus:border-jarvis-success outline-none resize-none"
          />
        </div>
        <div>
          <label className="text-xs text-jarvis-textMuted">Proje Adı</label>
          <input
            type="text"
            value={project}
            onChange={(e) => setProject(e.target.value)}
            placeholder="my-synthesis-project"
            className="w-full mt-1 px-3 py-2 rounded-md bg-jarvis-bg border border-jarvis-border text-sm focus:border-jarvis-success outline-none"
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="w-full py-2 rounded-md bg-jarvis-success text-white font-medium text-sm disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Sentezle'}
        </button>
      </form>
    </ModalShell>
  );
}

function ModalShell({ onClose, title, children }: {
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50"
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        className="w-full max-w-md p-6 rounded-xl bg-jarvis-panel border border-jarvis-border shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold">{title}</h3>
          <button onClick={onClose} className="p-1 hover:bg-jarvis-card rounded-md transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>
        {children}
      </motion.div>
    </motion.div>
  );
}

function WorkspaceGrid() {
  return (
    <div>
      <h3 className="text-xs font-medium text-jarvis-textMuted uppercase mb-3">Workspace Items</h3>
      <div className="grid grid-cols-1 gap-3">
        <div className="p-4 rounded-lg bg-jarvis-card border border-jarvis-border text-center text-xs text-jarvis-textMuted">
          No workspace items yet. Clone a site or generate an app to get started.
        </div>
      </div>
    </div>
  );
}
