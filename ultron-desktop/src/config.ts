// API Configuration
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/chat';

// Feature flags
export const FEATURES = {
  voiceEnabled: true,
  streamingEnabled: true,
  multiConversation: false, // Future feature
  fileUploads: false, // Future feature
};
