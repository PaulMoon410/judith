document.addEventListener('DOMContentLoaded', () => {
  const byId = id => document.getElementById(id);
  const toast = t => { const el = byId('toast'); el.textContent = t; el.classList.add('show'); setTimeout(() => el.classList.remove('show'), 2500); };
  const spin = (btn, on) => { btn.disabled = on; btn.innerHTML = on ? '<span class="spinner"></span>Working...' : btn.dataset.label; };

  byId('estimateForm').addEventListener('submit', async e => {
    e.preventDefault();
    const btn = byId('submitBtn'); btn.dataset.label = btn.textContent; spin(btn, true);
    try {
      const r = await fetch('/', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({
        name: byId('name').value,
        email: byId('email').value,
        phone: byId('phone').value,
        project_type: byId('project_type').value,
        details: byId('details').value
      })});
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || 'Request failed');
      toast(data.message || 'Submitted!');
      e.target.reset();
    } catch (err) {
      toast('Error: ' + err.message);
    } finally { spin(btn, false); }
  });

  byId('searchPriceBtn').addEventListener('click', async () => {
    const q = byId('priceQuery').value.trim();
    if (!q) return toast('Enter a material to search');
    const btn = byId('searchPriceBtn'); btn.dataset.label = btn.textContent; spin(btn, true);
    try {
      const r = await fetch('/api/pricing', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({query: q})});
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || 'Search failed');
      byId('priceOut').innerHTML = data.length
        ? '<table><thead><tr><th>Material</th><th class="num">Price</th><th class="num">Unit</th><th>Source</th></tr></thead><tbody>' +
          data.slice(0, 8).map(o => `<tr><td>${o.description || 'Unknown'}</td><td class="num">$${Number(o.price || o.unit_price || 0).toFixed(2)}</td><td class="num">${o.unit || 'each'}</td><td>${o.source || ''}</td></tr>`).join('') +
          '</tbody></table>' + (data.length > 8 ? `<p style="color:var(--muted);font-size:13px;margin-top:8px">+${data.length - 8} more results</p>` : '')
        : '<div class="msg err">No results found</div>';
    } catch (err) {
      byId('priceOut').innerHTML = '<div class="msg err">Error: ' + err.message + '</div>';
    } finally { spin(btn, false); }
  });

  byId('chatBtn').addEventListener('click', async () => {
    const msg = byId('chatInput').value.trim();
    if (!msg) return toast('Enter a question');
    const btn = byId('chatBtn'); btn.dataset.label = btn.textContent; spin(btn, true);
    try {
      const r = await fetch('/api/chat', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({message: msg})});
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || 'Chat failed');
      byId('chatOut').innerHTML = '<div class="msg ok">' + (data.response || data.answer || 'No response') + '</div>';
    } catch (err) {
      byId('chatOut').innerHTML = '<div class="msg err">Error: ' + err.message + '</div>';
    } finally { spin(btn, false); }
  });

  byId('laborBtn').addEventListener('click', async () => {
    const state = byId('stateInput').value.trim() || 'Maryland';
    const btn = byId('laborBtn'); btn.dataset.label = btn.textContent; spin(btn, true);
    try {
      const r = await fetch('/api/labor-rate');
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || 'Failed');
      byId('laborOut').innerHTML = '<div class="msg ok">Recommended rate for ' + state + ': <strong>$' + data.rate.toFixed(2) + '/hr</strong></div>';
    } catch (err) {
      byId('laborOut').innerHTML = '<div class="msg err">Error: ' + err.message + '</div>';
    } finally { spin(btn, false); }
  });

  byId('necBtn').addEventListener('click', async () => {
    const sqft = parseFloat(byId('sqftInput').value) || 0;
    const amps = parseFloat(byId('ampsInput').value) || 20;
    if (!sqft) return toast('Enter square footage');
    const btn = byId('necBtn'); btn.dataset.label = btn.textContent; spin(btn, true);
    try {
      const r = await fetch('/api/nec', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({sqft, amps})});
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || 'Calc failed');
      byId('necOut').innerHTML = '<pre>' + (data.report || 'No report') + '</pre>';
    } catch (err) {
      byId('necOut').innerHTML = '<div class="msg err">Error: ' + err.message + '</div>';
    } finally { spin(btn, false); }
  });
});