import React, { useState, useEffect, useRef } from 'react';
import Header from './components/Header';
import UploadScreen from './components/UploadScreen';
import ProcessingScreen from './components/ProcessingScreen';
import ReviewScreen from './components/ReviewScreen';
import CataloguesScreen from './components/CataloguesScreen';
import FindSuppliersScreen from './components/FindSuppliersScreen';
import PriceListsScreen from './components/PriceListsScreen';
import CombinationsScreen from './components/CombinationsScreen';
import ExportModal from './components/ExportModal';
import { PROCESSING_STEPS } from './data/catalogs';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

function relativeDate(ts) {
  const diff = Date.now() - ts;
  const mins = Math.floor(diff / 60000);
  if (mins < 2) return 'just now';
  if (mins < 60) return `${mins} min ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} hr ago`;
  const days = Math.floor(hrs / 24);
  if (days === 1) return '1 day ago';
  if (days < 7) return `${days} days ago`;
  const weeks = Math.floor(days / 7);
  return weeks === 1 ? '1 week ago' : `${weeks} weeks ago`;
}

export default function App() {
  const [tab, setTab] = useState('upload');
  const [screen, setScreen] = useState('upload');
  const [fileName, setFileName] = useState('');
  const [stepIndex, setStepIndex] = useState(-1);
  const [supplier, setSupplier] = useState(null);
  const [products, setProducts] = useState([]);
  const [exported, setExported] = useState(false);
  const [openCatalogId, setOpenCatalogId] = useState(null);
  const [uploadError, setUploadError] = useState(null);
  const [catalogs, setCatalogs] = useState([]);

  const currentCatalogIdRef = useRef(null);
  const timerRef = useRef(null);

  function reloadCatalogs() {
    fetch(`${API_BASE}/api/catalogs`)
      .then((r) => r.json())
      .then(setCatalogs)
      .catch(() => {});
  }

  // Load catalog list from backend on mount
  useEffect(() => { reloadCatalogs(); }, []);

  async function startProcessing(fileOrName) {
    clearInterval(timerRef.current);
    setUploadError(null);
    setExported(false);
    setTab('upload');
    currentCatalogIdRef.current = null;

    const isFile = fileOrName instanceof File;
    const name = isFile ? fileOrName.name : (fileOrName || 'catalog.pdf');
    setFileName(name);
    setScreen('processing');
    setStepIndex(0);

    let idx = 0;
    const maxAnimStep = PROCESSING_STEPS.length - 1;
    timerRef.current = setInterval(() => {
      idx += 1;
      if (idx <= maxAnimStep) setStepIndex(idx);
    }, 900);

    try {
      if (!isFile) throw new Error('Please select a real PDF file to upload.');

      const formData = new FormData();
      formData.append('file', fileOrName);
      const res = await fetch(`${API_BASE}/api/upload-catalog`, { method: 'POST', body: formData });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(err.detail || 'Upload failed');
      }
      const result = await res.json();

      currentCatalogIdRef.current = result.catalogId;

      // Add the new catalog to the library list (full images stripped, thumbnails kept)
      const newEntry = {
        id: result.catalogId,
        file: result.fileName,
        uploadedAt: Date.now(),
        pageCount: result.pageCount,
        status: 'in_review',
        coverImage: result.coverImage ?? null,
        supplier: {
          name: result.supplier.name || '',
          location: result.supplier.location || '',
          email: result.supplier.email || '',
          terms: result.supplier.terms || '',
        },
        products: result.products.map(({ image: _img, ...rest }) => rest),
      };
      setCatalogs((prev) => [newEntry, ...prev]);

      clearInterval(timerRef.current);
      setStepIndex(PROCESSING_STEPS.length);
      setSupplier(result.supplier);
      setProducts(result.products);
      setScreen('review');
    } catch (err) {
      clearInterval(timerRef.current);
      setUploadError(err.message || 'Something went wrong');
      setScreen('upload');
      setStepIndex(-1);
    }
  }

  async function handleApprove() {
    if (currentCatalogIdRef.current) {
      await fetch(`${API_BASE}/api/catalogs/${currentCatalogIdRef.current}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'reviewed' }),
      }).catch(() => {});
      setCatalogs((prev) =>
        prev.map((c) =>
          c.id === currentCatalogIdRef.current ? { ...c, status: 'reviewed' } : c
        )
      );
    }
    setExported(true);
  }

  function reset() {
    clearInterval(timerRef.current);
    setScreen('upload');
    setStepIndex(-1);
    setFileName('');
    setSupplier(null);
    setProducts([]);
    setExported(false);
    setUploadError(null);
    setTab('upload');
    currentCatalogIdRef.current = null;
  }

  function gotoUpload() {
    clearInterval(timerRef.current);
    setScreen('upload');
    setStepIndex(-1);
    setSupplier(null);
    setProducts([]);
    setExported(false);
    setUploadError(null);
    setOpenCatalogId(null);
    setTab('upload');
    currentCatalogIdRef.current = null;
  }

  useEffect(() => () => clearInterval(timerRef.current), []);

  function updateSupplier(key, val) {
    setSupplier((s) => ({ ...s, [key]: val }));
  }
  function confirmSupplier(key) {
    setSupplier((s) => ({ ...s, conf: { ...s.conf, [key]: 'high' } }));
  }
  function updateProduct(id, key, val) {
    setProducts((ps) => ps.map((p) => p.id === id ? { ...p, [key]: val } : p));
  }
  function confirmProductField(id, key) {
    setProducts((ps) => ps.map((p) => p.id === id ? { ...p, conf: { ...p.conf, [key]: 'high' } } : p));
  }
  function removeTag(id, tag) {
    setProducts((ps) => ps.map((p) => p.id === id ? { ...p, categories: p.categories.filter((t) => t !== tag) } : p));
  }
  function toggleReviewed(id) {
    setProducts((ps) => ps.map((p) => p.id === id ? { ...p, reviewed: !p.reviewed } : p));
  }

  const displayCatalogs = catalogs.map((c) => ({
    ...c,
    date: relativeDate(c.uploadedAt),
    pages: c.pageCount ?? c.pages ?? '?',
  }));

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100vh',
      background: '#f6f7f9', fontFamily: "'Hanken Grotesk', -apple-system, system-ui, sans-serif",
      color: '#1c2230', WebkitFontSmoothing: 'antialiased',
    }}>
      <Header
        tab={tab}
        onTabChange={(t) => { setTab(t); setOpenCatalogId(null); }}
        catalogCount={catalogs.length}
      />

      <main style={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
        {tab === 'upload' && screen === 'upload' && (
          <UploadScreen onStart={startProcessing} error={uploadError} />
        )}
        {tab === 'upload' && screen === 'processing' && (
          <ProcessingScreen fileName={fileName} stepIndex={stepIndex} />
        )}
        {tab === 'upload' && screen === 'review' && supplier && (
          <ReviewScreen
            fileName={fileName}
            supplier={supplier}
            products={products}
            onUpdateSupplier={updateSupplier}
            onConfirmSupplier={confirmSupplier}
            onUpdateProduct={updateProduct}
            onConfirmProductField={confirmProductField}
            onRemoveTag={removeTag}
            onToggleReviewed={toggleReviewed}
            onApprove={handleApprove}
            onReset={reset}
          />
        )}
        {tab === 'library' && (
          <CataloguesScreen
            catalogs={displayCatalogs}
            openCatalogId={openCatalogId}
            onOpenCatalog={setOpenCatalogId}
            onCloseCatalog={() => setOpenCatalogId(null)}
            onGotoUpload={gotoUpload}
          />
        )}
        {tab === 'pricing' && (
          <PriceListsScreen onPricesUpdated={reloadCatalogs} />
        )}
        {tab === 'combinations' && (
          <CombinationsScreen />
        )}
        {tab === 'search' && (
          <FindSuppliersScreen catalogs={displayCatalogs} />
        )}
      </main>

      {exported && (
        <ExportModal
          fileName={fileName}
          total={products.length}
          onReset={reset}
        />
      )}
    </div>
  );
}
