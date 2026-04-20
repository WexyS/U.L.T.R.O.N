import { useState, useRef, useEffect } from 'react';
import { Send, Code, Search, Monitor } from 'lucide-react';
import VoiceControl from './VoiceControl';

type Mode = 'chat' | 'code' | 'research' | 'rpa';

interface InputBoxProps {
  onSend: (message: string, mode: Mode) => void;
  disabled: boolean;
  isConnected: boolean;
}

const MODES: { key: Mode; label: string; icon: React.ReactNode }[] = [
  { key: 'chat',     label: 'Chat',     icon: <Send className="w-3.5 h-3.5" /> },
  { key: 'code',     label: 'Code',     icon: <Code className="w-3.5 h-3.5" /> },
  { key: 'research', label: 'Research', icon: <Search className="w-3.5 h-3.5" /> },
  { key: 'rpa',      label: 'RPA',      icon: <Monitor className="w-3.5 h-3.5" /> },
];

export default function InputBox({ onSend, disabled, isConnected }: InputBoxProps) {
  const [input, setInput] = useState('');
  const [mode, setMode] = useState<Mode>('chat');
  const [isListening, setIsListening] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const recognitionRef = useRef<any>(null);

  // Auto-resize textarea — max 200px
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 200) + 'px';
  }, [input]);

  // Focus on mount
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || disabled || !isConnected) return;
    onSend(trimmed, mode);
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
    // Re-focus after send
    setTimeout(() => textareaRef.current?.focus(), 50);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleVoiceInput = (text: string) => {
    setInput(prev => prev + (prev ? ' ' : '') + text);
  };

  const handleVoiceTTS = () => {
    // Optional TTS functionality wrapper
  };

  const canSend = input.trim().length > 0 && isConnected && !disabled;

  return (
    <div className="flex flex-col gap-2">
      {/* Mode tabs — subtle, small */}
      <div className="flex items-center gap-1 px-1" role="tablist" aria-label="Chat modes">
        {MODES.map(m => (
          <button
            key={m.key}
            onClick={() => setMode(m.key)}
            disabled={!isConnected}
            role="tab"
            aria-selected={mode === m.key}
            aria-controls="chat-input"
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-all select-none ${
              mode === m.key
                ? 'bg-purple-600 text-white shadow-sm'
                : 'text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800'
            }`}
          >
            {m.icon}
            <span className="hidden sm:inline">{m.label}</span>
          </button>
        ))}
      </div>

      {/* Main input container — Claude-style */}
      <div className={`flex items-end gap-2 rounded-xl border bg-white/80 dark:bg-zinc-900/80 backdrop-blur-xl shadow-lg transition-all duration-150 ${
        isConnected
          ? 'border-zinc-300 dark:border-zinc-700 focus-within:border-purple-400 dark:focus-within:border-purple-500 focus-within:shadow-md focus-within:shadow-purple-500/10'
          : 'border-red-300 dark:border-red-800 opacity-70'
      }`}>
        <label htmlFor="chat-input" className="sr-only">Mesajınızı buraya yazın</label>
        <textarea
          id="chat-input"
          ref={textareaRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            !isConnected ? 'Bağlantı bekleniyor...' :
            mode === 'chat'     ? 'Nasıl yardımcı olabilirim?' :
            mode === 'code'     ? 'Yazmamı istediğin kodu tarif et...' :
            mode === 'research' ? 'Neyi araştırmamı istersin?' :
            'Bilgisayarda hangi işlemi yapmamı istersin?'
          }
          disabled={!isConnected || disabled}
          rows={1}
          className="flex-1 resize-none bg-transparent px-4 py-3 text-sm text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 dark:placeholder-zinc-600 focus:outline-none disabled:opacity-50 leading-relaxed"
          style={{ fontSize: 'var(--app-font-size)', maxHeight: '200px', overflowY: 'auto' }}
        />

        <div className="flex items-center gap-1 px-2 pb-2 flex-shrink-0">
          <VoiceControl 
            onVoiceInput={handleVoiceInput}
            onTTS={handleVoiceTTS}
            disabled={!isConnected || disabled}
            language="tr-TR"
          />

          {/* Send button */}
          <button
            type="button"
            onClick={() => handleSubmit()}
            disabled={!canSend}
            className={`p-1.5 rounded-lg transition-all ${
              canSend
                ? 'bg-purple-600 text-white hover:bg-purple-700 active:scale-95 shadow-sm shadow-purple-500/30'
                : 'text-zinc-300 dark:text-zinc-600 cursor-not-allowed'
            }`}
            title="Gönder (Enter)"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Subtle hint */}
      <p className="text-center text-zinc-400 dark:text-zinc-600" style={{ fontSize: '10px' }}>
        {isConnected
          ? (disabled ? '⟳ İşleniyor...' : 'Enter gönder  •  Shift+Enter yeni satır')
          : '⚠ Ultron Core bekleniyor...'}
      </p>
    </div>
  );
}
