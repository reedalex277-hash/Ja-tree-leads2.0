'use strict';
const $ = id => document.getElementById(id);
let token = sessionStorage.getItem('ja_inbox_token') || '';
let rows = [], offset = 0;
const fragment = new URLSearchParams(location.hash.slice(1));
if (fragment.has('access_token')) {
  token = fragment.get('access_token');
  sessionStorage.setItem('ja_inbox_token', token);
}
const callbackError = fragment.get('error_description');
history.replaceState(null, '', location.pathname);
const message = value => { $('message').textContent = value; };
async function api(method, data, extra = '') {
  const res = await fetch('/api/inbox' + extra, {method, headers: {
    'Content-Type': 'application/json', ...(token ? {Authorization: 'Bearer ' + token} : {})
  }, ...(data ? {body: JSON.stringify(data)} : {})});
  const result = await res.json();
  if (res.status === 401) logout();
  if (!res.ok) throw new Error(result.error || 'Please try again.');
  return result;
}
function logout() {
  token = ''; rows = []; offset = 0;
  sessionStorage.removeItem('ja_inbox_token');
  $('requests').replaceChildren(); $('inbox').hidden = true; $('login').hidden = false;
}
function node(tag, text) { const el = document.createElement(tag); if (text !== undefined) el.textContent = text; return el; }
function inputLabel(parent, text, input) { const label = node('label', text); label.append(input); parent.append(label); }
function render() {
  $('requests').replaceChildren();
  const mode = $('filter').value;
  const visible = rows.filter(r => mode === 'all' || (mode === 'due' ? r.followup && new Date(r.followup) <= new Date() && !['won','lost'].includes(r.status) : r.status === mode));
  if (!visible.length) $('requests').append(node('p', 'No matching requests in the loaded results.'));
  for (const r of visible) {
    const card = node('article'); card.append(node('h2', r.name));
    card.append(node('p', 'Received ' + new Date(r.created_at).toLocaleString()));
    const details = node('p', `${r.service} · ${r.timing}\n${r.address}\n${r.city}, ${r.zip}\n\n${r.description}`); details.className = 'details'; card.append(details);
    const phone = node('a', 'Call ' + r.phone); phone.href = 'tel:' + r.phone.replace(/[^0-9+]/g, ''); card.append(phone);
    if (r.email) { card.append(node('p')); const email = node('a', 'Email customer'); email.href = 'mailto:' + encodeURIComponent(r.email); card.append(email); }
    if (r.followup && new Date(r.followup) <= new Date() && !['won','lost'].includes(r.status)) { const due = node('p', 'Follow-up due'); due.className = 'due'; card.append(due); }
    const form = node('form'), status = node('select');
    for (const value of ['new','contacted','quoted','won','lost']) { const option = node('option', value); option.value = value; status.append(option); }
    status.value = r.status; inputLabel(form, 'Status', status);
    const followup = node('input'); followup.type = 'datetime-local';
    if (r.followup) { const d = new Date(r.followup); followup.value = new Date(d - d.getTimezoneOffset()*60000).toISOString().slice(0,16); }
    inputLabel(form, 'Follow-up date and time', followup);
    const notes = node('textarea'); notes.maxLength = 5000; notes.value = r.notes || ''; inputLabel(form, 'Private notes', notes);
    const save = node('button', 'Save changes'); save.className = 'primary'; form.append(save);
    const result = node('p'); result.setAttribute('role','status'); form.append(result);
    form.addEventListener('submit', async event => { event.preventDefault(); save.disabled = true; result.textContent = 'Saving…';
      try { const saved = await api('PATCH', {id:r.id, status:status.value, notes:notes.value, followup:followup.value ? new Date(followup.value).toISOString() : null}); Object.assign(r, saved.request); result.textContent = 'Saved.'; }
      catch(error) { result.textContent = error.message; } finally { save.disabled = false; }
    }); card.append(form); card.append(node('small', 'Reference: ' + r.id)); $('requests').append(card);
  }
}
async function load(append = false) {
  message('Loading requests…'); $('more').disabled = true; $('refresh').disabled = true;
  try { const result = await api('GET', null, '?offset=' + (append ? offset : 0)); rows = append ? rows.concat(result.requests) : result.requests; offset = rows.length;
    $('login').hidden = true; $('inbox').hidden = false; $('more').hidden = result.requests.length < 100; render(); message('');
  } catch(error) { message(error.message); }
  finally { $('more').disabled = false; $('refresh').disabled = false; }
}
$('login').addEventListener('submit', async event => { event.preventDefault(); const button = $('login').querySelector('button'); button.disabled = true;
  try { await api('POST', {email:$('email').value}); message('Check your email for the sign-in link. Open it in this browser.'); }
  catch(error) { message(error.message); } finally { button.disabled = false; }
});
$('logout').onclick = () => { logout(); message('Signed out on this tab.'); };
$('refresh').onclick = () => load(); $('more').onclick = () => load(true); $('filter').onchange = render;
if (token) load(); else if (callbackError) message(callbackError);
