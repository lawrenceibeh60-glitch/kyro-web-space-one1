import { request } from './api/client.js';

const history = [];
let reference = null, imageUrl = null;

function el(tag, attrs = {}, text = '') {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (key === 'class') node.className = value;
    else node.setAttribute(key, value);
  }
  if (text) node.textContent = text;
  return node;
}

const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

export function initAIStudio() {
  if (document.getElementById('aiStudio')) return;
  const launch = el('button', { id: 'aiLaunch', class: 'ai-launch', title: 'Open AI character studio' }, 'AI Studio');
  document.querySelector('.topbar .spacer')?.after(launch);
  const root = el('section', { id: 'aiStudio', class: 'ai-studio', hidden: '' });
  const side = el('div', { class: 'ai-side' }), head = el('header', { class: 'ai-head' });
  head.append(el('span', {}, 'KAE / AI CHARACTER STUDIO'));
  const close = el('button', { type: 'button', 'aria-label': 'Close AI Studio' }, 'Close');
  head.append(close);
  const thread = el('div', { class: 'ai-thread', 'aria-live': 'polite' });
  const compose = el('form', { class: 'ai-compose' });
  const input = el('textarea', { placeholder: 'Describe a character, pose, expression, outfit, or animation idea…', maxlength: '12000' });
  const actions = el('div', { class: 'ai-actions' });
  const send = el('button', { class: 'primary', type: 'submit' }, 'Ask xKiro');
  const generate = el('button', { type: 'button' }, 'Generate image');
  actions.append(send, generate);
  compose.append(input, actions);
  side.append(head, thread, compose);

  const preview = el('div', { class: 'ai-preview' });
  const previewHead = el('header', { class: 'ai-head' }, 'CHARACTER OUTPUT');
  const body = el('div', { class: 'ai-preview-body' });
  const status = el('div', { class: 'ai-status' }, 'Checking xKiro configuration…');
  const stage = el('div', { class: 'ai-image-stage' });
  const image = el('img', { alt: 'Generated anime character preview', hidden: '' });
  stage.append(image);
  const prompt = el('textarea', { class: 'ai-prompt', placeholder: 'Image prompt used for generation' });
  const previewActions = el('div', { class: 'ai-actions' });
  const showRef = el('button', { type: 'button', disabled: '' }, 'Show over canvas');
  const download = el('a', { hidden: '', download: 'kae-character.png' }, 'Save image');
  download.style.cssText = 'padding:8px 10px;border:1px solid var(--line);color:inherit;text-decoration:none;font-size:12px';
  previewActions.append(showRef, download);
  const note = el('p', { class: 'ai-note' }, 'Canvas reference is a visual guide, not a rigged layer. Image-to-editable-parts and bone binding are not yet automatic. Generated images are not uploaded to your project automatically.');
  body.append(status, stage, prompt, previewActions, note);
  preview.append(previewHead, body);
  root.append(side, preview);
  document.body.append(root);

  function addMessage(role, content) {
    const message = el('div', { class: 'ai-msg ' + role });
    message.textContent = content;
    thread.append(message);
    thread.scrollTop = thread.scrollHeight;
  }
  function setBusy(value) {
    send.disabled = value;
    generate.disabled = value;
  }

  async function ask() {
    const message = input.value.trim();
    if (!message) return;
    input.value = '';
    addMessage('user', message);
    const previousHistory = history.slice(-12);
    history.push({ role: 'user', content: message });
    setBusy(true);
    status.textContent = 'Sending prompt to xKiro…';
    try {
      const result = await request('POST', '/api/ai/chat', { message, history: previousHistory });
      addMessage('assistant', result.reply);
      history.push({ role: 'assistant', content: result.reply });
      status.textContent = 'Chat ready · ' + (result.model || 'xKiro');
      if (/generate|draw|create an image|make an image/i.test(message)) prompt.value = message;
    } catch (error) {
      addMessage('assistant', 'AI unavailable: ' + error.message);
      status.textContent = error.message;
    } finally {
      setBusy(false);
    }
  }

  compose.addEventListener('submit', event => { event.preventDefault(); ask(); });
  input.addEventListener('keydown', event => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      ask();
    }
  });

  generate.addEventListener('click', async () => {
    const description = prompt.value.trim() || input.value.trim() ||
      [...history].reverse().find(item => item.role === 'user')?.content || '';
    if (!description) {
      status.textContent = 'Describe the character first.';
      input.focus();
      return;
    }
    prompt.value = description;
    setBusy(true);
    status.textContent = 'Submitting image job to xKiro…';
    try {
      let result = await request('POST', '/api/ai/images', { prompt: description });
      const deadline = Date.now() + 5 * 60 * 1000;
      while (result.status !== 'succeeded' && result.job_id && Date.now() < deadline) {
        status.textContent = 'Generating image… xKiro job ' + result.status;
        await delay(2500);
        result = await request('GET', '/api/ai/images/' + encodeURIComponent(result.job_id));
      }
      if (result.status !== 'succeeded') {
        throw new Error(Date.now() >= deadline ? 'Image generation timed out after 5 minutes.' : 'Image job did not return a completed image.');
      }
      const data = result.image || {};
      imageUrl = data.url || (data.b64_json ? 'data:image/png;base64,' + data.b64_json : null);
      if (!imageUrl) throw new Error('Image provider returned no usable image.');
      image.src = imageUrl;
      image.hidden = false;
      showRef.disabled = false;
      download.href = imageUrl;
      download.hidden = false;
      status.textContent = 'Image ready. You can save it or show it over the canvas as a temporary visual reference.';
      if (data.revised_prompt) prompt.value = data.revised_prompt;
    } catch (error) {
      status.textContent = 'Image generation failed: ' + error.message;
      addMessage('assistant', 'Image generation failed: ' + error.message);
    } finally {
      setBusy(false);
    }
  });

  function clearReference() {
    reference?.remove();
    reference = null;
    showRef.textContent = 'Show over canvas';
  }
  showRef.addEventListener('click', () => {
    const viewport = document.getElementById('viewport');
    if (!viewport || !imageUrl) return;
    if (reference) {
      clearReference();
      return;
    }
    reference = el('img', { class: 'ai-reference', alt: 'Temporary AI image reference overlay' });
    reference.src = imageUrl;
    viewport.append(reference);
    showRef.textContent = 'Hide canvas reference';
    root.hidden = true;
  });
  launch.addEventListener('click', () => { root.hidden = false; input.focus(); });
  close.addEventListener('click', () => { root.hidden = true; });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !root.hidden) root.hidden = true;
  });

  addMessage('assistant', 'Describe your anime character or animation idea. Ask xKiro to refine the design, then generate an image. Image generation runs as a job, so the preview appears when xKiro finishes.');
  request('GET', '/api/ai/status').then(result => {
    status.textContent = result.configured
      ? 'xKiro configured · chat ' + result.chat_model + ' · images ' + result.image_model
      : 'xKiro not configured: set XKIRO_API_KEY on the server.';
  }).catch(() => { status.textContent = 'Could not check xKiro configuration.'; });
}
