import React from 'react';

export default function ExportModal({ fileName, total, onReset }) {
  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(28,34,48,0.34)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 50,
    }}>
      <div style={{
        width: 380, background: '#fff', borderRadius: 18, padding: 28,
        textAlign: 'center', boxShadow: '0 24px 60px -20px rgba(28,34,48,0.4)',
        animation: 'rise .22s ease',
      }}>
        <div style={{
          width: 52, height: 52, borderRadius: '50%', background: '#e7f6ef',
          display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px',
        }}>
          <div style={{
            width: 18, height: 10,
            borderLeft: '3px solid #1f9d6b', borderBottom: '3px solid #1f9d6b',
            transform: 'rotate(-45deg) translate(1px,-2px)',
          }} />
        </div>
        <h3 style={{ margin: '0 0 6px', fontSize: 18, fontWeight: 800 }}>Exported to catalogue</h3>
        <p style={{ margin: '0 0 20px', fontSize: 14, color: '#6a7180', lineHeight: 1.5 }}>
          {total} products and 1 supplier from &ldquo;{fileName}&rdquo; were added to your catalogue.
        </p>
        <button
          onClick={onReset}
          style={{
            width: '100%', padding: 11, borderRadius: 11, background: '#4b56d6',
            color: '#fff', fontSize: 14, fontWeight: 700, cursor: 'pointer',
          }}
        >
          Upload another file
        </button>
      </div>
    </div>
  );
}
