import { useState, useEffect, useRef, useCallback } from 'react';

export interface ChatMessage {
  id?: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
}

export interface StreamChunk {
  type: 'started' | 'token' | 'complete' | 'error' | 'tool_call' | 'thought';
  content: string;
  metadata: Record<string, any>;
}

interface ProviderEntry {
  available?: boolean;
  latency_ms?: number | string;
  stats?: {
    avg_latency_ms?: number | string;
    [key: string]: any;
  };
  [key: string]: any;
}

export interface ProvidersState {
  current: { name: string; latency_ms: number } | null;
  available: string[];
  details: Record<string, ProviderEntry>;
  raw?: any;
}

function parseLatency(value: unknown): number {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string') {
    const parsed = Number(value.replace(/[^\d.]/g, ''));
    return Number.isFinite(parsed) ? parsed : 0;
  }
  return 0;
}

function normalizeProviders(rawProviders: any, statusData: any): ProvidersState {
  let details: Record<string, ProviderEntry> = {};

  if (rawProviders && typeof rawProviders === 'object' && !Array.isArray(rawProviders)) {
    if (rawProviders.details && typeof rawProviders.details === 'object' && !Array.isArray(rawProviders.details)) {
      details = rawProviders.details;
    } else if (rawProviders.providers && typeof rawProviders.providers === 'object' && !Array.isArray(rawProviders.providers)) {
      details = rawProviders.providers;
    } else {
      details = rawProviders;
    }
  }

  if (Object.keys(details).length === 0 && statusData?.llm_providers && typeof statusData.llm_providers === 'object') {
    details = statusData.llm_providers;
  }

  const available = Object.entries(details)
    .filter(([, value]) => Boolean((value as ProviderEntry)?.available))
    .map(([name]) => name);

  const currentName = available[0] ?? Object.keys(details)[0] ?? null;
  const currentEntry = currentName ? details[currentName] : null;
  const currentLatency = parseLatency(currentEntry?.latency_ms ?? currentEntry?.stats?.avg_latency_ms);

  return {
    current: currentName ? { name: currentName, latency_ms: currentLatency } : null,
    available,
    details,
    raw: rawProviders,
  };
}

interface UseUltronOptions {
  wsUrl?: string;
  apiUrl?: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

import { API_URL, WS_URL } from '../config';

export function useUltron({
  wsUrl = WS_URL,
  apiUrl = API_URL,
  reconnectInterval = 3000,
  maxReconnectAttempts = 10
}: UseUltronOptions = {}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentResponse, setCurrentResponse] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<any>(null);
  const [providers, setProviders] = useState<ProvidersState | null>(null);
  const [workspace, setWorkspace] = useState<any>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  const responseBuffer = useRef('');

  // Poll system status
  useEffect(() => {
    const pollAll = async () => {
      try {
        const [statusRes, providersRes, workspaceRes] = await Promise.all([
          fetch(`${apiUrl}/api/v2/status`).then(r => r.ok ? r.json() : null).catch(() => null),
          fetch(`${apiUrl}/api/v2/providers`).then(r => r.ok ? r.json() : null).catch(() => null),
          fetch(`${apiUrl}/api/v2/workspace/list`).then(r => r.ok ? r.json() : null).catch(() => null),
        ]);
        if (statusRes) setStatus(statusRes);
        setProviders(normalizeProviders(providersRes, statusRes));
        if (workspaceRes) setWorkspace(workspaceRes);
      } catch {
        // Silent fail
      }
    };

    pollAll();
    const interval = setInterval(pollAll, 5000);
    return () => clearInterval(interval);
  }, [apiUrl]);

  const connect = useCallback(async () => {
    if (wsRef.current?.readyState === WebSocket.OPEN || 
        wsRef.current?.readyState === WebSocket.CONNECTING) return;

    try {
      // Pre-flight: check if backend is reachable before opening WebSocket
      try {
        const healthRes = await fetch(`${apiUrl}/health`, { signal: AbortSignal.timeout(3000) });
        if (!healthRes.ok) {
          console.log('[Ultron] Backend not ready yet, retrying...');
          if (reconnectAttempts.current < maxReconnectAttempts) {
            const delay = Math.min(reconnectInterval * Math.pow(1.5, reconnectAttempts.current), 30000);
            reconnectTimeout.current = setTimeout(() => {
              reconnectAttempts.current++;
              connect();
            }, delay);
          }
          return;
        }
      } catch {
        console.log('[Ultron] Backend not reachable, retrying...');
        if (reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.min(reconnectInterval * Math.pow(1.5, reconnectAttempts.current), 30000);
          reconnectTimeout.current = setTimeout(() => {
            reconnectAttempts.current++;
            connect();
          }, delay);
        }
        return;
      }

      console.log('[Ultron] Attempting WebSocket connection to:', wsUrl);
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[Ultron] WebSocket connected successfully');
        setIsConnected(true);
        reconnectAttempts.current = 0;
        setError(null);
      };

      ws.onclose = (event) => {
        console.log('[Ultron] WebSocket disconnected, code:', event.code, 'reason:', event.reason);
        setIsConnected(false);
        setIsStreaming(false);
        setCurrentResponse('');
        responseBuffer.current = '';

        if (reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.min(reconnectInterval * Math.pow(1.5, reconnectAttempts.current), 30000);
          console.log(`[Ultron] Reconnecting in ${delay}ms... (${reconnectAttempts.current + 1}/${maxReconnectAttempts})`);
          reconnectTimeout.current = setTimeout(() => {
            reconnectAttempts.current++;
            connect();
          }, delay);
        } else {
          setError('Connection lost. Please ensure the backend is running on port 8000.');
          console.error('[Ultron] Max reconnection attempts reached');
        }
      };

      ws.onerror = (event) => {
        console.error('[Ultron] WebSocket error:', event);
        setError('WebSocket connection failed. Is the backend running on http://localhost:8000?');
      };

      ws.onmessage = (event) => {
        try {
          const data: StreamChunk = JSON.parse(event.data);

          switch (data.type) {
            case 'started':
              responseBuffer.current = '';
              setCurrentResponse('');
              setIsStreaming(true);
              break;
            case 'token':
              responseBuffer.current += data.content;
              setCurrentResponse(responseBuffer.current);
              break;
            case 'complete':
              setIsStreaming(false);
              // Use buffer first, then data.content, then fallback
              const finalContent = responseBuffer.current || data.content || 'No response received.';
              setMessages(prev => [...prev, {
                role: 'assistant',
                content: finalContent,
                timestamp: Date.now()
              }]);
              responseBuffer.current = '';
              setCurrentResponse('');
              break;
            case 'error':
              setIsStreaming(false);
              setError(data.content || 'An error occurred');
              responseBuffer.current = '';
              setCurrentResponse('');
              break;
          }
        } catch (err) {
          console.error('[Ultron] Failed to parse message:', err, event.data);
        }
      };
    } catch (err) {
      console.error('[Ultron] Connection failed:', err);
      setError('Failed to connect to Ultron backend');
    }
  }, [wsUrl, maxReconnectAttempts, reconnectInterval]);

  const disconnect = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  const sendMessage = useCallback((text: string, mode: 'chat' | 'code' | 'research' | 'rpa' = 'chat', conversationId?: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      setError('Not connected to backend');
      return;
    }

    const userMessage: ChatMessage = {
      role: 'user',
      content: text,
      timestamp: Date.now()
    };
    setMessages(prev => [...prev, userMessage]);

    wsRef.current.send(JSON.stringify({
      message: text,
      mode,
      stream: true,
      conversation_id: conversationId,
      history: messages.slice(-10) // Send last 10 messages for context
    }));
  }, [messages]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setCurrentResponse('');
    responseBuffer.current = '';
    setError(null);
  }, []);

  // Auto-connect on mount
  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return {
    messages,
    isStreaming,
    currentResponse,
    isConnected,
    error,
    status,
    providers,
    workspace,
    sendMessage,
    clearMessages,
    setMessages,
    connect,
    disconnect
  };
}
