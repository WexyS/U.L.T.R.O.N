export type SupportedLanguage = 'tr' | 'en';

export const LANGUAGES: Record<SupportedLanguage, string> = {
  tr: 'Türkçe',
  en: 'English',
};

export const TRANSLATIONS: Record<SupportedLanguage, Record<string, string>> = {
  tr: {
    title: "ULTRON AGI'ya hoş geldin",
    subtitle: 'Zeki, öğrenen ve sürekli gelişen yapay zeka asistanın. Ne yapmamı istersin?',
    newConversation: 'Yeni Konuşma',
    history: 'Geçmiş',
    connected: 'Bağlandı',
    disconnected: 'Bağlantı yok',
    backendWaiting: '⚠ Ultron v3.0 Engine bekleniyor...',
    sendHintConnected: 'Enter gönder  •  Shift+Enter yeni satır',
    sendHintProcessing: '⟳ İşleniyor...',
    placeholderChat: 'Nasıl yardımcı olabilirim?',
    placeholderCode: 'Yazmamı istediğin kodu tarif et...',
    placeholderResearch: 'Neyi araştırmamı istersin?',
    placeholderRpa: 'Bilgisayarda hangi işlemi yapmamı istersin?',
    modeChat: 'Chat',
    modeCode: 'Kod',
    modeResearch: 'Araştırma',
    modeRpa: 'RPA',
    sampleCode: 'Python kodumu analiz et ve optimize et:',
    sampleResearch: 'Şu konu hakkında araştır:',
    sampleImage: 'Görüntü üret:',
    sampleEmail: 'E-postalarımı kontrol et ve özetle',
    cardCodeTitle: 'Kod analizi',
    cardCodeDesc: 'Debug, optimize ve review',
    cardResearchTitle: 'Araştırma',
    cardResearchDesc: "Web'den bilgi topla",
    cardImageTitle: 'Görüntü üret',
    cardImageDesc: 'FLUX.1 ile görsel oluştur',
    cardEmailTitle: 'E-posta asistanı',
    cardEmailDesc: 'Oku, özetle, taslak yaz',
    voiceLanguageTitle: 'Ses dili',
    assistantErrorPrefix: 'Hata',
  },
  en: {
    title: 'Welcome to ULTRON AGI',
    subtitle: 'Your intelligent, learning, and self-evolving AI assistant. What can I do for you?',
    newConversation: 'New Conversation',
    history: 'History',
    connected: 'Connected',
    disconnected: 'Disconnected',
    backendWaiting: '⚠ Waiting for Ultron v3.0 engine...',
    sendHintConnected: 'Enter sends • Shift+Enter new line',
    sendHintProcessing: '⟳ Processing...',
    placeholderChat: 'How can I help you?',
    placeholderCode: 'Describe the code you want me to write...',
    placeholderResearch: 'What should I research?',
    placeholderRpa: 'Which desktop task should I perform?',
    modeChat: 'Chat',
    modeCode: 'Code',
    modeResearch: 'Research',
    modeRpa: 'RPA',
    sampleCode: 'Analyze and optimize my Python code:',
    sampleResearch: 'Research this topic:',
    sampleImage: 'Generate an image:',
    sampleEmail: 'Review and summarize my emails',
    cardCodeTitle: 'Code analysis',
    cardCodeDesc: 'Debug, optimize, and review',
    cardResearchTitle: 'Research',
    cardResearchDesc: 'Collect information from the web',
    cardImageTitle: 'Generate image',
    cardImageDesc: 'Create visuals with FLUX.1',
    cardEmailTitle: 'Email assistant',
    cardEmailDesc: 'Read, summarize, and draft emails',
    voiceLanguageTitle: 'Voice language',
    assistantErrorPrefix: 'Error',
  },
};

export function t(lang: SupportedLanguage, key: string, vars?: Record<string, string>) {
  let text = TRANSLATIONS[lang]?.[key] ?? TRANSLATIONS['en'][key] ?? key;
  if (vars) {
    Object.entries(vars).forEach(([name, value]) => {
      text = text.replace(new RegExp(`\{${name}\}`, 'g'), value);
    });
  }
  return text;
}
