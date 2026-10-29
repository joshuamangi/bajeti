'use strict';
/* =====================================================================
   Bajeti app shell (Prototype A, design/prototype-a).
   Pages are rendered by Jinja. This file adds the sheets, toasts with
   Undo, the hide-amounts toggle, the theme, and saving forms in the
   background: a form is posted with fetch, the handler's redirect
   carries the toast, and the page content is reloaded in place.
   ===================================================================== */
(function () {
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  const RM = () => window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  const store = {
    get(area, k) { try { return window[area].getItem(k); } catch (_) { return null; } },
    set(area, k, v) { try { window[area].setItem(k, v); } catch (_) { /* private mode */ } }
  };

  const S = { hidden: store.get('sessionStorage', 'bajeti-hidden') === '1', data: null };
  const readData = () => { const el = $('#pData'); try { S.data = el ? JSON.parse(el.textContent) : null; } catch (_) { S.data = null; } };
  const cats = () => (S.data && S.data.categories) || [];
  const catById = id => cats().find(c => c.id === +id);

  /* ---------- Money: thousands separators, 0 or 2 decimals, maskable ---------- */
  function fmtNum(n, dec) {
    const d = dec ?? (Number.isInteger(Math.round(n * 100) / 100) ? 0 : 2);
    return Math.abs(n).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
  }
  function moneyText(v, o = {}) { const n = Number(v) || 0; return (n < 0 ? '−' : (o.sign && n > 0 ? '+' : '')) + fmtNum(n, o.dec); }
  function money(v, o = {}) {
    const n = Number(v) || 0, t = moneyText(n, o);
    const cls = ['sensitive', o.cls || '', n < 0 && !o.noNeg ? 'p-negative' : ''].join(' ').trim();
    return `<span class="${cls}" data-value="${esc(t)}">${o.bare ? '' : '<span class="p-cur">KES</span> '}${t}</span>`;
  }
  const parseAmount = v => { const n = parseFloat(String(v || '').replace(/[,\s]/g, '')); return Number.isFinite(n) ? Math.round(n * 100) / 100 : NaN; };
  function statusText(c) {
    if (c.status === 'exceeded') return `${money(-Number(c.balance), { bare: true, dec: 0 })} over`;
    if (c.savings) return `${money(c.balance, { bare: true, dec: 0 })} saved`;
    if (c.status === 'zero') return 'Fully used';
    return `${money(c.balance, { bare: true, dec: 0 })} left`;
  }

  /* ---------- Hide amounts: every .sensitive is masked, screen readers hear "hidden amount" ---------- */
  const originals = new WeakMap();
  const MASK = '<span aria-hidden="true">••••</span><span class="p-visually-hidden">hidden amount</span>';
  function applyMask(root = document) {
    $$('.sensitive', root).forEach(el => {
      if (!originals.has(el)) originals.set(el, el.innerHTML);
      el.innerHTML = S.hidden ? MASK : originals.get(el);
    });
    $$('[data-act=eye]').forEach(b => {
      b.setAttribute('aria-pressed', String(S.hidden));
      const label = S.hidden ? 'Show amounts' : 'Hide amounts';
      b.setAttribute('aria-label', label); b.title = label;
      const i = b.querySelector('i'); if (i) i.className = 'fa ' + (S.hidden ? 'fa-eye-slash' : 'fa-eye');
    });
  }
  function setHidden(v) {
    S.hidden = v; store.set('sessionStorage', 'bajeti-hidden', v ? '1' : '0');
    document.documentElement.classList.toggle('p-values-hidden', v);
    applyMask();
  }

  /* ---------- Theme (light is the default) ---------- */
  function setTheme(t) {
    store.set('localStorage', 'bajeti-theme', t);
    document.documentElement.classList.toggle('light', t === 'light');
    const m = $('#pThemeColor');
    if (m) m.content = getComputedStyle(document.documentElement).getPropertyValue('--text').trim() || '#141821';
    $$('[data-act=theme]').forEach(b => { b.setAttribute('aria-checked', String(t === 'dark')); const x = b.querySelector('.p-switch-text'); if (x) x.textContent = t === 'dark' ? 'On' : 'Off'; });
  }
  const theme = () => (document.documentElement.classList.contains('light') ? 'light' : 'dark');

  /* ---------- Toast (snackbar with optional Undo) ---------- */
  let toastTimer;
  function toast(msg, { type = 'info', undo, ms } = {}) {
    const t = $('#pSnackBar'); if (!t) return; clearTimeout(toastTimer);
    const icon = { success: 'fa-circle-check', error: 'fa-circle-exclamation', warning: 'fa-triangle-exclamation', info: 'fa-circle-info' }[type] || 'fa-circle-info';
    t.className = '';
    t.innerHTML = `<i class="fa ${icon}" aria-hidden="true"></i><span>${msg}</span>${undo ? '<button type="button" class="p-toast-undo">Undo</button>' : ''}`;
    applyMask(t);
    void t.offsetWidth; t.className = 'show ' + type;
    if (undo) t.querySelector('.p-toast-undo').onclick = () => { hideToast(); undo(); };
    toastTimer = setTimeout(hideToast, ms || (undo ? 6000 : 3500));
  }
  function hideToast() { const t = $('#pSnackBar'); if (t) t.classList.remove('show'); }
  function toastFromUrl(url) {
    const p = new URL(url, location.href).searchParams;
    return p.get('message') ? { message: p.get('message'), type: p.get('toast') || 'info' } : null;
  }

  /* ---------- Sheets (modal): focus trap, Escape, backdrop tap ---------- */
  const FOCUSABLE = 'a[href],button:not([disabled]),input:not([disabled]):not([type=hidden]),select:not([disabled]),textarea:not([disabled]),summary,[tabindex]:not([tabindex="-1"])';
  const sheets = []; let sheetSeq = 0;
  function openSheet({ title, render, mount, live }) {
    const id = 'pSheet' + (++sheetSeq);
    const m = document.createElement('div');
    m.className = 'p-modal p-sheet';
    m.innerHTML = `<div class="p-modal-content" role="dialog" aria-modal="true" aria-labelledby="${id}t" tabindex="-1">
      <div class="p-sheet-grip" aria-hidden="true"></div>
      <div class="p-modal-head"><h2 class="p-modal-limit-name" id="${id}t">${title}</h2>
        <button type="button" class="p-close" data-act="close-sheet" aria-label="Close"><i class="fa fa-xmark" aria-hidden="true"></i></button></div>
      <div class="p-modal-body"></div></div>`;
    const entry = { m, render, mount, live, prev: document.activeElement };
    $('#pApp').appendChild(m);
    m.addEventListener('click', e => { if (e.target === m) closeSheet(); });
    sheets.push(entry); paintSheet(entry);
    document.body.classList.add('p-modal-open');
    $('#pMain').setAttribute('aria-hidden', 'true');
    requestAnimationFrame(() => { m.classList.add('open'); const f = m.querySelector('.p-modal-body ' + FOCUSABLE) || m.querySelector('.p-modal-content'); f.focus({ preventScroll: true }); });
    return entry;
  }
  function paintSheet(entry) {
    const body = entry.m.querySelector('.p-modal-body');
    const keep = $$('input[name],select[name],textarea[name]', body).filter(x => x.type !== 'radio' || x.checked).map(x => [x.name, x.type, x.value]);
    body.innerHTML = entry.render();
    keep.forEach(([n, t, v]) => {
      const el = body.querySelector(t === 'radio' ? `input[name="${n}"][value="${CSS.escape(v)}"]` : `[name="${n}"]`);
      if (!el) return; if (t === 'radio') el.checked = true; else if (t !== 'hidden') el.value = v;
    });
    applyMask(body);
    entry.mount && entry.mount(entry.m, entry);
  }
  function closeSheet() {
    const e = sheets.pop(); if (!e) return;
    e.m.classList.remove('open'); setTimeout(() => e.m.remove(), RM() ? 0 : 220);
    if (!sheets.length) { document.body.classList.remove('p-modal-open'); $('#pMain').removeAttribute('aria-hidden'); }
    const back = e.prev && document.contains(e.prev) ? e.prev : (sheets.length ? sheets[sheets.length - 1].m.querySelector('.p-modal-content') : $('#pMain'));
    back && back.focus({ preventScroll: true });
  }
  const closeAllSheets = () => { while (sheets.length) closeSheet(); };
  document.addEventListener('keydown', e => {
    if (!sheets.length) return;
    const top = sheets[sheets.length - 1].m;
    if (e.key === 'Escape') { e.preventDefault(); closeSheet(); return; }
    if (e.key === 'Tab') {
      const f = $$(FOCUSABLE, top).filter(x => x.offsetParent !== null || x === document.activeElement);
      if (!f.length) return;
      const first = f[0], last = f[f.length - 1];
      if (!top.contains(document.activeElement)) { e.preventDefault(); first.focus(); }
      else if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  });

  /* ---------- Saving in the background ---------- */
  async function post(url, fields) {
    const body = new URLSearchParams();
    Object.entries(fields).forEach(([k, v]) => { if (v !== undefined && v !== null) body.append(k, v); });
    let res;
    try { res = await fetch(url, { method: 'POST', body, credentials: 'same-origin', redirect: 'follow' }); }
    catch (_) { return { ok: false, message: 'No connection. Nothing was saved.', type: 'error' }; }
    if (res.redirected && new URL(res.url).pathname === '/login') { location.href = '/login'; return { ok: false }; }
    const t = res.redirected ? toastFromUrl(res.url) : null;
    if (!res.ok || !t) return { ok: false, message: 'Something went wrong. Nothing was saved.', type: 'error' };
    return { ok: t.type !== 'error', message: t.message, type: t.type };
  }
  async function refreshMain() {
    // The path alone: the active budget comes from its cookie, not a stale ?budget_id.
    const url = location.pathname;
    let html;
    try { const res = await fetch(url, { credentials: 'same-origin' }); if (!res.ok) throw new Error(res.status); html = await res.text(); }
    catch (_) { toast("Couldn't refresh. Pull down or tap refresh to try again.", { type: 'warning' }); return; }
    const doc = new DOMParser().parseFromString(html, 'text/html');
    const main = doc.querySelector('#pMain'), data = doc.querySelector('#pData');
    if (!main) { location.reload(); return; }
    const y = window.scrollY;
    $('#pMain').innerHTML = main.innerHTML;
    if (data && $('#pData')) $('#pData').textContent = data.textContent;
    readData(); applyMask(); restoreDismissed();
    window.scrollTo(0, y);
    sheets.forEach(s => { if (s.live) paintSheet(s); });
  }
  async function save(url, fields, { undo, success } = {}) {
    const r = await post(url, fields);
    if (r.ok === false && !r.message) return r;
    await refreshMain();
    if (!r.ok) { toast(esc(r.message), { type: 'error' }); return r; }
    toast(success || esc(r.message), { type: 'success', undo });
    return r;
  }

  /* Deletes wait 6 seconds so Undo needs nothing on the server. Leaving the page sends them at once. */
  const pending = new Map(); let pendingSeq = 0;
  function deferDelete({ url, fields = {}, rows = [], message }) {
    const key = ++pendingSeq;
    rows.forEach(r => { r.hidden = true; });
    const send = () => { if (!pending.has(key)) return; pending.delete(key); post(url, fields).then(r => { refreshMain(); if (r.ok === false && r.message) toast(esc(r.message), { type: 'error' }); }); };
    pending.set(key, { url, fields, timer: setTimeout(send, 6000) });
    toast(message, { type: 'warning', undo: () => { const p = pending.get(key); if (!p) return; clearTimeout(p.timer); pending.delete(key); rows.forEach(r => { r.hidden = false; }); toast('Restored'); } });
  }
  window.addEventListener('pagehide', () => {
    pending.forEach(p => { clearTimeout(p.timer); const b = new URLSearchParams(); Object.entries(p.fields).forEach(([k, v]) => b.append(k, v)); navigator.sendBeacon(p.url, b); });
    pending.clear();
  });
  const rowsFor = sel => $$(sel).map(el => el.closest('li,tr') || el);

  /* ---------- Sheets: add expense, category, edit expense, category form, transfer ---------- */
  const byName = (a, b) => a.name.localeCompare(b.name);
  const budget = () => S.data && S.data.budget;
  const month = () => (S.data && S.data.month) || '';
  const monthName = m => MONTHS[+String(m).slice(5, 7) - 1] || '';
  function recentCategories(n = 4) {
    const last = cats().map(c => ({ c, at: c.expenses.reduce((m, e) => (e.created_at > m ? e.created_at : m), '') })).filter(x => x.at);
    return last.sort((a, b) => b.at.localeCompare(a.at) || byName(a.c, b.c)).slice(0, n).map(x => x.c);
  }
  function scopeBar(text) {
    const bs = (S.data && S.data.budgets) || []; if (bs.length < 2) return '';
    return `<div class="p-scope"><p class="p-scope-label">${text}</p><div class="p-budget-switch" role="radiogroup" aria-label="Active budget">${bs.map(b => `<button type="button" role="radio" aria-checked="${b.id === budget().id}" class="p-switch-chip" data-act="set-budget" data-id="${b.id}"><span class="p-switch-radio" aria-hidden="true"></span><span class="p-switch-chip-text"><span>${esc(b.name)}</span><span class="p-switch-chip-type">${b.type === 'savings' ? 'Savings' : 'Expense'}</span></span></button>`).join('')}</div></div>`;
  }
  const catChip = (c, sel) => `<label class="p-chip" data-name="${esc(c.name.toLowerCase())}"><input type="radio" name="cat" value="${c.id}" ${c.id === sel ? 'checked' : ''}><span><b>${esc(c.name)}</b><small>${statusText(c)}</small></span></label>`;

  function openAddExpense(preset = {}) {
    if (!budget()) { toast('Create a budget first.', { type: 'warning' }); return; }
    let first = true;
    openSheet({
      title: 'Add expense', live: true, render: () => {
        const b = budget(), scope = cats().slice().sort(byName);
        const sel = first && preset.categoryId ? +preset.categoryId : null; first = false;
        // Letter filter from 2 categories (owner decision 2026-10-28); Recently used only past 8.
        const many = scope.length > 1, recent = scope.length > 8 && !sel ? recentCategories(4) : [];
        const letters = [...new Set(scope.map(c => c.name.trim().charAt(0).toUpperCase()))].sort();
        return `<form data-form="add-expense" novalidate class="p-modal-body">
          ${scopeBar('Budget')}
          <label class="p-amount-field" for="pAmt"><span class="p-amount-cur" aria-hidden="true">KES</span><input id="pAmt" name="amount" class="p-money-input" inputmode="decimal" autocomplete="off" enterkeyhint="next" placeholder="0" aria-label="Amount in KES" aria-describedby="pAmtErr"></label>
          <p class="p-error-text" id="pAmtErr" aria-live="polite"></p>
          <fieldset class="p-fieldset"><legend>Category</legend>
          ${many ? `<div class="p-letters" role="group" aria-label="Show categories starting with"><button type="button" class="p-letter p-letter-all" data-letter="" aria-pressed="true">All</button>${letters.map(l => `<button type="button" class="p-letter" data-letter="${esc(l)}" aria-pressed="false" aria-label="Categories starting with ${esc(l)}">${esc(l)}</button>`).join('')}</div>
          <p class="p-search-count" id="pCatCount" aria-live="polite"></p>` : ''}
          ${recent.length ? `<div class="p-chip-block" data-recent><p class="p-chip-group"><i class="fa fa-clock-rotate-left" aria-hidden="true"></i> Recently used</p><div class="p-chips">${recent.map(c => catChip(c, sel)).join('')}</div></div>` : ''}
          ${scope.length ? `<div class="p-chip-block" data-group><p class="p-chip-group">${esc(b.name)} · ${b.type === 'savings' ? 'Savings' : 'Expense'} · A–Z</p><div class="p-chips">${scope.map(c => catChip(c, sel)).join('')}</div></div>`
            : `<p class="p-category-progress-no-content">${esc(b.name)} has no categories yet. <button type="button" class="p-link-btn" data-act="cat-new">Add one</button></p>`}
          <p class="p-error-text" id="pCatErr" aria-live="polite"></p></fieldset>
          <label class="p-field"><span>Note</span><input name="description" maxlength="60" placeholder="What was it for?" autocomplete="off"></label>
          <div class="p-sheet-actions"><button type="button" class="p-modal-btn-tertiary" data-act="quick-from-form"><i class="fa fa-bolt" aria-hidden="true"></i> Quick Expense<small>adds the full allocation</small></button><button type="submit" class="p-modal-btn-primary"><i class="fa fa-check" aria-hidden="true"></i> ${b.type === 'savings' ? 'Add withdrawal' : 'Add expense'}</button></div>
        </form>`;
      },
      mount: m => {
        const f = m.querySelector('form');
        const upd = () => { const v = f.querySelector('input[name=cat]:checked')?.value; $$('input[name=cat]', f).forEach(i => i.closest('.p-chip').classList.toggle('is-picked', !!v && i.value === v && !i.checked)); };
        f.addEventListener('change', e => { if (e.target.name === 'cat') upd(); }); upd();
        const bar = m.querySelector('.p-letters'); if (!bar) return;
        bar.addEventListener('click', ev => {
          const btn = ev.target.closest('.p-letter'); if (!btn) return;
          const L = btn.getAttribute('aria-pressed') === 'true' && btn.dataset.letter ? '' : btn.dataset.letter;
          $$('.p-letter', bar).forEach(x => x.setAttribute('aria-pressed', String(x.dataset.letter === L)));
          const hits = [];
          $$('[data-group]', f).forEach(g => { let any = false; $$('.p-chip', g).forEach(ch => { const ok = !L || ch.dataset.name.charAt(0) === L.toLowerCase(); ch.hidden = !ok; if (ok) { any = true; hits.push(ch); } }); g.hidden = !any; });
          const r = f.querySelector('[data-recent]'); if (r) r.hidden = !!L;
          const cnt = $('#pCatCount', m);
          if (L && hits.length === 1) { const i = hits[0].querySelector('input'); i.checked = true; upd(); cnt.textContent = `Picked ${i.closest('.p-chip').querySelector('b').textContent}`; }
          else cnt.textContent = L ? `${hits.length} categor${hits.length === 1 ? 'y' : 'ies'} starting with ${L}` : '';
        });
      }
    });
  }
  const expenseType = c => (c.savings ? 'withdrawal' : 'spend');
  async function addExpense(c, amount, description) {
    const before = new Set(c.expenses.map(e => e.id));
    const r = await post('/dashboard/expenses', { category_id: c.id, amount, description, expense_type: expenseType(c), month: month() });
    if (!r.ok) { if (r.message) toast(esc(r.message), { type: 'error' }); return; }
    await refreshMain();
    const added = (catById(c.id)?.expenses || []).filter(e => !before.has(e.id)).sort((a, b) => b.id - a.id)[0];
    toast(`Added ${money(amount)} to ${esc(c.name)}`, {
      type: 'success',
      undo: added ? () => save(`/dashboard/expenses/${added.id}/delete`, { expense_type: added.type }, { success: 'Removed' }) : undefined
    });
  }
  function quickExpense(id) {
    const c = catById(id); if (!c) return;
    const amount = Number(c.allocated);
    if (!(amount > 0)) { toast(`${esc(c.name)} has nothing allocated.`, { type: 'warning' }); return; }
    addExpense(c, c.allocated, 'Quick Expense');
  }
  function submitAddExpense(f) {
    const amount = parseAmount(f.amount.value), cat = f.querySelector('input[name=cat]:checked');
    const aErr = $('#pAmtErr'), cErr = $('#pCatErr'); aErr.textContent = ''; cErr.textContent = ''; f.amount.removeAttribute('aria-invalid');
    if (!(amount > 0)) { aErr.textContent = 'Enter an amount greater than 0.'; f.amount.setAttribute('aria-invalid', 'true'); f.amount.focus(); return; }
    if (!cat) { cErr.textContent = 'Choose a category.'; f.querySelector('input[name=cat]')?.focus(); return; }
    const c = catById(cat.value);
    closeSheet();
    addExpense(c, amount.toFixed(2), f.description.value.trim() || (c.savings ? 'Withdrawal' : 'Expense'));
  }

  function categorySheet(id) {
    const c = catById(id); if (!c) return '<p>This category was removed.</p>';
    const n = esc(c.name), pct = Math.min(100, c.percent);
    const expenses = c.expenses.slice().sort((a, b) => b.created_at.localeCompare(a.created_at) || b.id - a.id);
    return `<div class="p-cat-sheet-top"><div><span class="p-small">${c.savings ? 'Saved' : 'Remaining'}</span><strong class="p-big ${Number(c.balance) < 0 ? 'p-negative' : 'p-positive'}">${money(c.balance)}</strong></div>
      <div class="p-cat-sheet-meta"><span class="p-category-status ${c.status}">${c.percent.toFixed(1)}% ${c.savings ? 'withdrawn' : 'used'}${c.status === 'exceeded' ? ' · over' : ''}</span><span class="p-small">of ${money(c.available)}</span></div></div>
      <div class="p-progress-bar" role="progressbar" aria-label="${n} used" aria-valuenow="${Math.round(pct)}" aria-valuemin="0" aria-valuemax="100"><span class="p-progress-fill p-${c.status}-fill" style="width:${pct}%"></span></div>
      <div class="p-sheet-actions"><button type="button" class="p-modal-btn-tertiary" data-act="quick" data-id="${c.id}"><i class="fa fa-bolt" aria-hidden="true"></i> Quick Expense</button><button type="button" class="p-modal-btn-primary" data-act="add-exp" data-id="${c.id}"><i class="fa fa-plus" aria-hidden="true"></i> Add Expense</button></div>
      <div class="p-category-progress-transfer-divider"><h4>Transfers</h4>${c.transfers.length ? `<ul class="p-category-progress-ul">${c.transfers.map(t => { const inn = t.direction === 'in'; return `<li class="p-category-progress-li" data-transfer="${t.id}"><span><b>${inn ? 'From' : 'To'} ${esc(t.other || 'another category')}</b>${t.description ? `<small>${esc(t.description)}</small>` : ''}</span><span class="${inn ? 'p-positive' : 'p-negative'}">${inn ? '+' : '−'}${money(t.amount, { bare: true })}</span>
        <span class="p-row-actions"><button type="button" class="p-icon-btn-danger" data-act="transfer-undo" data-id="${t.id}" aria-label="Undo transfer ${inn ? 'from' : 'to'} ${esc(t.other || 'another category')}" title="Undo transfer"><i class="fa fa-rotate-left" aria-hidden="true"></i></button></span></li>`; }).join('')}</ul>` : '<p class="p-category-progress-no-content">No transfer or top-up this month.</p>'}</div>
      <div class="p-category-progress-transfer-divider"><h4>Expenses <span class="p-count">${expenses.length}</span></h4>${expenses.length ? `<ul class="p-category-progress-ul">${expenses.map(e => `<li class="p-category-progress-li" data-exp="${e.id}"><span><b>${esc(e.description || 'Expense')}</b><small>${monthName(e.month)}${e.type === 'withdrawal' ? ' · withdrawal' : ''}</small></span><span>${money(e.amount)}</span>
        <span class="p-row-actions"><button type="button" class="p-icon-btn-warning" data-act="exp-edit" data-id="${e.id}" data-cat="${c.id}" aria-label="Edit ${esc(e.description || 'expense')}"><i class="fa fa-pencil" aria-hidden="true"></i></button>
        <button type="button" class="p-icon-btn-danger" data-act="exp-del" data-id="${e.id}" data-cat="${c.id}" aria-label="Delete ${esc(e.description || 'expense')}"><i class="fa fa-trash" aria-hidden="true"></i></button></span></li>`).join('')}</ul>` : '<p class="p-category-progress-no-content">No expenses this month. Use Quick Expense or Add Expense.</p>'}</div>
      ${c.target ? `<div class="p-category-progress-transfer-divider"><h4>Targets</h4><ul class="p-target-list"><li class="p-target-li">${targetTerms(c.target)}</li></ul></div>` : ''}
      <div class="p-category-progress-transfer-divider"><div class="p-sheet-actions p-sheet-actions-3">
        <button type="button" class="p-modal-btn-info" data-act="cat-topup" data-id="${c.id}">Top up</button>
        <button type="button" class="p-modal-btn-warning" data-act="cat-edit" data-id="${c.id}">Edit</button>
        <button type="button" class="p-modal-btn-danger" data-act="cat-del" data-id="${c.id}">Delete</button></div></div>`;
  }
  function targetTerms(t) {
    return [['short_term', 'Short term'], ['mid_term', 'Mid term'], ['long_term', 'Long term']].filter(([k]) => t[k]).map(([k, l]) => {
      const term = t[k], pct = Math.max(0, Math.min(100, term.percent)), done = term.percent >= 100;
      return `<div class="p-target-term"><div class="p-target-term-head"><span>${l} · ${money(term.amount, { bare: true })}</span><span class="${done ? 'p-positive' : ''}">${done ? '<i class="fa fa-circle-check" aria-hidden="true"></i> Target reached' : `${term.percent.toFixed(1)}% · ${money(term.remaining, { bare: true })} to go`}</span></div>
        <div class="p-progress-bar" role="progressbar" aria-label="${l}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.round(pct)}"><span class="p-progress-fill ${done ? 'p-ok-fill' : 'p-target-fill'}" style="width:${pct}%"></span></div></div>`;
    }).join('');
  }
  const openCategory = id => { const c = catById(id); if (c) openSheet({ title: esc(c.name), render: () => categorySheet(+id), live: true }); };

  function openExpenseEdit(cid, eid) {
    const c = catById(cid), e = c && c.expenses.find(x => x.id === +eid); if (!e) return;
    openSheet({
      title: 'Edit expense', render: () => `<form data-form="expense-edit" data-cat="${c.id}" data-id="${e.id}" class="p-modal-form-content" novalidate>
        <label class="p-field"><span>Amount</span><input name="amount" class="p-money-input" inputmode="decimal" value="${esc(e.amount)}" required></label>
        <label class="p-field"><span>Note</span><input name="description" value="${esc(e.description)}" maxlength="60"></label>
        <p class="p-error-text" data-err aria-live="polite"></p><button type="submit" class="p-modal-btn-primary">Save</button></form>`
    });
  }
  function submitExpenseEdit(f) {
    const c = catById(f.dataset.cat), e = c && c.expenses.find(x => x.id === +f.dataset.id); if (!e) return;
    const amount = parseAmount(f.amount.value);
    if (!(amount > 0)) { f.querySelector('[data-err]').textContent = 'Enter an amount greater than 0.'; return; }
    closeSheet();
    const old = { amount: e.amount, description: e.description };
    const url = `/dashboard/expenses/${e.id}/edit`, base = { category_id: c.id, expense_type: e.type, month: e.month };
    save(url, { ...base, amount: amount.toFixed(2), description: f.description.value.trim() }, {
      success: 'Expense updated', undo: () => save(url, { ...base, ...old }, { success: 'Restored' })
    });
  }

  function openCategoryForm(id) {
    const c = id ? catById(id) : null, b = budget();
    if (!b) { toast('Create a budget first.', { type: 'warning' }); return; }
    openSheet({
      title: c ? 'Edit ' + esc(c.name) : 'New category in ' + esc(b.name), render: () => `<form data-form="category" data-id="${c ? c.id : ''}" class="p-modal-form-content" novalidate>
        <label class="p-field"><span>Category name</span><input name="name" value="${esc(c ? c.name : '')}" required maxlength="40" placeholder="e.g. School fees"></label>
        <label class="p-field"><span>${b.type === 'savings' ? 'Monthly saving' : 'Allocated amount'}</span><input name="allocated" class="p-money-input" inputmode="decimal" value="${esc(c ? c.allocated : '')}" required></label>
        <p class="p-error-text" data-err aria-live="polite"></p><button type="submit" class="p-modal-btn-primary">${c ? 'Save' : 'Add category'}</button></form>`
    });
  }
  async function submitCategory(f) {
    const b = budget(), id = f.dataset.id, name = f.name.value.trim(), allocated = parseAmount(f.allocated.value), err = f.querySelector('[data-err]');
    if (!name) { err.textContent = 'Enter a name.'; f.name.focus(); return; }
    if (!(allocated >= 0)) { err.textContent = 'Enter an amount (0 or more).'; f.allocated.focus(); return; }
    if (cats().some(c => c.name.toLowerCase() === name.toLowerCase() && c.id !== +id)) { err.textContent = `${esc(name)} already exists in this budget.`; return; }
    closeSheet();
    if (!id) { save('/dashboard/categories', { name, category_type: b.type, budget_id: b.id, allocated_amount: allocated.toFixed(2) }); return; }
    const c = catById(id);
    if (name !== c.name) { const r = await post(`/dashboard/categories/${id}/edit`, { name }); if (!r.ok) { toast(esc(r.message || 'Could not rename.'), { type: 'error' }); await refreshMain(); return; } }
    if (allocated !== Number(c.allocated)) { save(`/dashboard/allocations/${b.id}/edit`, { category_id: id, allocated_amount: allocated.toFixed(2) }, { success: `Saved ${esc(name)}` }); return; }
    await refreshMain(); toast(`Saved ${esc(name)}`, { type: 'success' });
  }
  function deleteCategory(id) {
    const c = catById(id); if (!c) return;
    closeAllSheets();
    deferDelete({ url: `/dashboard/categories/${id}/delete`, rows: rowsFor(`[data-act=cat][data-id="${id}"]`), message: `Deleted ${esc(c.name)}` });
  }
  function deleteExpense(cid, eid) {
    const c = catById(cid), e = c && c.expenses.find(x => x.id === +eid); if (!e) return;
    deferDelete({ url: `/dashboard/expenses/${e.id}/delete`, fields: { expense_type: e.type }, rows: rowsFor(`[data-exp="${e.id}"]`), message: `Deleted ${esc(e.description || 'expense')}` });
  }

  function openTransfer(preset = {}) {
    const to = preset.to ? catById(preset.to) : null, b = budget(), list = cats().slice().sort(byName);
    if (!list.length) { toast('Add categories first.', { type: 'warning' }); return; }
    openSheet({
      title: to ? 'Top up ' + esc(to.name) : 'Move money', render: () => `<form data-form="transfer" class="p-modal-form-content" novalidate>
        <label class="p-field"><span>From</span><select name="from"><option value="unallocated">Unallocated in ${esc(b.name)}</option>${list.filter(c => !to || c.id !== to.id).map(c => `<option value="${c.id}">${esc(c.name)} (${S.hidden ? '••••' : moneyText(c.balance)} left)</option>`).join('')}</select></label>
        <label class="p-field"><span>To</span><select name="to">${list.map(c => `<option value="${c.id}" ${to && c.id === to.id ? 'selected' : ''}>${esc(c.name)}</option>`).join('')}</select></label>
        <label class="p-field"><span>Amount</span><input name="amount" class="p-money-input" inputmode="decimal" required></label>
        <label class="p-field"><span>Note (optional)</span><input name="note" maxlength="60"></label>
        <p class="p-error-text" data-err aria-live="polite"></p><button type="submit" class="p-modal-btn-primary"><i class="fa fa-arrow-right-arrow-left" aria-hidden="true"></i> Move money</button></form>`
    });
  }
  function submitTransfer(f) {
    const err = f.querySelector('[data-err]'), amount = parseAmount(f.amount.value), from = f.from.value, to = catById(f.to.value);
    if (!(amount > 0)) { err.textContent = 'Enter an amount greater than 0.'; return; }
    if (String(to.id) === from) { err.textContent = 'Pick two different categories.'; return; }
    if (from !== 'unallocated') {
      const src = catById(from);
      if (amount > Number(src.balance)) { err.textContent = `Only ${S.hidden ? 'a smaller amount' : 'KES ' + moneyText(src.balance)} is available there.`; return; }
      closeSheet();
      moveMoney(src, to, amount, f.note.value.trim());
      return;
    }
    // From unallocated: raise the category's allocation.
    closeSheet();
    const b = budget(), old = to.allocated, url = `/dashboard/allocations/${b.id}/edit`;
    save(url, { category_id: to.id, allocated_amount: (Number(to.allocated) + amount).toFixed(2) }, {
      success: `Added ${money(amount)} to ${esc(to.name)} from unallocated`,
      undo: () => save(url, { category_id: to.id, allocated_amount: old }, { success: 'Restored' })
    });
  }

  /* ---------- Budgets: create, edit, delete, allocations and targets ---------- */
  const budgetById = id => ((S.data && S.data.budgets) || []).find(b => b.id === +id);
  function openBudgetForm(id) {
    const b = id ? budgetById(id) : null, locked = b && b.name === 'Monthly';
    openSheet({
      title: b ? 'Edit ' + esc(b.name) : 'New budget', render: () => `<form data-form="budget" data-id="${b ? b.id : ''}" class="p-modal-form-content" novalidate>
        <label class="p-field"><span>Budget name</span><input name="name" value="${esc(b ? b.name : '')}" required maxlength="40" ${locked ? 'readonly aria-readonly="true"' : ''} placeholder="e.g. Holiday Fund"></label>
        <label class="p-field"><span>Budget type</span><select name="type" ${b ? 'disabled' : ''}><option value="expense" ${b && b.type === 'expense' ? 'selected' : ''}>Expense</option><option value="savings" ${b && b.type === 'savings' ? 'selected' : ''}>Savings</option></select></label>
        <label class="p-field"><span>Budget amount</span><input name="amount" class="p-money-input" inputmode="decimal" value="${esc(b ? b.amount : '')}" required></label>
        ${locked ? '<p class="p-small">Monthly budgets can only have the amount edited.</p>' : b ? '<p class="p-small">The type can’t change after a budget is created.</p>' : ''}
        <p class="p-error-text" data-err aria-live="polite"></p><button type="submit" class="p-modal-btn-primary">Save</button></form>`
    });
  }
  async function submitBudget(f) {
    const id = f.dataset.id, name = f.name.value.trim(), amount = parseAmount(f.amount.value), err = f.querySelector('[data-err]');
    if (!name) { err.textContent = 'Enter a name.'; return; }
    if (!(amount > 0)) { err.textContent = 'Enter an amount greater than 0.'; return; }
    closeSheet();
    if (id) {
      const b = budgetById(id), url = `/dashboard/budgets/${id}/edit`;
      save(url, { budget_name: name, budget_amount: amount.toFixed(2), budget_type: b.type }, {
        success: `Saved ${esc(name)}`, undo: () => save(url, { budget_name: b.name, budget_amount: b.amount, budget_type: b.type }, { success: 'Restored' })
      });
      return;
    }
    const before = new Set(((S.data && S.data.budgets) || []).map(b => b.id));
    const r = await post('/dashboard/budgets', { budget_name: name, budget_amount: amount.toFixed(2), budget_type: f.type.value });
    if (!r.ok) { toast(esc(r.message || 'Could not create the budget.'), { type: 'error' }); return; }
    await refreshMain();
    const created = ((S.data && S.data.budgets) || []).find(b => !before.has(b.id));
    toast(`Created ${esc(name)}. Add categories next.`, { type: 'success' });
    if (created) { await setActiveBudget(created.id); openBudgetManage(created.id); }
  }
  async function setDefaultBudget(el) {
    const r = await post(`/dashboard/budgets/${el.dataset.id}/default`, { is_default: el.dataset.on });
    toast(esc(r.message || 'Could not change the default budget.'), { type: r.ok ? 'success' : 'error' });
    if (r.ok) await refreshMain();
  }
  function deleteBudget(id) {
    const b = budgetById(id); if (!b) return;
    deferDelete({ url: `/dashboard/${id}/delete`, rows: rowsFor(`[data-act=budget-del][data-id="${id}"]`), message: `Deleted ${esc(b.name)}` });
  }
  async function openBudgetManage(id) {
    if (!budget() || budget().id !== +id) await setActiveBudget(id);
    const b = budget(); if (!b) return;
    openSheet({ title: esc(b.name) + ': allocations', render: budgetManage, live: true });
  }
  function budgetManage() {
    const b = budget(); if (!b) return '<p>This budget was removed.</p>';
    const list = cats().slice().sort(byName), allocated = list.reduce((s, c) => s + Number(c.allocated), 0), unallocated = Number(S.data.unallocated);
    const withTargets = list.filter(c => c.target);
    const totals = { short_term: 0, mid_term: 0, long_term: 0 };
    withTargets.forEach(c => Object.keys(totals).forEach(k => { if (c.target[k]) totals[k] += Number(c.target[k].amount); }));
    return `<div class="p-alloc-summary"><div><span>Budget</span><strong>${money(b.amount, { bare: true })}</strong></div><div><span>Allocated</span><strong>${money(allocated, { bare: true })}</strong></div><div><span>Unallocated</span><strong class="${unallocated < 0 ? 'p-negative' : ''}">${money(unallocated, { bare: true })}</strong></div></div>
      ${unallocated < 0 ? `<div class="p-alert-warning" role="note"><i class="fa fa-triangle-exclamation" aria-hidden="true"></i><p>Over-allocated by ${money(-unallocated)}. Lower an allocation or raise the budget.</p></div>` : ''}
      <div class="p-category-progress-transfer-divider"><h4>Add category</h4><form data-form="inline-category" class="p-inline-row" novalidate>
        <label class="p-visually-hidden" for="pIcName">Category name</label><input id="pIcName" name="name" placeholder="Name" maxlength="40" autocomplete="off">
        <label class="p-visually-hidden" for="pIcAmt">Allocated amount</label><input id="pIcAmt" name="allocated" class="p-money-input" inputmode="decimal" placeholder="Amount" autocomplete="off">
        <button type="submit" class="p-inline-submit" aria-label="Add category"><i class="fa fa-plus" aria-hidden="true"></i></button></form><p class="p-error-text" data-err aria-live="polite"></p></div>
      <div class="p-category-progress-transfer-divider"><h4>Allocations</h4>${list.length ? `<ul class="p-category-progress-ul">${list.map(c => `<li class="p-category-progress-li" data-alloc="${c.id}"><span>${esc(c.name)}</span><span class="p-alloc-amt">${money(c.allocated, { bare: true })}</span><span class="p-row-actions">
        <button type="button" class="p-icon-btn-warning" data-act="cat-edit" data-id="${c.id}" aria-label="Edit ${esc(c.name)} allocation"><i class="fa fa-pencil" aria-hidden="true"></i></button>
        <button type="button" class="p-icon-btn-danger" data-act="alloc-del" data-id="${c.id}" aria-label="Remove ${esc(c.name)} from ${esc(b.name)}"><i class="fa fa-trash" aria-hidden="true"></i></button></span></li>`).join('')}</ul>` : '<p class="p-category-progress-no-content">No categories yet. Add one above.</p>'}</div>
      <div class="p-category-progress-transfer-divider"><h4>Targets</h4>
        ${list.length ? `<form data-form="target" class="p-modal-form-content" novalidate><label class="p-field"><span>Category</span><select name="cid">${list.map(c => `<option value="${c.id}">${esc(c.name)}</option>`).join('')}</select></label>
        <div class="p-target-inputs">${[['short_term', 'Short'], ['mid_term', 'Mid'], ['long_term', 'Long']].map(([k, l]) => `<label class="p-field"><span>${l}</span><input name="${k}" class="p-money-input" inputmode="decimal" placeholder="0"></label>`).join('')}</div>
        <p class="p-error-text" data-err aria-live="polite"></p><button type="submit" class="p-modal-btn-tertiary"><i class="fa fa-bullseye" aria-hidden="true"></i> Save target</button></form>` : ''}
        <div class="p-target-totals">${[['short_term', 'Short'], ['mid_term', 'Mid'], ['long_term', 'Long']].map(([k, l]) => `<div><span class="p-target-total-label">${l} term</span><span class="p-target-total-value">${money(totals[k], { bare: true })}</span></div>`).join('')}</div>
        ${withTargets.length ? `<ul class="p-target-list">${withTargets.map(c => `<li class="p-target-li" data-target="${c.target.id}"><div class="p-target-head"><span class="p-category-name">${esc(c.name)}</span><span class="p-row-actions">
          <button type="button" class="p-icon-btn-warning" data-act="target-edit" data-id="${c.id}" aria-label="Edit targets for ${esc(c.name)}"><i class="fa fa-pencil" aria-hidden="true"></i></button>
          <button type="button" class="p-icon-btn-danger" data-act="target-del" data-id="${c.id}" aria-label="Delete targets for ${esc(c.name)}"><i class="fa fa-trash" aria-hidden="true"></i></button></span></div>${targetTerms(c.target)}</li>`).join('')}</ul>` : '<p class="p-category-progress-no-content">No targets yet. Set short, mid and long term amounts above.</p>'}</div>`;
  }
  function submitInlineCategory(f) {
    const b = budget(), name = f.name.value.trim(), allocated = parseAmount(f.allocated.value), err = f.parentElement.querySelector('[data-err]');
    err.textContent = '';
    if (!name) { err.textContent = 'Enter a name.'; f.name.focus(); return; }
    if (!(allocated >= 0)) { err.textContent = 'Enter an amount (0 or more).'; f.allocated.focus(); return; }
    if (cats().some(c => c.name.toLowerCase() === name.toLowerCase())) { err.textContent = `${esc(name)} already exists in this budget.`; return; }
    save('/dashboard/categories', { name, category_type: b.type, budget_id: b.id, allocated_amount: allocated.toFixed(2) }).then(() => { const n = $('#pIcName'); n && n.focus(); });
  }
  function deleteAllocation(cid) {
    const c = catById(cid), b = budget(); if (!c || !c.allocation_id) return;
    deferDelete({ url: `/dashboard/allocations/${b.id}/delete/${c.allocation_id}`, rows: rowsFor(`[data-alloc="${c.id}"]`), message: `Removed ${esc(c.name)} from ${esc(b.name)}` });
  }
  const termFields = f => Object.fromEntries(['short_term', 'mid_term', 'long_term'].map(k => [k + '_amount', f[k].value.trim()]));
  function submitTarget(f) {
    const err = f.querySelector('[data-err]'), fields = termFields(f);
    if (!Object.values(fields).some(v => parseAmount(v) > 0)) { err.textContent = 'Enter at least one target amount.'; return; }
    const c = catById(f.cid.value), b = budget();
    if (f.dataset.single) closeSheet();
    save('/dashboard/targets', { budget_id: b.id, category_id: c.id, ...fields }, { success: `Targets saved for ${esc(c.name)}` });
  }
  function openTargetForm(cid) {
    const c = catById(cid); if (!c) return;
    const t = c.target || {}, val = k => (t[k] ? esc(t[k].amount) : '');
    openSheet({
      title: 'Targets: ' + esc(c.name), render: () => `<form data-form="target" data-single="1" class="p-modal-form-content" novalidate><input type="hidden" name="cid" value="${c.id}">
        <div class="p-target-inputs">${[['short_term', 'Short term'], ['mid_term', 'Mid term'], ['long_term', 'Long term']].map(([k, l]) => `<label class="p-field"><span>${l}</span><input name="${k}" class="p-money-input" inputmode="decimal" value="${val(k)}" placeholder="0"></label>`).join('')}</div>
        <p class="p-small">Progress uses the category's balance (${money(c.balance)}).</p>
        <p class="p-error-text" data-err aria-live="polite"></p><button type="submit" class="p-modal-btn-primary">Save targets</button></form>`
    });
  }
  function deleteTarget(cid) {
    const c = catById(cid), b = budget(); if (!c || !c.target) return;
    deferDelete({ url: `/dashboard/targets/${b.id}/${c.target.id}/delete`, rows: rowsFor(`[data-target="${c.target.id}"]`), message: `Removed targets for ${esc(c.name)}` });
  }

  const transferIds = () => new Set(cats().flatMap(c => c.transfers.map(t => t.id)));
  async function moveMoney(src, to, amount, note) {
    const before = transferIds();
    const r = await post('/dashboard/transfers', { from_category_id: src.id, to_category_id: to.id, amount: amount.toFixed(2), description: note, month: month() });
    if (!r.ok) { if (r.message) toast(esc(r.message), { type: 'error' }); await refreshMain(); return; }
    await refreshMain();
    const added = [...transferIds()].filter(id => !before.has(id)).sort((a, b) => b - a)[0];
    toast(`Moved ${money(amount)} to ${esc(to.name)}`, {
      type: 'success', undo: added ? () => save(`/dashboard/transfers/${added}/undo`, {}, { success: 'Transfer undone' }) : undefined
    });
  }
  function undoTransfer(id) {
    deferDelete({ url: `/dashboard/transfers/${id}/undo`, rows: rowsFor(`[data-transfer="${id}"]`), message: 'Transfer undone' });
  }

  /* ---------- Recurring (monthly bills; docs/design/recurring.md) ---------- */
  function dueAction(el, name) {
    const id = el.dataset.id, date = el.dataset.date, label = esc(el.dataset.name);
    const undo = () => save(`/recurring/${id}/runs/${date}/undo`, {}, { success: 'Undone' });
    save(`/recurring/${id}/${name}`, { due_date: date }, { success: name === 'approve' ? `Recorded ${label}` : `Skipped ${label} this time`, undo });
  }
  function approveAll(el) {
    save(`/recurring/${el.dataset.id}/approve-all`, {}, { success: `Recorded ${el.dataset.count} payments for ${esc(el.dataset.name)}` });
  }
  function openRecurringForm(r) {
    const list = cats().slice().sort(byName);
    if (!list.length) { toast('Add a category to this budget first.', { type: 'warning' }); return; }
    const pad = n => String(n).padStart(2, '0'), now = new Date();
    const firstNext = `${now.getMonth() === 11 ? now.getFullYear() + 1 : now.getFullYear()}-${pad(now.getMonth() === 11 ? 1 : now.getMonth() + 2)}-01`;
    openSheet({
      title: r ? 'Edit ' + esc(r.name) : 'New recurring expense', render: () => `<form data-form="recurring" data-id="${r ? r.id : ''}" class="p-modal-form-content" novalidate>
        <label class="p-field"><span>Name</span><input name="name" value="${esc(r ? r.name : '')}" required maxlength="60" placeholder="e.g. Internet"></label>
        <label class="p-field"><span>Amount</span><input name="amount" class="p-money-input" inputmode="decimal" value="${esc(r ? r.amount : '')}" required></label>
        <label class="p-field"><span>Category in ${esc(budget().name)}</span><select name="category_id">${list.map(c => `<option value="${c.id}" ${r && r.category_id === c.id ? 'selected' : ''}>${esc(c.name)}</option>`).join('')}</select></label>
        <label class="p-field"><span>Next due date (repeats monthly)</span><input name="next_due" type="date" value="${esc(r ? r.next_due : firstNext)}" required></label>
        <p class="p-small" data-day-note></p>
        <fieldset class="p-fieldset"><legend>When it is due</legend>
          <label class="p-radio-card"><input type="radio" name="mode" value="ask_first" ${!r || r.mode === 'ask_first' ? 'checked' : ''}><span><b>Ask first</b><small>Shows in Due now on the due date for one tap</small></span></label>
          <label class="p-radio-card"><input type="radio" name="mode" value="auto" ${r && r.mode === 'auto' ? 'checked' : ''}><span><b>Auto-add</b><small>Recorded on the due date and listed under Recently added</small></span></label>
        </fieldset>
        <p class="p-error-text" data-err aria-live="polite"></p><button type="submit" class="p-modal-btn-primary">${r ? 'Save' : 'Add recurring expense'}</button></form>`,
      mount: m => {
        const f = m.querySelector('form'), note = f.querySelector('[data-day-note]');
        const upd = () => { const day = +String(f.next_due.value).slice(8, 10); note.textContent = day >= 29 ? `Due on day ${day}, or the last day of shorter months.` : ''; };
        f.next_due.addEventListener('change', upd); upd();
      }
    });
  }
  function submitRecurring(f) {
    const err = f.querySelector('[data-err]'), name = f.name.value.trim(), amount = parseAmount(f.amount.value);
    if (!name) { err.textContent = 'Enter a name.'; f.name.focus(); return; }
    if (!(amount > 0)) { err.textContent = 'Enter an amount greater than 0.'; f.amount.focus(); return; }
    if (!f.next_due.value) { err.textContent = 'Pick the next due date.'; f.next_due.focus(); return; }
    closeSheet();
    const id = f.dataset.id;
    save(id ? `/recurring/${id}/edit` : '/recurring', {
      name, amount: amount.toFixed(2), category_id: f.category_id.value, next_due: f.next_due.value,
      mode: f.querySelector('input[name=mode]:checked').value
    }, { success: `Saved ${esc(name)}` });
  }
  function deleteRecurring(el) {
    deferDelete({ url: `/recurring/${el.dataset.id}/delete`, rows: rowsFor(`[data-rec="${el.dataset.id}"]`), message: `Deleted ${esc(el.dataset.name)}` });
  }

  /* ---------- Payments inbox (docs/design/payments.md) ---------- */
  // Made-up messages for "Try a sample": fake names, numbers and codes.
  const SAMPLES = [
    'QXY78ZK2LM Confirmed. Ksh1,840.00 paid to Demo Supermarket. on 27/10/26 at 7:15 PM. New M-PESA balance is Ksh12,300.00. Transaction cost, Ksh0.00.',
    'QRT45UV6WX Confirmed. Ksh300.00 sent to DEMO WATER VENDOR 0700000000 on 27/10/26 at 9:02 AM. New M-PESA balance is Ksh8,743.00. Transaction cost, Ksh7.00.',
    'Your payment of KES 3,500.00 to Demo Fibre Internet was successful. Reference: FBR20261027.'
  ];
  let sampleIdx = 0;
  async function submitPaste(f) {
    const raw = f.raw.value.trim(), err = f.querySelector('[data-err]');
    err.textContent = '';
    if (!raw) { err.textContent = 'Paste a message first.'; f.raw.focus(); return; }
    const r = await post('/payments/capture', { raw });
    await refreshMain();
    if (r.ok === false && !r.message) return;
    toast(esc(r.message), { type: r.type === 'success' ? 'success' : r.type });
    if (r.type === 'success' || r.type === 'warning') { const t = $('#pPaste'); if (t && r.type === 'success') t.value = ''; }
  }
  function submitPayApprove(f) {
    const err = f.querySelector('[data-err]'), category = f.category_id.value;
    if (!category) { err.textContent = 'Choose a category.'; f.category_id.focus(); return; }
    const fields = { category_id: category, remember: f.remember && f.remember.checked ? '1' : '' };
    if (f.amount) {
      const amount = parseAmount(f.amount.value);
      if (!(amount > 0)) { err.textContent = 'Enter the amount.'; f.amount.focus(); return; }
      fields.amount = amount.toFixed(2);
    }
    const id = f.dataset.id;
    save(`/payments/${id}/approve`, fields, { undo: () => save(`/payments/${id}/restore`, {}, { success: 'Back in the inbox' }) });
  }
  function dismissPayment(el) {
    deferDelete({ url: `/payments/${el.dataset.id}/dismiss`, rows: rowsFor(`[data-pay="${el.dataset.id}"]`), message: `Dismissed ${esc(el.dataset.payee)}` });
  }

  async function setActiveBudget(id) {
    if (budget() && +id === budget().id) return;
    try { await fetch(`/dashboard?budget_id=${encodeURIComponent(id)}`, { credentials: 'same-origin' }); }
    catch (_) { toast("Couldn't switch budget. Check your connection.", { type: 'warning' }); return; }
    if (location.search) history.replaceState(null, '', location.pathname);
    await refreshMain();
  }

  /* ---------- Dismissed warnings stay dismissed for this session ---------- */
  function restoreDismissed() {
    $$('[data-dismiss-key]').forEach(el => { if (store.get('sessionStorage', 'bajeti-dismiss-' + el.dataset.dismissKey)) el.remove(); });
  }

  /* ---------- Event delegation ---------- */
  const ACT = {
    'close-sheet': () => closeSheet(),
    eye: () => setHidden(!S.hidden),
    refresh: async () => { await refreshMain(); toast('Up to date', { type: 'success' }); },
    theme: () => setTheme(theme() === 'light' ? 'dark' : 'light'),
    add: () => openAddExpense({}),
    'add-exp': el => openAddExpense({ categoryId: el.dataset.id }),
    quick: el => quickExpense(el.dataset.id),
    'quick-from-form': el => {
      const f = el.closest('form'), v = f.querySelector('input[name=cat]:checked');
      if (!v) { $('#pCatErr').textContent = 'Choose a category for Quick Expense.'; f.querySelector('input[name=cat]')?.focus(); return; }
      closeSheet(); quickExpense(v.value);
    },
    cat: el => openCategory(el.dataset.id),
    'cat-new': () => openCategoryForm(),
    'cat-edit': el => openCategoryForm(el.dataset.id),
    'cat-del': el => deleteCategory(el.dataset.id),
    'cat-topup': el => openTransfer({ to: el.dataset.id }),
    transfer: () => openTransfer({}),
    'transfer-undo': el => undoTransfer(el.dataset.id),
    'due-approve': el => dueAction(el, 'approve'),
    'due-skip': el => dueAction(el, 'skip'),
    'due-approve-all': el => approveAll(el),
    'rec-new': () => openRecurringForm(null),
    'rec-edit': el => openRecurringForm(JSON.parse(el.dataset.item)),
    'rec-pause': el => save(`/recurring/${el.dataset.id}/pause`, {}, { success: 'Paused' }),
    'rec-resume': el => save(`/recurring/${el.dataset.id}/resume`, {}, { success: 'Resumed' }),
    'rec-del': el => deleteRecurring(el),
    'paste-sample': () => { const t = $('#pPaste'); if (t) { t.value = SAMPLES[sampleIdx++ % SAMPLES.length]; t.focus(); } },
    'pay-dismiss': el => dismissPayment(el),
    'exp-edit': el => openExpenseEdit(el.dataset.cat, el.dataset.id),
    'exp-del': el => deleteExpense(el.dataset.cat, el.dataset.id),
    'set-budget': el => setActiveBudget(el.dataset.id),
    'budget-new': () => openBudgetForm(),
    'budget-edit': el => openBudgetForm(el.dataset.id),
    'budget-del': el => deleteBudget(el.dataset.id),
    'budget-default': el => setDefaultBudget(el),
    'budget-manage': el => openBudgetManage(el.dataset.id),
    'alloc-del': el => deleteAllocation(el.dataset.id),
    'target-edit': el => openTargetForm(el.dataset.id),
    'target-del': el => deleteTarget(el.dataset.id),
    'cats-all': el => {
      const open = el.getAttribute('aria-expanded') !== 'true';
      $$('.p-cat-extra').forEach(li => { li.hidden = !open; });
      el.setAttribute('aria-expanded', String(open));
      el.innerHTML = open ? 'Show fewer <i class="fa fa-chevron-up" aria-hidden="true"></i>' : `Show all ${el.dataset.count} categories <i class="fa fa-chevron-down" aria-hidden="true"></i>`;
    },
    'toggle-pass': el => {
      const i = el.parentElement.querySelector('input'), show = i.type === 'password';
      i.type = show ? 'text' : 'password'; el.setAttribute('aria-pressed', String(show));
      const what = (el.getAttribute('aria-label') || 'Show password').replace(/^(Show|Hide) /, '');
      el.setAttribute('aria-label', (show ? 'Hide ' : 'Show ') + what); el.querySelector('i').className = 'fa ' + (show ? 'fa-eye-slash' : 'fa-eye');
    },
    // The only confirm dialog in the app: everything else can be undone.
    'logout-all': (el, e) => {
      e.preventDefault();
      const form = el.closest('form');
      openSheet({
        title: 'Log out everywhere?', render: () => `<p>This signs out every phone and browser, including this one. You will need your password to log back in.</p>
          <div class="p-sheet-actions"><button type="button" class="p-modal-btn-secondary" data-act="close-sheet">Cancel</button><button type="button" class="p-modal-btn-danger" data-confirm-ok>Log out everywhere</button></div>`,
        mount: m => { m.querySelector('[data-confirm-ok]').onclick = () => form.submit(); }
      });
    },
    'alert-dismiss': el => { const box = el.closest('[data-dismiss-key]'); if (box) { store.set('sessionStorage', 'bajeti-dismiss-' + box.dataset.dismissKey, '1'); box.remove(); } }
  };
  const FORMS = {
    'add-expense': submitAddExpense, 'expense-edit': submitExpenseEdit, category: submitCategory, transfer: submitTransfer,
    budget: submitBudget, 'inline-category': submitInlineCategory, target: submitTarget, recurring: submitRecurring,
    paste: submitPaste, 'pay-approve': submitPayApprove
  };
  document.addEventListener('click', e => {
    const el = e.target.closest('[data-act]'); if (!el) return;
    const fn = ACT[el.dataset.act]; if (!fn) return;
    if (el.tagName === 'A') e.preventDefault();
    try { fn(el, e); } catch (err) { console.error('[Bajeti] action ' + el.dataset.act, err); toast('Something went wrong. Nothing was saved.', { type: 'error' }); }
  });
  document.addEventListener('submit', e => {
    const f = e.target;
    if (f.dataset.match) {
      const [a, b] = f.dataset.match.split(',').map(n => f.elements[n]), err = f.querySelector('[data-err]');
      if (a.value !== b.value) { e.preventDefault(); if (err) err.textContent = 'The passwords do not match.'; b.setAttribute('aria-invalid', 'true'); b.focus(); return; }
    }
    const h = FORMS[f.dataset.form]; if (!h) return;
    e.preventDefault();
    try { h(f); } catch (err) { console.error('[Bajeti] form ' + f.dataset.form, err); toast('Something went wrong. Nothing was saved.', { type: 'error' }); }
  });

  /* ---------- Boot ---------- */
  function boot() {
    readData();
    document.documentElement.classList.toggle('p-values-hidden', S.hidden);
    setTheme(theme());
    applyMask();
    restoreDismissed();
    const t = toastFromUrl(location.href);
    if (t) {
      toast(esc(t.message), { type: t.type });
      const clean = location.pathname + location.search.replace(/([?&])(toast|message)=[^&]*/g, '$1').replace(/[?&]+$/, '');
      history.replaceState(null, '', clean);
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();

  window.Bajeti = { toast, openSheet, closeSheet, save, post, refreshMain, deferDelete, money, moneyText, applyMask, esc, setActiveBudget };
})();
