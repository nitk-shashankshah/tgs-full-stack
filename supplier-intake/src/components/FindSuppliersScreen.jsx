import React, { useState, useMemo } from 'react';

export default function FindSuppliersScreen({ catalogs }) {
  const [query, setQuery] = useState('');
  const [catFilter, setCatFilter] = useState('All');

  const offers = useMemo(() => {
    const out = [];
    catalogs.forEach((c) => c.products.forEach((p) => out.push({
      name: p.name, sku: p.sku, price: p.price, currency: p.currency,
      moq: p.moq, lead: p.lead, categories: p.categories,
      thumbnail: p.thumbnail ?? null,
      supplierName: c.supplier.name, location: c.supplier.location,
    })));
    return out;
  }, [catalogs]);

  const allCategories = useMemo(() =>
    Array.from(new Set(offers.flatMap((o) => o.categories))).sort(),
    [offers]
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return offers
      .filter((o) => {
        const matchQ = !q
          || o.name.toLowerCase().includes(q)
          || o.supplierName.toLowerCase().includes(q)
          || o.categories.some((c) => c.toLowerCase().includes(q));
        const matchC = catFilter === 'All' || o.categories.includes(catFilter);
        return matchQ && matchC;
      })
      .sort((a, b) => parseFloat(a.price) - parseFloat(b.price));
  }, [offers, query, catFilter]);

  const minPrice = filtered.length ? Math.min(...filtered.map((o) => parseFloat(o.price))) : null;
  const supplierCount = new Set(filtered.map((o) => o.supplierName)).size;
  const searchSummary = `${filtered.length} ${filtered.length === 1 ? 'offer' : 'offers'} · ${supplierCount} ${supplierCount === 1 ? 'supplier' : 'suppliers'}`;

  return (
    <div style={{ maxWidth: 1080, margin: '0 auto', padding: '26px 26px 90px' }}>
      <div style={{ marginBottom: 18 }}>
        <h2 style={{ margin: 0, fontSize: 21, fontWeight: 800, letterSpacing: '-0.02em' }}>Find suppliers</h2>
        <p style={{ margin: '6px 0 0', fontSize: 13.5, color: '#8a90a0' }}>
          Search a product or category to compare every supplier across your catalogues — cheapest first.
        </p>
      </div>

      {/* Search box */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 11,
        background: '#fff', border: '1px solid #e7e9ee', borderRadius: 13,
        padding: '12px 16px', marginBottom: 14, boxShadow: '0 1px 2px rgba(28,34,48,0.04)',
      }}>
        <div style={{ width: 15, height: 15, borderRadius: '50%', border: '2px solid #b3b8c2', flexShrink: 0 }} />
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder='Search "skillet", "cast iron", "stockpot", "linen", a supplier…'
          style={{ flex: 1, minWidth: 0, fontSize: 15, fontWeight: 500, color: '#1c2230' }}
        />
        <span style={{ fontSize: 12.5, fontWeight: 600, color: '#9aa0ac', whiteSpace: 'nowrap' }}>
          {searchSummary}
        </span>
      </div>

      {/* Category chips */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 20 }}>
        {['All', ...allCategories].map((c) => {
          const active = catFilter === c;
          return (
            <button
              key={c}
              onClick={() => setCatFilter(c)}
              style={{
                padding: '6px 13px', borderRadius: 20,
                border: `1px solid ${active ? '#4b56d6' : '#d6d9e0'}`,
                background: active ? '#4b56d6' : '#ffffff',
                color: active ? '#ffffff' : '#5b6473',
                fontSize: 12.5, fontWeight: 600, cursor: 'pointer',
              }}
            >
              {c}
            </button>
          );
        })}
      </div>

      {filtered.length > 0 ? (
        <>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'minmax(0,2.2fr) minmax(0,1.6fr) 72px 92px 112px',
            gap: 14, padding: '0 18px 9px',
            fontSize: 11, fontWeight: 700, letterSpacing: '0.05em', textTransform: 'uppercase', color: '#9aa0ac',
          }}>
            <span>Product</span><span>Supplier</span><span>MOQ</span><span>Lead time</span>
            <span style={{ textAlign: 'right' }}>Unit price</span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {filtered.map((r, i) => {
              const isLow = parseFloat(r.price) === minPrice && filtered.length > 1;
              return (
                <div
                  key={i}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'minmax(0,2.2fr) minmax(0,1.6fr) 72px 92px 112px',
                    gap: 14, alignItems: 'center',
                    background: isLow ? '#f2faf5' : '#ffffff',
                    border: `1px solid ${isLow ? '#bfe3cf' : '#e7e9ee'}`,
                    borderRadius: 13, padding: '13px 18px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
                    <div style={{
                      width: 44, height: 44, borderRadius: 9, flexShrink: 0,
                      background: 'repeating-linear-gradient(135deg,#f0f2f5 0 8px,#e7eaef 8px 16px)',
                      border: '1px solid #e0e3ea', overflow: 'hidden',
                    }}>
                      {r.thumbnail && (
                        <img src={r.thumbnail} alt={r.name} style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }} />
                      )}
                    </div>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: 13.5, fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {r.name}
                      </div>
                      <div style={{ fontSize: 11.5, color: '#9aa0ac' }}>{r.categories.join(' · ')}</div>
                    </div>
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {r.supplierName}
                    </div>
                    <div style={{ fontSize: 11.5, color: '#9aa0ac', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {r.location}
                    </div>
                  </div>
                  <span style={{ fontSize: 13, fontFamily: "'JetBrains Mono', monospace", color: '#3a4253' }}>{r.moq}</span>
                  <span style={{ fontSize: 13, color: '#6a7180' }}>{r.lead}</span>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: 16, fontWeight: 700, fontFamily: "'JetBrains Mono', monospace" }}>
                      {r.currency}{r.price}
                    </div>
                    {isLow && (
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 10.5, fontWeight: 700, color: '#1f9d6b', marginTop: 2 }}>
                        <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#1f9d6b' }} />
                        Lowest price
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      ) : (
        <div style={{
          textAlign: 'center', padding: '54px 20px',
          background: '#fff', border: '1px solid #e7e9ee', borderRadius: 14,
        }}>
          <div style={{ fontSize: 14, fontWeight: 600, color: '#6a7180' }}>No products match your search.</div>
          <div style={{ fontSize: 13, color: '#9aa0ac', marginTop: 5 }}>
            Try a broader term or pick a different category above.
          </div>
        </div>
      )}
    </div>
  );
}
