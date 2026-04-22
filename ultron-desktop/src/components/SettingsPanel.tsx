import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'

interface SettingsState {
  darkMode: boolean
  language: 'tr' | 'en'
  streamingEnabled: boolean
  ngrokEnabled: boolean
  ngrokUrl: string
  activeModel: string
  daemonEnabled: boolean
  promptGuard: boolean
}

interface ProviderStatus {
  name: string
  model: string
  available: boolean
  latencyMs: number
  error?: string
}

export const SettingsPanel = ({ onClose }: { onClose: () => void }) => {
  const [settings, setSettings] = useState<SettingsState>({
    darkMode: true,
    language: 'tr',
    streamingEnabled: true,
    ngrokEnabled: false,
    ngrokUrl: '',
    activeModel: 'brain',
    daemonEnabled: true,
    promptGuard: true,
  })
  
  const [providers, setProviders] = useState<ProviderStatus[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'general' | 'providers' | 'agents' | 'security' | 'training'>('general')

  useEffect(() => {
    fetch('http://localhost:8000/api/v2/providers/status')
      .then(r => r.json())
      .then(data => {
        const ps: ProviderStatus[] = Object.entries(data).map(([name, s]: [string, any]) => ({
          name,
          model: s.model || 'unknown',
          available: s.available,
          latencyMs: s.latency_ms || 0,
          error: s.error,
        }))
        setProviders(ps)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  const toggle = (key: keyof SettingsState) => {
    setSettings(prev => ({ ...prev, [key]: !prev[key] }))
  }

  const TABS = [
    { id: 'general', label: 'Genel', icon: '⚙' },
    { id: 'providers', label: 'Providerlar', icon: '🌐' },
    { id: 'agents', label: 'Ajanlar', icon: '⚡' },
    { id: 'security', label: 'Güvenlik', icon: '🔒' },
    { id: 'training', label: 'Eğitim', icon: '🧠' },
  ] as const

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      style={{
        position: 'fixed',
        top: '10%',
        left: '10%',
        right: '10%',
        bottom: '10%',
        background: 'var(--bg1)',
        border: '1px solid var(--bd)',
        borderRadius: '24px',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 200,
        boxShadow: '0 20px 80px rgba(0,0,0,0.8)',
        overflow: 'hidden'
      }}
    >
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', padding: '20px 24px',
        borderBottom: '1px solid var(--bd)', gap: 15, flexShrink: 0,
        background: 'rgba(255,255,255,0.02)'
      }}>
        <button onClick={onClose} style={{
          width: 36, height: 36, borderRadius: '10px',
          background: 'var(--bg2)', border: '1px solid var(--bd)',
          color: 'var(--t1)', cursor: 'pointer', fontSize: 18,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>←</button>
        <span style={{ fontSize: '20px', fontWeight: 700 }}>Sistem Ayarları</span>
      </div>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Sidebar Tabs */}
        <div style={{
          width: '200px',
          borderRight: '1px solid var(--bd)',
          padding: '20px 12px',
          display: 'flex',
          flexDirection: 'column',
          gap: '4px',
          background: 'rgba(0,0,0,0.2)',
          overflowY: 'auto'
        }}>
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: '12px 16px',
                borderRadius: '12px',
                border: 'none',
                background: activeTab === tab.id ? 'rgba(124,111,247,0.1)' : 'transparent',
                color: activeTab === tab.id ? 'var(--acc)' : 'var(--t3)',
                fontFamily: 'var(--font)',
                fontSize: '14px',
                fontWeight: 600,
                cursor: 'pointer',
                textAlign: 'left',
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                transition: 'all 0.2s'
              }}
            >
              <span style={{ fontSize: '18px' }}>{tab.icon}</span> {tab.label}
            </button>
          ))}
        </div>

        {/* Content Area */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '30px' }}>
          {activeTab === 'general' && (
            <div style={{ maxWidth: '600px' }}>
              <h3 style={{ marginBottom: '20px', color: 'var(--t1)' }}>Genel Tercihler</h3>
              <SettingsRow icon="🌙" title="Karanlık Tema" sub="Karanlık modu zorla" right={<Toggle on={settings.darkMode} onToggle={() => toggle('darkMode')} />} />
              <SettingsRow icon="🇹🇷" title="Türkçe Dil Desteği" sub="Arayüz dilini ayarla" right={<Toggle on={settings.language === 'tr'} onToggle={() => {}} />} />
              <SettingsRow icon="💬" title="Streaming Modu" sub="Tokenleri canlı akışla al" right={<Toggle on={settings.streamingEnabled} onToggle={() => toggle('streamingEnabled')} />} />
              <SettingsRow icon="🌐" title="Ngrok Uzaktan Erişim" sub="Mobil bağlantı için" right={<Toggle on={settings.ngrokEnabled} onToggle={() => toggle('ngrokEnabled')} />} />
            </div>
          )}

          {activeTab === 'providers' && (
            <div>
              <h3 style={{ marginBottom: '20px', color: 'var(--t1)' }}>Zeka Sağlayıcıları (Providers)</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px' }}>
                {loading ? <div style={{ color: 'var(--t3)' }}>Bağlantılar taranıyor...</div> : 
                  providers.map(p => (
                    <div key={p.name} style={{ background: 'var(--bg2)', padding: '16px', borderRadius: '16px', border: '1px solid var(--bd)' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                        <span style={{ fontWeight: 600 }}>{p.name.toUpperCase()}</span>
                        <div style={{ width: 10, height: 10, borderRadius: '50%', background: p.available ? 'var(--ac2)' : '#ff6464' }} />
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--t3)' }}>Model: {p.model}</div>
                      <div style={{ fontSize: '12px', color: p.available ? 'var(--ac2)' : '#ff6464', marginTop: '4px' }}>
                        {p.available ? `${p.latencyMs}ms Gecikme` : p.error || 'Bağlantı yok'}
                      </div>
                    </div>
                  ))
                }
              </div>
            </div>
          )}

          {activeTab === 'agents' && (
            <div>
              <h3 style={{ marginBottom: '20px', color: 'var(--t1)' }}>Aktif Ajanlar</h3>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '12px' }}>
                {[
                  { n: 'Brain', i: '🧠', s: 'Genesis 14B' },
                  { n: 'Coder', i: '⚡', s: 'SFT v3.0' },
                  { n: 'Research', i: '🔍', s: 'Web Agent' },
                  { n: 'System', i: '🖥', s: 'OS Operator' },
                  { n: 'Creative', i: '🎨', s: 'SDXL/Flux' },
                  { n: 'Memory', i: '💾', s: 'Long-term' }
                ].map(a => (
                  <div key={a.n} style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '12px', background: 'var(--bg2)', borderRadius: '12px' }}>
                    <span style={{ fontSize: '24px' }}>{a.i}</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: '14px', fontWeight: 600 }}>{a.n}</div>
                      <div style={{ fontSize: '11px', color: 'var(--t3)' }}>{a.s}</div>
                    </div>
                    <Toggle on={true} onToggle={() => {}} />
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'training' && (
            <div>
              <h3 style={{ marginBottom: '20px', color: 'var(--t1)' }}>Neural Training Progress</h3>
              <div style={{ background: 'linear-gradient(135deg, rgba(124,111,247,0.1), rgba(86,207,191,0.1))', padding: '24px', borderRadius: '24px', border: '1px solid var(--bd)' }}>
                <div style={{ fontSize: '24px', fontWeight: 800, color: 'var(--acc)', marginBottom: '10px' }}>Ultron Genesis v3.0</div>
                <div style={{ fontSize: '14px', color: 'var(--t2)', marginBottom: '20px' }}>52K Training Samples → Target: 1.3M High Quality Neural Tokens</div>
                <div style={{ height: '8px', background: 'var(--bg3)', borderRadius: '4px', overflow: 'hidden' }}>
                  <motion.div 
                    initial={{ width: 0 }}
                    animate={{ width: '42%' }}
                    transition={{ duration: 2, ease: "easeOut" }}
                    style={{ height: '100%', background: 'linear-gradient(90deg, var(--acc), var(--ac2))' }} 
                  />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '10px', fontSize: '12px', color: 'var(--t3)' }}>
                  <span>Progress: 42%</span>
                  <span>Estimated Time: 12h 45m</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}

const SettingsRow = ({ icon, title, sub, right }: { icon: string; title: string; sub: string; right: React.ReactNode }) => (
  <div style={{ display: 'flex', alignItems: 'center', padding: '16px 0', borderBottom: '1px solid var(--bd)', gap: '15px' }}>
    <span style={{ fontSize: '20px', width: '30px' }}>{icon}</span>
    <div style={{ flex: 1 }}>
      <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--t1)' }}>{title}</div>
      <div style={{ fontSize: '12px', color: 'var(--t3)' }}>{sub}</div>
    </div>
    {right}
  </div>
)

const Toggle = ({ on, onToggle }: { on: boolean; onToggle: () => void }) => (
  <div onClick={onToggle} style={{
    width: '44px', height: '24px', borderRadius: '12px', cursor: 'pointer',
    background: on ? 'var(--acc)' : 'var(--bg4)',
    display: 'flex', alignItems: 'center', padding: '2px',
    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
    boxShadow: on ? '0 0 15px rgba(124,111,247,0.4)' : 'none'
  }}>
    <div style={{
      width: '20px', height: '20px', borderRadius: '50%', background: '#fff',
      transform: on ? 'translateX(20px)' : 'translateX(0)',
      transition: 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
      boxShadow: '0 2px 5px rgba(0,0,0,0.2)'
    }} />
  </div>
)
