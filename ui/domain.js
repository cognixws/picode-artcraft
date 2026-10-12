/* Pure domain decisions, shared by browser tests and the page. */
(function (root) {
  const labels = {
    ready: ['Ready', 'Ready to open', 'muted'],
    connected: ['Connected', 'Connected to agents', 'ok'],
    'not-installed': ['Not installed', 'Not installed on this computer', 'muted'],
    uncontrolled: ['Needs connection', 'Open without an agent connection', 'warn'],
    'connection-error': ['Connection issue', 'Agent connection unavailable', 'warn'],
    error: ['Check failed', 'Could not check this app', 'warn'],
    checking: ['Checking…', 'Checking this app…', 'muted'],
    unavailable: ['Unavailable', 'Extension unavailable', 'warn'],
  };
  function state(row, workspace) {
    if (row.state === 'connected' && row.openedForRoot && workspace?.path && row.openedForRoot !== workspace.path) {
      return { id: 'other-workspace', short: 'Other workspace', label: 'Opened for another workspace', tone: 'warn', action: 'refresh' };
    }
    const [short, label, tone] = labels[row.state] || labels.checking;
    const action = row.state === 'unavailable' ? 'settings' : row.state === 'not-installed' ? 'download' : row.state === 'ready' ? 'open' : ['uncontrolled', 'connection-error', 'error'].includes(row.state) ? 'refresh' : null;
    return { id: row.state || 'checking', short, label, tone, action };
  }
  function matches(row, query, category, availability, workspace) {
    const text = [row.title, row.kind, row.purpose, ...(row.extensions || [])].join(' ').toLowerCase();
    const status = state(row, workspace);
    return text.includes(query.trim().toLowerCase()) && (category === 'All' || row.category === category) &&
      (availability === 'all' || availability === 'installed' && row.installed || availability === 'connected' && status.id === 'connected' || availability === 'attention' && status.tone === 'warn');
  }
  const domain = { state, matches };
  root.CraftDomain = domain;
  if (typeof module !== 'undefined') module.exports = domain;
})(globalThis);
