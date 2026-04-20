import { useRef, useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  User, Bot, Volume2, VolumeX, Copy, Check, RotateCcw,
  Edit2, Share2, ThumbsUp, ThumbsDown, Clock, Zap
} from 'lucide-react';
import StreamingMessage from './StreamingMessage';
import type { ChatMessage } from '../hooks/useUltron';
import { API_URL } from '../config';

interface ChatAreaProps {
  messages: ChatMessage[];
  currentResponse: string;
  isStreaming: boolean;
  isProcessing?: boolean;
  model?: string;
  latency?: number;
}

export default function ChatArea({ 
  messages, 
  currentResponse, 
  isStreaming,
  isProcessing = false,
  model = 'Ollama',
  latency = 0
}: ChatAreaProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const [speakingId, setSpeakingId] = useState<number | null>(null);
  const [audioElement, setAudioElement] = useState<HTMLAudioElement | null>(null);
  const [copiedId, setCopiedId] = useState<number | null>(null);
  const [feedbackGiven, setFeedbackGiven] = useState<{[key: number]: 'up' | 'down' | null}>({});

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, currentResponse]);

  // Cleanup audio on unmount
  useEffect(() => {
    return () => {
      if (audioElement) {
        audioElement.pause();
        URL.revokeObjectURL(audioElement.src);
      }
    };
  }, []);

  const speakMessage = async (text: string, idx: number) => {
    // Stop current speech
    if (audioElement) {
      audioElement.pause();
      URL.revokeObjectURL(audioElement.src);
      setAudioElement(null);
      setSpeakingId(null);
      return;
    }

    try {
      const res = await fetch(`${API_URL}/api/v2/tts`, {
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

  const copyMessage = useCallback(async (content: string, idx: number) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedId(idx);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      console.error('Copy failed:', err);
    }
  }, []);

  const handleFeedback = useCallback((idx: number, type: 'up' | 'down') => {
    setFeedbackGiven(prev => ({ ...prev, [idx]: type }));
  }, []);

  const formatTimestamp = (timestamp: number) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div
      ref={chatContainerRef}
      className="flex-1 overflow-y-auto scroll-smooth"
      style={{ backgroundColor: 'rgb(var(--color-bg))' }}
    >
      <div className="max-w-5xl mx-auto px-6 py-10 space-y-8">
        {messages.length === 0 && !currentResponse ? (
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="flex flex-col items-center justify-center min-h-[60vh] text-center"
          >
            <motion.h2 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="text-6xl font-bold mb-6 font-serif tracking-tight text-zinc-900 dark:text-zinc-100"
            >
              Good afternoon, Eren
            </motion.h2>
            <motion.p 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="max-w-2xl text-2xl mb-12 text-zinc-500 dark:text-zinc-400 font-medium"
            >
              How can I help you today?
            </motion.p>

            {/* Capability Cards */}
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
              className="grid grid-cols-2 md:grid-cols-4 gap-4 w-full max-w-2xl"
            >
              {[
                { icon: '💬', title: 'Chat', desc: 'Natural conversation' },
                { icon: '💻', title: 'Code', desc: 'Write & debug' },
                { icon: '🔍', title: 'Research', desc: 'Deep analysis' },
                { icon: '🤖', title: 'Agents', desc: 'Multi-agent tasks' },
              ].map((item, i) => (
                <motion.div
                  key={item.title}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.4 + i * 0.1 }}
                  whileHover={{ scale: 1.05, y: -2 }}
                  className="p-4 rounded-xl border cursor-pointer transition-all"
                  style={{ 
                    backgroundColor: 'rgb(var(--color-card))', 
                    borderColor: 'rgb(var(--color-border))'
                  }}
                >
                  <div className="text-2xl mb-2">{item.icon}</div>
                  <div className="font-semibold text-sm" style={{ color: 'rgb(var(--color-text))' }}>{item.title}</div>
                  <div className="text-xs" style={{ color: 'rgb(var(--color-text-muted))' }}>{item.desc}</div>
                </motion.div>
              ))}
            </motion.div>

            {/* Model Info */}
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.8 }}
              className="mt-12 flex items-center gap-2 text-xs"
              style={{ color: 'rgb(var(--color-text-muted))' }}
            >
              <Zap className="w-3 h-3" />
              <span>Powered by {model}</span>
              <span>•</span>
              <span>Latency: {latency}ms</span>
            </motion.div>
          </motion.div>
        ) : (
          <>
            {/* Messages List */}
            <AnimatePresence initial={false}>
              {messages.map((msg, idx) => (
                <motion.div
                  key={msg.id || `msg-${idx}-${msg.timestamp}`}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                  className="group relative"
                >
                  <div className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    {/* Assistant Avatar */}
                    {msg.role === 'assistant' && (
                      <div className="flex-shrink-0 mt-1">
                        <div className="w-8 h-8 rounded-full flex items-center justify-center bg-purple-100 dark:bg-purple-500/20">
                          <Bot className="w-5 h-5 text-purple-600 dark:text-purple-400" strokeWidth={1.5} />
                        </div>
                      </div>
                    )}

                    {/* Message Content */}
                    <div className={`flex-1 max-w-[85%] lg:max-w-3xl ${msg.role === 'user' ? 'order-1' : ''}`}>
                      <div
                        className={
                          msg.role === 'user'
                            ? 'message-bubble-user ml-auto'
                            : 'message-bubble-assistant'
                        }
                      >
                        <div className="prose prose-sm lg:prose-base max-w-none dark:prose-invert">
                          {msg.role === 'user' ? (
                            <p className="whitespace-pre-wrap">{msg.content}</p>
                          ) : (
                            <StreamingMessage content={msg.content} />
                          )}
                        </div>
                      </div>

                      {/* Message Actions */}
                      <motion.div 
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className={`flex items-center gap-2 mt-2 ${
                          msg.role === 'user' ? 'justify-end' : 'justify-start'
                        } opacity-0 group-hover:opacity-100 transition-opacity`}
                      >
                        {/* Timestamp */}
                        <div className="flex items-center gap-1 text-xs" style={{ color: 'rgb(var(--color-text-muted))' }}>
                          <Clock className="w-3 h-3" />
                          <span>{formatTimestamp(msg.timestamp)}</span>
                        </div>

                        {msg.role === 'assistant' && (
                          <>
                            {/* Copy Button */}
                            <button
                              onClick={() => copyMessage(msg.content, idx)}
                              className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                              title="Copy message"
                            >
                              {copiedId === idx ? (
                                <Check className="w-3.5 h-3.5 text-green-500" />
                              ) : (
                                <Copy className="w-3.5 h-3.5" style={{ color: 'rgb(var(--color-text-muted))' }} />
                              )}
                            </button>

                            {/* Regenerate Button */}
                            <button
                              className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                              title="Regenerate response"
                            >
                              <RotateCcw className="w-3.5 h-3.5" style={{ color: 'rgb(var(--color-text-muted))' }} />
                            </button>

                            {/* TTS Button */}
                            <button
                              onClick={() => speakMessage(msg.content, idx)}
                              className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                              title={speakingId === idx ? 'Stop speaking' : 'Speak message'}
                            >
                              {speakingId === idx ? (
                                <VolumeX className="w-3.5 h-3.5 text-ultron-primary" />
                              ) : (
                                <Volume2 className="w-3.5 h-3.5" style={{ color: 'rgb(var(--color-text-muted))' }} />
                              )}
                            </button>

                            {/* Feedback Buttons */}
                            <div className="flex gap-1 ml-2">
                              <button
                                onClick={() => handleFeedback(idx, 'up')}
                                className={`p-1.5 rounded-lg transition-colors ${
                                  feedbackGiven[idx] === 'up' 
                                    ? 'bg-green-100 dark:bg-green-900/30' 
                                    : 'hover:bg-gray-100 dark:hover:bg-gray-800'
                                }`}
                                title="Helpful"
                              >
                                <ThumbsUp className={`w-3.5 h-3.5 ${
                                  feedbackGiven[idx] === 'up' ? 'text-green-500' : ''
                                }`} style={{ color: feedbackGiven[idx] === 'up' ? undefined : 'rgb(var(--color-text-muted))' }} />
                              </button>
                              <button
                                onClick={() => handleFeedback(idx, 'down')}
                                className={`p-1.5 rounded-lg transition-colors ${
                                  feedbackGiven[idx] === 'down' 
                                    ? 'bg-red-100 dark:bg-red-900/30' 
                                    : 'hover:bg-gray-100 dark:hover:bg-gray-800'
                                }`}
                                title="Not helpful"
                              >
                                <ThumbsDown className={`w-3.5 h-3.5 ${
                                  feedbackGiven[idx] === 'down' ? 'text-red-500' : ''
                                }`} style={{ color: feedbackGiven[idx] === 'down' ? undefined : 'rgb(var(--color-text-muted))' }} />
                              </button>
                            </div>
                          </>
                        )}
                      </motion.div>
                    </div>

                    {/* User Avatar */}
                    {msg.role === 'user' && (
                      <div className="flex-shrink-0 mt-1 hidden">
                        {/* Hidden to match Claude's cleaner look without user avatars */}
                      </div>
                    )}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>

            {/* Streaming Response */}
            {isStreaming && currentResponse && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex gap-4"
              >
                <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 bg-purple-100 dark:bg-purple-500/20 mt-1">
                  <Bot className="w-5 h-5 text-purple-600 dark:text-purple-400" strokeWidth={1.5} />
                </div>
                <div className="flex-1 max-w-3xl">
                  <div className="message-bubble-assistant">
                    <div className="prose prose-sm lg:prose-base max-w-none dark:prose-invert">
                      <StreamingMessage content={currentResponse} isStreaming={true} />
                    </div>
                  </div>
                  {/* Streaming indicator */}
                  <div className="flex items-center gap-2 px-0 text-[10px] font-bold uppercase tracking-widest text-purple-600 dark:text-purple-400">
                    <motion.div
                      animate={{ opacity: [0.3, 1, 0.3] }}
                      transition={{ duration: 1.5, repeat: Infinity }}
                      className="w-1.5 h-1.5 rounded-full bg-purple-600 dark:bg-purple-400"
                    />
                    <span>Generating...</span>
                  </div>
                </div>
              </motion.div>
            )}

            {/* Processing Indicator (no tokens yet) */}
            {isProcessing && !currentResponse && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex gap-4"
              >
                <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 bg-indigo-600 shadow-sm">
                  <Bot className="w-5 h-5 text-white" strokeWidth={1.5} />
                </div>
                <div className="flex-1 max-w-3xl">
                  <div className="px-6 py-4">
                    <div className="flex items-center gap-1.5">
                      {[0, 1, 2].map(i => (
                        <motion.div
                          key={i}
                          className="w-2 h-2 rounded-full bg-indigo-500/40"
                          animate={{ scale: [1, 1.5, 1], opacity: [0.4, 1, 0.4] }}
                          transition={{ 
                            duration: 1, 
                            repeat: Infinity, 
                            delay: i * 0.2,
                            ease: "easeInOut"
                          }}
                        />
                      ))}
                    </div>
                  </div>
                </div>
              </motion.div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
}
