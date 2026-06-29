import React from 'react';

export default function Header({ tab, onTabChange, catalogCount }) {
  const tabs = [
    { key: 'upload', label: 'Upload', badge: false },
    { key: 'library', label: 'Catalogues', badge: true, badgeText: String(catalogCount) },
    { key: 'pricing', label: 'Price lists', badge: false },
    { key: 'combinations', label: 'Combinations', badge: false },
    { key: 'search', label: 'Find suppliers', badge: false },
  ];

  return (
    <header style={{
      flex: 'none', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      gap: 24, padding: '0 24px', height: 60, background: '#ffffff', borderBottom: '1px solid #e7e9ee',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 11, minWidth: 200 }}>
        <div style={{
          width: 30, height: 30, borderRadius: 9, background: '#4b56d6',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 2px 6px rgba(75,86,214,0.35)',
        }}>
          <div style={{ width: 11, height: 11, borderRadius: 3, background: '#ffffff' }} />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.05 }}>
          <span style={{ fontSize: 15, fontWeight: 700, letterSpacing: '-0.01em' }}>Intake</span>
          <span style={{ fontSize: 11, color: '#9aa0ac', fontWeight: 500, letterSpacing: '0.02em' }}>Supplier catalogue OCR</span>
        </div>
      </div>

      <nav style={{ display: 'flex', alignItems: 'center', gap: 3 }}>
        {tabs.map((t) => {
          const active = tab === t.key;
          return (
            <button
              key={t.key}
              onClick={() => onTabChange(t.key)}
              style={{
                display: 'flex', alignItems: 'center', gap: 7, padding: '8px 13px',
                borderRadius: 9, background: active ? '#eef0fc' : 'transparent',
                color: active ? '#3a44b8' : '#7b8290',
                fontSize: 13.5, fontWeight: 600, cursor: 'pointer',
              }}
            >
              {t.label}
              {t.badge && (
                <span style={{
                  fontSize: 11, fontWeight: 700, fontFamily: "'JetBrains Mono', monospace",
                  color: active ? '#4b56d6' : '#aab0bb', background: '#ffffff',
                  border: '1px solid #e7e9ee', padding: '0 6px', borderRadius: 20,
                }}>
                  {t.badgeText}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      <div style={{ display: 'flex', alignItems: 'center', gap: 14, minWidth: 200, justifyContent: 'flex-end' }}>
        <span style={{ fontSize: 13, fontWeight: 600, color: '#6a7180', cursor: 'pointer' }}>Help</span>
        <div style={{
          width: 32, height: 32, borderRadius: '50%', background: '#e9ebf2',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 12, fontWeight: 700, color: '#5b6473', fontFamily: "'JetBrains Mono', monospace",
        }}>
          OP
        </div>
      </div>
    </header>
  );
}
