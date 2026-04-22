import { motion, AnimatePresence } from 'framer-motion'

interface MobileDrawerProps {
  open: boolean
  onClose: () => void
  onSettingsClick: () => void
  children?: React.ReactNode
}

export const MobileDrawer = ({ open, onClose, onSettingsClick, children }: MobileDrawerProps) => (
  <AnimatePresence>
    {open && (
      <>
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.6)',
            backdropFilter: 'blur(4px)',
            zIndex: 100,
          }}
        />
        {/* Panel */}
        <motion.div
          initial={{ x: '-100%' }}
          animate={{ x: 0 }}
          exit={{ x: '-100%' }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            bottom: 0,
            width: '85%',
            maxWidth: 320,
            background: 'var(--bg1)',
            borderRight: '1px solid var(--bd)',
            zIndex: 101,
            display: 'flex',
            flexDirection: 'column',
            boxShadow: '20px 0 50px rgba(0,0,0,0.5)',
          }}
        >
          <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', height: '100%' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
              <span style={{ fontSize: '18px', fontWeight: 700, color: 'var(--acc)' }}>ULTRON</span>
              <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--t3)', fontSize: '24px', cursor: 'pointer' }}>×</button>
            </div>
            
            <div style={{ flex: 1, overflowY: 'auto' }}>
              {children}
            </div>

            <button 
              onClick={() => { onClose(); onSettingsClick(); }}
              style={{
                marginTop: 'auto',
                padding: '12px',
                background: 'var(--bg2)',
                border: '1px solid var(--bd)',
                borderRadius: '12px',
                color: 'var(--t1)',
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                cursor: 'pointer'
              }}
            >
              <span style={{ fontSize: '18px' }}>⚙</span> Ayarlar
            </button>
          </div>
        </motion.div>
      </>
    )}
  </AnimatePresence>
)
