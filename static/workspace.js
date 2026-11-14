'use strict';

(() => {
  const $ = id => document.getElementById(id);
  const estimateForm = $('estimate-form');
  const scheduleForm = $('schedule-form');
  const actualForm = $('actual-form');
  const currency = value => new Intl.NumberFormat('en-US', {style: 'currency', currency: 'USD'}).format(Number(value));
  const localTime = value => new Date(value).toLocaleString();
  let csrf = '';
  let current = null;
  let jobList = [];
  let dirty = false;
  let busy = false;

  function node(tag, content, className) {
    const element = document.createElement(tag);
    if (content !== undefined) element.textContent = content;
    if (className) element.className = className;
    return element;
  }

  function notify(message, error = false) {
    $('message').textContent = message;
    $('message').className = error ? 'error' : '';
    $('message').hidden = false;
  }

  async function run(task) {
    if (busy) return;
    busy = true;
    try {
      await task();
    } catch (error) {
      notify(error.message, true);
    } finally {
      busy = false;
    }
  }

  function on(id, event, task) {
    $(id).addEventListener(event, e => {
      e.preventDefault();
      run(() => task(e));
    });
  }

  async function api(path, method = 'GET', data) {
    const headers = {'X-Judith-Request': 'workspace'};
    if (csrf) headers['X-CSRF-Token'] = csrf;
    if (data !== undefined && !(data instanceof FormData)) headers['Content-Type'] = 'application/json';
    const response = await fetch('/workspace/api' + path, {
      method, headers, credentials: 'same-origin',
      body: data === undefined ? undefined : data instanceof FormData ? data : JSON.stringify(data)
    });
    const payload = await response.json();
    if (!response.ok) {
      if (response.status === 401) {
        $('workspace').hidden = true;
        $('login-panel').hidden = false;
        $('logout').hidden = true;
      }
      throw new Error(payload.error || `Request failed (${response.status}).`);
    }
    return payload;
  }

  function markDirty() {
    dirty = true;
    $('totals-label').textContent = 'Unsaved changes: calculate or save to update totals. Quoting uses saved values only.';
    $('quote').disabled = true;
  }

  function ensureSaved() {
    if (dirty) throw new Error('Save your draft before taking this action.');
  }

  function mayLeave() {
    return !dirty || window.confirm('Leave without saving your draft changes?');
  }

  async function loadDashboard() {
    const [templates, records] = await Promise.all([api('/templates'), api('/jobs')]);
    jobList = records;
    $('templates').replaceChildren();
    templates.forEach(template => {
      const button = node('button', template.name, 'secondary');
      button.type = 'button';
      button.addEventListener('click', () => run(async () => {
        showJob(await api('/jobs', 'POST', {template_id: template.id}));
      }));
      $('templates').append(button);
    });
    renderJobs();
    $('workspace').hidden = false;
    $('dashboard').hidden = false;
    $('editor').hidden = true;
    $('login-panel').hidden = true;
    $('logout').hidden = false;
    current = null;
    dirty = false;
  }

  function jobCard(job, scheduled = false) {
    const row = node('div', undefined, 'job-row');
    const description = node('div');
    description.append(node('strong', job.title), node('p', `${job.customer || 'No customer yet'} | ${job.status} | ${currency(job.totals.total)}`));
    if (scheduled) {
      description.append(node('p', `${localTime(job.schedule.start)} - ${localTime(job.schedule.end)}`));
      description.append(node('p', `Crew: ${job.schedule.crew.join(', ')} | ${job.address}`));
      if (job.schedule.override_reason) description.append(node('p', `Conflict override: ${job.schedule.override_reason}`));
    } else if (job.comparison) {
      description.append(node('p', `Direct-cost variance: ${currency(job.comparison.direct_cost_variance)} | Labor variance: ${job.comparison.labor_hours_variance} person-hours`));
    }
    const button = node('button', 'Open job', 'secondary');
    button.addEventListener('click', () => run(async () => showJob(await api('/jobs/' + job.id))));
    row.append(description, button);
    return row;
  }

  function renderJobs() {
    const query = $('job-filter').value.toLowerCase();
    const filtered = jobList.filter(job => `${job.title} ${job.customer} ${job.status}`.toLowerCase().includes(query));
    $('job-list').replaceChildren(...filtered.map(job => jobCard(job)));
    if (!filtered.length) $('job-list').append(node('p', 'No matching jobs. Start with a template or blank estimate.'));
    const scheduled = jobList.filter(job => job.status === 'scheduled')
      .sort((a, b) => new Date(a.schedule.start) - new Date(b.schedule.start));
    $('schedule-list').replaceChildren(...scheduled.map(job => jobCard(job, true)));
    if (!scheduled.length) $('schedule-list').append(node('p', 'Accepted jobs will appear here after you schedule them.'));
  }

  function fill(form, data) {
    Array.from(form.elements).forEach(input => {
      if (!input.name || data[input.name] === undefined) return;
      if (input.type === 'checkbox') input.checked = data[input.name];
      else input.value = data[input.name];
    });
  }

  function read(form) {
    const result = {};
    Array.from(form.elements).forEach(input => {
      if (input.name) result[input.name] = input.type === 'checkbox' ? input.checked : input.value;
    });
    return result;
  }

  function inputField(label, name, value, type = 'text', step = '.01') {
    const wrapper = node('label', label);
    const input = node('input');
    input.dataset.field = name;
    input.type = type;
    if (type === 'number') {
      input.min = '0';
      input.step = step;
      input.required = true;
    }
    if (type === 'checkbox') {
      input.checked = Boolean(value);
      wrapper.className = 'check';
    } else input.value = value || '';
    wrapper.append(input);
    return wrapper;
  }

  function addItem(item = {}) {
    const card = node('div', undefined, 'item');
    const grid = node('div', undefined, 'grid');
    [
      ['Description', 'description', item.description],
      ['Quantity', 'quantity', item.quantity || '1', 'number', '.001'],
      ['Base unit (ea, ft, box...)', 'unit', item.unit || 'ea'],
      ['Material cost / base unit ($)', 'unit_cost', item.unit_cost || '0', 'number', '.0001'],
      ['Person-hours / unit', 'hours_per_unit', item.hours_per_unit || '0', 'number', '.001'],
      ['Material waste (%)', 'waste_percent', item.waste_percent || '0', 'number'],
      ['Supplier / quote reference', 'supplier', item.supplier],
      ['Exact spec / SKU / brand', 'specification', item.specification],
      ['Price verified on', 'verified_on', item.verified_on, 'date'],
      ['Customer-supplied material ($0)', 'customer_supplied', item.customer_supplied, 'checkbox']
    ].forEach(args => grid.append(inputField(...args)));
    const field = name => grid.querySelector(`[data-field="${name}"]`);
    field('description').required = true;
    field('description').maxLength = 240;
    field('unit').required = true;
    field('unit').maxLength = 20;
    field('supplier').maxLength = 240;
    field('specification').maxLength = 500;
    field('waste_percent').max = '100';
    const actions = node('div', undefined, 'actions');
    const search = node('button', 'Find candidate prices', 'secondary');
    search.type = 'button';
    const normalize = node('button', 'Convert package price', 'secondary');
    normalize.type = 'button';
    const remove = node('button', 'Remove item', 'secondary');
    remove.type = 'button';
    const results = node('div', undefined, 'search-results');
    search.addEventListener('click', () => run(async () => {
      const offers = await api('/price-search', 'POST', {query: field('description').value});
      results.replaceChildren(node('p', 'Candidates only: verify the exact product, package size, stock, and delivered price before entering a unit cost.'));
      if (!offers.length) results.append(node('p', 'No candidates found.'));
      offers.forEach(offer => {
        const paragraph = node('p', `${offer.source}: ${offer.title} - ${currency(offer.price)} `);
        if (/^https?:\/\//i.test(offer.url)) {
          const link = node('a', 'View listing');
          link.href = offer.url;
          link.target = '_blank';
          link.rel = 'noopener noreferrer';
          paragraph.append(link);
        }
        results.append(paragraph);
      });
    }));
    normalize.addEventListener('click', () => run(async () => {
      const rawPrice = window.prompt('Delivered package price ($), excluding sales tax:');
      if (rawPrice === null) return;
      const rawUnits = window.prompt(`Number of base units (${field('unit').value}) in the package:`);
      if (rawUnits === null) return;
      const price = Number(rawPrice);
      const units = Number(rawUnits);
      if (!rawPrice.trim() || !rawUnits.trim() || !Number.isFinite(price) || !Number.isFinite(units) || price <= 0 || units <= 0) {
        throw new Error('Package price and base-unit count must be positive numbers.');
      }
      field('unit_cost').value = (price / units).toFixed(4);
      field('verified_on').value = '';
      markDirty();
    }));
    remove.addEventListener('click', () => {
      card.remove();
      markDirty();
    });
    grid.addEventListener('input', event => {
      if (['description', 'unit', 'unit_cost', 'supplier', 'specification'].includes(event.target.dataset.field)) {
        field('verified_on').value = '';
      }
      if (event.target.dataset.field === 'customer_supplied' && event.target.checked) {
        field('unit_cost').value = '0';
      }
    });
    actions.append(search, normalize, remove);
    card.append(grid, actions, results);
    $('items').append(card);
  }

  function draft() {
    return {
      ...read(estimateForm), version: current.version,
      items: Array.from($('items').children).map(card => {
        const item = {};
        card.querySelectorAll('[data-field]').forEach(input => {
          item[input.dataset.field] = input.type === 'checkbox' ? input.checked : input.value;
        });
        return item;
      })
    };
  }

  function metrics(target, entries) {
    $(target).replaceChildren(...entries.map(([label, value]) => {
      const metric = node('div', undefined, 'metric');
      metric.append(node('span', label), node('strong', value));
      return metric;
    }));
  }

  function renderTotals(totals, preview = false) {
    $('totals-label').textContent = preview ? 'Preview of unsaved draft. Save before quoting.' : 'Saved estimate';
    metrics('totals', [
      ['Materials incl. waste & consumables', currency(totals.materials)],
      ['Labor', `${currency(totals.labor)} / ${Number(totals.labor_hours).toFixed(2)} person-hrs`],
      ['Direct cost incl. permits/equipment/other', currency(totals.direct_cost)],
      ['Overhead allowance', currency(totals.overhead)],
      ['Contingency allowance', currency(totals.contingency)],
      ['Cost basis', currency(totals.cost_basis)],
      ['Profit allowance', currency(totals.profit_allowance)],
      ['Effective markup / margin', `${totals.markup_percent}% / ${totals.margin_percent}%`],
      ['Selling price before tax', currency(totals.subtotal)],
      ['Tax', currency(totals.tax)],
      ['Customer total', currency(totals.total)]
    ]);
    $('warnings').replaceChildren(...totals.warnings.map(warning => node('li', warning)));
    if (!totals.warnings.length) $('warnings').append(node('li', 'Review checks passed.'));
  }

  function showJob(job) {
    current = job;
    dirty = false;
    $('dashboard').hidden = true;
    $('editor').hidden = false;
    $('editor-title').textContent = job.title;
    $('job-status').textContent = `${job.status} | version ${job.version}`;
    $('message').hidden = true;
    fill(estimateForm, job);
    $('items').replaceChildren();
    job.items.forEach(addItem);
    const locked = job.status !== 'draft';
    $('estimate-fields').disabled = locked;
    $('locked-note').hidden = !locked;
    $('save-estimate').hidden = locked;
    $('preview').hidden = locked;
    $('quote').hidden = locked;
    $('quote').disabled = job.totals.warnings.length > 0;
    $('accept').hidden = job.status !== 'quoted';
    $('invoice').hidden = job.status !== 'completed';
    $('schedule-fields').disabled = !['accepted', 'scheduled'].includes(job.status);
    $('actual-fields').disabled = !['accepted', 'scheduled', 'completed'].includes(job.status);
    $('complete').hidden = job.status !== 'scheduled';
    $('unschedule').hidden = job.status !== 'scheduled';
    $('complete').disabled = !job.actual;
    renderTotals(job.totals);
    scheduleForm.reset();
    if (job.schedule) {
      const start = new Date(job.schedule.start);
      const local = new Date(start.getTime() - start.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
      fill(scheduleForm, {...job.schedule, start: local, crew: job.schedule.crew.join(', ')});
      $('scheduled-summary').textContent = `Reserved: ${localTime(job.schedule.start)} - ${localTime(job.schedule.end)} (${job.schedule.duration_minutes} minutes). ${job.schedule.override_reason ? 'Override: ' + job.schedule.override_reason : ''}`;
    } else $('scheduled-summary').textContent = 'Not scheduled yet.';
    actualForm.reset();
    if (job.actual) fill(actualForm, job.actual);
    $('comparison').replaceChildren();
    if (job.comparison) metrics('comparison', [
      ['Actual direct costs', currency(job.comparison.actual_cost)],
      ['Direct-cost variance (+ = over budget)', currency(job.comparison.direct_cost_variance)],
      ['Labor hours variance (+ = over budget)', job.comparison.labor_hours_variance],
      ['Selling price less actual direct cost (before overhead)', currency(job.comparison.remaining_before_overhead)]
    ]);
    updateDuration();
    window.scrollTo(0, 0);
  }

  function updateDuration() {
    if (!current) return;
    const values = read(scheduleForm);
    const crew = values.crew.split(',').map(value => value.trim()).filter(Boolean);
    const hours = Number(current.totals.labor_hours) / Math.max(crew.length, 1)
      + Number(values.travel_hours) + Number(values.buffer_hours);
    $('duration').textContent = crew.length ? `Suggested reserved duration: ${(Math.ceil(hours * 60) / 60).toFixed(2)} elapsed hours for ${crew.length} people. Review workday limits and breaks.` : 'Enter a crew to see the suggested duration.';
  }

  function localTimestamp(value) {
    const date = new Date(value);
    if (!Number.isFinite(date.getTime())) throw new Error('Choose a valid local start time.');
    const offset = -date.getTimezoneOffset();
    const hours = String(Math.floor(Math.abs(offset) / 60)).padStart(2, '0');
    const minutes = String(Math.abs(offset) % 60).padStart(2, '0');
    return `${value}:00${offset >= 0 ? '+' : '-'}${hours}:${minutes}`;
  }

  function printJob(invoice = false) {
    ensureSaved();
    const job = current;
    const sheet = $('print-sheet');
    sheet.replaceChildren(node('h1', `The Judith Group | ${invoice ? 'Invoice' : job.status === 'draft' ? 'DRAFT - NOT A QUOTE' : 'Estimate'}`));
    sheet.append(node('p', `Reference: ${job.id} | ${job.title}`), node('p', `Customer: ${job.customer}`),
      node('p', `Site: ${job.address}`), node('p', `Quote valid through: ${job.valid_until}`),
      node('h2', 'Scope & assumptions'), node('p', job.scope, 'multiline'),
      node('h2', 'Exclusions'), node('p', job.exclusions, 'multiline'));
    const table = node('table', undefined, 'print-table');
    const heading = node('tr');
    ['Description', 'Quantity', 'Unit'].forEach(value => heading.append(node('th', value)));
    table.append(heading);
    job.items.forEach(item => {
      const row = node('tr');
      [item.description, item.quantity, item.unit].forEach(value => row.append(node('td', value)));
      table.append(row);
    });
    sheet.append(table, node('p', `Fixed price before tax: ${currency(job.totals.subtotal)}`),
      node('p', `Tax: ${currency(job.totals.tax)}`), node('h2', `Total: ${currency(job.totals.total)}`),
      node('p', 'Work outside the stated scope requires a separately approved change order. No payment has been recorded by this document.'));
    if (job.status === 'draft') sheet.append(node('p', 'Unreviewed planning draft. Not approved for customer acceptance.'));
    window.print();
  }

  on('login-form', 'submit', async () => {
    const result = await api('/login', 'POST', {password: $('password').value});
    csrf = result.csrf;
    $('password').value = '';
    $('message').hidden = true;
    await loadDashboard();
  });
  on('logout', 'click', async () => {
    if (!mayLeave()) return;
    await api('/logout', 'POST', {});
    csrf = '';
    current = null;
    dirty = false;
    $('workspace').hidden = true;
    $('login-panel').hidden = false;
    $('logout').hidden = true;
    $('print-sheet').replaceChildren();
  });
  on('new-job', 'click', async () => showJob(await api('/jobs', 'POST', {})));
  on('back', 'click', async () => {
    if (mayLeave()) await loadDashboard();
  });
  on('pdf-form', 'submit', async () => {
    const form = new FormData();
    form.append('file', $('pdf-file').files[0]);
    showJob(await api('/import-pdf', 'POST', form));
  });
  on('add-item', 'click', async () => {
    addItem();
    markDirty();
  });
  estimateForm.addEventListener('input', markDirty);
  $('job-filter').addEventListener('input', renderJobs);
  scheduleForm.addEventListener('input', updateDuration);
  on('estimate-form', 'submit', async () => {
    showJob(await api('/jobs/' + current.id, 'PUT', draft()));
    notify('Draft saved.');
  });
  on('preview', 'click', async () => renderTotals(await api('/preview', 'POST', draft()), true));
  ['quote', 'accept', 'complete', 'unschedule'].forEach(action => on(action, 'click', async () => {
    ensureSaved();
    if (!window.confirm({quote: 'Lock these saved prices and scope as a quote?', accept: 'Record that the customer accepted this quote?', complete: 'Mark this job completed with the recorded actual costs?', unschedule: 'Release this crew reservation? The job will remain accepted.'}[action])) return;
    showJob(await api('/jobs/' + current.id + '/action', 'POST', {action, version: current.version}));
  }));
  on('revision', 'click', async () => {
    ensureSaved();
    showJob(await api('/jobs/' + current.id + '/revision', 'POST', {}));
    notify('Revision created. Original quote and any scheduled work are unchanged. Coordinate scope changes before scheduling this revision.');
  });
  on('save-template', 'click', async () => {
    ensureSaved();
    const name = window.prompt('Template name:', current.title);
    if (!name) return;
    await api('/jobs/' + current.id + '/template', 'POST', {name});
    notify('Template saved without customer details. Review prices and labor whenever reusing it.');
  });
  on('schedule-form', 'submit', async () => {
    const values = read(scheduleForm);
    values.start = localTimestamp(values.start);
    values.crew = values.crew.split(',').map(value => value.trim()).filter(Boolean);
    showJob(await api('/jobs/' + current.id + '/schedule', 'POST', {...values, version: current.version}));
    notify('Crew schedule saved.');
  });
  on('actual-form', 'submit', async () => {
    showJob(await api('/jobs/' + current.id + '/actuals', 'POST', {...read(actualForm), version: current.version}));
    notify('Actual costs saved.');
  });
  on('print', 'click', async () => printJob());
  on('invoice', 'click', async () => printJob(true));
  window.addEventListener('beforeunload', event => {
    if (dirty) {
      event.preventDefault();
      event.returnValue = '';
    }
  });

  run(async () => {
    try {
      const result = await api('/session');
      csrf = result.csrf;
    } catch (error) {
      if (!error.message.includes('Sign in')) notify(error.message, true);
      return;
    }
    await loadDashboard();
  });
})();
