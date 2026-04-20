import { useState, useCallback, useEffect } from 'react';
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

  // Filter conversations by search query
  const filteredConversations = conversations.filter(conv =>
    conv.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Group conversations by time
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

  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = diffMs / (1000 * 60 * 60);
    const diffDays = diffHours / 24;

    if (diffHours < 1) {
      return 'Just now';
    } else if (diffHours < 24) {
      return `${Math.floor(diffHours)}h ago`;
    } else if (diffDays < 7) {
      return `${Math.floor(diffDays)}d ago`;
    } else {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/50 z-30"
          />

          {/* Sidebar - positioned to the left of main sidebar */}
          <motion.div
            initial={{ x: -320, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -320, opacity: 0 }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed left-0 top-0 bottom-0 w-80 z-40 flex flex-col"
            style={{
              backgroundColor: 'rgb(var(--color-panel))',
              borderRight: '1px solid rgb(var(--color-border))'
            }}
          >
            {/* Header */}
            <div className="p-4 border-b" style={{ borderColor: 'rgb(var(--color-border))' }}>
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-bold" style={{ color: 'rgb(var(--color-text))' }}>
                  Conversations
                </h2>
                <button
                  onClick={onClose}
                  title="Konuşma panelini kapat"
                  className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                >
                  <X className="w-5 h-5" style={{ color: 'rgb(var(--color-text-muted))' }} />
                </button>
              </div>

              {/* New Conversation Button */}
              <button
                onClick={onNewConversation}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl font-medium transition-all hover:scale-105"
                style={{ 
                  background: 'linear-gradient(135deg, rgb(var(--color-accent)), #4f46e5)',
                  color: 'white',
                  boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)'
                }}
              >
                <Plus className="w-5 h-5" />
                <span>New Chat</span>
              </button>

              {/* Search Input */}
              <div className="mt-3 relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: 'rgb(var(--color-text-muted))' }} />
                <input
                  type="text"
                  placeholder="Search conversations..."
                  title="Konuşmalarda ara"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-3 py-2 rounded-lg text-sm border transition-colors focus:outline-none focus:ring-2 focus:ring-ultron-primary/50"
                  style={{ 
                    backgroundColor: 'rgb(var(--color-bg))',
                    borderColor: 'rgb(var(--color-border))',
                    color: 'rgb(var(--color-text))'
                  }}
                />
              </div>
            </div>

            {/* Conversation List */}
            <div className="flex-1 overflow-y-auto">
              {Object.entries(groupedConversations).map(([group, convs]) => (
                <div key={group} className="mb-2">
                  {/* Group Header */}
                  <div className="px-4 py-2 text-xs font-semibold uppercase tracking-wide" style={{ color: 'rgb(var(--color-text-muted))' }}>
                    {group}
                  </div>

                  {/* Conversations in Group */}
                  {convs.map(conv => (
                    <div
                      key={conv.id}
                      className={`group relative mx-2 mb-1 rounded-xl cursor-pointer transition-all ${
                        conv.id === activeConversationId ? 'ring-2 ring-ultron-primary' : 'hover:bg-gray-100/50 dark:hover:bg-gray-800/50'
                      }`}
                      style={{ 
                        backgroundColor: conv.id === activeConversationId ? 'rgb(var(--color-bg))' : 'transparent'
                      }}
                      onClick={() => onSelectConversation(conv.id)}
                    >
                      <div className="p-3">
                        {/* Title */}
                        {editingId === conv.id ? (
                          <div className="flex items-center gap-2">
                            <input
                              type="text"
                              value={editingTitle}
                              onChange={(e) => setEditingTitle(e.target.value)}
                              title="Konuşma başlığını düzenle"
                              placeholder="Yeni başlık"
                              onKeyDown={(e) => {
                                if (e.key === 'Enter') handleSaveEdit();
                                if (e.key === 'Escape') handleCancelEdit();
                              }}
                              className="flex-1 px-2 py-1 text-sm rounded border focus:outline-none focus:ring-2 focus:ring-ultron-primary/50"
                              style={{ 
                                backgroundColor: 'rgb(var(--color-bg))',
                                borderColor: 'rgb(var(--color-border))',
                                color: 'rgb(var(--color-text))'
                              }}
                              autoFocus
                            />
                            <button onClick={handleSaveEdit} title="Başlığı kaydet" className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded">
                              <Check className="w-4 h-4 text-green-500" />
                            </button>
                            <button onClick={handleCancelEdit} title="Düzenlemeyi iptal et" className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded">
                              <X className="w-4 h-4 text-red-500" />
                            </button>
                          </div>
                        ) : (
                          <>
                            <div className="flex items-start justify-between gap-2">
                              <div className="flex items-center gap-2 flex-1 min-w-0">
                                <MessageSquare className="w-4 h-4 flex-shrink-0" style={{ color: 'rgb(var(--color-text-muted))' }} />
                                <span className="text-sm font-medium truncate" style={{ color: 'rgb(var(--color-text))' }}>
                                  {conv.title}
                                </span>
                              </div>
                              
                              {/* More Actions Menu */}
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setShowMenuId(showMenuId === conv.id ? null : conv.id);
                                }}
                                title="Konuşma seçenekleri"
                                className="opacity-0 group-hover:opacity-100 p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded transition-opacity"
                              >
                                <MoreVertical className="w-4 h-4" style={{ color: 'rgb(var(--color-text-muted))' }} />
                              </button>
                            </div>

                            {/* Metadata */}
                            <div className="flex items-center gap-3 mt-1.5 text-xs" style={{ color: 'rgb(var(--color-text-muted))' }}>
                              <div className="flex items-center gap-1">
                                <Clock className="w-3 h-3" />
                                <span>{formatTime(conv.updatedAt)}</span>
                              </div>
                              <div className="flex items-center gap-1">
                                <MessageSquare className="w-3 h-3" />
                                <span>{conv.messageCount} msgs</span>
                              </div>
                            </div>
                          </>
                        )}
                      </div>

                      {/* Context Menu */}
                      <AnimatePresence>
                        {showMenuId === conv.id && (
                          <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                            className="absolute right-2 top-12 w-36 rounded-lg shadow-lg overflow-hidden z-10"
                            style={{ 
                              backgroundColor: 'rgb(var(--color-card))',
                              border: '1px solid rgb(var(--color-border))'
                            }}
                          >
                            <button
                              onClick={() => handleStartEdit(conv)}
                              className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                              style={{ color: 'rgb(var(--color-text))' }}
                            >
                              <Edit2 className="w-3.5 h-3.5" />
                              <span>Rename</span>
                            </button>
                            <button
                              onClick={() => handleDelete(conv.id)}
                              className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors text-red-500"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                              <span>Delete</span>
                            </button>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  ))}
                </div>
              ))}

              {/* Empty State */}
              {filteredConversations.length === 0 && (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <MessageSquare className="w-12 h-12 mb-3" style={{ color: 'rgb(var(--color-text-muted))' }} />
                  <p className="text-sm font-medium" style={{ color: 'rgb(var(--color-text))' }}>
                    {searchQuery ? 'No conversations found' : 'No conversations yet'}
                  </p>
                  <p className="text-xs mt-1" style={{ color: 'rgb(var(--color-text-muted))' }}>
                    {searchQuery ? 'Try a different search' : 'Start a new chat to begin'}
                  </p>
                </div>
              )}
            </div>

            {/* Footer Stats & Clear All */}
            <div className="p-4 border-t text-xs" style={{ 
              borderColor: 'rgb(var(--color-border))',
              color: 'rgb(var(--color-text-muted))'
            }}>
              <div className="flex items-center justify-between mb-2">
                <span>{conversations.length} conversations</span>
                <div className="flex items-center gap-1">
                  <Calendar className="w-3 h-3" />
                  <span>Today</span>
                </div>
              </div>
              {conversations.length > 0 && onClearAllConversations && (
                <AnimatePresence mode="wait">
                  {confirmClearAll ? (
                    <motion.div
                      key="confirm"
                      initial={{ opacity: 0, y: 4 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -4 }}
                      className="flex items-center gap-2"
                    >
                      <AlertTriangle className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />
                      <span className="text-red-500 text-xs">Tümü silinsin mi?</span>
                      <button
                        onClick={() => { onClearAllConversations(); setConfirmClearAll(false); }}
                        className="px-2 py-1 rounded text-xs font-medium bg-red-500 text-white hover:bg-red-600 transition-colors"
                      >
                        Evet
                      </button>
                      <button
                        onClick={() => setConfirmClearAll(false)}
                        className="px-2 py-1 rounded text-xs font-medium hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
                        style={{ color: 'rgb(var(--color-text))' }}
                      >
                        İptal
                      </button>
                    </motion.div>
                  ) : (
                    <motion.button
                      key="trigger"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      exit={{ opacity: 0 }}
                      onClick={() => setConfirmClearAll(true)}
                      className="w-full flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 border border-red-200 dark:border-red-800/40 transition-colors"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                      Tüm Konuşmaları Temizle
                    </motion.button>
                  )}
                </AnimatePresence>
              )}
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

// Helper function to group conversations by time
function groupByTime(conversations: Conversation[]): Record<string, Conversation[]> {
  const now = new Date();
  const groups: Record<string, Conversation[]> = {};

  conversations.forEach(conv => {
    const diffMs = now.getTime() - conv.updatedAt;
    const diffHours = diffMs / (1000 * 60 * 60);
    const diffDays = diffHours / 24;

    let group: string;
    if (diffHours < 1) {
      group = 'Last hour';
    } else if (diffHours < 24) {
      group = 'Today';
    } else if (diffDays < 2) {
      group = 'Yesterday';
    } else if (diffDays < 7) {
      group = 'Last 7 days';
    } else if (diffDays < 30) {
      group = 'Last 30 days';
    } else {
      group = 'Older';
    }

    if (!groups[group]) {
      groups[group] = [];
    }
    groups[group].push(conv);
  });

  return groups;
}
