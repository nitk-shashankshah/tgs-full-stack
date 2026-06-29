import React from 'react';
import { PROCESSING_STEPS } from '../data/catalogs';

export default function ProcessingScreen({ fileName, stepIndex }) {
  const pct = Math.round(Math.min(Math.max(stepIndex, 0), PROCESSING_STEPS.length) / PROCESSING_STEPS.length * 100);

  return (
    <div style={{ minHeight: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '48px 24px' }}>
      <div style={{
        width: '100%', maxWidth: 520, background: '#fff', border: '1px solid #e7e9ee',
        borderRadius: 18, padding: '32px 34px', boxShadow: '0 12px 40px -16px rgba(28,34,48,0.18)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 13, marginBottom: 22 }}>
          <div style={{
            width: 42, height: 52, borderRadius: 6, flexShrink: 0,
            background: 'repeating-linear-gradient(135deg,#eef0f3 0 7px,#e4e7ed 7px 14px)',
            border: '1px solid #e0e3ea',
          }} />
          <div style={{ minWidth: 0 }}>
            <div style={{
              fontSize: 14, fontWeight: 600, fontFamily: "'JetBrains Mono', monospace",
              whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
            }}>
              {fileName}
            </div>
            <div style={{ fontSize: 12.5, color: '#9aa0ac', marginTop: 2 }}>
              Extracting with AI — this takes a few seconds
            </div>
          </div>
        </div>

        <div style={{ height: 7, borderRadius: 6, background: '#eef0f3', overflow: 'hidden', marginBottom: 24 }}>
          <div style={{
            height: '100%',
            width: `${pct}%`,
            borderRadius: 6,
            background: '#4b56d6',
            transition: 'width .5s ease',
            backgroundImage: 'linear-gradient(45deg,rgba(255,255,255,0.22) 25%,transparent 25%,transparent 50%,rgba(255,255,255,0.22) 50%,rgba(255,255,255,0.22) 75%,transparent 75%)',
            backgroundSize: '18px 18px',
            animation: 'barflow 0.7s linear infinite',
          }} />
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {PROCESSING_STEPS.map((label, i) => {
            const state = i < stepIndex ? 'done' : i === stepIndex ? 'active' : 'pending';
            return (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 13 }}>
                <div style={{
                  width: 18, height: 18, borderRadius: '50%', flexShrink: 0,
                  border: `2px solid ${state === 'pending' ? '#dfe2e8' : '#4b56d6'}`,
                  background: state === 'done' ? '#4b56d6' : '#ffffff',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  animation: state === 'active' ? 'pulse 1.4s infinite' : 'none',
                }}>
                  <div style={{
                    width: 6, height: 6, borderRadius: '50%',
                    background: state === 'done' ? '#ffffff' : state === 'active' ? '#4b56d6' : 'transparent',
                  }} />
                </div>
                <span style={{
                  fontSize: 14,
                  fontWeight: state === 'active' ? 700 : 500,
                  color: state === 'pending' ? '#9aa0ac' : '#1c2230',
                }}>
                  {label}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
