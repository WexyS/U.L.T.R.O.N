import { useState, useEffect, useCallback, useRef } from 'react';
import { Mic, MicOff, Volume2, VolumeX, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// SpeechRecognition types
interface SpeechRecognitionEvent extends Event {
  resultIndex: number;
  results: SpeechRecognitionResultList;
}

interface VoiceControlProps {
  onVoiceInput?: (text: string) => void;
  onTTS?: (text: string) => void;
  isListening: boolean;
  isSpeaking: boolean;
  disabled?: boolean;
  /** Preferred language: 'tr-TR' (Turkish) or 'en-US' (English). Defaults to 'tr-TR'. */
  language?: 'tr-TR' | 'en-US';
}

export default function VoiceControl({
  onVoiceInput,
  onTTS,
  isListening,
  isSpeaking,
  disabled = false,
  language = 'tr-TR',
}: VoiceControlProps) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [recognition, setRecognition] = useState<any>(null);
  const [transcript, setTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);
  const langRef = useRef(language);

  // Keep language ref in sync
  useEffect(() => {
    langRef.current = language;
  }, [language]);

  // Initialize Speech Recognition
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const SpeechRecognition =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

      if (SpeechRecognition) {
        const recognitionInstance = new SpeechRecognition();
        recognitionInstance.continuous = true;
        recognitionInstance.interimResults = true;
        recognitionInstance.lang = language;

        recognitionInstance.onresult = (event: SpeechRecognitionEvent) => {
          let finalTranscript = '';
          let interimTranscript = '';

          for (let i = event.resultIndex; i < event.results.length; i++) {
            const t = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
              finalTranscript += t;
            } else {
              interimTranscript += t;
            }
          }

          setTranscript(interimTranscript || finalTranscript);

          if (finalTranscript.trim() && onVoiceInput) {
            onVoiceInput(finalTranscript.trim());
          }
        };

        recognitionInstance.onerror = (event: any) => {
          console.error('Speech recognition error:', event.error);
          
          const isTauri = typeof window !== 'undefined' && '__TAURI__' in window;
          const networkErrorMsg = isTauri 
            ? 'Desktop App (WebView2) does not support native Voice Recognition. Please open Ultron UI in Google Chrome.'
            : 'Speech recognition requires an internet connection. Please check your network and try again.';

          // Provide user-friendly error messages
          const errorMessages: Record<string, string> = {
            'not-allowed': 'Microphone access denied. Please allow microphone permission in your browser settings.',
            'network': networkErrorMsg,
            'no-speech': 'No speech detected. Please try again and speak clearly.',
            'audio-capture': 'No microphone found. Please ensure a microphone is connected.',
            'language-not-recognized': `Language ${language} may not be supported. Try switching to English.`,
          };
          setError(errorMessages[event.error] || `Error: ${event.error}`);
        };

        recognitionInstance.onend = () => {
          setTranscript('');
        };

        setRecognition(recognitionInstance);
      } else {
        setError('Speech recognition not supported. Try Chrome or Edge browser.');
      }
    }
  }, [onVoiceInput, language]);

  // Toggle listening
  const toggleListening = useCallback(() => {
    if (!recognition || disabled) return;

    if (isListening) {
      recognition.stop();
    } else {
      setError(null);
      // Update language before starting
      recognition.lang = langRef.current;
      try {
        recognition.start();
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : String(e);
        setError(`Failed to start: ${msg}`);
      }
    }
  }, [recognition, isListening, disabled]);

  // Toggle TTS
  const toggleSpeaking = useCallback(() => {
    if (disabled) return;

    if (isSpeaking) {
      if (onTTS) {
        onTTS(''); // Stop speaking
      }
      window.speechSynthesis.cancel();
    } else {
      // Test TTS
      const utterance = new SpeechSynthesisUtterance('Ultron activated');
      utterance.lang = language;
      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      window.speechSynthesis.speak(utterance);
    }
  }, [isSpeaking, disabled, onTTS, language]);

  return (
    <div className="flex items-center gap-2">
      {/* Language Toggle */}
      <button
        onClick={() => {
          if (isListening) recognition?.stop();
          // Language is controlled via props — this just shows current state
        }}
        className="px-2 py-1 text-xs rounded-md border transition-colors hover:opacity-80"
        style={{
          backgroundColor: 'rgb(var(--color-panel))',
          borderColor: 'rgb(var(--color-border))',
          color: 'rgb(var(--color-text-muted))',
        }}
        title={`Current: ${language === 'tr-TR' ? 'Turkish' : 'English'}. Change in InputBox.`}
        aria-label={`Voice language: ${language === 'tr-TR' ? 'Turkish' : 'English'}`}
      >
        {language === 'tr-TR' ? '🇹🇷' : '🇺🇸'}
      </button>

      {/* Voice Input Button */}
      <motion.button
        whileHover={{ scale: disabled ? 1 : 1.05 }}
        whileTap={{ scale: disabled ? 1 : 0.95 }}
        onClick={toggleListening}
        disabled={disabled}
        className={`
          relative p-2.5 rounded-full transition-all duration-200
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'hover:bg-ultron-card'}
          ${isListening ? 'bg-ultron-accent/20 ring-2 ring-ultron-accent animate-pulse' : ''}
        `}
        title={isListening ? 'Stop listening' : 'Start listening'}
      >
        <AnimatePresence mode="wait">
          {isListening ? (
            <motion.div
              key="listening"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0 }}
            >
              <Mic className="w-5 h-5 text-ultron-accent" />
            </motion.div>
          ) : (
            <motion.div
              key="idle"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0 }}
            >
              <MicOff className="w-5 h-5 text-ultron-textMuted" />
            </motion.div>
          )}
        </AnimatePresence>

        {/* Listening indicator */}
        {isListening && (
          <motion.div
            className="absolute -top-1 -right-1 w-3 h3 bg-ultron-accent rounded-full"
            animate={{ scale: [1, 1.2, 1] }}
            transition={{ duration: 1, repeat: Infinity }}
          />
        )}
      </motion.button>

      {/* Voice Output (TTS) Button */}
      <motion.button
        whileHover={{ scale: disabled ? 1 : 1.05 }}
        whileTap={{ scale: disabled ? 1 : 0.95 }}
        onClick={toggleSpeaking}
        disabled={disabled}
        className={`
          p-2.5 rounded-full transition-all duration-200
          ${disabled ? 'opacity-50 cursor-not-allowed' : 'hover:bg-ultron-card'}
          ${isSpeaking ? 'bg-ultron-accent/20 ring-2 ring-ultron-accent animate-pulse' : ''}
        `}
        title={isSpeaking ? 'Stop speaking' : 'Enable voice response'}
      >
        <AnimatePresence mode="wait">
          {isSpeaking ? (
            <motion.div
              key="speaking"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0 }}
            >
              <Volume2 className="w-5 h-5 text-ultron-accent" />
            </motion.div>
          ) : (
            <motion.div
              key="silent"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0 }}
            >
              <VolumeX className="w-5 h-5 text-ultron-textMuted" />
            </motion.div>
          )}
        </AnimatePresence>
      </motion.button>

      {/* Transcript display */}
      <AnimatePresence>
        {transcript && (
          <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -10 }}
            className="px-3 py-1.5 text-xs rounded-md bg-ultron-card border border-ultron-border max-w-xs truncate"
          >
            <span className="text-ultron-textMuted">🎤</span> {transcript}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Error display */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="px-3 py-1.5 text-xs rounded-md bg-ultron-danger/10 border border-ultron-danger/30 text-ultron-danger"
          >
            ⚠️ {error}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Loading indicator */}
      {(isListening || isSpeaking) && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex items-center gap-1 text-xs text-ultron-textMuted"
        >
          <Loader2 className="w-3 h-3 animate-spin" />
          <span>{isListening ? 'Listening...' : 'Speaking...'}</span>
        </motion.div>
      )}
    </div>
  );
}
