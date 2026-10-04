const form = document.querySelector('#request-form');
let requestId = crypto.randomUUID();
form.addEventListener('submit', async event => {
  event.preventDefault();
  const button = document.querySelector('#submit-request');
  const message = document.querySelector('#request-message');
  const data = Object.fromEntries(new FormData(form));
  data.consent = form.elements.consent.checked;
  data.request_id = requestId;
  button.disabled = true;
  message.textContent = 'Sending your request…';
  try {
    const response = await fetch('/api/requests', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
    const result = await response.json();
    if (!response.ok || !result.success) throw new Error(result.error || 'Unable to send your request. Please try again.');
    form.reset();
    form.hidden = true;
    const confirmation = document.createElement('section');
    confirmation.className = 'request-card';
    confirmation.setAttribute('role', 'status');
    confirmation.textContent = 'Your request has been received. J&A will follow up about your estimate. Reference: ' + result.request_id;
    form.after(confirmation);
  } catch(error) {
    message.textContent = error.message;
    button.disabled = false;
  }
});
