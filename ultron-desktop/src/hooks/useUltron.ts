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

interface UseUltronOptions {
  wsUrl?: string;
  apiUrl?: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

export function useUltron({
  wsUrl = 'ws://localhost:8000/ws/chat',
  apiUrl = 'http://localhost:8000',
  reconnectInterval = 3000,
  maxReconnectAttempts = 10
}: UseUltronOptions = {}) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentResponse, setCurrentResponse] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<any>(null);
  const [providers, setProviders] = useState<any>(null);
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
          fetch(`${apiUrl}/status`).then(r => r.ok ? r.json() : null),
          fetch(`${apiUrl}/providers`).then(r => r.ok ? r.json() : null),
          fetch(`${apiUrl}/api/v2/workspace/list`).then(r => r.ok ? r.json() : null).catch(() => null),
        ]);
        if (statusRes) setStatus(statusRes);
        if (providersRes) setProviders(providersRes);
        if (workspaceRes) setWorkspace(workspaceRes);
      } catch {
        // Silent fail
      }
    };

    pollAll();
    const interval = setInterval(pollAll, 5000);
    return () => clearInterval(interval);
  }, [apiUrl]);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[Ultron] WebSocket connected');
        setIsConnected(true);
        reconnectAttempts.current = 0;
        setError(null);
      };

      ws.onclose = () => {
        console.log('[Ultron] WebSocket disconnected');
        setIsConnected(false);
        setIsStreaming(false);

        if (reconnectAttempts.current < maxReconnectAttempts) {
          reconnectTimeout.current = setTimeout(() => {
            reconnectAttempts.current++;
            console.log(`[Ultron] Reconnecting... (${reconnectAttempts.current}/${maxReconnectAttempts})`);
            connect();
          }, reconnectInterval);
        } else {
          setError('Connection lost. Please check if the backend is running.');
        }
      };

      ws.onerror = () => {
        console.error('[Ultron] WebSocket error');
        setError('WebSocket error occurred');
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

  const sendMessage = useCallback((text: string, mode: 'chat' | 'code' | 'research' | 'rpa' = 'chat') => {
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
      stream: true
    }));
  }, []);

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
    connect,
    disconnect
  };
}
