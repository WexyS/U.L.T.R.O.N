import { useRef, useEffect, useState } from 'react';
import { User, Bot, Volume2, VolumeX } from 'lucide-react';
import StreamingMessage from './StreamingMessage';
import type { ChatMessage } from '../hooks/useUltron';

interface ChatAreaProps {
  messages: ChatMessage[];
  currentResponse: string;
  isStreaming: boolean;
}

export default function ChatArea({ messages, currentResponse, isStreaming }: ChatAreaProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const [speakingId, setSpeakingId] = useState<number | null>(null);
  const [audioElement, setAudioElement] = useState<HTMLAudioElement | null>(null);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentResponse]);

  // Cleanup audio on unmount
  useEffect(() => {
    return () => {
      audioElement?.pause();
    };
  }, [audioElement]);

  const speakMessage = async (text: string, idx: number) => {
    // Stop current speech
    if (audioElement) {
      audioElement.pause();
      setAudioElement(null);
      setSpeakingId(null);
      return;
    }

    try {
      const res = await fetch('http://localhost:8000/api/v2/tts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text.substring(0, 2000), language: 'en' }),
      });

      if (!res.ok) throw new Error('TTS failed');

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const audio = new Audio(url);
      audio.onended = () => {
        setSpeakingId(null);
        setAudioElement(null);
      };
      audio.onerror = () => {
        setSpeakingId(null);
        setAudioElement(null);
      };
      setAudioElement(audio);
      setSpeakingId(idx);
      await audio.play();
    } catch (err) {
      console.error('TTS error:', err);
      setSpeakingId(null);
      setAudioElement(null);
    }
  };

  return (
    <div 
      ref={chatContainerRef}
      className="flex-1 overflow-y-auto p-6 space-y-6 scroll-smooth"
    >
      {messages.length === 0 && !currentResponse ? (
        <div className="flex flex-col items-center justify-center h-full text-center">
          <div className="relative mb-6">
            <div className="w-24 h-24 rounded-full border-2 border-ultron-primary/30 flex items-center justify-center animate-pulse-slow">
              <div className="w-16 h-16 rounded-full bg-ultron-primary/10 flex items-center justify-center">
                <Bot className="w-8 h-8 text-ultron-primary" />
              </div>
            </div>
            <div className="absolute -inset-2 rounded-full border border-ultron-primary/20 animate-spin-slow" />
          </div>
          <h2 className="text-2xl font-semibold mb-2" style={{ color: 'var(--color-text)' }}>Ultron v2.0</h2>
          <p className="max-w-md" style={{ color: 'var(--color-text-secondary)' }}>
            Your personal AI assistant is ready. Ask me anything, write code, conduct research, or control your system.
          </p>
          <div className="mt-8 grid grid-cols-2 gap-3 text-sm">
            <div className="p-3 rounded-lg border text-sm" style={{ backgroundColor: 'var(--color-card)', borderColor: 'var(--color-border)', color: 'var(--color-text-secondary)' }}>
              💬 General chat & questions
            </div>
            <div className="p-3 rounded-lg border text-sm" style={{ backgroundColor: 'var(--color-card)', borderColor: 'var(--color-border)', color: 'var(--color-text-secondary)' }}>
              💻 Code generation & debugging
            </div>
            <div className="p-3 rounded-lg border text-sm" style={{ backgroundColor: 'var(--color-card)', borderColor: 'var(--color-border)', color: 'var(--color-text-secondary)' }}>
              🔍 Deep research & analysis
            </div>
            <div className="p-3 rounded-lg border text-sm" style={{ backgroundColor: 'var(--color-card)', borderColor: 'var(--color-border)', color: 'var(--color-text-secondary)' }}>
              🖥️ System control & RPA
            </div>
          </div>
        </div>
      ) : (
        <>
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex gap-4 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
            >
              <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                msg.role === 'user' 
                  ? 'bg-ultron-primary/20 border border-ultron-primary/50' 
                  : 'bg-ultron-accent/10 border border-ultron-accent/50'
              }`}>
                {msg.role === 'user' ? (
                  <User className="w-4 h-4 text-ultron-primary" />
                ) : (
                  <Bot className="w-4 h-4 text-ultron-accent" />
                )}
              </div>
              
              <div className={`flex-1 max-w-3xl ${msg.role === 'user' ? 'text-right' : ''}`}>
                {msg.role === 'user' ? (
                  <div className="inline-block px-4 py-3 rounded-2xl bg-ultron-panel border border-ultron-border text-left">
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                  </div>
                ) : (
                  <div className="text-left flex items-start gap-2">
                    <div className="flex-1">
                      <StreamingMessage content={msg.content} />
                    </div>
                    <button
                      onClick={() => speakMessage(msg.content, idx)}
                      className={`flex-shrink-0 p-1.5 rounded-md transition-colors mt-1 ${
                        speakingId === idx
                          ? 'bg-ultron-primary/20 text-ultron-primary'
                          : 'text-ultron-textMuted hover:text-ultron-primary hover:bg-ultron-card'
                      }`}
                      title={speakingId === idx ? 'Stop speaking' : 'Speak this message'}
                    >
                      {speakingId === idx ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Streaming response */}
          {currentResponse && (
            <div className="flex gap-4">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-ultron-accent/10 border border-ultron-accent/50 flex items-center justify-center">
                <Bot className="w-4 h-4 text-ultron-accent" />
              </div>
              <div className="flex-1 max-w-3xl">
                <StreamingMessage content={currentResponse} isStreaming={isStreaming} />
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </>
      )}
    </div>
  );
}
