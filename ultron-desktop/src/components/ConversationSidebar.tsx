import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Plus, Search, Trash2, Edit2, Check, X, 
  MessageSquare, Clock, Calendar, MoreVertical, AlertTriangle 
} from 'lucide-react';

export interface Conversation {
  id: string;
  title: string;
  messageCount: number;
  createdAt: number;
  updatedAt: number;
  model: string;
  mode: string;
}

interface ConversationSidebarProps {
  conversations: Conversation[];
  activeConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onNewConversation: () => void;
  onDeleteConversation: (id: string) => void;
  onRenameConversation: (id: string, newTitle: string) => void;
  onClearAllConversations?: () => void;
  isOpen: boolean;
  onClose: () => void;
}

export default function ConversationSidebar({
  conversations,
  activeConversationId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  onRenameConversation,
  onClearAllConversations,
  isOpen,
  onClose
}: ConversationSidebarProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');
  const [showMenuId, setShowMenuId] = useState<string | null>(null);
  const [confirmClearAll, setConfirmClearAll] = useState(false);

  const filteredConversations = conversations.filter(conv =>
    (conv.title || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  const groupedConversations = groupByTime(filteredConversations);

  const handleStartEdit = useCallback((conv: Conversation) => {
    setEditingId(conv.id);
    setEditingTitle(conv.title);
    setShowMenuId(null);
  }, []);

  const handleSaveEdit = useCallback(() => {
    if (editingId && editingTitle.trim()) {
      onRenameConversation(editingId, editingTitle.trim());
    }
    setEditingId(null);
    setEditingTitle('');
  }, [editingId, editingTitle, onRenameConversation]);

  const handleCancelEdit = useCallback(() => {
    setEditingId(null);
    setEditingTitle('');
  }, []);

  const handleDelete = useCallback((id: string) => {
    onDeleteConversation(id);
    setShowMenuId(null);
  }, [onDeleteConversation]);

  const formatTime = (timestamp: any) => {
    const date = new Date(timestamp);
    if (isNaN(date.getTime())) return 'Tarih belirsiz';

    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = diffMs / (1000 * 60 * 60);
    const diffDays = diffHours / 24;

    if (diffHours < 1) return 'Az önce';
    if (diffHours < 24) return `${Math.floor(diffHours)} sa önce`;
    if (diffDays < 7) return `${Math.floor(diffDays)} gün önce`;
    return date.toLocaleDateString('tr-TR', { month: 'short', day: 'numeric' });
  };

  return (
    <div className="h-full flex flex-col bg-zinc-50/50 dark:bg-[#1E1E1E]/50">
      {/* Header */}
      <div className="p-6 border-b border-zinc-200 dark:border-zinc-800/50">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-zinc-900 dark:text-white font-serif">Konuşmalar</h2>
          <button
            onClick={onClose}
            className="lg:hidden p-2 rounded-xl hover:bg-zinc-200 dark:hover:bg-zinc-800 transition-colors"
          >
            <X className="w-5 h-5 text-zinc-500" />
          </button>
        </div>

        {/* New Conversation Button */}
        <button
          onClick={onNewConversation}
          className="w-full flex items-center justify-center gap-3 px-4 py-3.5 rounded-[1.5rem] font-bold transition-all hover:scale-[1.02] active:scale-95 bg-purple-600 text-white shadow-lg shadow-purple-500/20"
        >
          <Plus className="w-5 h-5" />
          <span>Yeni Sohbet</span>
        </button>

        {/* Search */}
        <div className="mt-4 relative group">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400 group-focus-within:text-purple-500 transition-colors" />
          <input
            type="text"
            placeholder="Sohbetlerde ara..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-11 pr-4 py-2.5 rounded-[1.25rem] text-sm bg-white dark:bg-zinc-900/50 border border-zinc-200 dark:border-zinc-800/50 focus:outline-none focus:ring-2 focus:ring-purple-500/20 transition-all"
          />
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6 scrollbar-premium">
        {Object.entries(groupedConversations).map(([group, convs]) => (
          <div key={group} className="space-y-2">
            <h3 className="px-4 text-[10px] font-bold text-zinc-400 uppercase tracking-widest">{group}</h3>
            {convs.map(conv => (
              <div
                key={conv.id}
                className={`group relative px-4 py-3 rounded-2xl cursor-pointer transition-all ${
                  conv.id === activeConversationId 
                    ? 'bg-white dark:bg-zinc-900 shadow-sm border border-zinc-200 dark:border-zinc-800/50 ring-1 ring-purple-500/20' 
                    : 'hover:bg-white/50 dark:hover:bg-zinc-900/50'
                }`}
                onClick={() => onSelectConversation(conv.id)}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    {editingId === conv.id ? (
                      <input
                        autoFocus
                        value={editingTitle}
                        onChange={(e) => setEditingTitle(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSaveEdit()}
                        onBlur={handleSaveEdit}
                        className="w-full bg-zinc-100 dark:bg-zinc-800 px-2 py-1 rounded text-sm outline-none ring-2 ring-purple-500/50"
                      />
                    ) : (
                      <p className={`text-sm font-semibold truncate ${conv.id === activeConversationId ? 'text-zinc-900 dark:text-white' : 'text-zinc-600 dark:text-zinc-400'}`}>
                        {conv.title}
                      </p>
                    )}
                    <div className="flex items-center gap-3 mt-1">
                      <span className="text-[10px] font-medium text-zinc-400">{formatTime(conv.updatedAt)}</span>
                      <span className="text-[10px] font-medium text-zinc-400">• {conv.messageCount} mesaj</span>
                    </div>
                  </div>
                  
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setShowMenuId(showMenuId === conv.id ? null : conv.id);
                    }}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:bg-zinc-200 dark:hover:bg-zinc-800 rounded-lg transition-all"
                  >
                    <MoreVertical className="w-4 h-4 text-zinc-400" />
                  </button>
                </div>

                <AnimatePresence>
                  {showMenuId === conv.id && (
                    <motion.div
                      initial={{ opacity: 0, scale: 0.95, y: -10 }}
                      animate={{ opacity: 1, scale: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.95, y: -10 }}
                      className="absolute right-2 top-10 w-32 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl shadow-xl z-20 overflow-hidden"
                    >
                      <button
                        onClick={(e) => { e.stopPropagation(); handleStartEdit(conv); }}
                        className="w-full px-3 py-2 text-left text-xs font-bold hover:bg-zinc-50 dark:hover:bg-zinc-800 flex items-center gap-2"
                      >
                        <Edit2 className="w-3 h-3" /> Düzenle
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDelete(conv.id); }}
                        className="w-full px-3 py-2 text-left text-xs font-bold text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center gap-2"
                      >
                        <Trash2 className="w-3 h-3" /> Sil
                      </button>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            ))}
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-zinc-200 dark:border-zinc-800/50">
        {onClearAllConversations && (
          <button
            onClick={onClearAllConversations}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-2xl text-xs font-bold text-zinc-400 hover:text-red-500 hover:bg-red-500/5 transition-all"
          >
            <Trash2 className="w-4 h-4" />
            Geçmişi Temizle
          </button>
        )}
      </div>
    </div>
  );
}

function groupByTime(conversations: Conversation[]): Record<string, Conversation[]> {
  const now = new Date();
  const groups: Record<string, Conversation[]> = {};

  [...conversations].sort((a, b) => {
    const dateA = new Date(a.updatedAt).getTime();
    const dateB = new Date(b.updatedAt).getTime();
    return dateB - dateA;
  }).forEach(conv => {
    const date = new Date(conv.updatedAt);
    if (isNaN(date.getTime())) {
      const group = 'Daha Eski';
      if (!groups[group]) groups[group] = [];
      groups[group].push(conv);
      return;
    }
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    let group: string;
    if (diffDays === 0) group = 'Bugün';
    else if (diffDays === 1) group = 'Dün';
    else if (diffDays < 7) group = 'Geçen Hafta';
    else group = 'Daha Eski';

    if (!groups[group]) groups[group] = [];
    groups[group].push(conv);
  });

  return groups;
}
