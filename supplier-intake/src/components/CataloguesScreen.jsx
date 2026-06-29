import React, { useState, useEffect } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

function statusMeta(status) {
  return status === 'reviewed'
    ? { label: 'Reviewed', color: '#1f9d6b', bg: '#e7f6ef', border: '#bfe3cf', dot: '#1f9d6b' }
    : { label: 'In review', color: '#9a6a14', bg: '#fdf8ec', border: '#ecd9a6', dot: '#c98a1a' };
}

export default function CataloguesScreen({ catalogs, openCatalogId, onOpenCatalog, onCloseCatalog, onGotoUpload }) {
  const [fullCatalog, setFullCatalog] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!openCatalogId) { setFullCatalog(null); return; }
    setLoading(true);
    fetch(`${API_BASE}/api/catalogs/${openCatalogId}`)
      .then((r) => r.json())
      .then((data) => { setFullCatalog(data); setLoading(false); })
      .catch(() => {
        // fallback to slim catalog from props
        setFullCatalog(catalogs.find((c) => c.id === openCatalogId) ?? null);
        setLoading(false);
      });
  }, [openCatalogId]);

  return (
    <div style={{ maxWidth: 1080, margin: '0 auto', padding: '26px 26px 90px' }}>
      {!openCatalogId && (
        <ListView catalogs={catalogs} onOpenCatalog={onOpenCatalog} onGotoUpload={onGotoUpload} />
      )}
      {openCatalogId && loading && (
        <div style={{ textAlign: 'center', padding: 60, color: '#9aa0ac', fontSize: 13.5 }}>Loading…</div>
      )}
      {openCatalogId && !loading && fullCatalog && (
        <DetailView catalog={fullCatalog} onClose={onCloseCatalog} />
      )}
    </div>
  );
}

function ListView({ catalogs, onOpenCatalog, onGotoUpload }) {
  return (
    <>
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', marginBottom: 22 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 21, fontWeight: 800, letterSpacing: '-0.02em' }}>Catalogues</h2>
          <p style={{ margin: '6px 0 0', fontSize: 13.5, color: '#8a90a0' }}>
            Every uploaded catalogue and the supplier &amp; products extracted from it.
          </p>
        </div>
        <button
          onClick={onGotoUpload}
          style={{
            display: 'flex', alignItems: 'center', gap: 7, padding: '9px 16px', borderRadius: 10,
            background: '#4b56d6', color: '#fff', fontSize: 13.5, fontWeight: 700, cursor: 'pointer',
            boxShadow: '0 2px 6px rgba(75,86,214,0.30)',
          }}
        >
          <span style={{ fontSize: 17, lineHeight: 1, marginTop: -1 }}>+</span> Upload new
        </button>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(0,2.4fr) minmax(0,1.5fr) 80px 70px 116px 30px',
        gap: 14, padding: '0 16px 9px',
        fontSize: 11, fontWeight: 700, letterSpacing: '0.05em', textTransform: 'uppercase', color: '#9aa0ac',
      }}>
        <span>Catalogue</span>
        <span>Supplier</span>
        <span>Products</span>
        <span>Pages</span>
        <span>Status</span>
        <span />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {catalogs.map((c) => {
          const sm = statusMeta(c.status);
          return (
            <div
              key={c.id}
              onClick={() => onOpenCatalog(c.id)}
              style={{
                display: 'grid',
                gridTemplateColumns: 'minmax(0,2.4fr) minmax(0,1.5fr) 80px 70px 116px 30px',
                gap: 14, alignItems: 'center',
                background: '#fff', border: '1px solid #e7e9ee', borderRadius: 13,
                padding: '13px 16px', cursor: 'pointer',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
                <div style={{
                  width: 38, height: 46, borderRadius: 7, flexShrink: 0,
                  background: 'repeating-linear-gradient(135deg,#eef0f3 0 6px,#e4e7ed 6px 12px)',
                  border: '1px solid #e0e3ea', overflow: 'hidden',
                }}>
                  {c.coverImage && (
                    <img src={c.coverImage} alt={c.file} style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
                  )}
                </div>
                <div style={{ minWidth: 0 }}>
                  <div style={{
                    fontSize: 13, fontWeight: 600, fontFamily: "'JetBrains Mono', monospace",
                    whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                  }}>
                    {c.file}
                  </div>
                  <div style={{ fontSize: 11.5, color: '#9aa0ac' }}>{c.date}</div>
                </div>
              </div>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: 13.5, fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {c.supplier.name}
                </div>
                <div style={{ fontSize: 11.5, color: '#9aa0ac', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {c.supplier.location}
                </div>
              </div>
              <span style={{ fontSize: 13.5, fontWeight: 700, fontFamily: "'JetBrains Mono', monospace", color: '#4b56d6' }}>
                {c.products.length}
              </span>
              <span style={{ fontSize: 13, color: '#6a7180', fontFamily: "'JetBrains Mono', monospace" }}>
                {c.pages}
              </span>
              <span style={{
                display: 'inline-flex', alignItems: 'center', gap: 6, padding: '4px 10px',
                borderRadius: 20, background: sm.bg, border: `1px solid ${sm.border}`,
                fontSize: 12, fontWeight: 600, color: sm.color, width: 'fit-content',
              }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: sm.dot }} />
                {sm.label}
              </span>
              <span style={{ fontSize: 16, color: '#c2c7d0', textAlign: 'right' }}>→</span>
            </div>
          );
        })}
      </div>
    </>
  );
}

function DetailView({ catalog, onClose }) {
  const sm = statusMeta(catalog.status);
  return (
    <>
      <button
        onClick={onClose}
        style={{
          display: 'flex', alignItems: 'center', gap: 7, padding: '7px 13px', borderRadius: 9,
          border: '1px solid #d6d9e0', background: '#fff', fontSize: 13, fontWeight: 600,
          color: '#5b6473', cursor: 'pointer', marginBottom: 16,
        }}
      >
        ← All catalogues
      </button>

      <div style={{ background: '#fff', border: '1px solid #e7e9ee', borderRadius: 16, padding: '20px 22px', marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <div style={{
              width: 44, height: 54, borderRadius: 7, flexShrink: 0,
              background: 'repeating-linear-gradient(135deg,#eef0f3 0 7px,#e4e7ed 7px 14px)',
              border: '1px solid #e0e3ea', overflow: 'hidden',
            }}>
              {catalog.coverImage && (
                <img src={catalog.coverImage} alt={catalog.file} style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
              )}
            </div>
            <div>
              <h2 style={{ margin: 0, fontSize: 19, fontWeight: 800, letterSpacing: '-0.02em' }}>
                {catalog.supplier.name}
              </h2>
              <div style={{ fontSize: 12.5, color: '#9aa0ac', fontFamily: "'JetBrains Mono', monospace", marginTop: 3 }}>
                {catalog.file} · {catalog.pages} pages · {catalog.date}
              </div>
            </div>
          </div>
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: 6, padding: '5px 11px',
            borderRadius: 20, background: sm.bg, border: `1px solid ${sm.border}`,
            fontSize: 12.5, fontWeight: 600, color: sm.color,
          }}>
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: sm.dot }} />
            {sm.label}
          </span>
        </div>

        <div style={{ display: 'flex', gap: 30, flexWrap: 'wrap', marginTop: 16, paddingTop: 16, borderTop: '1px solid #eef0f3' }}>
          {[
            { label: 'Location', value: catalog.supplier.location },
            { label: 'Email', value: catalog.supplier.email },
            { label: 'Terms', value: catalog.supplier.terms },
          ].map((m) => (
            <div key={m.label}>
              <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: '0.05em', textTransform: 'uppercase', color: '#9aa0ac', marginBottom: 3 }}>
                {m.label}
              </div>
              <div style={{ fontSize: 13.5, fontWeight: 600, color: '#3a4253' }}>{m.value}</div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ background: '#fff', border: '1px solid #e7e9ee', borderRadius: 16, overflow: 'hidden' }}>
        <div style={{
          display: 'grid', gridTemplateColumns: 'minmax(0,2fr) minmax(0,1.5fr) 80px 80px 90px',
          gap: 12, padding: '12px 18px', background: '#fafbfc', borderBottom: '1px solid #eef0f3',
          fontSize: 11, fontWeight: 700, letterSpacing: '0.05em', textTransform: 'uppercase', color: '#9aa0ac',
        }}>
          <span>Product</span><span>Category</span><span>MOQ</span><span>Lead</span>
          <span style={{ textAlign: 'right' }}>Price</span>
        </div>
        {catalog.products.map((p) => (
          <div
            key={p.sku}
            style={{
              display: 'grid', gridTemplateColumns: 'minmax(0,2fr) minmax(0,1.5fr) 80px 80px 90px',
              gap: 12, padding: '13px 18px', alignItems: 'center', borderBottom: '1px solid #f2f3f6',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 11, minWidth: 0 }}>
              <div style={{
                width: 44, height: 44, borderRadius: 8, flexShrink: 0,
                background: 'repeating-linear-gradient(135deg,#f0f2f5 0 6px,#e7eaef 6px 12px)',
                border: '1px solid #e0e3ea',
                overflow: 'hidden',
              }}>
                {p.image && (
                  <img src={p.image} alt={p.name} style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
                )}
              </div>
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: 13.5, fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {p.name}
                </div>
                <div style={{ fontSize: 11.5, color: '#9aa0ac', fontFamily: "'JetBrains Mono', monospace" }}>{p.sku}</div>
              </div>
            </div>
            <span style={{ fontSize: 12.5, color: '#6a7180' }}>{p.categories.join(' · ')}</span>
            <span style={{ fontSize: 13, fontFamily: "'JetBrains Mono', monospace", color: '#3a4253' }}>{p.moq}</span>
            <span style={{ fontSize: 13, color: '#6a7180' }}>{p.lead}</span>
            <span style={{ fontSize: 14, fontWeight: 700, fontFamily: "'JetBrains Mono', monospace", textAlign: 'right' }}>
              {p.currency}{p.price}
            </span>
          </div>
        ))}
      </div>
    </>
  );
}
