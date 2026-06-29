import React, { useState } from 'react';

function confMeta(level) {
  if (level === 'med') return { label2: 'Confirm', dot: '#c98a1a', text: '#9a6a14', flagged: true, bg: '#fdf8ec', border: '#ecd9a6' };
  if (level === 'low') return { label2: 'Verify', dot: '#c0492f', text: '#a93c26', flagged: true, bg: '#fbeee9', border: '#eccabc' };
  return { label2: 'OK', dot: '#1f9d6b', text: '#1f9d6b', flagged: false, bg: '#ffffff', border: '#e3e6ec' };
}

function FieldBox({ label, value, onChange, conf, onConfirm, style }) {
  const m = confMeta(conf);
  return (
    <div style={{ border: `1px solid ${m.border}`, background: m.bg, borderRadius: 11, padding: '9px 12px', ...style }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, marginBottom: 3 }}>
        <label style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase', color: '#9aa0ac' }}>
          {label}
        </label>
        {m.flagged && (
          <button
            onClick={onConfirm}
            style={{
              display: 'flex', alignItems: 'center', gap: 5, padding: '2px 7px', borderRadius: 20,
              background: '#fff', border: `1px solid ${m.border}`, fontSize: 10.5, fontWeight: 700,
              color: m.text, cursor: 'pointer',
            }}
          >
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: m.dot }} />
            {m.label2}
          </button>
        )}
      </div>
      <input value={value} onChange={onChange} style={{ width: '100%', fontSize: 13.5, fontWeight: 600, color: '#1c2230' }} />
    </div>
  );
}

export default function ReviewScreen({ fileName, supplier, products, onUpdateSupplier, onConfirmSupplier, onUpdateProduct, onConfirmProductField, onRemoveTag, onToggleReviewed, onApprove, onReset }) {
  const [onlyFlagged, setOnlyFlagged] = useState(false);

  const supplierFieldDefs = [
    ['name', 'Supplier name'], ['contact', 'Primary contact'],
    ['email', 'Email'], ['phone', 'Phone'],
    ['location', 'Location'], ['terms', 'Terms'],
  ];

  const fkeys = ['name', 'sku', 'price', 'moq', 'specs'];
  const enrichedProducts = products.map((p) => {
    const meta = {};
    fkeys.forEach((k) => { meta[k] = confMeta(p.conf[k]); });
    const flaggedCount = fkeys.filter((k) => meta[k].flagged).length;
    return { ...p, meta, flaggedCount };
  });

  const flaggedTotal = enrichedProducts.reduce((a, p) => a + p.flaggedCount, 0)
    + supplierFieldDefs.filter(([key]) => confMeta(supplier.conf[key]).flagged).length;

  const visibleProducts = onlyFlagged ? enrichedProducts.filter((p) => p.flaggedCount > 0) : enrichedProducts;
  const total = products.length;
  const reviewedCount = products.filter((p) => p.reviewed).length;

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '22px 26px 90px' }}>
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 20, flexWrap: 'wrap', marginBottom: 20 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', lineHeight: 1.2 }}>
            <h2 style={{ margin: 0, fontSize: 21, fontWeight: 800, letterSpacing: '-0.02em', whiteSpace: 'nowrap' }}>
              Review extracted data
            </h2>
            <span style={{
              fontSize: 12, fontWeight: 600, fontFamily: "'JetBrains Mono', monospace",
              color: '#6a7180', background: '#eef0f3', padding: '3px 9px', borderRadius: 7, whiteSpace: 'nowrap',
            }}>
              {fileName}
            </span>
          </div>
          <p style={{ margin: '6px 0 0', fontSize: 13.5, color: '#8a90a0' }}>
            Edit any field, confirm flagged values, then export to your catalogue.
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {flaggedTotal > 0 && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: 7, padding: '8px 12px',
              borderRadius: 10, background: '#fdf8ec', border: '1px solid #ecd9a6',
            }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#c98a1a' }} />
              <span style={{ fontSize: 12.5, fontWeight: 600, color: '#9a6a14' }}>
                {flaggedTotal} fields need review
              </span>
            </div>
          )}
          <button onClick={onReset} style={{
            padding: '9px 15px', borderRadius: 10, border: '1px solid #d6d9e0', background: '#fff',
            fontSize: 13.5, fontWeight: 600, color: '#5b6473', cursor: 'pointer',
          }}>
            Re-upload
          </button>
          <button onClick={onApprove} style={{
            padding: '9px 17px', borderRadius: 10, background: '#4b56d6', color: '#fff',
            fontSize: 13.5, fontWeight: 700, cursor: 'pointer', boxShadow: '0 2px 6px rgba(75,86,214,0.30)',
          }}>
            Approve &amp; export ({total})
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,360px) minmax(0,1fr)', gap: 24, alignItems: 'start' }}>
        {/* Document preview */}
        <div style={{ position: 'sticky', top: 0, background: '#fff', border: '1px solid #e7e9ee', borderRadius: 16, overflow: 'hidden' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '13px 16px', borderBottom: '1px solid #eef0f3' }}>
            <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: '#9aa0ac' }}>
              Source document
            </span>
            <span style={{ fontSize: 11.5, fontWeight: 500, fontFamily: "'JetBrains Mono', monospace", color: '#9aa0ac' }}>PDF</span>
          </div>
          <div style={{ padding: 16 }}>
            <div style={{
              position: 'relative', aspectRatio: '3/4', borderRadius: 9,
              border: '1px solid #e0e3ea',
              background: 'repeating-linear-gradient(135deg,#f0f2f5 0 11px,#e7eaef 11px 22px)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: '#a7adb9', letterSpacing: '0.04em' }}>
                PDF page 1 · catalogue
              </span>
              <div style={{
                position: 'absolute', left: '14%', top: '26%', width: '34%', height: '9%',
                border: '2px solid #4b56d6', borderRadius: 4, background: 'rgba(75,86,214,0.10)',
              }} />
              <div style={{
                position: 'absolute', left: '54%', top: '58%', width: '32%', height: '13%',
                border: '2px solid #4b56d6', borderRadius: 4, background: 'rgba(75,86,214,0.10)',
              }} />
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
              {[true, false, false, false].map((active, i) => (
                <div key={i} style={{
                  flex: 1, aspectRatio: '3/4', borderRadius: 6,
                  border: active ? '2px solid #4b56d6' : '1px solid #e0e3ea',
                  background: 'repeating-linear-gradient(135deg,#f0f2f5 0 7px,#e7eaef 7px 14px)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  {i === 3 && <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: '#a7adb9' }}>+3</span>}
                </div>
              ))}
            </div>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 7, marginTop: 14,
              padding: '9px 11px', borderRadius: 9, background: '#f6f7f9',
            }}>
              <div style={{ width: 11, height: 11, borderRadius: 3, border: '2px solid #4b56d6', background: 'rgba(75,86,214,0.12)', flexShrink: 0 }} />
              <span style={{ fontSize: 11.5, color: '#8a90a0', lineHeight: 1.35 }}>
                Highlights mark where each value was found.
              </span>
            </div>
          </div>
        </div>

        {/* Data column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          {/* Supplier */}
          <div style={{ background: '#fff', border: '1px solid #e7e9ee', borderRadius: 16, padding: '18px 20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
                <div style={{ width: 26, height: 26, borderRadius: 7, background: '#eef0fc', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <div style={{ width: 9, height: 9, borderRadius: '50%', border: '2px solid #4b56d6' }} />
                </div>
                <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700 }}>Supplier</h3>
              </div>
              <span style={{ fontSize: 11.5, fontWeight: 600, fontFamily: "'JetBrains Mono', monospace", color: '#9aa0ac' }}>1 detected</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 11 }}>
              {supplierFieldDefs.map(([key, label]) => (
                <FieldBox
                  key={key}
                  label={label}
                  value={supplier[key]}
                  conf={supplier.conf[key]}
                  onChange={(e) => onUpdateSupplier(key, e.target.value)}
                  onConfirm={() => onConfirmSupplier(key)}
                />
              ))}
            </div>
          </div>

          {/* Products header */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 14, flexWrap: 'wrap', padding: '0 2px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
              <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700 }}>Products</h3>
              <span style={{
                fontSize: 12, fontWeight: 700, fontFamily: "'JetBrains Mono', monospace",
                color: '#4b56d6', background: '#eef0fc', padding: '2px 8px', borderRadius: 7,
              }}>
                {total}
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
              <span style={{ fontSize: 12.5, fontWeight: 600, color: '#8a90a0' }}>
                {reviewedCount} of {total} reviewed
              </span>
              <button
                onClick={() => setOnlyFlagged((v) => !v)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 7, padding: '6px 11px',
                  borderRadius: 9,
                  border: `1px solid ${onlyFlagged ? '#ecd9a6' : '#d6d9e0'}`,
                  background: onlyFlagged ? '#fdf8ec' : '#ffffff',
                  fontSize: 12.5, fontWeight: 600,
                  color: onlyFlagged ? '#9a6a14' : '#5b6473',
                  cursor: 'pointer',
                }}
              >
                <span style={{ width: 7, height: 7, borderRadius: '50%', background: '#c98a1a' }} />
                Only needs review
              </button>
            </div>
          </div>

          {/* Product cards */}
          {visibleProducts.map((p) => (
            <ProductCard
              key={p.id}
              p={p}
              onUpdateProduct={onUpdateProduct}
              onConfirmProductField={onConfirmProductField}
              onRemoveTag={onRemoveTag}
              onToggleReviewed={onToggleReviewed}
            />
          ))}

          {onlyFlagged && visibleProducts.length === 0 && (
            <div style={{ textAlign: 'center', padding: 34, color: '#9aa0ac', fontSize: 13.5 }}>
              All products reviewed — nothing flagged. 🎉
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ProductCard({ p, onUpdateProduct, onConfirmProductField, onRemoveTag, onToggleReviewed }) {
  return (
    <div style={{
      background: '#fff',
      border: `1px solid ${p.reviewed ? '#bfe3cf' : p.flaggedCount > 0 ? '#ecd9a6' : '#e7e9ee'}`,
      borderRadius: 16, padding: 16, display: 'flex', gap: 16,
    }}>
      {/* Product image */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, flexShrink: 0, width: 108 }}>
        <div style={{
          width: 108, height: 108, borderRadius: 11, border: '1px solid #e0e3ea', overflow: 'hidden',
          background: 'repeating-linear-gradient(135deg,#f0f2f5 0 9px,#e7eaef 9px 18px)',
          display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 3,
        }}>
          {p.image ? (
            <img
              src={p.image}
              alt={p.name}
              style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
            />
          ) : (
            <>
              <div style={{ width: 22, height: 22, borderRadius: 5, border: '2px solid #c2c7d0' }} />
              <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 9, color: '#a7adb9' }}>no image</span>
            </>
          )}
        </div>
        <button style={{ fontSize: 11.5, fontWeight: 600, color: '#4b56d6', cursor: 'pointer', textAlign: 'center' }}>
          Replace image
        </button>
      </div>

      {/* Fields */}
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 12 }}>
        {/* Name + Price */}
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
          <ProductFieldBox
            label="Product name"
            value={p.name}
            conf={p.conf.name}
            onChange={(e) => onUpdateProduct(p.id, 'name', e.target.value)}
            onConfirm={() => onConfirmProductField(p.id, 'name')}
            inputStyle={{ fontSize: 15.5, fontWeight: 700, letterSpacing: '-0.01em' }}
            style={{ flex: 1 }}
          />
          <div style={{
            flexShrink: 0, width: 118,
            border: `1px solid ${confMeta(p.conf.price).border}`,
            background: confMeta(p.conf.price).bg,
            borderRadius: 11, padding: '8px 12px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 6, marginBottom: 2 }}>
              <label style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase', color: '#9aa0ac' }}>
                Unit price
              </label>
              {confMeta(p.conf.price).flagged && (
                <button
                  onClick={() => onConfirmProductField(p.id, 'price')}
                  style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 0,
                    width: 15, height: 15, borderRadius: '50%', background: confMeta(p.conf.price).dot, cursor: 'pointer',
                  }}
                >
                  <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#fff' }} />
                </button>
              )}
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 3 }}>
              <span style={{ fontSize: 14, fontWeight: 600, color: '#8a90a0', fontFamily: "'JetBrains Mono', monospace" }}>
                {p.currency}
              </span>
              <input
                value={p.price}
                onChange={(e) => onUpdateProduct(p.id, 'price', e.target.value)}
                style={{ width: '100%', fontSize: 16, fontWeight: 700, color: '#1c2230', fontFamily: "'JetBrains Mono', monospace" }}
              />
            </div>
          </div>
        </div>

        {/* SKU + MOQ */}
        <div style={{ display: 'flex', gap: 11 }}>
          <ProductFieldBox
            label="SKU"
            value={p.sku}
            conf={p.conf.sku}
            onChange={(e) => onUpdateProduct(p.id, 'sku', e.target.value)}
            onConfirm={() => onConfirmProductField(p.id, 'sku')}
            inputStyle={{ fontFamily: "'JetBrains Mono', monospace" }}
            style={{ flex: 1 }}
          />
          <ProductFieldBox
            label="MOQ (units)"
            value={p.moq}
            conf={p.conf.moq}
            onChange={(e) => onUpdateProduct(p.id, 'moq', e.target.value)}
            onConfirm={() => onConfirmProductField(p.id, 'moq')}
            inputStyle={{ fontFamily: "'JetBrains Mono', monospace" }}
            style={{ flex: 1 }}
          />
        </div>

        {/* Specs */}
        <div style={{
          border: `1px solid ${confMeta(p.conf.specs).border}`,
          background: confMeta(p.conf.specs).bg,
          borderRadius: 11, padding: '8px 12px',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, marginBottom: 2 }}>
            <label style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase', color: '#9aa0ac' }}>
              Description &amp; specs
            </label>
            {confMeta(p.conf.specs).flagged && (
              <button
                onClick={() => onConfirmProductField(p.id, 'specs')}
                style={{
                  display: 'flex', alignItems: 'center', gap: 5, padding: '2px 7px', borderRadius: 20,
                  background: '#fff', border: `1px solid ${confMeta(p.conf.specs).border}`,
                  fontSize: 10.5, fontWeight: 700, color: confMeta(p.conf.specs).text, cursor: 'pointer',
                }}
              >
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: confMeta(p.conf.specs).dot }} />
                {confMeta(p.conf.specs).label2}
              </button>
            )}
          </div>
          <textarea
            rows={2}
            value={p.specs}
            onChange={(e) => onUpdateProduct(p.id, 'specs', e.target.value)}
            style={{ width: '100%', fontSize: 13, fontWeight: 500, color: '#3a4253', lineHeight: 1.45 }}
          />
        </div>

        {/* Tags + Review button */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 7, flexWrap: 'wrap' }}>
            <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase', color: '#9aa0ac' }}>
              Category
            </span>
            {p.categories.map((t) => (
              <span key={t} style={{
                display: 'inline-flex', alignItems: 'center', gap: 5, padding: '4px 7px 4px 10px',
                borderRadius: 7, background: '#eef0fc', color: '#3a44b8', fontSize: 12, fontWeight: 600,
              }}>
                {t}
                <span
                  onClick={() => onRemoveTag(p.id, t)}
                  style={{ cursor: 'pointer', color: '#8189d8', fontWeight: 700, lineHeight: 1 }}
                >
                  ×
                </span>
              </span>
            ))}
            <button style={{
              padding: '4px 9px', borderRadius: 7, border: '1px dashed #cfd3dc',
              fontSize: 12, fontWeight: 600, color: '#9aa0ac', cursor: 'pointer',
            }}>
              + Add
            </button>
          </div>
          <button
            onClick={() => onToggleReviewed(p.id)}
            style={{
              display: 'flex', alignItems: 'center', gap: 7, padding: '7px 13px', borderRadius: 9,
              border: `1px solid ${p.reviewed ? '#bfe3cf' : '#d6d9e0'}`,
              background: p.reviewed ? '#e7f6ef' : '#ffffff',
              fontSize: 12.5, fontWeight: 700,
              color: p.reviewed ? '#1f9d6b' : '#5b6473',
              cursor: 'pointer',
            }}
          >
            <span style={{
              width: 13, height: 13, borderRadius: '50%',
              border: `2px solid ${p.reviewed ? '#1f9d6b' : '#5b6473'}`,
              background: p.reviewed ? '#1f9d6b' : 'transparent',
            }} />
            {p.reviewed ? 'Reviewed' : 'Mark reviewed'}
          </button>
        </div>
      </div>
    </div>
  );
}

function ProductFieldBox({ label, value, conf, onChange, onConfirm, inputStyle, style }) {
  const m = confMeta(conf);
  return (
    <div style={{ border: `1px solid ${m.border}`, background: m.bg, borderRadius: 11, padding: '8px 12px', ...style }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, marginBottom: 2 }}>
        <label style={{ fontSize: 11, fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase', color: '#9aa0ac' }}>
          {label}
        </label>
        {m.flagged && (
          <button
            onClick={onConfirm}
            style={{
              display: 'flex', alignItems: 'center', gap: 5, padding: '2px 7px', borderRadius: 20,
              background: '#fff', border: `1px solid ${m.border}`, fontSize: 10.5, fontWeight: 700,
              color: m.text, cursor: 'pointer',
            }}
          >
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: m.dot }} />
            {m.label2}
          </button>
        )}
      </div>
      <input value={value} onChange={onChange} style={{ width: '100%', fontSize: 13.5, fontWeight: 600, color: '#1c2230', ...inputStyle }} />
    </div>
  );
}
