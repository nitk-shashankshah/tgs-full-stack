import React, { useRef, useState, useEffect } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

function relativeDate(ts) {
  const diff = Date.now() - ts;
  const mins = Math.floor(diff / 60000);
  if (mins < 2) return 'just now';
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} hr ago`;
  const days = Math.floor(hrs / 24);
  return days === 1 ? '1 day ago' : `${days} days ago`;
}

export default function PriceListsScreen({ onPricesUpdated }) {
  const fileRef = useRef(null);
  const [dragover, setDragover] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [processingFile, setProcessingFile] = useState('');
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);       // most recent upload result
  const [history, setHistory] = useState([]);        // all past price list uploads

  useEffect(() => {
    fetch(`${API_BASE}/api/pricelists`)
      .then((r) => r.json())
      .then(setHistory)
      .catch(() => {});
  }, []);

  async function handleFile(file) {
    if (!file || !file.name.toLowerCase().endsWith('.pdf')) {
      setError('Please upload a PDF file.');
      return;
    }
    setError(null);
    setResult(null);
    setProcessing(true);
    setProcessingFile(file.name);

    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch(`${API_BASE}/api/upload-pricelist`, { method: 'POST', body: formData });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(err.detail || 'Upload failed');
      }
      const data = await res.json();
      setResult(data);
      setHistory((prev) => [data, ...prev]);
      if (data.updates?.length > 0) onPricesUpdated?.();
    } catch (err) {
      setError(err.message || 'Something went wrong');
    } finally {
      setProcessing(false);
    }
  }

  return (
    <div style={{ maxWidth: 820, margin: '0 auto', padding: '28px 26px 90px' }}>
      <div style={{ marginBottom: 22 }}>
        <h2 style={{ margin: 0, fontSize: 21, fontWeight: 800, letterSpacing: '-0.02em' }}>Price lists</h2>
        <p style={{ margin: '6px 0 0', fontSize: 13.5, color: '#8a90a0' }}>
          Upload a supplier price list PDF to automatically fill missing prices across your catalogues.
        </p>
      </div>

      {/* Upload zone */}
      {!processing && (
        <div
          onClick={() => fileRef.current?.click()}
          onDrop={(e) => { e.preventDefault(); setDragover(false); const f = e.dataTransfer.files?.[0]; if (f) handleFile(f); }}
          onDragOver={(e) => { e.preventDefault(); if (!dragover) setDragover(true); }}
          onDragLeave={() => setDragover(false)}
          style={{
            border: `2px dashed ${dragover ? '#4b56d6' : '#cfd3dc'}`,
            background: dragover ? '#eef0fc' : '#fbfbfd',
            borderRadius: 16, padding: '36px 32px', textAlign: 'center', cursor: 'pointer',
            transition: 'border-color .15s, background .15s', marginBottom: 22,
          }}
        >
          <div style={{
            width: 46, height: 46, borderRadius: 13, background: '#eef0fc',
            display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 14px',
          }}>
            <span style={{ fontSize: 20 }}>₹</span>
          </div>
          <div style={{ fontSize: 15, fontWeight: 700, marginBottom: 4 }}>Drop a price list PDF here</div>
          <div style={{ fontSize: 13, color: '#8a90a0', marginBottom: 16 }}>or click to browse</div>
          <button
            onClick={(e) => { e.stopPropagation(); fileRef.current?.click(); }}
            style={{
              padding: '9px 18px', borderRadius: 10, background: '#4b56d6', color: '#fff',
              fontSize: 13.5, fontWeight: 600, cursor: 'pointer', boxShadow: '0 2px 6px rgba(75,86,214,0.28)',
            }}
          >
            Browse files
          </button>
          <input type="file" accept=".pdf" ref={fileRef} onChange={(e) => { if (e.target.files?.[0]) handleFile(e.target.files[0]); }} style={{ display: 'none' }} />
        </div>
      )}

      {/* Processing state */}
      {processing && (
        <div style={{
          background: '#fff', border: '1px solid #e7e9ee', borderRadius: 16,
          padding: '28px 30px', marginBottom: 22, display: 'flex', alignItems: 'center', gap: 18,
        }}>
          <div style={{
            width: 40, height: 40, borderRadius: '50%',
            border: '3px solid #eef0fc', borderTopColor: '#4b56d6',
            flexShrink: 0, animation: 'spin 0.8s linear infinite',
          }} />
          <div>
            <div style={{ fontSize: 14, fontWeight: 700 }}>Extracting prices from {processingFile}…</div>
            <div style={{ fontSize: 12.5, color: '#8a90a0', marginTop: 3 }}>
              Matching against your catalogues — this may take a moment.
            </div>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div style={{
          padding: '12px 16px', borderRadius: 10, background: '#fbeee9',
          border: '1px solid #eccabc', fontSize: 13.5, color: '#a93c26', marginBottom: 18,
        }}>
          {error}
        </div>
      )}

      {/* Latest result */}
      {result && (
        <ResultCard result={result} isLatest />
      )}

      {/* History */}
      {history.filter((h) => h.id !== result?.id).length > 0 && (
        <div style={{ marginTop: result ? 24 : 0 }}>
          <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: '#9aa0ac', marginBottom: 12 }}>
            Previous uploads
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {history.filter((h) => h.id !== result?.id).map((h) => (
              <ResultCard key={h.id} result={h} />
            ))}
          </div>
        </div>
      )}

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}

function ResultCard({ result, isLatest }) {
  const [open, setOpen] = useState(isLatest);
  const updated = result.updates?.length ?? 0;
  const extracted = result.productsExtracted ?? 0;

  return (
    <div style={{ background: '#fff', border: '1px solid #e7e9ee', borderRadius: 14, overflow: 'hidden' }}>
      {/* Header row */}
      <div
        onClick={() => setOpen((v) => !v)}
        style={{
          display: 'flex', alignItems: 'center', gap: 14, padding: '14px 18px', cursor: 'pointer',
        }}
      >
        <div style={{
          width: 36, height: 44, borderRadius: 6, flexShrink: 0,
          background: 'repeating-linear-gradient(135deg,#eef0f3 0 7px,#e4e7ed 7px 14px)',
          border: '1px solid #e0e3ea',
        }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 13.5, fontWeight: 600, fontFamily: "'JetBrains Mono', monospace", whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {result.file}
          </div>
          <div style={{ fontSize: 11.5, color: '#9aa0ac', marginTop: 1 }}>
            {result.supplierName || 'Unknown supplier'} · {relativeDate(result.uploadedAt)}
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: '#6a7180' }}>
            {extracted} prices extracted
          </span>
          {updated > 0 ? (
            <span style={{
              display: 'inline-flex', alignItems: 'center', gap: 5, padding: '4px 10px',
              borderRadius: 20, background: '#e7f6ef', border: '1px solid #bfe3cf',
              fontSize: 12, fontWeight: 700, color: '#1f9d6b',
            }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#1f9d6b' }} />
              {updated} updated
            </span>
          ) : (
            <span style={{
              display: 'inline-flex', alignItems: 'center', gap: 5, padding: '4px 10px',
              borderRadius: 20, background: '#f6f7f9', border: '1px solid #e7e9ee',
              fontSize: 12, fontWeight: 700, color: '#9aa0ac',
            }}>
              No matches
            </span>
          )}
          <span style={{ fontSize: 14, color: '#c2c7d0', transform: open ? 'rotate(90deg)' : 'none', transition: 'transform .2s' }}>›</span>
        </div>
      </div>

      {/* Updates table */}
      {open && result.updates?.length > 0 && (
        <div style={{ borderTop: '1px solid #eef0f3' }}>
          <div style={{
            display: 'grid', gridTemplateColumns: 'minmax(0,2fr) minmax(0,1.4fr) 110px 100px',
            gap: 12, padding: '10px 18px', background: '#fafbfc',
            fontSize: 11, fontWeight: 700, letterSpacing: '0.05em', textTransform: 'uppercase', color: '#9aa0ac',
          }}>
            <span>Product</span><span>Catalogue</span><span>Match</span><span style={{ textAlign: 'right' }}>Price set</span>
          </div>
          {result.updates.map((u, i) => (
            <div
              key={i}
              style={{
                display: 'grid', gridTemplateColumns: 'minmax(0,2fr) minmax(0,1.4fr) 110px 100px',
                gap: 12, padding: '11px 18px', alignItems: 'center',
                borderTop: i > 0 ? '1px solid #f2f3f6' : undefined,
              }}
            >
              <div style={{ fontSize: 13.5, fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {u.productName}
              </div>
              <div style={{ fontSize: 12, color: '#6a7180', fontFamily: "'JetBrains Mono', monospace", whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {u.catalogFile}
              </div>
              <span style={{
                display: 'inline-flex', alignItems: 'center', gap: 5, padding: '3px 8px',
                borderRadius: 20, fontSize: 11.5, fontWeight: 600,
                background: u.matchType === 'sku' ? '#eef0fc' : '#f6f7f9',
                color: u.matchType === 'sku' ? '#3a44b8' : '#6a7180',
                width: 'fit-content',
              }}>
                {u.matchType === 'sku' ? 'SKU' : 'Name'}
              </span>
              <div style={{ textAlign: 'right', fontSize: 14, fontWeight: 700, fontFamily: "'JetBrains Mono', monospace" }}>
                {u.currency}{u.newPrice}
              </div>
            </div>
          ))}
        </div>
      )}

      {open && (!result.updates || result.updates.length === 0) && (
        <div style={{ borderTop: '1px solid #eef0f3', padding: '18px 20px', fontSize: 13.5, color: '#9aa0ac' }}>
          No products matched — no prices were updated. Make sure the supplier's catalog has been uploaded first.
        </div>
      )}
    </div>
  );
}
