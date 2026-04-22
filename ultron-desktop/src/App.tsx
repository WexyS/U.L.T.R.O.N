import { useState, useEffect, useRef, useCallback } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'

// ── TYPES ──────────────────────────────────────────────────
interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  thinking?: string
  steps?: { label: string; status: 'done' | 'active' | 'pending' }[]
  timestamp: Date
}

interface Conversation {
  id: string
  title: string
  messages: Message[]
  color: string
  isNew?: boolean
}

interface Agent {
  name: string
  status: 'running' | 'ready' | 'idle' | 'error'
}

// ── CONSTANTS ─────────────────────────────────────────────
const SAMPLE_CONVERSATIONS: Conversation[] = [
  {
    id: 'c1',
    title: 'Python bug analizi ve fix',
    color: '#7c6ff7',
    messages: [],
  },
  { id: 'c2', title: 'Veri seti hazırlama', color: '#56cfbf', messages: [], isNew: true },
  { id: 'c3', title: 'FLUX görüntü üretme', color: '#e879a0', messages: [] },
  { id: 'c4', title: 'Sistem optimizasyonu', color: 'var(--t4)', messages: [] },
  { id: 'c5', title: 'E-posta özetleme', color: 'var(--t4)', messages: [] },
]

const WELCOME_CARDS = [
  { icon: '💻', title: 'Kod analizi', desc: 'Debug, optimize ve review', prompt: 'Python kodumu analiz et ve optimize et: ' },
  { icon: '🔍', title: 'Araştırma', desc: "Web'den bilgi topla", prompt: 'Şu konu hakkında araştır: ' },
  { icon: '🎨', title: 'Görüntü üret', desc: 'FLUX.1 ile görsel oluştur', prompt: 'Görüntü üret: ' },
  { icon: '📧', title: 'E-posta asistanı', desc: 'Oku, özetle, taslak yaz', prompt: 'E-postalarımı kontrol et ve özetle' },
]

// ── HOOKS ─────────────────────────────────────────────────
function useWebSocket(url: string) {
  const ws = useRef<WebSocket | null>(null)
  const [connected, setConnected] = useState(false)

  const send = useCallback((data: object) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(data))
    }
  }, [])

  useEffect(() => {
    const connect = () => {
      try {
        ws.current = new WebSocket(url)
        ws.current.onopen  = () => setConnected(true)
        ws.current.onclose = () => { setConnected(false); setTimeout(connect, 3000) }
        ws.current.onerror = () => ws.current?.close()
      } catch { /* WebSocket yoksa mock mode */ }
    }
    connect()
    return () => ws.current?.close()
  }, [url])

  return { send, connected, ws }
}

// ── COMPONENTS ────────────────────────────────────────────

// TypingDots
const TypingDots = () => (
  <div style={{ display: 'flex', gap: 5, padding: '12px 4px', alignItems: 'center' }}>
    {[0, 1, 2].map(i => (
      <div key={i} style={{
        width: 8, height: 8, borderRadius: '50%',
        background: i === 0 ? 'var(--acc)' : `rgba(124,111,247,${0.6 - i * 0.25})`,
        animation: `typBounce 1.3s ${i * 0.15}s ease-in-out infinite`,
      }} />
    ))}
  </div>
)

// ReActSteps
const ReActSteps = ({ steps }: { steps: Message['steps'] }) => (
  <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap', marginBottom: 12 }}>
    {steps?.map((s, i) => (
      <span key={i} style={{
        padding: '3px 9px', borderRadius: 20, fontSize: 10, fontWeight: 600,
        letterSpacing: 0.4, display: 'flex', alignItems: 'center', gap: 4,
        background: s.status === 'done' ? 'rgba(86,207,191,0.1)'
          : s.status === 'active' ? 'rgba(124,111,247,0.15)'
          : 'var(--bg2)',
        color: s.status === 'done' ? 'var(--acc2)'
          : s.status === 'active' ? '#9d94ff'
          : 'var(--t4)',
        border: `1px solid ${s.status === 'done' ? 'rgba(86,207,191,0.2)'
          : s.status === 'active' ? 'rgba(124,111,247,0.3)'
          : 'var(--bd)'}`,
      }}>
        {s.status === 'done' ? '✓' : s.status === 'active' ? '⟳' : ''}
        {s.label}
      </span>
    ))}
  </div>
)

// ThinkBlock
const ThinkBlock = ({ content }: { content: string }) => (
  <div style={{
    marginBottom: 12, padding: '10px 13px',
    background: 'rgba(124,111,247,0.05)',
    borderLeft: '2px solid rgba(124,111,247,0.4)',
    borderRadius: '0 8px 8px 0',
  }}>
    <div style={{
      fontSize: 10, color: 'var(--acc)', fontWeight: 600,
      letterSpacing: 0.8, marginBottom: 5, display: 'flex', gap: 5,
    }}>
      ◈ DÜŞÜNCE SÜRECİ
    </div>
    <div style={{ fontSize: 12, color: 'var(--t3)', fontFamily: 'var(--mono)', lineHeight: 1.6 }}>
      {content}
    </div>
  </div>
)

// CodeBlock
const CodeBlock = ({ language, children }: { language: string; children: string }) => {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard.writeText(children)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }
  return (
    <div style={{
      background: 'var(--bg2)', border: '1px solid var(--bd)',
      borderRadius: 10, overflow: 'hidden', margin: '12px 0',
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '8px 13px', borderBottom: '1px solid var(--bd)',
        background: 'rgba(255,255,255,0.02)',
      }}>
        <span style={{ fontSize: 11, color: 'var(--t3)', fontFamily: 'var(--mono)', fontWeight: 500 }}>
          {language || 'code'}
        </span>
        <button onClick={copy} style={{
          fontSize: 11, color: copied ? 'var(--acc2)' : 'var(--t3)',
          background: 'none', border: 'none', cursor: 'pointer', fontFamily: 'var(--font)',
          transition: 'color .15s',
        }}>
          {copied ? '✓ Kopyalandı' : '📋 Kopyala'}
        </button>
      </div>
      <SyntaxHighlighter
        language={language || 'text'}
        style={vscDarkPlus}
        customStyle={{ margin: 0, padding: 14, background: 'transparent', fontSize: 12.5 }}
      >
        {children}
      </SyntaxHighlighter>
    </div>
  )
}

// MessageBubble
const MessageBubble = ({ msg }: { msg: Message }) => {
  const isUser = msg.role === 'user'
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      style={{
        display: 'flex', gap: 12, flexDirection: isUser ? 'row-reverse' : 'row',
      }}
    >
      {/* Avatar */}
      <div style={{
        width: 32, height: 32, borderRadius: 9, flexShrink: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 13, fontWeight: 600,
        background: isUser
          ? 'linear-gradient(135deg,#e879a0,#7c6ff7)'
          : 'linear-gradient(135deg,#1e1e27,#2a2a38)',
        border: isUser ? 'none' : '1px solid rgba(124,111,247,0.3)',
        color: isUser ? '#fff' : 'var(--acc)',
      }}>
        {isUser ? 'E' : '⚡'}
      </div>

      {/* Content */}
      <div style={{ maxWidth: 580 }}>
        <div style={{
          lineHeight: 1.65, fontSize: 14,
          ...(isUser ? {
            background: 'var(--bg3)',
            border: '1px solid rgba(124,111,247,0.15)',
            padding: '11px 14px',
            borderRadius: '14px 4px 14px 14px',
            color: 'var(--t1)',
          } : {
            background: 'transparent',
            padding: '4px 0',
            color: 'var(--t1)',
          }),
        }}>
          {/* ReAct Steps */}
          {msg.steps && <ReActSteps steps={msg.steps} />}
          
          {/* Thinking */}
          {msg.thinking && <ThinkBlock content={msg.thinking} />}

          {/* Content */}
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              code({ node, inline, className, children, ...props }) {
                const match = /language-(\w+)/.exec(className || '')
                return !inline && match ? (
                  <CodeBlock language={match[1]}>{String(children).replace(/\n$/, '')}</CodeBlock>
                ) : (
                  <code style={{
                    background: 'var(--bg3)', padding: '2px 6px',
                    borderRadius: 5, fontSize: '0.9em', fontFamily: 'var(--mono)',
                  }} {...props}>{children}</code>
                )
              },
              p: ({ children }) => <p style={{ marginBottom: 8 }}>{children}</p>,
              strong: ({ children }) => <strong style={{ color: 'var(--t1)', fontWeight: 600 }}>{children}</strong>,
            }}
          >
            {msg.content}
          </ReactMarkdown>
        </div>

        {/* Actions */}
        {!isUser && (
          <div style={{ display: 'flex', gap: 4, marginTop: 8 }}>
            {['👍', '👎'].map(emoji => (
              <button key={emoji} style={{
                padding: '3px 7px', background: 'transparent',
                border: '1px solid var(--bd)', borderRadius: 6,
                fontSize: 12, cursor: 'pointer', transition: 'all .2s', lineHeight: 1,
              }}
              onMouseEnter={e => (e.currentTarget.style.transform = 'scale(1.15)')}
              onMouseLeave={e => (e.currentTarget.style.transform = 'scale(1)')}
              >
                {emoji}
              </button>
            ))}
            {['📋 Kopyala', '⟳ Yenile'].map(lbl => (
              <button key={lbl} style={{
                padding: '4px 8px', background: 'var(--bg2)',
                border: '1px solid var(--bd)', borderRadius: 6,
                fontSize: 11, color: 'var(--t3)', cursor: 'pointer',
                fontFamily: 'var(--font)', transition: 'all .15s',
              }}
              onMouseEnter={e => { e.currentTarget.style.background = 'var(--bg3)'; e.currentTarget.style.color = 'var(--t2)' }}
              onMouseLeave={e => { e.currentTarget.style.background = 'var(--bg2)'; e.currentTarget.style.color = 'var(--t3)' }}
              >
                {lbl}
              </button>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  )
}

// AgentChip
const AgentChip = ({ name, status }: Agent) => {
  const colors = {
    running: { bg: 'rgba(124,111,247,0.12)', color: '#9d94ff', bd: 'rgba(124,111,247,0.25)' },
    ready:   { bg: 'rgba(86,207,191,0.1)',  color: 'var(--acc2)', bd: 'rgba(86,207,191,0.2)' },
    idle:    { bg: 'var(--bg2)', color: 'var(--t4)', bd: 'var(--bd)' },
    error:   { bg: 'rgba(255,100,100,0.1)', color: '#ff6464', bd: 'rgba(255,100,100,0.2)' },
  }
  const c = colors[status]
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 5, padding: '4px 9px',
      borderRadius: 20, fontSize: 11, fontWeight: 500, cursor: 'pointer',
      background: c.bg, color: c.color, border: `1px solid ${c.bd}`,
      transition: 'all .15s',
    }}>
      <div style={{
        width: 5, height: 5, borderRadius: '50%', background: 'currentColor',
        animation: status === 'running' ? 'chipPulse 1.4s infinite' : 'none',
      }} />
      {name}
    </div>
  )
}

// Sidebar
const Sidebar = ({
  conversations, activeId, onSelect, onNew,
}: {
  conversations: Conversation[]
  activeId: string
  onSelect: (id: string) => void
  onNew: () => void
}) => (
  <div style={{
    width: 252, background: 'var(--bg1)', display: 'flex', flexDirection: 'column',
    borderRight: '1px solid var(--bd)', flexShrink: 0,
  }}>
    {/* Header */}
    <div style={{ padding: '16px 14px 12px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginBottom: 14 }}>
        <div style={{
          width: 32, height: 32, borderRadius: 9, flexShrink: 0,
          background: 'linear-gradient(135deg,#7c6ff7,#56cfbf)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 4px 14px rgba(124,111,247,0.4)',
        }}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
          </svg>
        </div>
        <div>
          <div style={{ fontSize: 15, fontWeight: 600, letterSpacing: 0.2 }}>ULTRON</div>
          <div style={{ fontSize: 10, color: 'var(--t3)' }}>AGI v3.0</div>
        </div>
      </div>
      <button onClick={onNew} style={{
        display: 'flex', alignItems: 'center', gap: 7, width: '100%',
        padding: '9px 11px', borderRadius: 'var(--r)',
        border: '1px solid var(--bd2)', background: 'rgba(124,111,247,0.08)',
        color: 'var(--acc)', fontSize: 13, fontWeight: 500, cursor: 'pointer',
        transition: 'all .2s', fontFamily: 'var(--font)',
      }}
      onMouseEnter={e => { e.currentTarget.style.background = 'rgba(124,111,247,0.16)'; e.currentTarget.style.transform = 'translateY(-1px)' }}
      onMouseLeave={e => { e.currentTarget.style.background = 'rgba(124,111,247,0.08)'; e.currentTarget.style.transform = 'translateY(0)' }}
      >
        <div style={{
          width: 18, height: 18, borderRadius: 5, background: 'rgba(124,111,247,0.25)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12,
        }}>＋</div>
        Yeni Konuşma
      </button>
    </div>

    {/* Conv label */}
    <div style={{ padding: '14px 14px 6px', fontSize: 10, color: 'var(--t4)', fontWeight: 600, letterSpacing: 1.2, textTransform: 'uppercase' }}>
      Geçmiş
    </div>

    {/* Conv list */}
    <div style={{ flex: 1, overflowY: 'auto', padding: '0 8px' }}>
      <AnimatePresence>
        {conversations.map(c => (
          <motion.div
            key={c.id}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -10 }}
            onClick={() => onSelect(c.id)}
            style={{
              padding: '8px 8px', borderRadius: 8, cursor: 'pointer',
              marginBottom: 1, display: 'flex', alignItems: 'center', gap: 9,
              background: activeId === c.id ? 'var(--bg3)' : 'transparent',
              border: activeId === c.id ? '1px solid rgba(124,111,247,0.18)' : '1px solid transparent',
              transition: 'all .15s',
            }}
            whileHover={{ background: 'var(--bg3)' }}
          >
            <div style={{ width: 7, height: 7, borderRadius: '50%', background: c.color, flexShrink: 0 }} />
            <span style={{
              fontSize: 13, color: activeId === c.id ? 'var(--t1)' : 'var(--t2)',
              fontWeight: activeId === c.id ? 500 : 400,
              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', flex: 1,
            }}>
              {c.title}
            </span>
            {c.isNew && (
              <span style={{ padding: '1px 6px', background: 'rgba(124,111,247,0.15)', color: 'var(--acc)', fontSize: 10, borderRadius: 4 }}>
                Yeni
              </span>
            )}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>

    {/* Footer */}
    <div style={{ padding: 12, borderTop: '1px solid var(--bd)' }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 7, padding: '8px 10px',
        background: 'var(--bg2)', borderRadius: 'var(--r)', border: '1px solid var(--bd)',
        marginBottom: 6,
      }}>
        <div style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--acc2)', animation: 'glow 2s infinite' }} />
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 12, fontWeight: 500 }}>Groq • Llama-3.3</div>
          <div style={{ fontSize: 10, color: 'var(--t3)' }}>312ms • 8 provider</div>
        </div>
        <div style={{ padding: '2px 6px', background: 'rgba(86,207,191,0.1)', color: 'var(--acc2)', fontSize: 10, borderRadius: 4 }}>●●●</div>
      </div>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8, padding: '8px 10px',
        borderRadius: 'var(--r)', cursor: 'pointer', transition: 'background .15s',
      }}
      onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg2)')}
      onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
      >
        <div style={{
          width: 28, height: 28, borderRadius: 8,
          background: 'linear-gradient(135deg,#e879a0,#7c6ff7)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 600,
        }}>E</div>
        <div>
          <div style={{ fontSize: 13, fontWeight: 500 }}>Eren</div>
          <div style={{ fontSize: 10, color: 'var(--t3)' }}>ULTRON Master</div>
        </div>
        <div style={{ marginLeft: 'auto', width: 6, height: 6, borderRadius: '50%', background: 'var(--acc2)' }} />
      </div>
    </div>
  </div>
)

// WelcomeScreen
const WelcomeScreen = ({ onCardClick }: { onCardClick: (prompt: string) => void }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 40, textAlign: 'center' }}
  >
    <div style={{
      width: 52, height: 52, borderRadius: 15,
      background: 'linear-gradient(135deg,#7c6ff7,#56cfbf)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      margin: '0 auto 20px', boxShadow: '0 8px 30px rgba(124,111,247,0.35)',
    }}>
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>
      </svg>
    </div>
    <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 8 }}>ULTRON AGI'ya hoş geldin</h1>
    <p style={{ fontSize: 14, color: 'var(--t2)', maxWidth: 360, lineHeight: 1.6, marginBottom: 28 }}>
      Zeki, öğrenen ve sürekli gelişen yapay zeka asistanın. Ne yapmamı istersin?
    </p>
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, width: '100%', maxWidth: 400 }}>
      {WELCOME_CARDS.map(card => (
        <button key={card.title} onClick={() => onCardClick(card.prompt)} style={{
          padding: '12px 14px', background: 'var(--bg2)', border: '1px solid var(--bd)',
          borderRadius: 10, cursor: 'pointer', textAlign: 'left', transition: 'all .2s',
          fontFamily: 'var(--font)', color: 'var(--t1)',
        }}
        onMouseEnter={e => { e.currentTarget.style.background = 'var(--bg3)'; e.currentTarget.style.borderColor = 'rgba(124,111,247,0.25)'; e.currentTarget.style.transform = 'translateY(-1px)' }}
        onMouseLeave={e => { e.currentTarget.style.background = 'var(--bg2)'; e.currentTarget.style.borderColor = 'var(--bd)'; e.currentTarget.style.transform = 'translateY(0)' }}
        >
          <div style={{ fontSize: 18, marginBottom: 6 }}>{card.icon}</div>
          <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 2 }}>{card.title}</div>
          <div style={{ fontSize: 11, color: 'var(--t3)', lineHeight: 1.4 }}>{card.desc}</div>
        </button>
      ))}
    </div>
  </motion.div>
)

// ChatInput
const ChatInput = ({ onSend, disabled }: { onSend: (text: string) => void; disabled: boolean }) => {
  const [value, setValue] = useState('')
  const taRef = useRef<HTMLTextAreaElement>(null)

  const submit = () => {
    if (!value.trim() || disabled) return
    onSend(value)
    setValue('')
    if (taRef.current) taRef.current.style.height = 'auto'
  }

  return (
    <div style={{ padding: '12px 18px 14px', flexShrink: 0 }}>
      <div style={{
        background: 'var(--bg2)', border: '1px solid rgba(255,255,255,0.1)',
        borderRadius: 14, overflow: 'hidden',
        transition: 'border-color .25s, box-shadow .25s',
      }}
      onFocus={(e) => { (e.currentTarget as HTMLDivElement).style.borderColor = 'rgba(124,111,247,0.5)'; (e.currentTarget as HTMLDivElement).style.boxShadow = '0 0 0 3px rgba(124,111,247,0.07)' }}
      onBlur={(e) => { (e.currentTarget as HTMLDivElement).style.borderColor = 'rgba(255,255,255,0.1)'; (e.currentTarget as HTMLDivElement).style.boxShadow = 'none' }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-end', padding: '11px 12px 11px 14px', gap: 8 }}>
          <textarea
            ref={taRef}
            value={value}
            onChange={e => {
              setValue(e.target.value)
              e.target.style.height = 'auto'
              e.target.style.height = Math.min(e.target.scrollHeight, 130) + 'px'
            }}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() } }}
            placeholder="ULTRON'a bir şey sor..."
            rows={1}
            style={{
              flex: 1, background: 'transparent', border: 'none', outline: 'none',
              color: 'var(--t1)', fontFamily: 'var(--font)', fontSize: 14,
              resize: 'none', maxHeight: 130, lineHeight: 1.55,
            }}
          />
          <div style={{ display: 'flex', alignItems: 'center', gap: 5, flexShrink: 0 }}>
            {['🎙', '📎'].map(icon => (
              <button key={icon} style={{
                width: 32, height: 32, borderRadius: 8, border: 'none',
                background: 'transparent', cursor: 'pointer', fontSize: 15,
                color: 'var(--t3)', transition: 'all .15s',
              }}
              onMouseEnter={e => { e.currentTarget.style.background = 'var(--bg3)'; e.currentTarget.style.color = 'var(--t2)' }}
              onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--t3)' }}
              >{icon}</button>
            ))}
            <button onClick={submit} style={{
              width: 32, height: 32, borderRadius: 8, border: 'none', cursor: 'pointer',
              background: 'linear-gradient(135deg,var(--acc),var(--acc2))',
              boxShadow: '0 2px 12px rgba(124,111,247,0.4)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              transition: 'all .15s',
            }}
            onMouseEnter={e => { e.currentTarget.style.transform = 'scale(1.08)'; e.currentTarget.style.boxShadow = '0 4px 18px rgba(124,111,247,0.55)' }}
            onMouseLeave={e => { e.currentTarget.style.transform = 'scale(1)'; e.currentTarget.style.boxShadow = '0 2px 12px rgba(124,111,247,0.4)' }}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
              </svg>
            </button>
          </div>
        </div>
        <div style={{ padding: '0 14px 10px', display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          {['⚡ CoderAgent', '🔍 Web Araştırma', '📁 Dosya Analizi', '🎨 Görüntü Üret'].map(lbl => (
            <div key={lbl} style={{
              padding: '3px 8px', background: 'var(--bg3)', border: '1px solid var(--bd)',
              borderRadius: 6, fontSize: 11, color: 'var(--t3)', cursor: 'pointer', transition: 'all .15s',
            }}
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--bg4)'; e.currentTarget.style.color = 'var(--t2)' }}
            onMouseLeave={e => { e.currentTarget.style.background = 'var(--bg3)'; e.currentTarget.style.color = 'var(--t3)' }}
            >
              {lbl}
            </div>
          ))}
          <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--t4)' }}>⇧ Enter → yeni satır</span>
        </div>
      </div>
    </div>
  )
}

// ── MAIN APP ──────────────────────────────────────────────
export default function App() {
  const [conversations, setConversations] = useState<Conversation[]>(SAMPLE_CONVERSATIONS)
  const [activeId, setActiveId] = useState('c1')
  const [messages, setMessages] = useState<Message[]>([])
  const [isTyping, setIsTyping] = useState(false)
  const [showWelcome, setShowWelcome] = useState(false)
  const msgsEndRef = useRef<HTMLDivElement>(null)
  const { send: wsSend, connected } = useWebSocket('ws://localhost:8000/ws/chat')

  const agents: Agent[] = [
    { name: 'WebSearch', status: 'ready' },
    { name: 'CoderAgent', status: 'running' },
    { name: 'EmailAgent', status: 'idle' },
  ]

  const scrollToBottom = () => {
    msgsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => { scrollToBottom() }, [messages, isTyping])

  const handleSend = async (text: string) => {
    setShowWelcome(false)
    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: text,
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, userMsg])
    setIsTyping(true)

    // WebSocket logic for real backend communication
    if (connected) {
      wsSend({ type: 'message', content: text })
    } else {
      // Mock mode fallback for UI testing
      setTimeout(() => {
        setIsTyping(false)
        const assistantMsg: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: `**${text}** sorusunu aldım. Şu an 52k Mega-Dataset eğitimi arka planda devam ettiği için bazı fonksiyonlarım kısıtlı olabilir ancak analizinizi yapıyorum...\n\nBu konuda size detaylı bilgi verebilirim. Daha fazla bağlam paylaşırsanız daha iyi yardımcı olabilirim.`,
          steps: [
            { label: 'THINK', status: 'done' },
            { label: 'PLAN', status: 'done' },
            { label: 'ACT', status: 'done' },
            { label: 'RESPOND', status: 'active' },
          ],
          timestamp: new Date(),
        }
        setMessages(prev => [...prev, assistantMsg])
      }, 1800)
    }
  }

  const handleNewChat = () => {
    setMessages([])
    setShowWelcome(true)
    setActiveId('')
  }

  const handleCardClick = (prompt: string) => {
    setShowWelcome(false)
    document.querySelector('textarea')?.focus()
    // Trigger handleSend with prompt
    handleSend(prompt)
  }

  return (
    <div style={{ display: 'flex', height: '100vh', background: 'var(--bg0)', overflow: 'hidden' }}>
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={(id) => { setActiveId(id); setShowWelcome(false) }}
        onNew={handleNewChat}
      />

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* Topbar */}
        <div style={{
          padding: '12px 20px', borderBottom: '1px solid var(--bd)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          background: 'rgba(13,13,16,0.9)', backdropFilter: 'blur(10px)', flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ fontSize: 14, fontWeight: 500 }}>
              {showWelcome ? 'ULTRON AGI' : conversations.find(c => c.id === activeId)?.title || 'Yeni Konuşma'}
            </span>
            <span style={{ padding: '3px 8px', background: 'var(--bg3)', border: '1px solid var(--bd)', borderRadius: 5, fontSize: 11, color: 'var(--t2)' }}>
              {connected ? '● Online' : '○ Offline'} • ultron-v1
            </span>
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            {agents.map(a => <AgentChip key={a.name} {...a} />)}
          </div>
        </div>

        {/* Messages or Welcome */}
        {showWelcome ? (
          <WelcomeScreen onCardClick={handleCardClick} />
        ) : (
          <div style={{ flex: 1, overflowY: 'auto', padding: '28px 24px', display: 'flex', flexDirection: 'column', gap: 24 }}>
            <AnimatePresence>
              {messages.map(msg => <MessageBubble key={msg.id} msg={msg} />)}
            </AnimatePresence>
            {isTyping && (
              <div style={{ display: 'flex', gap: 12 }}>
                <div style={{ width: 32, height: 32, borderRadius: 9, background: 'linear-gradient(135deg,#1e1e27,#2a2a38)', border: '1px solid rgba(124,111,247,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, color: 'var(--acc)', flexShrink: 0 }}>⚡</div>
                <div style={{ background: 'transparent', padding: '4px 0' }}>
                  <TypingDots />
                </div>
              </div>
            )}
            <div ref={msgsEndRef} />
          </div>
        )}

        {/* Daemon bar */}
        <div style={{ padding: '6px 20px', background: 'rgba(86,207,191,0.04)', borderTop: '1px solid rgba(86,207,191,0.08)', display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
          <div style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--acc2)', animation: 'glow 2s infinite' }} />
          <span style={{ fontSize: 11, color: 'var(--acc2)', opacity: 0.8, flex: 1 }}>Araştırma daemon aktif</span>
          {['🔬 3 keşif', '⚡ 8/8 sağlıklı', '📊 52K öğreniliyor'].map(t => (
            <span key={t} style={{ padding: '2px 7px', background: 'rgba(86,207,191,0.08)', border: '1px solid rgba(86,207,191,0.15)', borderRadius: 4, fontSize: 10, color: 'var(--acc2)' }}>{t}</span>
          ))}
        </div>

        <ChatInput onSend={handleSend} disabled={isTyping} />
      </div>
    </div>
  )
}
