import React, { useRef, useState } from 'react';

export default function UploadScreen({ onStart, error }) {
  const fileRef = useRef(null);
  const [dragover, setDragover] = useState(false);

  const recentFiles = [
    { name: 'Nordic_Kitchenware_Catalogue_2026.pdf', meta: '6 pages · 4 products detected · 2 days ago' },
    { name: 'Meridian_Glassware_Pricelist_Q2.pdf', meta: '3 pages · 9 products detected · 5 days ago' },
  ];

  return (
    <div style={{
      minHeight: '100%', display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', padding: '48px 24px',
    }}>
      <div style={{ width: '100%', maxWidth: 640 }}>
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <h1 style={{ margin: '0 0 8px', fontSize: 28, fontWeight: 800, letterSpacing: '-0.02em' }}>
            Upload a supplier catalogue
          </h1>
          <p style={{ margin: 0, fontSize: 15, color: '#6a7180', lineHeight: 1.5 }}>
            Drop a PDF spec sheet or catalogue and AI will extract the supplier, pricing, product details and images for you to review.
          </p>
        </div>

        {error && (
          <div style={{
            marginBottom: 18, padding: '12px 16px', borderRadius: 10,
            background: '#fbeee9', border: '1px solid #eccabc',
            fontSize: 13.5, color: '#a93c26', fontWeight: 500,
          }}>
            {error}
          </div>
        )}

        <div
          onClick={() => fileRef.current?.click()}
          onDrop={(e) => { e.preventDefault(); setDragover(false); const f = e.dataTransfer.files?.[0]; if (f) onStart(f); }}
          onDragOver={(e) => { e.preventDefault(); if (!dragover) setDragover(true); }}
          onDragLeave={(e) => { e.preventDefault(); setDragover(false); }}
          style={{
            border: `2px dashed ${dragover ? '#4b56d6' : '#cfd3dc'}`,
            background: dragover ? '#eef0fc' : '#fbfbfd',
            borderRadius: 18, padding: '44px 32px', textAlign: 'center', cursor: 'pointer',
            transition: 'border-color .15s, background .15s',
          }}
        >
          <div style={{
            width: 56, height: 56, borderRadius: 16, background: '#eef0fc',
            display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 18px',
          }}>
            <div style={{
              width: 20, height: 20, borderRadius: 5, border: '2.5px solid #4b56d6',
              borderBottomColor: 'transparent', borderRightColor: 'transparent',
              transform: 'rotate(45deg)', marginTop: 5,
            }} />
          </div>
          <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 5 }}>Drag &amp; drop your file here</div>
          <div style={{ fontSize: 13.5, color: '#8a90a0', marginBottom: 20 }}>
            or click to browse — PDF up to 50&nbsp;MB
          </div>
          <button
            onClick={(e) => { e.stopPropagation(); fileRef.current?.click(); }}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 8, padding: '10px 18px',
              borderRadius: 10, background: '#4b56d6', color: '#fff', fontSize: 14, fontWeight: 600,
              cursor: 'pointer', boxShadow: '0 2px 6px rgba(75,86,214,0.30)',
            }}
          >
            Browse files
          </button>
          <input
            type="file"
            accept=".pdf"
            ref={fileRef}
            onChange={(e) => { if (e.target.files?.[0]) onStart(e.target.files[0]); }}
            style={{ display: 'none' }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10, margin: '22px 4px 12px' }}>
          <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: '#9aa0ac' }}>
            Recent
          </span>
          <div style={{ flex: 1, height: 1, background: '#e7e9ee' }} />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {recentFiles.map((f) => (
            <div
              key={f.name}
              onClick={() => onStart(f.name)}
              style={{
                display: 'flex', alignItems: 'center', gap: 13, padding: '12px 14px',
                background: '#fff', border: '1px solid #e7e9ee', borderRadius: 12, cursor: 'pointer',
              }}
            >
              <div style={{
                width: 34, height: 42, borderRadius: 5, flexShrink: 0,
                background: 'repeating-linear-gradient(135deg,#eef0f3 0 7px,#e4e7ed 7px 14px)',
                border: '1px solid #e0e3ea',
              }} />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  fontSize: 13.5, fontWeight: 600, fontFamily: "'JetBrains Mono', monospace",
                  whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                }}>
                  {f.name}
                </div>
                <div style={{ fontSize: 12, color: '#9aa0ac' }}>{f.meta}</div>
              </div>
              <span style={{ fontSize: 12.5, fontWeight: 600, color: '#4b56d6', flexShrink: 0 }}>Open →</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
