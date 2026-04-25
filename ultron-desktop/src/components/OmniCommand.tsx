import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface Command {
  id: string;
  icon: string;
  label: string;
  description: string;
  action: () => void;
}

export const OmniCommand = ({ 
  isOpen, 
  setIsOpen,
  onCommand
}: { 
  isOpen: boolean; 
  setIsOpen: (b: boolean) => void;
  onCommand: (cmdId: string) => void;
}) => {
  const [search, setSearch] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const commands: Command[] = [
    { id: 'route-coder', icon: '⚡', label: 'Route to CoderAgent', description: 'Force task to CoderAgent', action: () => onCommand('route-coder') },
    { id: 'route-researcher', icon: '🔍', label: 'Route to Researcher', description: 'Deep web search and synthesis', action: () => onCommand('route-researcher') },
    { id: 'switch-qwen', icon: '🧠', label: 'Switch to Qwen 2.5', description: 'Set active model to qwen2.5:14b', action: () => onCommand('switch-qwen') },
    { id: 'switch-llama', icon: '🦙', label: 'Switch to Llama 3', description: 'Set active model to llama3:8b', action: () => onCommand('switch-llama') },
    { id: 'open-terminal', icon: '💻', label: 'Open Dev Terminal', description: 'Launch background processes', action: () => onCommand('open-terminal') },
    { id: 'clear-memory', icon: '🗑️', label: 'Clear Memory', description: 'Wipe current conversation context', action: () => onCommand('clear-memory') },
  ];

  const filtered = commands.filter(c => c.label.toLowerCase().includes(search.toLowerCase()) || c.description.toLowerCase().includes(search.toLowerCase()));

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen(true);
      }
      if (e.key === 'Escape') setIsOpen(false);
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [setIsOpen]);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setSearch('');
      setSelectedIndex(0);
    }
  }, [isOpen]);

  const handleKeyNavigation = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex(prev => (prev + 1) % filtered.length);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex(prev => (prev - 1 + filtered.length) % filtered.length);
    } else if (e.key === 'Enter' && filtered.length > 0) {
      e.preventDefault();
      filtered[selectedIndex].action();
      setIsOpen(false);
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(7, 5, 13, 0.8)',
          backdropFilter: 'blur(8px)',
          zIndex: 1000,
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'center',
          paddingTop: '15vh'
        }} onClick={() => setIsOpen(false)}>
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            transition={{ duration: 0.15 }}
            onClick={e => e.stopPropagation()}
            style={{
              width: '100%',
              maxWidth: 640,
              background: 'var(--bg1)',
              border: '1px solid var(--bd)',
              borderRadius: 24,
              boxShadow: '0 30px 60px rgba(0,0,0,0.8), 0 0 40px var(--acc-glow)',
              overflow: 'hidden'
            }}
          >
            <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--bd2)', display: 'flex', alignItems: 'center', gap: 16 }}>
              <span style={{ fontSize: 24, color: 'var(--acc)' }}>⌘</span>
              <input
                ref={inputRef}
                value={search}
                onChange={e => { setSearch(e.target.value); setSelectedIndex(0); }}
                onKeyDown={handleKeyNavigation}
                placeholder="Type a command or search..."
                style={{
                  background: 'transparent',
                  border: 'none',
                  outline: 'none',
                  color: 'var(--t1)',
                  fontSize: 20,
                  width: '100%',
                  fontWeight: 500,
                  fontFamily: 'var(--font)'
                }}
              />
            </div>
            
            <div style={{ maxHeight: 400, overflowY: 'auto', padding: 12 }}>
              {filtered.map((cmd, idx) => (
                <div
                  key={cmd.id}
                  onClick={() => { cmd.action(); setIsOpen(false); }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 16,
                    padding: '16px',
                    borderRadius: 16,
                    cursor: 'pointer',
                    background: idx === selectedIndex ? 'var(--bg3)' : 'transparent',
                    borderLeft: idx === selectedIndex ? '3px solid var(--acc2)' : '3px solid transparent'
                  }}
                  onMouseEnter={() => setSelectedIndex(idx)}
                >
                  <div style={{
                    width: 40, height: 40, borderRadius: 12,
                    background: idx === selectedIndex ? 'var(--bg4)' : 'var(--bg2)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 20, color: 'var(--t1)'
                  }}>
                    {cmd.icon}
                  </div>
                  <div>
                    <div style={{ fontSize: 15, fontWeight: 600, color: idx === selectedIndex ? 'var(--t1)' : 'var(--t2)' }}>{cmd.label}</div>
                    <div style={{ fontSize: 13, color: 'var(--t3)', marginTop: 4 }}>{cmd.description}</div>
                  </div>
                </div>
              ))}
              {filtered.length === 0 && (
                <div style={{ padding: 40, textAlign: 'center', color: 'var(--t3)', fontSize: 15 }}>
                  Komut bulunamadı.
                </div>
              )}
            </div>
            
            <div style={{ padding: '12px 24px', background: 'var(--bg2)', borderTop: '1px solid var(--bd)', fontSize: 11, color: 'var(--t3)', display: 'flex', justifyContent: 'space-between' }}>
              <span><strong style={{ color: 'var(--t2)' }}>↑↓</strong> to navigate</span>
              <span><strong style={{ color: 'var(--t2)' }}>Enter</strong> to select</span>
              <span><strong style={{ color: 'var(--t2)' }}>Esc</strong> to close</span>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};
