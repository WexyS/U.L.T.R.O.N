import { useState, useCallback, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Code2, Play, RotateCcw, ChevronDown, ChevronRight,
  FileCode, FilePlus, FileX, Check, X, Loader2,
  FolderTree, Send, RefreshCw, Copy, Sparkles
} from 'lucide-react';

interface FileChange {
  path: string;
  action: 'create' | 'modify' | 'delete';
  content: string;
  original: string;
  diff: string;
  applied: boolean;
}

interface ComposerSession {
  session_id: string;
  prompt: string;
  workspace: string;
  changes: FileChange[];
  status: 'pending' | 'applied' | 'rolled_back';
}

const API_BASE = 'http://127.0.0.1:8000';

export default function ComposerPanel() {
  const [prompt, setPrompt] = useState('');
  const [workspace, setWorkspace] = useState('');
  const [contextFiles, setContextFiles] = useState<string[]>([]);
  const [contextFileInput, setContextFileInput] = useState('');
  const [session, setSession] = useState<ComposerSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedFiles, setExpandedFiles] = useState<Set<string>>(new Set());
  const [projectContext, setProjectContext] = useState<string | null>(null);
  const [showContext, setShowContext] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px';
    }
  }, [prompt]);

  const handleGenerate = useCallback(async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    setError(null);
    setSession(null);

    try {
      const res = await fetch(`${API_BASE}/api/v2/composer/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: prompt.trim(),
          workspace: workspace || '',
          context_files: contextFiles,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Generation failed');
      }

      const data = await res.json();
      setSession(data);
      // Auto-expand all files
      setExpandedFiles(new Set(data.changes.map((c: FileChange) => c.path)));
    } catch (e: any) {
      setError(e.message || 'Failed to generate changes');
    } finally {
      setLoading(false);
    }
  }, [prompt, workspace, contextFiles]);

  const handleApply = useCallback(async () => {
    if (!session) return;
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_BASE}/api/v2/composer/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: session.session_id }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Apply failed');
      }

      const result = await res.json();
      setSession(prev => prev ? { ...prev, status: 'applied' } : null);
    } catch (e: any) {
      setError(e.message || 'Failed to apply changes');
    } finally {
      setLoading(false);
    }
  }, [session]);

  const handleRollback = useCallback(async () => {
    if (!session) return;
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_BASE}/api/v2/composer/rollback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: session.session_id }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Rollback failed');
      }

      setSession(prev => prev ? { ...prev, status: 'rolled_back' } : null);
    } catch (e: any) {
      setError(e.message || 'Failed to rollback changes');
    } finally {
      setLoading(false);
    }
  }, [session]);

  const loadContext = useCallback(async () => {
    try {
      const filesParam = contextFiles.length > 0 ? `&files=${contextFiles.join(',')}` : '';
      const res = await fetch(`${API_BASE}/api/v2/composer/context?workspace=${encodeURIComponent(workspace)}${filesParam}`);
      if (res.ok) {
        const data = await res.json();
        setProjectContext(data.context);
        setShowContext(true);
      }
    } catch {
      setError('Failed to load project context');
    }
  }, [workspace, contextFiles]);

  const addContextFile = useCallback(() => {
    if (contextFileInput.trim() && !contextFiles.includes(contextFileInput.trim())) {
      setContextFiles(prev => [...prev, contextFileInput.trim()]);
      setContextFileInput('');
    }
  }, [contextFileInput, contextFiles]);

  const toggleFileExpand = useCallback((path: string) => {
    setExpandedFiles(prev => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  }, []);

  const getActionIcon = (action: string) => {
    switch (action) {
      case 'create': return <FilePlus className="w-4 h-4 text-green-400" />;
      case 'modify': return <FileCode className="w-4 h-4 text-yellow-400" />;
      case 'delete': return <FileX className="w-4 h-4 text-red-400" />;
      default: return <FileCode className="w-4 h-4" />;
    }
  };

  const getActionBadge = (action: string) => {
    const colors: Record<string, string> = {
      create: 'bg-green-500/20 text-green-400 border-green-500/30',
      modify: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
      delete: 'bg-red-500/20 text-red-400 border-red-500/30',
    };
    return (
      <span className={`px-1.5 py-0.5 text-[10px] font-semibold uppercase rounded border ${colors[action] || ''}`}>
        {action}
      </span>
    );
  };

  const renderDiff = (diff: string) => {
    if (!diff) return <p className="text-xs opacity-50 italic px-4 py-2">No diff available</p>;
    const lines = diff.split('\n');
    return (
      <pre className="text-xs leading-relaxed font-mono overflow-x-auto">
        {lines.map((line, i) => {
          let className = 'px-4 py-0.5 ';
          if (line.startsWith('+++') || line.startsWith('---')) {
            className += 'text-gray-400 bg-gray-800/50';
          } else if (line.startsWith('@@')) {
            className += 'text-blue-400 bg-blue-500/10';
          } else if (line.startsWith('+')) {
            className += 'text-green-400 bg-green-500/10';
          } else if (line.startsWith('-')) {
            className += 'text-red-400 bg-red-500/10';
          } else {
            className += 'text-gray-300';
          }
          return (
            <div key={i} className={className}>
              {line || ' '}
            </div>
          );
        })}
      </pre>
    );
  };

  return (
    <div className="flex flex-col h-full" style={{ backgroundColor: 'rgb(var(--color-bg))' }}>
      {/* Header */}
      <div className="flex items-center gap-3 p-4 border-b" style={{ borderColor: 'rgb(var(--color-border))' }}>
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #8b5cf6, #6366f1)' }}>
            <Code2 className="w-4 h-4 text-white" />
          </div>
          <div>
            <h2 className="text-sm font-bold" style={{ color: 'rgb(var(--color-text))' }}>Composer</h2>
            <p className="text-[10px]" style={{ color: 'rgb(var(--color-text-muted))' }}>Multi-file code generation</p>
          </div>
        </div>

        {session && (
          <div className="ml-auto flex items-center gap-2">
            {session.status === 'pending' && (
              <>
                <button
                  onClick={handleApply}
                  disabled={loading}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-white transition-all hover:scale-105"
                  style={{ background: 'linear-gradient(135deg, #22c55e, #16a34a)' }}
                >
                  <Play className="w-3.5 h-3.5" />
                  Uygula
                </button>
                <button
                  onClick={() => setSession(null)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors hover:bg-gray-200 dark:hover:bg-gray-700"
                  style={{ color: 'rgb(var(--color-text-muted))' }}
                >
                  <X className="w-3.5 h-3.5" />
                  İptal
                </button>
              </>
            )}
            {session.status === 'applied' && (
              <button
                onClick={handleRollback}
                disabled={loading}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-orange-400 border border-orange-400/30 hover:bg-orange-500/10 transition-colors"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                Geri Al
              </button>
            )}
            {session.status === 'rolled_back' && (
              <span className="text-xs font-medium text-gray-400">Geri Alındı</span>
            )}
          </div>
        )}
      </div>

      {/* Workspace + Context Config */}
      <div className="p-3 border-b space-y-2" style={{ borderColor: 'rgb(var(--color-border))' }}>
        <div className="flex gap-2">
          <input
            type="text"
            value={workspace}
            onChange={e => setWorkspace(e.target.value)}
            placeholder="Çalışma dizini (ör: C:\proje\yol)"
            title="Çalışma dizinini belirleyin"
            className="flex-1 px-3 py-1.5 rounded-lg text-xs border transition-colors focus:outline-none focus:ring-2 focus:ring-purple-500/50"
            style={{
              backgroundColor: 'rgb(var(--color-panel))',
              borderColor: 'rgb(var(--color-border))',
              color: 'rgb(var(--color-text))',
            }}
          />
          <button
            onClick={loadContext}
            title="Proje yapısını yükle"
            className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs border transition-colors hover:bg-gray-100 dark:hover:bg-gray-800"
            style={{ borderColor: 'rgb(var(--color-border))', color: 'rgb(var(--color-text-muted))' }}
          >
            <FolderTree className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Context files */}
        {contextFiles.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {contextFiles.map(f => (
              <span
                key={f}
                className="flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-mono border"
                style={{
                  backgroundColor: 'rgb(var(--color-panel))',
                  borderColor: 'rgb(var(--color-border))',
                  color: 'rgb(var(--color-text-muted))',
                }}
              >
                {f.split(/[/\\]/).pop()}
                <button
                  onClick={() => setContextFiles(prev => prev.filter(x => x !== f))}
                  className="hover:text-red-400"
                >
                  <X className="w-2.5 h-2.5" />
                </button>
              </span>
            ))}
          </div>
        )}

        <div className="flex gap-2">
          <input
            type="text"
            value={contextFileInput}
            onChange={e => setContextFileInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && addContextFile()}
            placeholder="Bağlam dosyası ekle (ör: src/app.tsx)"
            title="Bağlam dosyası yolu"
            className="flex-1 px-3 py-1.5 rounded-lg text-xs border transition-colors focus:outline-none focus:ring-2 focus:ring-purple-500/50"
            style={{
              backgroundColor: 'rgb(var(--color-panel))',
              borderColor: 'rgb(var(--color-border))',
              color: 'rgb(var(--color-text))',
            }}
          />
          <button
            onClick={addContextFile}
            title="Dosya ekle"
            className="px-2.5 py-1.5 rounded-lg text-xs border transition-colors hover:bg-gray-100 dark:hover:bg-gray-800"
            style={{ borderColor: 'rgb(var(--color-border))', color: 'rgb(var(--color-text-muted))' }}
          >
            <FilePlus className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Project Context View */}
      <AnimatePresence>
        {showContext && projectContext && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="border-b overflow-hidden"
            style={{ borderColor: 'rgb(var(--color-border))' }}
          >
            <div className="p-3 max-h-48 overflow-y-auto">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold" style={{ color: 'rgb(var(--color-text))' }}>
                  Proje Yapısı
                </span>
                <button onClick={() => setShowContext(false)} className="text-xs opacity-50 hover:opacity-100">
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
              <pre className="text-[10px] leading-relaxed font-mono whitespace-pre-wrap"
                style={{ color: 'rgb(var(--color-text-muted))' }}>
                {projectContext}
              </pre>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Changes View */}
      <div className="flex-1 overflow-y-auto">
        {session && session.changes.length > 0 ? (
          <div className="divide-y" style={{ borderColor: 'rgb(var(--color-border))' }}>
            {/* Summary bar */}
            <div className="px-4 py-2 flex items-center gap-3 text-xs" style={{ 
              backgroundColor: 'rgb(var(--color-panel))',
              color: 'rgb(var(--color-text-muted))',
            }}>
              <Sparkles className="w-3.5 h-3.5 text-purple-400" />
              <span>
                {session.changes.length} dosya değişikliği •{' '}
                {session.changes.filter(c => c.action === 'create').length} yeni •{' '}
                {session.changes.filter(c => c.action === 'modify').length} düzenleme •{' '}
                {session.changes.filter(c => c.action === 'delete').length} silme
              </span>
              {session.status === 'applied' && (
                <span className="ml-auto flex items-center gap-1 text-green-400">
                  <Check className="w-3 h-3" /> Uygulandı
                </span>
              )}
            </div>

            {/* File changes */}
            {session.changes.map((change) => (
              <div key={change.path} style={{ borderColor: 'rgb(var(--color-border))' }}>
                {/* File header */}
                <button
                  onClick={() => toggleFileExpand(change.path)}
                  className="w-full flex items-center gap-2 px-4 py-2.5 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                >
                  {expandedFiles.has(change.path)
                    ? <ChevronDown className="w-3.5 h-3.5 text-gray-400" />
                    : <ChevronRight className="w-3.5 h-3.5 text-gray-400" />
                  }
                  {getActionIcon(change.action)}
                  <span className="text-xs font-mono flex-1 text-left truncate" style={{ color: 'rgb(var(--color-text))' }}>
                    {change.path}
                  </span>
                  {getActionBadge(change.action)}
                </button>

                {/* Diff view */}
                <AnimatePresence>
                  {expandedFiles.has(change.path) && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden border-t"
                      style={{
                        borderColor: 'rgb(var(--color-border))',
                        backgroundColor: 'rgb(15, 15, 20)',
                      }}
                    >
                      <div className="max-h-80 overflow-y-auto">
                        {renderDiff(change.diff)}
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ))}
          </div>
        ) : !loading && (
          <div className="flex flex-col items-center justify-center h-full text-center px-8">
            <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-4"
              style={{ background: 'linear-gradient(135deg, #8b5cf620, #6366f120)' }}>
              <Code2 className="w-8 h-8 text-purple-400" />
            </div>
            <h3 className="text-sm font-semibold mb-1" style={{ color: 'rgb(var(--color-text))' }}>
              Composer ile Kod Oluştur
            </h3>
            <p className="text-xs max-w-xs" style={{ color: 'rgb(var(--color-text-muted))' }}>
              Ne oluşturmak istediğinizi yazın. Composer birden fazla dosyayı aynı anda oluşturabilir,
              düzenleyebilir veya silebilir.
            </p>
          </div>
        )}

        {loading && (
          <div className="flex flex-col items-center justify-center h-full gap-3">
            <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
            <span className="text-xs" style={{ color: 'rgb(var(--color-text-muted))' }}>
              Kod oluşturuluyor...
            </span>
          </div>
        )}
      </div>

      {/* Error */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="mx-3 mb-2 px-3 py-2 rounded-lg text-xs bg-red-500/10 text-red-400 border border-red-500/20 flex items-center justify-between"
          >
            <span>{error}</span>
            <button onClick={() => setError(null)}>
              <X className="w-3.5 h-3.5" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input */}
      <div className="p-3 border-t" style={{ borderColor: 'rgb(var(--color-border))' }}>
        <div className="flex gap-2 items-end">
          <textarea
            ref={textareaRef}
            value={prompt}
            onChange={e => setPrompt(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleGenerate();
              }
            }}
            placeholder="Ne oluşturmak istiyorsun? (ör: 'React login sayfası oluştur', 'API'ye auth ekle')"
            title="Kod oluşturma promptu"
            rows={1}
            className="flex-1 px-4 py-2.5 rounded-xl text-sm border resize-none transition-colors focus:outline-none focus:ring-2 focus:ring-purple-500/50"
            style={{
              backgroundColor: 'rgb(var(--color-panel))',
              borderColor: 'rgb(var(--color-border))',
              color: 'rgb(var(--color-text))',
              minHeight: '40px',
              maxHeight: '200px',
            }}
          />
          <button
            onClick={handleGenerate}
            disabled={loading || !prompt.trim()}
            className="flex items-center justify-center w-10 h-10 rounded-xl text-white transition-all hover:scale-105 disabled:opacity-40 disabled:hover:scale-100"
            style={{
              background: loading || !prompt.trim()
                ? 'rgb(var(--color-border))'
                : 'linear-gradient(135deg, #8b5cf6, #6366f1)',
            }}
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </div>
  );
}
