import { request } from './api/client.js';

const history = [];
let reference = null, imageUrl = null, videoUrl = null, currentProject = null, latestVideoAnalysis = '', latestCreativeDirection = '', currentPlan = null, latestSampledFrames = null, currentVectorPlan = null;

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

function projectSummary() {
  if (!currentProject) return null;
  return {
    id: currentProject.id,
    name: currentProject.name,
    version: currentProject.version,
    settings: currentProject.settings || {},
    scenes: Array.isArray(currentProject.scenes) ? currentProject.scenes.map(scene => ({
      id: scene.id, name: scene.name,
      layers: Array.isArray(scene.layers) ? scene.layers.map(layer => ({ id: layer.id, name: layer.name, type: layer.type })) : [],
    })) : [],
    drawings: currentProject.drawings && typeof currentProject.drawings === 'object'
      ? Object.fromEntries(Object.entries(currentProject.drawings).slice(0, 100).map(([id, drawing]) => [id, { id, name: drawing?.name || id }])) : {},
    characters: Array.isArray(currentProject.characters) ? currentProject.characters.slice(0, 100).map(c => ({ id: c.id, name: c.name })) : [],
    rigs: Array.isArray(currentProject.rigs) ? currentProject.rigs.slice(0, 100).map(r => ({ id: r.id, name: r.name })) : [],
  };
}

async function loadCurrentProject() {
  const projectId = new URLSearchParams(location.search).get('project');
  if (!projectId) return;
  try {
    currentProject = await request('GET', '/api/projects/' + encodeURIComponent(projectId));
  } catch (_) {
    currentProject = null;
  }
}

export function initAIStudio() {
  if (document.getElementById('aiStudio')) return;
  const launch = el('button', { id: 'aiLaunch', class: 'ai-launch', title: 'Open integrated KAE AI workspace' }, 'AI Workspace');
  document.querySelector('.topbar .spacer')?.after(launch);
  const root = el('section', { id: 'aiStudio', class: 'ai-studio', hidden: '' });
  const side = el('div', { class: 'ai-side' }), head = el('header', { class: 'ai-head' });
  head.append(el('span', {}, 'KAE / ENGINE AI'));
  const close = el('button', { type: 'button', 'aria-label': 'Close AI workspace' }, 'Close');
  head.append(close);
  const providerPanel = el('section', { class: 'ai-provider-panel', 'aria-label': 'AI provider settings' });
  providerPanel.append(el('div', { class: 'ai-section-title' }, 'AI PROVIDER CONNECTION'));
  const providerStatus = el('div', { class: 'ai-provider-status' });
  const providerDot = el('span', { class: 'ai-provider-dot', 'aria-hidden': 'true' });
  const providerStatusText = el('span', {}, 'Not connected · key stays in this browser session');
  providerStatus.append(providerDot, providerStatusText);
  const providerGrid = el('div', { class: 'ai-provider-grid' });
  const providerSelect = el('select', { class: 'ai-provider-control', 'aria-label': 'AI company' });
  const baseUrl = el('input', { class: 'ai-provider-control', type: 'url', placeholder: 'https://api.example.com/v1', 'aria-label': 'API base URL' });
  const apiKey = el('input', { class: 'ai-provider-control', type: 'password', placeholder: 'Paste API key (never shown again)', autocomplete: 'off', spellcheck: 'false', 'aria-label': 'Provider API key' });
  const modelSelect = el('select', { class: 'ai-provider-control', 'aria-label': 'AI model' });
  const customModel = el('input', { class: 'ai-provider-control', type: 'text', placeholder: 'Optional: custom model ID', autocomplete: 'off', 'aria-label': 'Custom model ID' });
  const refreshModels = el('button', { type: 'button' }, 'Load models');
  const testProvider = el('button', { type: 'button', class: 'primary' }, 'Test & connect');
  const providerActions = el('div', { class: 'ai-provider-actions' });
  providerActions.append(refreshModels, testProvider);
  function providerField(label, control) {
    const wrap = el('label', { class: 'ai-provider-field' });
    wrap.append(el('span', {}, label), control);
    return wrap;
  }
  providerGrid.append(
    providerField('COMPANY', providerSelect),
    providerField('MODEL', modelSelect),
    providerField('API KEY', apiKey),
    providerField('CUSTOM MODEL ID (OPTIONAL)', customModel),
    providerField('API BASE URL', baseUrl),
  );
  providerPanel.append(providerStatus, providerGrid, providerActions,
    el('p', { class: 'ai-provider-help' }, 'Keys are sent over HTTPS for your AI requests and kept only in this tab session. They are not saved to the KAE server. Claude uses its native API; other listed providers use OpenAI-compatible chat endpoints.'));
  const thread = el('div', { class: 'ai-thread', 'aria-live': 'polite' });
  const compose = el('form', { class: 'ai-compose' });
  const input = el('textarea', { placeholder: 'Describe a character, animation, or change to the current project…', maxlength: '12000' });
  const actions = el('div', { class: 'ai-actions' });
  const send = el('button', { class: 'primary', type: 'submit' }, 'Ask KAE AI');
  const generate = el('button', { type: 'button' }, 'Generate image');
  actions.append(send, generate);
  compose.append(input, actions);
  side.append(head, providerPanel, thread, compose);

  const preview = el('div', { class: 'ai-preview' });
  const previewHead = el('header', { class: 'ai-head' }, 'REFERENCE & OUTPUT');
  const body = el('div', { class: 'ai-preview-body' });
  const status = el('div', { class: 'ai-status' }, 'Loading KAE engine capabilities…');

  const videoPanel = el('section', { class: 'ai-video-panel' });
  videoPanel.append(el('div', { class: 'ai-section-title' }, 'VIDEO → MOTION ANALYSIS'));
  const videoInput = el('input', { type: 'file', accept: 'video/mp4,video/webm,video/quicktime,video/*', 'aria-label': 'Choose reference video' });
  const video = el('video', { class: 'ai-reference-video', controls: '', playsinline: '', preload: 'metadata', hidden: '' });
  const videoMeta = el('div', { class: 'ai-note' }, 'Choose a short reference clip. KAE samples up to 6 frames in your browser; the original video file is not sent to xKiro.');
  const sceneSelect = el('select', { class: 'ai-scene-select', 'aria-label': 'Scene for vector reconstruction' });
  const analyze = el('button', { type: 'button', class: 'primary', disabled: '' }, 'Analyze reference video');
  const reconstruct = el('button', { type: 'button', disabled: '' }, 'Reconstruct editable vector cels');
  const applyReconstruction = el('button', { type: 'button', class: 'primary', disabled: '' }, 'Add reconstruction as a new layer');
  const vectorSummary = el('pre', { class: 'ai-plan-summary', hidden: '' });
  const vectorPreview = el('div', { class: 'ai-vector-preview', hidden: '' });
  const buildPlan = el('button', { type: 'button', disabled: '' }, 'Build transform-keyframe plan');
  const applyPlan = el('button', { type: 'button', class: 'primary', disabled: '' }, 'Apply transform keyframes');
  const planSummary = el('pre', { class: 'ai-plan-summary', hidden: '' });
  videoPanel.append(videoInput, video, videoMeta, analyze, sceneSelect, reconstruct, vectorSummary, vectorPreview, applyReconstruction, buildPlan, planSummary, applyPlan);

  const stage = el('div', { class: 'ai-image-stage' });
  const image = el('img', { alt: 'Generated anime character preview', hidden: '' });
  stage.append(image);
  const prompt = el('textarea', { class: 'ai-prompt', placeholder: 'Image prompt used for generation' });
  const previewActions = el('div', { class: 'ai-actions' });
  const showRef = el('button', { type: 'button', disabled: '' }, 'Show over canvas');
  const download = el('a', { hidden: '', download: 'kae-character.png' }, 'Save image');
  download.style.cssText = 'padding:8px 10px;border:1px solid var(--line);color:inherit;text-decoration:none;font-size:12px';
  previewActions.append(showRef, download);
  const note = el('p', { class: 'ai-note' }, 'The AI receives the sampled frames and the KAE capability/schema inventory. It will analyze the motion and ask for your creative changes. Analysis is not yet a finished animation; reconstruction must be generated as editable KAE project data.');
  body.append(status, videoPanel, stage, prompt, previewActions, note);
  preview.append(previewHead, body);
  root.append(side, preview);
  document.body.append(root);

  function addMessage(role, content) {
    const message = el('div', { class: 'ai-msg ' + role });
    message.textContent = content;
    thread.append(message);
    thread.scrollTop = thread.scrollHeight;
  }
  const providerCatalog = [
    {id:'openai',label:'OpenAI',base_url:'https://api.openai.com/v1',models:['gpt-4.1','gpt-4.1-mini','gpt-4o','gpt-4o-mini']},
    {id:'anthropic',label:'Anthropic / Claude',base_url:'https://api.anthropic.com/v1',models:['claude-sonnet-4-5','claude-haiku-4-5','claude-opus-4-1']},
    {id:'groq',label:'Groq',base_url:'https://api.groq.com/openai/v1',models:['openai/gpt-oss-120b','llama-3.3-70b-versatile','qwen/qwen3-32b']},
    {id:'openrouter',label:'OpenRouter',base_url:'https://openrouter.ai/api/v1',models:['openai/gpt-4.1-mini','anthropic/claude-sonnet-4.5','google/gemini-2.5-flash']},
    {id:'together',label:'Together AI',base_url:'https://api.together.xyz/v1',models:['openai/gpt-oss-120b','meta-llama/Llama-3.3-70B-Instruct-Turbo']},
    {id:'deepseek',label:'DeepSeek',base_url:'https://api.deepseek.com/v1',models:['deepseek-chat','deepseek-reasoner']},
    {id:'mistral',label:'Mistral',base_url:'https://api.mistral.ai/v1',models:['mistral-large-latest','mistral-small-latest','codestral-latest']},
    {id:'xai',label:'xAI',base_url:'https://api.x.ai/v1',models:['grok-4','grok-3','grok-3-mini']},
    {id:'cerebras',label:'Cerebras',base_url:'https://api.cerebras.ai/v1',models:['llama-3.3-70b','qwen-3-32b']},
    {id:'fireworks',label:'Fireworks AI',base_url:'https://api.fireworks.ai/inference/v1',models:['accounts/fireworks/models/llama-v3p3-70b-instruct']},
    {id:'perplexity',label:'Perplexity',base_url:'https://api.perplexity.ai',models:['sonar-pro','sonar']},
    {id:'nvidia',label:'NVIDIA NIM',base_url:'https://integrate.api.nvidia.com/v1',models:['meta/llama-3.3-70b-instruct']},
    {id:'xkiro',label:'xKiro',base_url:'https://api.xkiro.com/v1',models:['mistralai/devstral-medium']},
    {id:'custom',label:'Custom OpenAI-compatible',base_url:'',models:[]},
  ];
  let connectedProvider = null;
  function providerProfile() {
    const selected = providerCatalog.find(item => item.id === providerSelect.value) || providerCatalog[0];
    return {
      provider: selected.id,
      base_url: baseUrl.value.trim() || selected.base_url,
      api_key: apiKey.value.trim(),
      model: customModel.value.trim() || modelSelect.value,
    };
  }
  function providerLight(state, message) {
    providerDot.className = 'ai-provider-dot ' + state;
    providerStatusText.textContent = message;
  }
  function populateModels(models, selected) {
    modelSelect.replaceChildren();
    for (const model of models) modelSelect.append(el('option', { value: model }, model));
    if (selected && models.includes(selected)) modelSelect.value = selected;
    if (!models.length) modelSelect.append(el('option', { value: '' }, 'Load models after entering an API key'));
  }
  function resetProviderForSelection() {
    const item = providerCatalog.find(provider => provider.id === providerSelect.value) || providerCatalog[0];
    baseUrl.value = item.base_url;
    baseUrl.disabled = item.id !== 'custom';
    customModel.value = '';
    populateModels(item.models);
    connectedProvider = null;
    try { sessionStorage.removeItem('kae-ai-provider-config'); } catch (_) {}
    providerLight('', 'Not connected · enter key and test');
  }
  providerCatalog.forEach(item => providerSelect.append(el('option', { value: item.id }, item.label)));
  providerSelect.addEventListener('change', resetProviderForSelection);
  refreshModels.addEventListener('click', async () => {
    const profile = providerProfile();
    if (!profile.api_key) { providerLight('bad', 'API key required to load provider models'); apiKey.focus(); return; }
    refreshModels.disabled = true;
    providerLight('checking', 'Fetching model list from ' + providerSelect.options[providerSelect.selectedIndex].text + '…');
    try {
      const result = await request('POST', '/api/ai/providers/models', { provider_config: profile });
      populateModels(result.models || [], profile.model);
      providerLight('', 'Models loaded · ' + (result.models || []).length + ' available');
    } catch (error) {
      const item = providerCatalog.find(provider => provider.id === profile.provider);
      populateModels(item?.models || [], profile.model);
      providerLight('bad', 'Could not fetch live models: ' + error.message + ' · showing fallback list');
    } finally { refreshModels.disabled = false; }
  });
  testProvider.addEventListener('click', async () => {
    const profile = providerProfile();
    if (!profile.api_key) { providerLight('bad', 'API key required'); apiKey.focus(); return; }
    if (!profile.model) { providerLight('bad', 'Choose a model first'); modelSelect.focus(); return; }
    testProvider.disabled = true;
    refreshModels.disabled = true;
    providerLight('checking', 'Testing API key and waiting for a real model response…');
    try {
      const result = await request('POST', '/api/ai/providers/test', { provider_config: profile });
      sessionStorage.setItem('kae-ai-provider-config', JSON.stringify(profile));
      connectedProvider = profile;
      providerLight('good', 'CONNECTED · ' + result.provider + ' / ' + result.model + ' responded');
      status.textContent = 'AI connected · ' + result.provider + ' · ' + result.model;
      addMessage('assistant', 'Provider connection verified. ' + result.provider + ' responded using ' + result.model + '. KAE AI chat and supported planning/analysis actions will use this connection.');
    } catch (error) {
      connectedProvider = null;
      try { sessionStorage.removeItem('kae-ai-provider-config'); } catch (_) {}
      providerLight('bad', 'CONNECTION FAILED · ' + error.message);
      status.textContent = 'AI provider connection failed: ' + error.message;
    } finally { testProvider.disabled = false; refreshModels.disabled = false; }
  });
  try {
    const saved = JSON.parse(sessionStorage.getItem('kae-ai-provider-config') || 'null');
    if (saved) {
      providerSelect.value = saved.provider || 'xkiro';
      const selected = providerCatalog.find(item => item.id === providerSelect.value);
      baseUrl.value = saved.base_url || selected?.base_url || '';
      baseUrl.disabled = providerSelect.value !== 'custom';
      apiKey.value = saved.api_key || '';
      populateModels(selected?.models || [], saved.model);
      customModel.value = (selected?.models || []).includes(saved.model) ? '' : (saved.model || '');
      connectedProvider = saved;
      providerLight('good', 'SESSION CONFIGURED · ' + (selected?.label || saved.provider) + ' · run Test & connect to verify');
    } else resetProviderForSelection();
  } catch (_) { resetProviderForSelection(); }

  function setBusy(value) {
    send.disabled = value;
    generate.disabled = value;
    analyze.disabled = value || !videoInput.files?.[0];
    buildPlan.disabled = value || !latestVideoAnalysis || !currentProject?.id;
    applyPlan.disabled = value || !currentPlan?.ops?.length;
    reconstruct.disabled = value || !currentProject?.id || !videoInput.files?.[0];
    applyReconstruction.disabled = value || !currentVectorPlan?.frames?.length;
  }

  async function ask() {
    const message = input.value.trim();
    if (!message) return;
    input.value = '';
    addMessage('user', message);
    const previousHistory = history.slice(-12);
    history.push({ role: 'user', content: message });
    if (latestVideoAnalysis) latestCreativeDirection = message;
    setBusy(true);
    status.textContent = 'Consulting KAE engine context and capabilities…';
    try {
      const result = await request('POST', '/api/ai/chat', {
        message, history: previousHistory, project: projectSummary(),
      });
      addMessage('assistant', result.reply);
      history.push({ role: 'assistant', content: result.reply });
      status.textContent = 'KAE AI ready · ' + (result.model || 'provider model');
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

  videoInput.addEventListener('change', () => {
    const file = videoInput.files?.[0];
    latestSampledFrames = null;
    latestVideoAnalysis = '';
    latestCreativeDirection = '';
    currentVectorPlan = null;
    currentPlan = null;
    vectorPreview.replaceChildren();
    vectorPreview.hidden = true;
    vectorSummary.hidden = true;
    planSummary.hidden = true;
    applyReconstruction.disabled = true;
    applyPlan.disabled = true;
    if (videoUrl) URL.revokeObjectURL(videoUrl);
    videoUrl = null;
    analyze.disabled = true;
    if (!file) {
      video.hidden = true;
      video.removeAttribute('src');
      videoMeta.textContent = 'Choose a short reference clip.';
      return;
    }
    if (!file.type.startsWith('video/')) {
      videoMeta.textContent = 'Choose a valid video file.';
      videoInput.value = '';
      return;
    }
    if (file.size > 250 * 1024 * 1024) {
      videoMeta.textContent = 'This video is over 250 MB. Choose a shorter or compressed reference clip.';
      videoInput.value = '';
      return;
    }
    videoUrl = URL.createObjectURL(file);
    video.src = videoUrl;
    video.hidden = false;
    videoMeta.textContent = file.name + ' · ' + (file.size / (1024 * 1024)).toFixed(1) + ' MB · original stays in your browser';
    video.onloadedmetadata = () => {
      if (!Number.isFinite(video.duration) || video.duration <= 0) {
        videoMeta.textContent = 'Could not read video duration. Try MP4 or WebM.';
        analyze.disabled = true;
        return;
      }
      analyze.disabled = false;
      videoMeta.textContent = file.name + ' · ' + video.duration.toFixed(2) + ' seconds · up to 6 frames will be sampled';
    };
    video.onerror = () => {
      videoMeta.textContent = 'This browser could not decode the video. Try MP4 (H.264) or WebM.';
      analyze.disabled = true;
    };
  });

  function seekTo(seconds) {
    return new Promise((resolve, reject) => {
      if (Math.abs(video.currentTime - seconds) < 0.025 && video.readyState >= 2) return resolve();
      const timer = setTimeout(() => cleanup(new Error('Video frame seek timed out.')), 8000);
      const done = () => cleanup();
      const failed = () => cleanup(new Error('Could not decode a video frame.'));
      function cleanup(error) {
        clearTimeout(timer);
        video.removeEventListener('seeked', done);
        video.removeEventListener('error', failed);
        error ? reject(error) : resolve();
      }
      video.addEventListener('seeked', done, { once: true });
      video.addEventListener('error', failed, { once: true });
      video.currentTime = Math.min(Math.max(0, seconds), Math.max(0, video.duration - 0.04));
    });
  }

  async function sampleVideoFrames() {
    if (!video.duration || !Number.isFinite(video.duration)) throw new Error('Video duration is not available.');
    const count = Math.min(6, Math.max(2, Math.ceil(video.duration / 2)));
    const originalTime = video.currentTime;
    const width = Math.min(768, video.videoWidth || 768);
    const height = Math.max(1, Math.round(width * (video.videoHeight || 432) / Math.max(1, video.videoWidth || 768)));
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = Math.min(768, height);
    const ctx = canvas.getContext('2d', { alpha: false });
    if (!ctx) throw new Error('Browser canvas is unavailable.');
    const frames = [];
    for (let i = 0; i < count; i++) {
      const timestamp = count === 1 ? 0 : (video.duration * i / count);
      await seekTo(timestamp);
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      frames.push({ timestamp_seconds: Number(timestamp.toFixed(3)), data_url: canvas.toDataURL('image/jpeg', 0.62) });
    }
    await seekTo(originalTime).catch(() => {});
    return frames;
  }

  analyze.addEventListener('click', async () => {
    if (!videoInput.files?.[0]) return;
    setBusy(true);
    status.textContent = 'Sampling reference frames locally…';
    addMessage('user', 'Analyze reference video: ' + videoInput.files[0].name);
    try {
      const frames = await sampleVideoFrames();
      latestSampledFrames = frames;
      status.textContent = 'Sending ' + frames.length + ' sampled frames for motion analysis…';
      const result = await request('POST', '/api/ai/video/analyze', { frames, project: projectSummary() });
      const analysis = result.analysis || 'The model returned no analysis.';
      addMessage('assistant', 'REFERENCE ANALYSIS (' + result.frames_analyzed + ' frames)\n\n' + analysis);
      latestVideoAnalysis = analysis;
      latestCreativeDirection = '';
      currentPlan = null;
      currentVectorPlan = null;
      vectorSummary.hidden = true;
      applyReconstruction.disabled = true;
      planSummary.hidden = true;
      applyPlan.disabled = true;
      buildPlan.disabled = !currentProject?.id;
      history.push({ role: 'user', content: 'Reference video analysis follows. Use it as the source of truth for later reconstruction requests:\n' + analysis });
      history.push({ role: 'assistant', content: analysis });
      status.textContent = 'Analysis complete. Tell KAE what you want changed, then discuss the reconstruction plan.';
      addMessage('assistant', 'What creative changes would you like before I build a keyframe plan for the existing KAE layers?');
      input.value = '';
      input.placeholder = 'Tell KAE what to change in the motion before building the plan…';
      input.focus();
    } catch (error) {
      status.textContent = 'Video analysis failed: ' + error.message;
      addMessage('assistant', 'Video analysis failed: ' + error.message);
    } finally {
      setBusy(false);
    }
  });


  function renderVectorPreview(plan) {
    vectorPreview.replaceChildren();
    const ns = 'http://www.w3.org/2000/svg';
    for (const [index, frame] of plan.frames.entries()) {
      const card = el('div', { class: 'ai-vector-card' });
      card.append(el('div', { class: 'ai-vector-label' }, 'CEL ' + (index + 1) + ' · ' + frame.strokes.length + ' strokes'));
      const svg = document.createElementNS(ns, 'svg');
      svg.setAttribute('viewBox', '0 0 ' + plan.canvas.width + ' ' + plan.canvas.height);
      svg.setAttribute('role', 'img');
      svg.setAttribute('aria-label', 'Editable vector cel preview ' + (index + 1));
      for (const stroke of frame.strokes) {
        const path = document.createElementNS(ns, 'path');
        path.setAttribute('d', stroke.commands.map(command => command.join(' ')).join(' '));
        path.setAttribute('fill', stroke.fill || 'none');
        path.setAttribute('stroke', stroke.color || '#222222');
        path.setAttribute('stroke-width', String(stroke.width || 2));
        path.setAttribute('stroke-linecap', 'round');
        path.setAttribute('stroke-linejoin', 'round');
        path.setAttribute('vector-effect', 'non-scaling-stroke');
        svg.append(path);
      }
      card.append(svg);
      vectorPreview.append(card);
    }
    vectorPreview.hidden = false;
  }

  reconstruct.addEventListener('click', async () => {
    if (!currentProject?.id) {
      status.textContent = 'Open a saved KAE project before reconstructing vector cels.';
      return;
    }
    const selectedScene = sceneSelect.value;
    if (!selectedScene) {
      status.textContent = 'Choose a target scene for the new reconstruction layer.';
      return;
    }
    const direction = input.value.trim() || latestCreativeDirection;
    if (!direction) {
      status.textContent = 'Tell KAE what to preserve or change in the reference before reconstructing.';
      input.focus();
      return;
    }
    setBusy(true);
    status.textContent = 'Sampling the reference locally and asking the vision model for editable vector contours…';
    try {
      if (!latestSampledFrames) latestSampledFrames = await sampleVideoFrames();
      const result = await request('POST', '/api/ai/video/reconstruction/plan', {
        frames: latestSampledFrames,
        project: projectSummary(),
        direction,
      });
      currentVectorPlan = result;
      const frameLines = result.frames.map((frame, index) =>
        'Cel ' + (index + 1) + ': ' + frame.strokes.length + ' editable strokes' +
        ' · source ' + Number(frame.timestamp_seconds || 0).toFixed(2) + 's'
      );
      vectorSummary.textContent = result.summary + '\nCanvas: ' + result.canvas.width + ' × ' + result.canvas.height +
        '\nEditable cels: ' + result.frames.length + '\n\n' + frameLines.join('\n') +
        '\n\nThis is a vector approximation. Review before adding it to your project.';
      vectorSummary.hidden = false;
      renderVectorPreview(result);
      applyReconstruction.disabled = !result.frames.length;
      addMessage('assistant', 'Vector reconstruction plan is ready: ' + result.frames.length +
        ' editable cels. Review the preview summary. Nothing has been added to the project yet.');
      status.textContent = 'Vector plan ready. Applying will add new drawings and a new layer, preserving existing art.';
    } catch (error) {
      currentVectorPlan = null;
      vectorSummary.textContent = 'Reconstruction failed: ' + error.message;
      vectorSummary.hidden = false;
      vectorPreview.replaceChildren();
      vectorPreview.hidden = true;
      applyReconstruction.disabled = true;
      status.textContent = 'Could not reconstruct vector cels: ' + error.message;
    } finally {
      setBusy(false);
    }
  });

  applyReconstruction.addEventListener('click', async () => {
    if (!currentVectorPlan?.frames?.length || !currentProject?.id || !sceneSelect.value) return;
    if (!confirm('Add ' + currentVectorPlan.frames.length + ' editable vector cels to a NEW layer in the selected scene? Existing drawings and layers will be preserved.')) return;
    setBusy(true);
    status.textContent = 'Validating and adding native vector drawings to the saved KAE project…';
    try {
      const result = await request('POST', '/api/ai/video/reconstruction/apply', {
        project_id: currentProject.id,
        scene_id: sceneSelect.value,
        plan: currentVectorPlan,
      });
      currentProject = await request('GET', '/api/projects/' + encodeURIComponent(currentProject.id));
      currentVectorPlan = null;
      applyReconstruction.disabled = true;
      addMessage('assistant', 'Added ' + result.frames + ' editable vector cels to a new layer (' + result.layer_id +
        '). Existing art was preserved. Reload the editor to refresh the scene and timeline.');
      status.textContent = 'Reconstruction added to a new layer. Reload the editor to see the vector cels.';
    } catch (error) {
      status.textContent = 'Could not apply reconstruction: ' + error.message;
      addMessage('assistant', 'Apply failed: ' + error.message);
    } finally {
      setBusy(false);
    }
  });

  buildPlan.addEventListener('click', async () => {
    const direction = input.value.trim() || latestCreativeDirection;
    if (!currentProject?.id) {
      status.textContent = 'Open a saved KAE project before creating a keyframe plan.';
      return;
    }
    if (!latestVideoAnalysis) {
      status.textContent = 'Analyze a reference video first.';
      return;
    }
    if (!direction) {
      status.textContent = 'Tell KAE what changes you want in the instruction box, then build the plan.';
      input.focus();
      return;
    }
    setBusy(true);
    status.textContent = 'Building and validating a keyframe plan against your real scenes, layers, FPS and duration…';
    try {
      const result = await request('POST', '/api/ai/animation/plan', {
        project_id: currentProject.id,
        analysis: latestVideoAnalysis,
        direction,
      });
      currentPlan = result;
      planSummary.textContent = result.summary + '\n\nValidated keyframes: ' + result.ops.length +
        '\nProject duration: ' + result.frame_limit + ' frames' +
        '\n\n' + result.ops.slice(0, 80).map((op, index) =>
          (index + 1) + '. ' + op.scene_id + ' / ' + op.layer_id + ' · ' + op.channel +
          ' = ' + op.value + ' at frame ' + op.time + ' (' + op.ease + ')'
        ).join('\n') + (result.ops.length > 80 ? '\n…more operations omitted from preview' : '');
      planSummary.hidden = false;
      applyPlan.disabled = !result.ops.length;
      addMessage('assistant', 'KEYFRAME PLAN READY — ' + result.summary + '\n' +
        result.ops.length + ' validated keyframes. Review the plan in the reference panel. Nothing has been changed yet.');
      status.textContent = result.ops.length
        ? 'Plan validated. Review it, then explicitly apply it to the current project.'
        : 'No keyframes were proposed. The request may require artwork generation or unsupported operations.';
    } catch (error) {
      currentPlan = null;
      planSummary.textContent = error.message;
      planSummary.hidden = false;
      applyPlan.disabled = true;
      status.textContent = 'Could not build a valid keyframe plan: ' + error.message;
    } finally {
      setBusy(false);
    }
  });

  applyPlan.addEventListener('click', async () => {
    if (!currentPlan?.ops?.length || !currentProject?.id) return;
    const dirty = document.getElementById('dirty');
    if (dirty && !dirty.hidden) {
      status.textContent = 'Save your current editor changes first. Applying the plan to the saved project now could conflict with unsaved edits.';
      return;
    }
    if (!confirm('Apply ' + currentPlan.ops.length + ' keyframes to the saved KAE project? This changes the project on disk.')) return;
    setBusy(true);
    status.textContent = 'Applying validated keyframes to the saved project…';
    try {
      const result = await request('POST', '/api/projects/' + encodeURIComponent(currentProject.id) + '/timeline/script', {
        ops: currentPlan.ops,
      });
      currentProject = await request('GET', '/api/projects/' + encodeURIComponent(currentProject.id));
      addMessage('assistant', 'Applied ' + result.applied + ' keyframes to the saved project. Reload the editor to refresh the timeline and viewport.');
      status.textContent = 'Applied ' + result.applied + ' keyframes. Reload the editor to see the saved animation changes.';
      currentPlan = null;
      applyPlan.disabled = true;
      buildPlan.disabled = false;
    } catch (error) {
      status.textContent = 'Could not apply keyframes: ' + error.message;
      addMessage('assistant', 'Apply failed: ' + error.message);
    } finally {
      setBusy(false);
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
      if (result.status !== 'succeeded') throw new Error(Date.now() >= deadline ? 'Image generation timed out after 5 minutes.' : 'Image job did not return a completed image.');
      const data = result.image || {};
      imageUrl = data.url || (data.b64_json ? 'data:image/png;base64,' + data.b64_json : null);
      if (!imageUrl) throw new Error('Image provider returned no usable image.');
      image.src = imageUrl;
      image.hidden = false;
      showRef.disabled = false;
      download.href = imageUrl;
      download.hidden = false;
      status.textContent = 'Image ready. Save it or show it over the canvas as a temporary visual reference.';
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

  addMessage('assistant', 'I am connected to KAE’s capability inventory and native project schemas. Upload a reference video to analyze its sampled frames, then tell me your creative changes. I will distinguish supported operations from features that still need implementation.');
  loadCurrentProject().finally(() => {
    sceneSelect.replaceChildren();
    const scenes = Array.isArray(currentProject?.scenes) ? currentProject.scenes : [];
    for (const scene of scenes) {
      sceneSelect.append(el('option', { value: scene.id }, scene.name || scene.id));
    }
    sceneSelect.disabled = !scenes.length;
    if (!scenes.length) sceneSelect.append(el('option', { value: '' }, 'Open a project with a scene first'));
    setBusy(false);
    request('GET', '/api/ai/status').then(result => {
      status.textContent = result.configured
        ? 'KAE AI connected · chat ' + result.chat_model + ' · image model ' + result.image_model
        : 'xKiro not configured: set XKIRO_API_KEY on the server or use ignored xkiro.txt.';
    }).catch(() => { status.textContent = 'Could not check AI configuration.'; });
  });
}
