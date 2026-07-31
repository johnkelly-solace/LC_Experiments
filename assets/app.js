(function () {
  const rows = Array.from(document.querySelectorAll('#exp-tbody tr'));
  const catChips = document.querySelectorAll('.chip[data-cat]');
  const resChips = document.querySelectorAll('.chip[data-res]');
  const searchInput = document.getElementById('search-input');
  const emptyState = document.getElementById('empty-state');

  let activeCat = 'All';
  let activeRes = 'All';
  let query = '';

  function applyFilters() {
    let visibleCount = 0;
    rows.forEach((row) => {
      const cat = row.dataset.cat;
      const res = row.dataset.res;
      const text = row.dataset.search;
      const matchCat = activeCat === 'All' || cat === activeCat;
      const matchRes = activeRes === 'All' || res === activeRes;
      const matchQuery = !query || text.includes(query);
      const show = matchCat && matchRes && matchQuery;
      row.style.display = show ? '' : 'none';
      if (show) visibleCount++;
    });
    emptyState.style.display = visibleCount === 0 ? 'block' : 'none';
  }

  catChips.forEach((chip) => {
    chip.addEventListener('click', () => {
      catChips.forEach((c) => c.classList.remove('active'));
      chip.classList.add('active');
      activeCat = chip.dataset.cat;
      applyFilters();
    });
  });

  resChips.forEach((chip) => {
    chip.addEventListener('click', () => {
      resChips.forEach((c) => c.classList.remove('active'));
      chip.classList.add('active');
      activeRes = chip.dataset.res;
      applyFilters();
    });
  });

  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      query = e.target.value.trim().toLowerCase();
      applyFilters();
    });
  }

  rows.forEach((row) => {
    row.addEventListener('click', (e) => {
      if (e.target.tagName === 'A') return;
      const href = row.dataset.href;
      if (href) window.location.href = href;
    });
  });

  // Sortable columns
  const headers = document.querySelectorAll('th[data-sort]');
  let sortState = {};
  headers.forEach((th) => {
    th.addEventListener('click', () => {
      const key = th.dataset.sort;
      const tbody = document.getElementById('exp-tbody');
      const currentRows = Array.from(tbody.querySelectorAll('tr'));
      const asc = !sortState[key];
      sortState = {};
      sortState[key] = asc;
      currentRows.sort((a, b) => {
        const av = a.dataset[key] || '';
        const bv = b.dataset[key] || '';
        return asc ? av.localeCompare(bv) : bv.localeCompare(av);
      });
      currentRows.forEach((r) => tbody.appendChild(r));
    });
  });
})();
