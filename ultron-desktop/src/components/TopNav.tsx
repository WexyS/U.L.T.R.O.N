import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

const FAVORITE_MODELS = [
  { id: 'qwen2.5:14b', name: 'Qwen 2.5 14B', badge: 'Elite' },
  { id: 'llama3:8b', name: 'Llama 3 8B', badge: 'Fast' },
  { id: 'mistral:latest', name: 'Mistral Latest', badge: 'Reliable' },
];

interface Model {
  name: string;
  size: number;
}

export const TopNav = ({ 
  onSettingsClick, 
  activeModel, 
  setActiveModel,
  temperature,
  setTemperature 
}: { 
  onSettingsClick: () => void;
  activeModel: string;
  setActiveModel: (m: string) => void;
  temperature: number;
  setTemperature: (t: number) => void;
}) => {
  const [showModels, setShowModels] = useState(false);
  const [ollamaModels, setOllamaModels] = useState<Model[]>([]);
  const [fetching, setFetching] = useState(false);

  useEffect(() => {
    if (showModels && ollamaModels.length === 0 && !fetching) {
      setFetching(true);
      fetch('http://127.0.0.1:11434/api/tags')
        .then(res => res.json())
        .then(data => {
          if (data.models) {
            setOllamaModels(data.models);
          }
        })
        .catch(err => console.error("Ollama API tags fetch error:", err))
        .finally(() => setFetching(false));
    }
  }, [showModels]);

  const handleModelSelect = (modelName: string) => {
    setActiveModel(modelName);
    setShowModels(false);
    // Notify Backend
    fetch('http://localhost:8000/api/v2/config/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: modelName })
    }).catch(() => {});
  };

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '12px 24px',
      background: 'rgba(10, 7, 18, 0.7)',
      backdropFilter: 'blur(16px)',
      borderBottom: '1px solid var(--bd)',
      zIndex: 100,
      position: 'relative'
    }}>
      {/* Logo & Version */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{
          width: 32, height: 32, borderRadius: 8,
          background: 'linear-gradient(135deg, var(--acc), var(--acc2))',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 0 15px var(--acc-glow)'
        }}>
          <span style={{ color: '#fff', fontWeight: 900, fontSize: 18 }}>U</span>
        </div>
        <div>
          <div style={{ fontWeight: 800, fontSize: 16, letterSpacing: '0.5px', color: 'var(--t1)' }}>ULTRON</div>
          <div style={{ fontSize: 10, color: 'var(--acc2)', fontWeight: 600, letterSpacing: '1px' }}>AGI v3.0 ELITE</div>
        </div>
      </div>

      {/* Model & Temp Controls */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
        {/* Model Selector */}
        <div style={{ position: 'relative' }}>
          <button 
            onClick={() => setShowModels(!showModels)}
            style={{
              background: 'var(--bg2)',
              border: '1px solid var(--bd)',
              padding: '6px 16px',
              borderRadius: 20,
              color: 'var(--t1)',
              fontSize: 13,
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              cursor: 'pointer',
              transition: 'all 0.2s',
              boxShadow: showModels ? '0 0 10px var(--acc-glow)' : 'none'
            }}
          >
            <span style={{ color: 'var(--acc)' }}>⚡</span>
            {activeModel}
            <span style={{ fontSize: 10, opacity: 0.5 }}>▼</span>
          </button>

          <AnimatePresence>
            {showModels && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 10 }}
                style={{
                  position: 'absolute',
                  top: '100%',
                  marginTop: 8,
                  right: 0,
                  width: 280,
                  background: 'var(--bg1)',
                  border: '1px solid var(--bd)',
                  borderRadius: 16,
                  overflow: 'hidden',
                  boxShadow: '0 20px 40px rgba(0,0,0,0.8)',
                  zIndex: 200
                }}
              >
                <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--bd2)', fontSize: 11, fontWeight: 700, color: 'var(--t3)', letterSpacing: 1 }}>FAVORİLER</div>
                {FAVORITE_MODELS.map(m => (
                  <div 
                    key={m.id} 
                    onClick={() => handleModelSelect(m.id)}
                    style={{
                      padding: '12px 16px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      cursor: 'pointer',
                      background: activeModel === m.id ? 'var(--bg3)' : 'transparent',
                      borderLeft: activeModel === m.id ? '3px solid var(--acc)' : '3px solid transparent'
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = 'var(--bg3)'}
                    onMouseLeave={e => e.currentTarget.style.background = activeModel === m.id ? 'var(--bg3)' : 'transparent'}
                  >
                    <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--t1)' }}>{m.name}</span>
                    <span style={{ fontSize: 10, padding: '2px 6px', background: 'var(--bg4)', borderRadius: 4, color: 'var(--acc)' }}>{m.badge}</span>
                  </div>
                ))}
                
                <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--bd2)', borderTop: '1px solid var(--bd2)', fontSize: 11, fontWeight: 700, color: 'var(--t3)', letterSpacing: 1 }}>
                  YEREL MODELLER (OLLAMA)
                </div>
                <div style={{ maxHeight: 200, overflowY: 'auto' }}>
                  {fetching && <div style={{ padding: 16, fontSize: 12, color: 'var(--t3)' }}>Yükleniyor...</div>}
                  {ollamaModels.map(m => (
                    <div 
                      key={m.name} 
                      onClick={() => handleModelSelect(m.name)}
                      style={{
                        padding: '10px 16px',
                        cursor: 'pointer',
                        fontSize: 13,
                        color: activeModel === m.name ? 'var(--acc)' : 'var(--t2)',
                        background: activeModel === m.name ? 'var(--bg3)' : 'transparent',
                        borderLeft: activeModel === m.name ? '3px solid var(--acc)' : '3px solid transparent'
                      }}
                      onMouseEnter={e => e.currentTarget.style.background = 'var(--bg3)'}
                      onMouseLeave={e => e.currentTarget.style.background = activeModel === m.name ? 'var(--bg3)' : 'transparent'}
                    >
                      {m.name}
                    </div>
                  ))}
                  <div 
                    onClick={() => {
                      alert('Terminalden yeni model indirmek için komut paletini (Ctrl+K) kullanabilirsiniz.');
                      setShowModels(false);
                    }}
                    style={{
                      padding: '12px 16px', cursor: 'pointer', fontSize: 12, fontWeight: 600, color: 'var(--acc2)',
                      textAlign: 'center', borderTop: '1px solid var(--bd)'
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = 'var(--bg3)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    + Yeni Model İndir
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Temperature Slider */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, background: 'var(--bg2)', padding: '6px 16px', borderRadius: 20, border: '1px solid var(--bd)' }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--t2)' }}>Creativity</span>
          <input 
            type="range" 
            min="0" 
            max="1" 
            step="0.1" 
            value={temperature}
            onChange={(e) => setTemperature(parseFloat(e.target.value))}
            style={{ width: 80, accentColor: 'var(--acc2)' }}
          />
          <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--acc2)', width: 24 }}>{temperature.toFixed(1)}</span>
        </div>

        {/* Settings Button */}
        <button 
          onClick={onSettingsClick}
          style={{
            width: 36, height: 36, borderRadius: '50%',
            background: 'var(--bg2)', border: '1px solid var(--bd)',
            display: 'flex', alignItems: 'center', justifyItems: 'center', justifyContent: 'center',
            cursor: 'pointer', color: 'var(--t2)', transition: 'all 0.2s'
          }}
          onMouseEnter={e => { e.currentTarget.style.color = 'var(--t1)'; e.currentTarget.style.boxShadow = '0 0 10px var(--acc-glow)' }}
          onMouseLeave={e => { e.currentTarget.style.color = 'var(--t2)'; e.currentTarget.style.boxShadow = 'none' }}
        >
          ⚙
        </button>
      </div>
    </div>
  );
};
