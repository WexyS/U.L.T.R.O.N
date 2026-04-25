import { motion } from 'framer-motion';

export const DraggablePanel = ({ 
  title, 
  onClose, 
  children,
  defaultX = 20,
  defaultY = 20,
  width = 600,
  height = 500
}: { 
  title: string; 
  onClose: () => void; 
  children: React.ReactNode;
  defaultX?: number;
  defaultY?: number;
  width?: number;
  height?: number;
}) => {
  return (
    <motion.div
      drag
      dragMomentum={false}
      initial={{ opacity: 0, scale: 0.9, x: defaultX, y: defaultY }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      style={{
        position: 'absolute',
        width,
        height,
        background: 'var(--bg1)',
        border: '1px solid var(--bd)',
        borderRadius: 24,
        boxShadow: '0 30px 60px rgba(0,0,0,0.6), 0 0 20px var(--acc-glow)',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        zIndex: 50,
      }}
    >
      <div 
        className="drag-handle"
        style={{ 
          padding: '16px 20px', 
          background: 'rgba(255,255,255,0.02)', 
          borderBottom: '1px solid var(--bd)',
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          cursor: 'grab',
        }}
        onPointerDown={(e) => (e.currentTarget.style.cursor = 'grabbing')}
        onPointerUp={(e) => (e.currentTarget.style.cursor = 'grab')}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--acc2)', boxShadow: '0 0 8px var(--acc2-glow)' }} />
          <span style={{ fontSize: 13, fontWeight: 700, letterSpacing: 1, color: 'var(--t2)' }}>{title.toUpperCase()}</span>
        </div>
        <button 
          onClick={onClose}
          style={{
            width: 28, height: 28, borderRadius: 8, background: 'var(--bg3)', 
            color: 'var(--t3)', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'all 0.2s'
          }}
          onMouseEnter={e => { e.currentTarget.style.background = '#ff4444'; e.currentTarget.style.color = '#fff' }}
          onMouseLeave={e => { e.currentTarget.style.background = 'var(--bg3)'; e.currentTarget.style.color = 'var(--t3)' }}
        >
          ✕
        </button>
      </div>
      <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
        {children}
      </div>
    </motion.div>
  );
};
