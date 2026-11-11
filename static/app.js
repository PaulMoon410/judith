document.addEventListener('DOMContentLoaded', () => {
  const byId = id => document.getElementById(id);
  const PANELS = ['blueprint', 'room', 'estimate', 'materials', 'labor'];
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const money = n => (typeof n === 'number' || /^[\d.]+$/.test(n)) ? '$' + Number(n).toFixed(2) : esc(n ?? '');

  function toast(text) {
    const t = byId('toast');
    t.textContent = text;
    t.classList.add('show');
    clearTimeout(toast._t);
    toast._t = setTimeout(() => t.classList.remove('show'), 2500);
  }

  function setStep(n) {
    document.querySelectorAll('.step').forEach(s => {
      const i = Number(s.dataset.step);
      s.classList.toggle('active', i === n);
      s.classList.toggle('done', i < n);
    });
  }

  function msg(el, kind, text) { el.innerHTML = `<div class="msg ${kind}">${esc(text)}</div>`; }

  async function api(url, body, btn) {
    const label = btn && btn.innerHTML;
    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner"></span>Working...'; }
    try {
      const r = await fetch(url, {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.error || `Request failed (${r.status})`);
      return data;
    } finally {
      if (btn) { btn.disabled = false; btn.innerHTML = label; }
    }
  }

  function show(id) {
    PANELS.forEach(x => { const e = byId(x); if (e) e.style.display = x === id ? 'block' : 'none'; });
    document.querySelectorAll('#workflow-buttons button').forEach(b => b.classList.toggle('sel', b.dataset.target === id));
    const e = byId(id); if (e) e.scrollIntoView({behavior: 'smooth', block: 'start'});
  }

  function showMenu() {
    byId('menu').style.display = 'block';
    setStep(3);
    byId('menu').scrollIntoView({behavior: 'smooth'});
  }

  function setType(t) {
    window._type = t;
    byId('code').style.display = 'block';
    setStep(2);
    toast('Building type: ' + t);
  }

  byId('occType').addEventListener('change', e => { if (e.target.value) setType(e.target.value); });
  byId('continueBtn').addEventListener('click', () => { window._edition = byId('edition').value; showMenu(); });
  document.querySelectorAll('#workflow-buttons button').forEach(b => b.addEventListener('click', () => show(b.dataset.target)));

  byId('runNecBtn').addEventListener('click', async e => {
    const out = byId('necout');
    if (!byId('sqft').value || !byId('amps').value) { toast('Enter square footage and amps'); return; }
    try {
      const d = await api('/api/nec', {sqft: byId('sqft').value, amps: byId('amps').value}, e.currentTarget);
      out.style.display = 'block';
      out.textContent = d.report;
    } catch (err) { out.style.display = 'block'; out.textContent = err.message; }
  });

  byId('saveEstBtn').addEventListener('click', async e => {
    const out = byId('estout');
    if (!byId('title').value.trim()) { toast('Please enter a title'); return; }
    try {
      const d = await api('/api/estimate', {title: byId('title').value, desc: byId('desc').value}, e.currentTarget);
      msg(out, 'ok', `Saved "${d.title}"`);
    } catch (err) { msg(out, 'err', err.message); }
  });

  byId('searchMatBtn').addEventListener('click', async e => {
    const out = byId('matout');
    if (!byId('mq').value.trim()) { toast('Enter a search term'); return; }
    try {
      const d = await api('/api/price-search', {query: byId('mq').value}, e.currentTarget);
      const rows = Array.isArray(d) ? d : (d.offers || []);
      if (!rows.length) { out.innerHTML = '<div class="msg">No results found.</div>'; return; }
      const cols = Object.keys(rows[0]).filter(k => typeof rows[0][k] !== 'object');
      out.innerHTML = '<table><thead><tr>' + cols.map(c => `<th>${esc(c)}</th>`).join('') + '</tr></thead><tbody>' +
        rows.map(r => '<tr>' + cols.map(c => `<td>${/price|cost/i.test(c) ? money(r[c]) : esc(r[c])}</td>`).join('') + '</tr>').join('') +
        '</tbody></table>';
    } catch (err) { msg(out, 'err', err.message); }
  });

  byId('runLaborBtn').addEventListener('click', async e => {
    const out = byId('laborout');
    try {
      const d = await api('/api/labor-compare', {state: byId('state').value}, e.currentTarget);
      const rec = d.recommended;
      out.innerHTML = `<div class="hint">Recommended rate</div><div class="stat">${typeof rec === 'number' ? money(rec) + '/hr' : esc(rec ?? 'n/a')}</div>` +
        ((d.sources || []).length
          ? '<table><thead><tr>' + Object.keys(d.sources[0]).map(k => `<th>${esc(k)}</th>`).join('') + '</tr></thead><tbody>' +
            d.sources.map(s => '<tr>' + Object.values(s).map(v => `<td>${esc(typeof v === 'object' ? JSON.stringify(v) : v)}</td>`).join('') + '</tr>').join('') +
            '</tbody></table>'
          : '');
    } catch (err) { msg(out, 'err', err.message); }
  });

  const drop = byId('drop'), file = byId('bpFile');
  async function upload(f) {
    const out = byId('bpout');
    byId('dropText').textContent = f.name;
    const fd = new FormData(); fd.append('file', f);
    out.innerHTML = '<div class="msg"><span class="spinner"></span>Uploading...</div>';
    try {
      const r = await fetch('/api/upload', {method: 'POST', body: fd});
      const d = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(d.error || 'Upload is not available on this server');
      msg(out, 'ok', `Uploaded ${d.filename}`);
    } catch (err) { msg(out, 'err', err.message); }
  }
  file.addEventListener('change', () => { if (file.files[0]) upload(file.files[0]); });
  ['dragover', 'dragenter'].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add('over'); }));
  ['dragleave', 'drop'].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.remove('over'); }));
  drop.addEventListener('drop', e => { if (e.dataTransfer.files[0]) upload(e.dataTransfer.files[0]); });

  fetch('/api/materials').then(r => r.json()).then(d => {
    const u = byId('matlist');
    d.forEach(m => {
      const li = document.createElement('li');
      li.innerHTML = `<span>${esc(m.description || m.name)}</span><span class="badge">${money(m.unit_price)}</span>`;
      u.appendChild(li);
    });
  }).catch(() => {});
});
