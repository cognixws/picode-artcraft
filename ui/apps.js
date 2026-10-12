(async () => {
  const $ = id => document.getElementById(id);
  const el = (tag, cls, text) => { const node = document.createElement(tag); if (cls) node.className = cls; if (text !== undefined) node.textContent = text; return node; };
  const button = (text, fn, cls = '') => { const b = el('button', 'pc-button ' + cls, text); b.type = 'button'; b.onclick = fn; return b; };
  const paths = {
    document: 'M6 3h8l4 4v14H6z M14 3v5h4 M9 12h6 M9 16h6',
    slides: 'M3 4h18v13H3z M8 21l4-4 4 4 M7 8h10 M7 12h6',
    grid: 'M3 3h18v18H3z M3 9h18 M3 15h18 M9 3v18 M15 3v18',
    image: 'M3 3h18v18H3z M3 17l6-6 5 5 3-3 4 4 M15 7h.01',
    vector: 'M12 3l9 9-9 9-9-9z M7 12h10 M12 7v10',
    sun: 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M12 2v3 M12 19v3 M2 12h3 M19 12h3 M5 5l2 2 M17 17l2 2 M5 19l2-2 M17 7l2-2',
    motion: 'M13 2l-9 12h7l-1 8 10-13h-8z',
    film: 'M3 3h18v18H3z M7 3v18 M17 3v18 M3 8h4 M3 16h4 M17 8h4 M17 16h4 M10 8l5 4-5 4z',
    layout: 'M3 3h18v18H3z M7 7h10 M7 11h4v6H7z M14 11h3 M14 14h3 M14 17h3',
    pdf: 'M6 3h8l4 4v14H6z M14 3v5h4 M9 12h6 M9 16h3',
  };
  function icon(kind) {
    const wrap = el('span', 'app-icon'); wrap.setAttribute('aria-hidden', 'true');
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 24 24'); svg.setAttribute('fill', 'none'); svg.setAttribute('stroke', 'currentColor'); svg.setAttribute('stroke-width', '1.5'); svg.setAttribute('stroke-linejoin', 'round'); svg.setAttribute('stroke-linecap', 'round');
    const p = document.createElementNS(svg.namespaceURI, 'path'); p.setAttribute('d', paths[kind] || paths.document); svg.append(p); wrap.append(svg); return wrap;
  }
  new ResizeObserver(entries => { const wide = entries[0].contentRect.width > 760; const toolbar = document.querySelector('.toolbar'); if (wide) toolbar.setAttribute('data-align-row', ''); else toolbar.removeAttribute('data-align-row'); }).observe(document.querySelector('.shell'));
  await picode.use('theme');
  const proc = await picode.use('process');
  const ctx = await picode.use('context');
  const links = await picode.use('links');
  const settings = () => links.open(new URL('/#/extensions/artcraft', location.href).href).catch(e => problem(e.message));
  $('settings').onclick = settings;
  const { state, matches } = CraftDomain;
  let apps = [], workspaces = [], selected = null, fileContext = null;
  let workspacesOK = false, refreshTask = null, timer, lastCheck = null;
  const rows = new Map(), operations = new Map(), previews = new Map();
  const workspace = () => workspaces.find(w => w.id === $('workspace').value);
  function problem(text) { $('problem-text').textContent = text; $('problem').hidden = false; }
  function blocked(text) { $('blocked-text').textContent = text; $('blocked').hidden = false; }
  async function call(path, body) {
    const r = await proc.request(path, body === undefined ? { method: 'GET' } : { method: 'POST', body: JSON.stringify(body), contentType: 'application/json' });
    let data;
    try { data = JSON.parse(r.body || '{}'); } catch { throw new Error('The app status could not be read. Try again.'); }
    if (r.status === 503) { workspacesOK = false; blocked('Enable Crafting Apps in a workspace to use this page.'); $('problem').hidden = true; $('workspace').replaceChildren(el('option', '', 'Unavailable')); $('workspace').disabled = true; apps = apps.map(a => ({ ...a, state: 'unavailable' })); renderCatalog(); renderDetail(); const error = new Error('The extension is unavailable.'); error.unavailable = true; throw error; }
    if (r.status >= 400) throw new Error(data.message || 'The extension could not complete this action.');
    return data;
  }
  function badge(s, short) { const b = el('span', 'badge', short ? s.short : s.label); b.dataset.tone = s.tone; return b; }
  function select(id, openDetail = true) {
    selected = id;
    if (openDetail) $('split').classList.add('show-detail');
    renderCatalog(); renderDetail();
  }
  function renderCatalog() {
    const active = document.activeElement?.dataset.app;
    const visible = apps.filter(a => matches(a, $('search').value, $('category').value, $('availability').value, workspace()));
    $('catalog').replaceChildren();
    for (const category of ['Documents', 'Images', 'Motion']) {
      const group = visible.filter(a => a.category === category);
      if (!group.length) continue;
      $('catalog').append(el('h3', 'group-label', category));
      for (const a of group) {
        let row = rows.get(a.app);
        if (!row) {
          row = el('button', 'app-row'); row.type = 'button'; row.dataset.app = a.app;
          row.onclick = () => select(a.app);
          const copy = el('span', 'copy'); copy.append(el('span', 'app-name', a.title), el('span', 'app-kind', a.kind));
          row.append(icon(a.icon), copy, el('span', 'badge')); rows.set(a.app, row);
        }
        row.setAttribute('aria-current', String(a.app === selected));
        const s = state(a, workspace()), pending = operations.get(a.app)?.busy;
        const b = row.querySelector('.badge'); b.textContent = pending ? 'Working…' : s.short; b.dataset.tone = s.tone;
        $('catalog').append(row);
      }
    }
    if (!visible.length) {
      const empty = el('div', 'catalog-empty'); empty.append(el('p', 'pc-muted', 'No apps match these filters.'), button('Clear filters', () => { $('search').value = ''; $('category').value = 'All'; $('availability').value = 'all'; renderCatalog(); $('search').focus(); })); $('catalog').append(empty);
    }
    if (active && rows.get(active)?.isConnected) rows.get(active).focus();
  }
  function renderDetail() {
    const a = apps.find(a => a.app === selected);
    if (!a) return;
    const old = $('detail'), detailsOpen = old.querySelector('details')?.open, s = state(a, workspace());
    const operation = operations.get(a.app) || {}, shot = previews.get(a.app);
    old.replaceChildren();
    const back = button('← All apps', () => { $('split').classList.remove('show-detail'); rows.get(a.app)?.focus(); }, 'back');
    const title = el('div'); title.append(el('h2', '', a.title), el('p', '', a.purpose));
    const head = el('div', 'detail-head'); head.append(icon(a.icon), title); old.append(back, head);
    const connection = el('div', 'connection'); connection.append(badge(s));
    if (s.action === 'download') connection.append(button('Get ' + a.title, () => links.open(a.download).catch(e => problem(e.message)), 'primary'));
    if (s.action === 'open') {
      const b = button(operation.busy ? 'Opening…' : 'Open ' + a.title, () => act(a, 'open', b), 'primary');
      b.disabled = operation.busy || !workspacesOK || !workspace()?.path; connection.append(b);
    }
    if (s.action === 'settings') connection.append(button('Extension settings', settings));
    if (s.action === 'refresh') connection.append(button('Check again', () => refresh(true)));
    old.append(connection);
    if (['uncontrolled', 'connection-error', 'other-workspace'].includes(s.id)) old.append(el('p', 'pc-muted operation-message', s.id === 'other-workspace' ? 'Save your work and close the app before opening it for this workspace.' : 'Save your work and close the app, then open it here to connect your agents.'));
    if (a.message) old.append(el('p', 'pc-warn operation-message', a.message));
    if (operation.message) { const p = el('p', 'operation-message', operation.message); p.setAttribute('role', 'status'); old.append(p); }
    const preview = el('section', 'preview'); preview.setAttribute('aria-label', 'Preview');
    const previewHead = el('div', 'preview-head'); previewHead.append(el('h3', '', 'Preview'));
    if (s.id === 'connected') {
      const b = button(operation.busy ? 'Working…' : shot ? 'Refresh preview' : 'Show preview', () => act(a, 'snapshot', b));
      b.disabled = !!operation.busy; previewHead.append(b);
    }
    const content = el('div', 'preview-body');
    if (shot) {
      if (shot.table) {
        const scroll = el('div', 'table-wrap'), table = el('table', 'cell-preview');
        const caption = el('caption', '', (shot.table.sheet || 'Spreadsheet') + ' · ' + (shot.table.range || 'A1:H12')); table.append(caption);
        const tbody = el('tbody'); for (const values of shot.table.values || []) { const tr = el('tr'); for (const value of values) tr.append(el('td', '', value == null ? '' : String(value))); tbody.append(tr); } table.append(tbody); scroll.append(table); content.append(scroll);
      } else { const img = el('img'); img.src = shot.src; img.alt = shot.caption + ' from ' + a.title; content.append(img); }
      content.append(el('p', 'preview-caption', shot.caption));
      if (s.id !== 'connected' || shot.stale) content.append(el('p', 'preview-stale', 'Last preview — refresh to check the current view.'));
    } else content.append(el('p', 'preview-empty', s.id === 'connected' ? 'No preview captured yet.' : s.id === 'not-installed' ? 'Get the app to start working here.' : s.id === 'unavailable' ? 'Enable the extension to preview your work.' : 'Open and connect the app to preview your work.'));
    preview.append(previewHead, content); old.append(preview);
    const details = el('details'); details.open = !!detailsOpen; details.append(el('summary', '', 'Files and connection details'));
    const dl = el('dl');
    for (const [label, value] of [['Files', a.extensions.length ? a.extensions.join(', ') : 'Photo library'], ['Integration', 'Tested against ' + a.version], ['Location', a.folder || 'Not found on this computer']]) dl.append(el('dt', '', label), el('dd', '', value));
    details.append(dl); old.append(details);
  }
  async function act(a, action, trigger) {
    if (operations.get(a.app)?.busy) return;
    const ws = workspace();
    if (action === 'open' && (!workspacesOK || !ws?.path)) { blocked('Choose an enabled workspace with a folder.'); return; }
    operations.set(a.app, { busy: true, message: action === 'open' ? 'Opening ' + a.title + '…' : 'Capturing preview…' }); renderCatalog(); renderDetail();
    try {
      const result = await call('/' + action, { app: a.app, workspace: ws?.id });
      if (action === 'snapshot') previews.set(a.app, { src: result.image ? 'data:' + (result.mime || 'image/png') + ';base64,' + result.image : null, table: result.table, caption: result.caption || 'Window snapshot', stale: false });
      operations.set(a.app, { busy: false, message: action === 'open' ? result.message : '' });
      await refresh();
    } catch (e) {
      if (previews.has(a.app)) previews.get(a.app).stale = true;
      operations.set(a.app, { busy: false, message: e.message });
    } finally {
      renderCatalog(); if (selected === a.app) { renderDetail(); $('detail').querySelector('button:not(.back):not(:disabled)')?.focus({ preventScroll: true }); }
    }
  }
  async function loadWorkspaces() {
    try {
      const prior = $('workspace').value;
      const data = await call('/workspaces'); workspaces = data.workspaces || [];
      $('workspace').replaceChildren();
      for (const w of workspaces) { const option = el('option', '', w.name); option.value = w.id; $('workspace').append(option); }
      const want = workspaces.some(w => w.id === prior) ? prior : ctx?.current()?.workspaceId;
      if (workspaces.some(w => w.id === want)) $('workspace').value = want;
      workspacesOK = true; $('workspace').disabled = false; $('blocked').hidden = true;
      if (!workspaces.length) { $('workspace').append(el('option', '', 'No enabled workspace')); blocked('Enable Crafting Apps in a workspace to open apps.'); }
      else if (!workspace()?.path) blocked('This workspace has no folder. Choose a workspace with a folder.');
    } catch (e) { workspacesOK = false; if (!workspaces.length) { $('workspace').replaceChildren(el('option', '', 'Unavailable')); $('workspace').disabled = true; } if (!e.unavailable) problem('Could not load workspaces. Try again.'); }
  }
  async function refresh(manual = false) {
    if (refreshTask) return refreshTask;
    clearTimeout(timer);
    refreshTask = (async () => {
      if (manual) { $('refresh').disabled = true; $('refresh').textContent = 'Refreshing…'; }
      try {
        const result = await call('/status');
        const incoming = new Map((result.apps || []).map(a => [a.app, a]));
        apps = apps.map(a => incoming.get(a.app) || { ...a, state: 'error', message: 'No status returned. Try Refresh.' });
        lastCheck = Date.now(); $('freshness').textContent = 'Checked just now';
        if (workspacesOK) $('problem').hidden = true;
        renderCatalog(); renderDetail(); updateFile();
      } catch (e) { if (!e.unavailable) problem(e.message); $('freshness').textContent = e.unavailable ? 'Extension unavailable' : lastCheck ? 'Last check failed · previous results shown' : 'Status unavailable'; }
      finally { $('refresh').disabled = false; $('refresh').textContent = 'Refresh'; }
    })();
    try { await refreshTask; } finally { refreshTask = null; function tick() { if (!document.hidden) refresh(); else timer = setTimeout(tick, 10000); } timer = setTimeout(tick, 10000); }
  }
  function updateFile() {
    const path = fileContext?.path;
    const choices = path ? apps.filter(a => a.extensions.some(ext => path.toLowerCase().endsWith(ext))) : [];
    $('file-banner').hidden = !path;
    if (!path) return;
    $('file-name').textContent = path.split(/[\\/]/).pop();
    const a = choices.length === 1 ? choices[0] : choices.find(a => a.app === selected);
    $('file-description').textContent = a ? a.title + (!a.installed ? ' · Not installed' : !workspacesOK || !workspace()?.path ? ' · Workspace unavailable' : '') : choices.length ? 'Choose a compatible app to open this file.' : 'No compatible Crafting App for this file.';
    $('file-action').hidden = !a;
    if (a) {
      $('file-action').textContent = operations.get(a.app)?.busy ? 'Opening…' : 'Open in ' + a.title;
      $('file-action').disabled = !!operations.get(a.app)?.busy || !a.installed || !workspacesOK || !workspace()?.path;
      $('file-action').onclick = async () => {
        if (operations.get(a.app)?.busy) return;
        const ws = workspace()?.id; operations.set(a.app, {busy: true, message: 'Opening file…'}); renderCatalog(); renderDetail(); updateFile();
        try { const r = await call('/open-file', { path, app: a.app, workspace: ws }); if (fileContext?.path === path) $('file-message').textContent = r.message; select(a.app); await refresh(); }
        catch (e) { if (fileContext?.path === path) $('file-message').textContent = e.message; }
        finally { operations.set(a.app, {busy: false, message: ''}); renderCatalog(); renderDetail(); updateFile(); }
      };
    }
  }
  async function retry() { if (!apps.length) { try { apps = (await call('/catalog')).apps.map(a => ({ ...a, state: 'checking' })); selected = apps[0]?.app; $('surface').hidden = false; } catch (e) { if (!e.unavailable) problem(e.message); return; } } await loadWorkspaces(); await refresh(true); }
  $('retry').onclick = retry;
  $('refresh').onclick = async () => { if (!workspacesOK) await retry(); else { await loadWorkspaces(); await refresh(true); } };
  $('workspace').onchange = () => { $('blocked').hidden = !!workspace()?.path; if (!workspace()?.path) blocked('This workspace has no folder. Choose another workspace.'); renderCatalog(); renderDetail(); updateFile(); };
  for (const id of ['search', 'category', 'availability']) $(id).addEventListener(id === 'search' ? 'input' : 'change', renderCatalog);
  document.addEventListener('keydown', e => { if ((e.ctrlKey || e.metaKey) && e.key === 'f') { e.preventDefault(); $('search').focus(); } if (e.key === 'Escape') { $('split').classList.remove('show-detail'); rows.get(selected)?.focus(); } });
  if (!proc) { blocked('Enable Crafting Apps in a workspace to use this page.'); $('surface').hidden = true; $('workspace').disabled = true; $('refresh').hidden = true; return; }
  try {
    apps = (await call('/catalog')).apps.map(a => ({ ...a, state: 'checking' }));
    selected = apps[0]?.app; renderCatalog(); renderDetail();
    await loadWorkspaces();
    function contextChanged(c) { if (c?.path !== fileContext?.path) $('file-message').textContent = ''; fileContext = c; if (c?.workspaceId && workspaces.some(w => w.id === c.workspaceId)) $('workspace').value = c.workspaceId; const fileApp = c?.path && apps.find(a => a.extensions.some(ext => c.path.toLowerCase().endsWith(ext))); if (fileApp) selected = fileApp.app; renderCatalog(); renderDetail(); updateFile(); }
    if (ctx) { contextChanged(ctx.current()); ctx.onChange(contextChanged); }
    await refresh();
    const events = await picode.use('events'); events?.onChange(async () => { await loadWorkspaces(); await refresh(); });
    document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
  } catch (e) { if (e.unavailable) { $('surface').hidden = true; $('workspace').disabled = true; } else { problem(e.message); $('catalog').replaceChildren(el('p', 'catalog-empty', 'Could not load apps. Use Retry to try again.')); } }
})();
