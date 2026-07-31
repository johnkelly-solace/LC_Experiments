/* Lifecycle Dashboard — screenshot storage & UI
   Uses IndexedDB so screenshots persist across reloads with zero backend.
   NOTE: this storage is local to whichever browser/device adds the images —
   it does not sync to other people viewing the same page elsewhere. Use the
   Export/Import buttons to move a set of screenshots to another machine. */
(function () {
  const DB_NAME = 'lifecycle_dashboard_screenshots';
  const DB_VERSION = 1;
  const STORE = 'images';

  function openDB() {
    return new Promise((resolve, reject) => {
      if (!window.indexedDB) { reject(new Error('IndexedDB not available')); return; }
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = (e) => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains(STORE)) {
          db.createObjectStore(STORE, { keyPath: 'id' });
        }
      };
      req.onsuccess = (e) => resolve(e.target.result);
      req.onerror = () => reject(req.error);
    });
  }

  async function putRecord(record) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const req = db.transaction(STORE, 'readwrite').objectStore(STORE).put(record);
      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error);
    });
  }

  async function deleteRecord(id) {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const req = db.transaction(STORE, 'readwrite').objectStore(STORE).delete(id);
      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error);
    });
  }

  async function getAll() {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const req = db.transaction(STORE, 'readonly').objectStore(STORE).getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => reject(req.error);
    });
  }

  function fileToDataURL(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(reader.error);
      reader.readAsDataURL(file);
    });
  }

  function escapeHtml(s) {
    const d = document.createElement('div');
    d.textContent = s || '';
    return d.innerHTML;
  }

  async function init({ slug, variantALabel, variantBLabel }) {
    const slotA = document.getElementById('shot-slot-a');
    const slotB = document.getElementById('shot-slot-b');
    const gallery = document.getElementById('shot-gallery');
    const addBtn = document.getElementById('add-shot-btn');
    const addForm = document.getElementById('add-shot-form');
    const addFile = document.getElementById('add-shot-file');
    const addFileLabel = document.getElementById('add-shot-file-label');
    const addSource = document.getElementById('add-shot-source');
    const addCaption = document.getElementById('add-shot-caption');
    const addSave = document.getElementById('add-shot-save');
    const addCancel = document.getElementById('add-shot-cancel');
    const exportBtn = document.getElementById('export-shots-btn');
    const importInput = document.getElementById('import-shots-input');

    // If IndexedDB genuinely isn't available (very old browser / locked-down
    // private mode), fail quietly with a note instead of a broken UI.
    try {
      await openDB();
    } catch (err) {
      [slotA, slotB, gallery].forEach((el) => {
        if (el) el.innerHTML = '<div class="shot-empty-gallery">Screenshot storage isn\u2019t available in this browser (IndexedDB blocked).</div>';
      });
      if (addBtn) addBtn.style.display = 'none';
      return;
    }

    function renderSlot(el, record, slotKey, label) {
      if (!el) return;
      if (record) {
        el.innerHTML = `
          <span class="shot-label">${escapeHtml(label)}</span>
          <img src="${record.dataUrl}" alt="${escapeHtml(label)}">
          <div class="shot-slot-actions">
            <label class="shot-replace">Replace<input type="file" accept="image/*" class="shot-slot-input" data-slot="${slotKey}" hidden></label>
            <button class="shot-remove-slot" data-slot="${slotKey}" type="button">Remove</button>
          </div>`;
      } else {
        el.innerHTML = `
          <span class="shot-label">${escapeHtml(label)}</span>
          <label class="shot-empty-slot">
            <span>+ Add screenshot</span>
            <input type="file" accept="image/*" class="shot-slot-input" data-slot="${slotKey}" hidden>
          </label>`;
      }
      const input = el.querySelector('.shot-slot-input');
      if (input) {
        input.addEventListener('change', async (e) => {
          const file = e.target.files[0];
          if (!file) return;
          const dataUrl = await fileToDataURL(file);
          await putRecord({ id: `${slug}__${slotKey}`, slug, slot: slotKey, dataUrl, addedAt: Date.now() });
          refresh();
        });
      }
      const removeBtn = el.querySelector('.shot-remove-slot');
      if (removeBtn) {
        removeBtn.addEventListener('click', async () => {
          await deleteRecord(`${slug}__${slotKey}`);
          refresh();
        });
      }
    }

    async function refresh() {
      const all = (await getAll()).filter((r) => r.slug === slug);
      const a = all.find((r) => r.slot === 'a');
      const b = all.find((r) => r.slot === 'b');
      renderSlot(slotA, a, 'a', variantALabel);
      renderSlot(slotB, b, 'b', variantBLabel);

      const items = all
        .filter((r) => r.slot === 'gallery')
        .sort((x, y) => (y.addedAt || 0) - (x.addedAt || 0));

      if (!gallery) return;
      if (items.length === 0) {
        gallery.innerHTML = '<div class="shot-empty-gallery">No additional screenshots yet \u2014 add HEX charts, CIO exports, creative previews, anything.</div>';
        return;
      }
      gallery.innerHTML = '';
      items.forEach((item) => {
        const card = document.createElement('div');
        card.className = 'shot-card';
        card.innerHTML = `
          <img src="${item.dataUrl}" alt="${escapeHtml(item.caption || item.source || 'screenshot')}">
          <div class="shot-card-meta">
            <span class="shot-source-tag">${escapeHtml(item.source || 'Other')}</span>
            <span class="shot-caption">${escapeHtml(item.caption || '')}</span>
            <button class="shot-remove" data-id="${item.id}" type="button" title="Remove">&times;</button>
          </div>`;
        gallery.appendChild(card);
      });
      gallery.querySelectorAll('.shot-remove').forEach((btn) => {
        btn.addEventListener('click', async () => {
          await deleteRecord(btn.dataset.id);
          refresh();
        });
      });
    }

    if (addBtn && addForm) {
      addBtn.addEventListener('click', () => {
        addForm.style.display = addForm.style.display === 'flex' ? 'none' : 'flex';
      });
    }
    if (addFile && addFileLabel) {
      addFile.addEventListener('change', () => {
        addFileLabel.textContent = addFile.files[0] ? addFile.files[0].name : 'Choose file\u2026';
      });
    }
    if (addCancel) {
      addCancel.addEventListener('click', () => {
        addForm.style.display = 'none';
        addFile.value = '';
        addCaption.value = '';
        if (addFileLabel) addFileLabel.textContent = 'Choose file\u2026';
      });
    }
    if (addSave) {
      addSave.addEventListener('click', async () => {
        const file = addFile.files[0];
        if (!file) { addFile.focus(); return; }
        const dataUrl = await fileToDataURL(file);
        const id = `${slug}__gallery-${Date.now()}`;
        await putRecord({
          id, slug, slot: 'gallery',
          source: addSource.value, caption: addCaption.value, dataUrl, addedAt: Date.now(),
        });
        addForm.style.display = 'none';
        addFile.value = '';
        addCaption.value = '';
        if (addFileLabel) addFileLabel.textContent = 'Choose file\u2026';
        refresh();
      });
    }
    if (exportBtn) {
      exportBtn.addEventListener('click', async () => {
        const all = (await getAll()).filter((r) => r.slug === slug);
        if (all.length === 0) { alert('No screenshots stored for this experiment yet.'); return; }
        const blob = new Blob([JSON.stringify(all)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${slug}-screenshots.json`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      });
    }
    if (importInput) {
      importInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        try {
          const text = await file.text();
          const records = JSON.parse(text);
          for (const r of records) {
            r.slug = slug; // force into this experiment regardless of source
            await putRecord(r);
          }
          refresh();
        } catch (err) {
          alert('Could not read that file \u2014 expected a screenshots .json export from this dashboard.');
        }
        importInput.value = '';
      });
    }

    refresh();
  }

  window.ScreenshotUI = { init };
})();
