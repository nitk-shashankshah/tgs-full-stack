const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

async function request(path, options) {
  const res = await fetch(`${API_BASE}${path}`, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || 'Request failed');
  }
  return res;
}

async function requestJson(path, options) {
  const res = await request(path, options);
  return res.json();
}

function jsonBody(body) {
  return { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
}

// ── Catalogues ──────────────────────────────────────────────────────────────

export function uploadCatalogue(file) {
  const formData = new FormData();
  formData.append('file', file);
  return requestJson('/api/catalogues/upload', { method: 'POST', body: formData });
}

export function getCatalogueDownloadUrl(catalogueId) {
  return `${API_BASE}/api/catalogues/${catalogueId}/download`;
}

export function processCatalogue(catalogueId, catalogueS3Url) {
  return requestJson('/api/catalogues/process', {
    method: 'POST',
    ...jsonBody({ catalogue_id: catalogueId, catalogue_s3_url: catalogueS3Url }),
  });
}

export function addTempProducts(catalogueId, products) {
  return requestJson('/api/products/temp-bulk', {
    method: 'POST',
    ...jsonBody({ catalogue_id: catalogueId, products }),
  });
}

export function listCatalogues() {
  return requestJson('/api/catalogues');
}

export function getCatalogue(catalogueId) {
  return requestJson(`/api/catalogues/${catalogueId}`);
}

export function updateCatalogueStatus(catalogueId, status) {
  return requestJson(`/api/catalogues/${catalogueId}`, {
    method: 'PATCH',
    ...jsonBody({ status }),
  });
}

// ── Price lists ─────────────────────────────────────────────────────────────

export function uploadPriceList(file) {
  const formData = new FormData();
  formData.append('file', file);
  return requestJson('/api/pricelists/upload', { method: 'POST', body: formData });
}

export function listPriceLists() {
  return requestJson('/api/pricelists');
}

// ── Combinations & brochures ────────────────────────────────────────────────

export function findCombinations(query) {
  return requestJson('/api/combinations', { method: 'POST', ...jsonBody({ query }) });
}

export async function generateBrochure(payload) {
  const res = await request('/api/catalogues/generate-brochure', {
    method: 'POST',
    ...jsonBody(payload),
  });
  return res.blob();
}
