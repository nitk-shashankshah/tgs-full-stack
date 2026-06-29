import React, { useState } from 'react';

const API_BASE = 'http://localhost:8000';

const EXAMPLES = [
  'I want to create a gift hamper for ₹5000',
  'Find me shirts and wallets combinations for ₹3000',
  'Suggest eco-friendly products under ₹2000',
  'Corporate gifting kit for ₹10000',
];

export default function CombinationsScreen() {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  async function handleSearch(q) {
    const text = (q ?? query).trim();
    if (!text) return;
    setQuery(text);
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch(`${API_BASE}/api/combinations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: text }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Request failed' }));
        throw new Error(err.detail || 'Request failed');
      }
      setResult(await res.json());
    } catch (err) {
      setError(err.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '28px 26px 90px' }}>
      <div style={{ marginBottom: 22 }}>
        <h2 style={{ margin: 0, fontSize: 21, fontWeight: 800, letterSpacing: '-0.02em' }}>Product combinations</h2>
        <p style={{ margin: '6px 0 0', fontSize: 13.5, color: '#8a90a0' }}>
          Describe what you're looking for and AI will suggest product combinations from your catalogues.
        </p>
      </div>

      {/* Search input */}
      <div style={{
        background: '#fff', border: '1px solid #e7e9ee', borderRadius: 14,
        padding: '14px 16px', marginBottom: 14,
        boxShadow: '0 1px 4px rgba(28,34,48,0.06)',
        display: 'flex', alignItems: 'flex-end', gap: 12,
      }}>
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSearch(); } }}
          placeholder='e.g. "I want to create a gift hamper for ₹5000" or "shirts and wallets under ₹3000"'
          rows={2}
          style={{
            flex: 1, fontSize: 15, fontWeight: 500, color: '#1c2230',
            resize: 'none', lineHeight: 1.5,
          }}
        />
        <button
          onClick={() => handleSearch()}
          disabled={loading || !query.trim()}
          style={{
            flexShrink: 0, padding: '10px 20px', borderRadius: 10,
            background: loading || !query.trim() ? '#c5c9e8' : '#4b56d6',
            color: '#fff', fontSize: 13.5, fontWeight: 700,
            cursor: loading || !query.trim() ? 'default' : 'pointer',
            transition: 'background .15s',
          }}
        >
          {loading ? 'Finding…' : 'Find combinations'}
        </button>
      </div>

      {/* Example chips */}
      {!result && !loading && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 28 }}>
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              onClick={() => handleSearch(ex)}
              style={{
                padding: '7px 13px', borderRadius: 20, fontSize: 12.5, fontWeight: 600,
                border: '1px solid #d6d9e0', background: '#fff', color: '#5b6473',
                cursor: 'pointer',
              }}
            >
              {ex}
            </button>
          ))}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div style={{
          background: '#fff', border: '1px solid #e7e9ee', borderRadius: 14,
          padding: '36px', textAlign: 'center',
        }}>
          <div style={{
            width: 36, height: 36, borderRadius: '50%',
            border: '3px solid #eef0fc', borderTopColor: '#4b56d6',
            margin: '0 auto 14px', animation: 'spin 0.8s linear infinite',
          }} />
          <div style={{ fontSize: 14, fontWeight: 700, color: '#1c2230' }}>Finding the best combinations…</div>
          <div style={{ fontSize: 12.5, color: '#9aa0ac', marginTop: 4 }}>Claude is searching across all your catalogues</div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div style={{
          padding: '12px 16px', borderRadius: 10, background: '#fbeee9',
          border: '1px solid #eccabc', fontSize: 13.5, color: '#a93c26',
        }}>
          {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <div>
              <div style={{ fontSize: 13.5, fontWeight: 600, color: '#1c2230' }}>
                {result.query_understanding}
              </div>
              <div style={{ fontSize: 12, color: '#9aa0ac', marginTop: 2 }}>
                {result.combinations?.length ?? 0} combinations found
              </div>
            </div>
            <button
              onClick={() => { setResult(null); setQuery(''); }}
              style={{
                padding: '7px 13px', borderRadius: 9, border: '1px solid #d6d9e0',
                background: '#fff', fontSize: 12.5, fontWeight: 600, color: '#5b6473', cursor: 'pointer',
              }}
            >
              New search
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {result.combinations?.map((combo, i) => (
              <CombinationCard
                key={i}
                combo={combo}
                budget={result.budget}
                currency={result.currency}
                index={i}
              />
            ))}
          </div>
        </>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}

function CombinationCard({ combo, budget, currency, index }) {
  const [generating, setGenerating] = React.useState(false);

  const withinBudget = !budget || combo.total <= budget;
  const pct = budget ? Math.min(100, Math.round(combo.total / budget * 100)) : null;

  const accent = ['#4b56d6', '#1f9d6b', '#c98a1a', '#c0492f'][index % 4];
  const accentBg = ['#eef0fc', '#e7f6ef', '#fdf8ec', '#fbeee9'][index % 4];
  const accentBorder = ['#c5c9e8', '#bfe3cf', '#ecd9a6', '#eccabc'][index % 4];

  async function handleGenerateBrochure() {
    setGenerating(true);
    try {
      const res = await fetch(`${API_BASE}/api/generate-brochure`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: combo.title,
          description: combo.description ?? '',
          currency: combo.currency ?? currency,
          total: combo.total,
          products: (combo.products ?? []).map((p) => ({
            name: p.name,
            price: p.price,
            currency: p.currency ?? combo.currency ?? currency,
            quantity: p.quantity ?? 1,
            supplier: p.supplier ?? '',
            categories: p.categories ?? [],
            thumbnail: p.thumbnail ?? null,
          })),
        }),
      });
      if (!res.ok) throw new Error('Failed to generate brochure');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const safeName = combo.title.replace(/[^a-zA-Z0-9 ]/g, '').trim().replace(/ +/g, '_') || 'brochure';
      a.download = `${safeName}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert(err.message || 'Brochure generation failed');
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div style={{ background: '#fff', border: `1px solid ${accentBorder}`, borderRadius: 16, overflow: 'hidden' }}>
      {/* Card header */}
      <div style={{ padding: '16px 20px', borderBottom: '1px solid #f2f3f6', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginBottom: 4 }}>
            <span style={{
              width: 22, height: 22, borderRadius: 7, background: accentBg,
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 11, fontWeight: 800, color: accent, flexShrink: 0,
            }}>
              {index + 1}
            </span>
            <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, letterSpacing: '-0.01em' }}>{combo.title}</h3>
          </div>
          <p style={{ margin: 0, fontSize: 13, color: '#6a7180', lineHeight: 1.5 }}>{combo.description}</p>
        </div>

        <div style={{ flexShrink: 0, textAlign: 'right', display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 8 }}>
          <div style={{ fontSize: 20, fontWeight: 800, fontFamily: "'JetBrains Mono', monospace", color: accent }}>
            {combo.currency ?? currency}{combo.total?.toLocaleString('en-IN')}
          </div>
          {budget && (
            <div style={{ fontSize: 11, fontWeight: 600, color: withinBudget ? '#1f9d6b' : '#c0492f' }}>
              {withinBudget ? `${pct}% of budget` : 'Exceeds budget'}
            </div>
          )}
          <button
            onClick={handleGenerateBrochure}
            disabled={generating}
            style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '7px 12px', borderRadius: 8,
              background: generating ? '#f0ede8' : '#FAF6F0',
              border: '1px solid #D4B483',
              color: generating ? '#8A7A68' : '#B8860B',
              fontSize: 12, fontWeight: 700,
              cursor: generating ? 'default' : 'pointer',
              transition: 'all .15s',
              whiteSpace: 'nowrap',
            }}
          >
            <svg width="13" height="13" viewBox="0 0 16 16" fill="none" style={{ flexShrink: 0 }}>
              <path d="M3 4h10v1.5H3V4zm0 3h10v1.5H3V7zm0 3h6v1.5H3V10z" fill="currentColor" />
              <rect x="1.5" y="1.5" width="13" height="13" rx="1.5" stroke="currentColor" strokeWidth="1.3" fill="none" />
            </svg>
            {generating ? 'Generating…' : 'Generate brochure'}
          </button>
        </div>
      </div>

      {/* Budget bar */}
      {budget && (
        <div style={{ height: 3, background: '#f2f3f6' }}>
          <div style={{
            height: '100%', width: `${pct}%`, maxWidth: '100%',
            background: withinBudget ? accent : '#c0492f',
            transition: 'width .6s ease',
          }} />
        </div>
      )}

      {/* Product list */}
      <div style={{ padding: '4px 0' }}>
        {combo.products?.map((p, j) => (
          <div
            key={j}
            style={{
              display: 'flex', alignItems: 'center', gap: 13,
              padding: '11px 20px',
              borderTop: j > 0 ? '1px solid #f5f6f8' : undefined,
            }}
          >
            <div style={{
              width: 46, height: 46, borderRadius: 9, flexShrink: 0,
              background: 'repeating-linear-gradient(135deg,#f0f2f5 0 8px,#e7eaef 8px 16px)',
              border: '1px solid #e0e3ea', overflow: 'hidden',
            }}>
              {p.thumbnail && (
                <img src={p.thumbnail} alt={p.name} style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
              )}
            </div>

            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 13.5, fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {p.name}
              </div>
              <div style={{ fontSize: 11.5, color: '#9aa0ac', marginTop: 1 }}>
                {p.supplier}
                {p.categories?.length > 0 && ` · ${p.categories[0]}`}
              </div>
            </div>

            {p.quantity > 1 && (
              <span style={{ fontSize: 12, fontWeight: 600, color: '#6a7180', flexShrink: 0 }}>
                ×{p.quantity}
              </span>
            )}

            <div style={{ flexShrink: 0, textAlign: 'right' }}>
              <div style={{ fontSize: 14, fontWeight: 700, fontFamily: "'JetBrains Mono', monospace" }}>
                {p.currency}{(p.price * (p.quantity ?? 1)).toLocaleString('en-IN')}
              </div>
              {p.quantity > 1 && (
                <div style={{ fontSize: 11, color: '#9aa0ac' }}>{p.currency}{p.price} each</div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Footer total */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '11px 20px', borderTop: '1px solid #f2f3f6',
        background: accentBg,
      }}>
        <span style={{ fontSize: 12.5, fontWeight: 600, color: '#6a7180' }}>
          {combo.products?.length} product{combo.products?.length !== 1 ? 's' : ''}
        </span>
        <span style={{ fontSize: 14, fontWeight: 800, fontFamily: "'JetBrains Mono', monospace", color: accent }}>
          Total: {combo.currency ?? currency}{combo.total?.toLocaleString('en-IN')}
        </span>
      </div>
    </div>
  );
}
