import { useState, useRef, useEffect } from 'react';
import { Send, Code, Search, Monitor, Languages } from 'lucide-react';
import VoiceControl from './VoiceControl';

type Mode = 'chat' | 'code' | 'research' | 'rpa';
type VoiceLang = 'tr-TR' | 'en-US';

interface InputBoxProps {
  onSend: (message: string, mode: Mode) => void;
  disabled: boolean;
  isConnected: boolean;
}

const MODES: { key: Mode; label: string; icon: React.ReactNode; color: string }[] = [
  { key: 'chat', label: 'Chat', icon: <Send className="w-4 h-4" />, color: 'var(--color-accent)' },
  { key: 'code', label: 'Code', icon: <Code className="w-4 h-4" />, color: '#a855f7' },
  { key: 'research', label: 'Research', icon: <Search className="w-4 h-4" />, color: '#3b82f6' },
  { key: 'rpa', label: 'RPA', icon: <Monitor className="w-4 h-4" />, color: '#f97316' },
];

export default function InputBox({ onSend, disabled, isConnected }: InputBoxProps) {
  const [input, setInput] = useState('');
  const [mode, setMode] = useState<Mode>('chat');
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [voiceLang, setVoiceLang] = useState<VoiceLang>('tr-TR');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 150) + 'px';
    }
  }, [input]);

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || disabled || !isConnected) return;
    onSend(trimmed, mode);
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleVoiceInput = (text: string) => {
    setInput((prev) => prev + (prev ? ' ' : '') + text);
    setIsListening(false);
  };

  const handleTTS = (text: string) => {
    if (!text) {
      setIsSpeaking(false);
    } else {
      setIsSpeaking(true);
      // Speak the text
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'tr-TR';
      utterance.onend = () => setIsSpeaking(false);
      utterance.onerror = () => setIsSpeaking(false);
      window.speechSynthesis.speak(utterance);
    }
  };

  const resolveModeColor = (color: string) => {
    if (color === 'var(--color-accent)') return 'rgb(var(--color-accent))';
    return color;
  };

  return (
    <div className="bg-white dark:bg-[#1E1E1E] p-8 rounded-[3rem] mx-auto max-w-5xl relative shadow-2xl border border-zinc-200 dark:border-zinc-800/50 transform transition-all focus-within:scale-[1.01]">
      {/* Mode selector */}
      <div className="flex items-center gap-2 mb-4">
        {MODES.map((m) => (
          <button
            key={m.key}
            onClick={() => setMode(m.key)}
            disabled={!isConnected}
            className={`flex items-center gap-2 px-4 py-2 rounded-2xl text-xs font-bold transition-all ${
              mode === m.key
                ? 'text-white shadow-md'
                : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-500 hover:text-zinc-900 dark:hover:text-zinc-100'
            }`}
            style={
              mode === m.key
                ? {
                    backgroundColor: resolveModeColor(m.color),
                  }
                : undefined
            }
          >
            {m.icon}
            <span className="uppercase tracking-wider">{m.label}</span>
          </button>
        ))}

        {/* Voice Control */}
        <div className="ml-auto">
          <VoiceControl
            onVoiceInput={handleVoiceInput}
            onTTS={handleTTS}
            isListening={isListening}
            isSpeaking={isSpeaking}
            disabled={!isConnected || disabled}
          />
        </div>
      </div>

      {/* Input form */}
      <div className="relative group">
        <form onSubmit={handleSubmit} className="flex gap-4 items-end">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              mode === 'chat' ? "Nasıl yardımcı olabilirim?" :
              mode === 'code' ? "Yazmamı istediğin kodu tarif et..." :
              mode === 'research' ? "Neyi araştırmamı istersin?" :
              "Bilgisayarda hangi işlemi yapmamı istersin?"
            }
            disabled={!isConnected || disabled}
            rows={1}
            className="flex-1 bg-transparent border-none px-4 py-4 text-xl text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 dark:placeholder-zinc-500 resize-none focus:outline-none focus:ring-0 transition-all disabled:opacity-50 min-h-[60px]"
          />
          <button
            type="submit"
            disabled={!input.trim() || !isConnected || disabled}
            className="p-4 bg-purple-600 hover:bg-purple-700 disabled:bg-zinc-200 dark:disabled:bg-zinc-800 text-white rounded-2xl transition-all active:scale-90 flex items-center justify-center shadow-lg shadow-purple-500/20"
          >
            <Send className="w-6 h-6" />
          </button>
        </form>
      </div>

      {/* Status text */}
      <div className="mt-3 text-[10px] font-bold uppercase tracking-widest text-zinc-400 dark:text-zinc-600 text-center">
        {isConnected ? (
          disabled ? 'İşleniyor...' : `Enter ile gönder • Shift+Enter ile alt satır`
        ) : (
          <span className="text-red-500">Bağlantı kesildi — Ultron Core bekleniyor...</span>
        )}
      </div>
    </div>
  );
}
