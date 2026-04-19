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
    <div className="border-t border-ultron-border bg-ultron-panel p-4 backdrop-blur-sm">
      {/* Mode selector */}
      <div className="flex items-center gap-2 mb-3">
        {MODES.map((m) => (
          <button
            key={m.key}
            onClick={() => setMode(m.key)}
            disabled={!isConnected}
            title={`${m.label} moduna geç`}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
              mode === m.key
                ? 'text-white shadow-lg'
                : 'bg-ultron-bg border border-ultron-border text-ultron-textMuted hover:text-white hover:border-ultron-primary/50'
            }`}
            style={
              mode === m.key
                ? {
                    backgroundColor: resolveModeColor(m.color),
                    boxShadow: `0 8px 20px ${resolveModeColor(m.color)}33`,
                  }
                : undefined
            }
          >
            {m.icon}
            {m.label}
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
      <form onSubmit={handleSubmit} className="flex gap-3">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            mode === 'chat' ? "Bana istediğini sor..." :
            mode === 'code' ? "Yazmamı istediğin kodu tarif et..." :
            mode === 'research' ? "Neyi araştırmamı istersin?" :
            "Bilgisayarda hangi işlemi yapmamı istersin?"
          }
          disabled={!isConnected || disabled}
          rows={1}
          className="flex-1 bg-ultron-bg border border-ultron-border rounded-xl px-4 py-3 text-ultron-text placeholder-ultron-textMuted/50 resize-none focus:outline-none focus:border-ultron-primary/50 focus:ring-1 focus:ring-ultron-primary/20 transition-all disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!input.trim() || !isConnected || disabled}
          title="Mesajı gönder"
          className="px-6 py-3 bg-ultron-primary hover:bg-ultron-primary/80 disabled:bg-ultron-border disabled:text-ultron-textMuted/50 text-white font-medium rounded-xl transition-all disabled:cursor-not-allowed shadow-lg shadow-ultron-primary/20"
        >
          <Send className="w-5 h-5" />
        </button>
      </form>

      {/* Status text */}
      <div className="mt-2 text-xs text-ultron-textMuted/50 text-center">
        {isConnected ? (
          disabled ? 'İşleniyor...' : `Göndermek için Enter, yeni satır için Shift+Enter`
        ) : (
          <span className="text-ultron-danger">Bağlantı yok — backend bekleniyor...</span>
        )}
      </div>
    </div>
  );
}
