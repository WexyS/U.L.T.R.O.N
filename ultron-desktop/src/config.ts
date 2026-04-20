// API Configuration
// Use relative path for API so it goes through Vite proxy (handles LAN and HTTPS Mixed Content)
export const API_URL = import.meta.env.VITE_API_URL || '';

// Dynamically build WS URL based on current host and protocol
const getWsUrl = () => {
  if (typeof window === 'undefined') return 'ws://localhost:8000/ws/chat';
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  // Use Vite's proxy for WebSockets too
  return import.meta.env.VITE_WS_URL || `${protocol}//${window.location.host}/ws/chat`;
};

export const WS_URL = getWsUrl();

// Feature flags
export const FEATURES = {
  voiceEnabled: true,
  streamingEnabled: true,
  multiConversation: true,
  fileUploads: false, // Future feature
};
