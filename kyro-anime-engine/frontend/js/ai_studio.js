import { request } from './api/client.js';

const history = [];
let reference = null, imageUrl = null, videoUrl = null, currentProject = null, latestVideoAnalysis = '', currentPlan = null;

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
  const thread = el('div', { class: 'ai-thread', 'aria-live': 'polite' });
  const compose = el('form', { class: 'ai-compose' });
  const input = el('textarea', { placeholder: 'Describe a character, animation, or change to the current project…', maxlength: '12000' });
  const actions = el('div', { class: 'ai-actions' });
  const send = el('button', { class: 'primary', type: 'submit' }, 'Ask KAE AI');
  const generate = el('button', { type: 'button' }, 'Generate image');
  actions.append(send, generate);
  compose.append(input, actions);
  side.append(head, thread, compose);

  const preview = el('div', { class: 'ai-preview' });
  const previewHead = el('header', { class: 'ai-head' }, 'REFERENCE & OUTPUT');
  const body = el('div', { class: 'ai-preview-body' });
  const status = el('div', { class: 'ai-status' }, 'Loading KAE engine capabilities…');

  const videoPanel = el('section', { class: 'ai-video-panel' });
  videoPanel.append(el('div', { class: 'ai-section-title' }, 'VIDEO → MOTION ANALYSIS'));
  const videoInput = el('input', { type: 'file', accept: 'video/mp4,video/webm,video/quicktime,video/*', 'aria-label': 'Choose reference video' });
  const video = el('video', { class: 'ai-reference-video', controls: '', playsinline: '', preload: 'metadata', hidden: '' });
  const videoMeta = el('div', { class: 'ai-note' }, 'Choose a short reference clip. KAE samples up to 6 frames in your browser; the original video file is not sent to xKiro.');
  const analyze = el('button', { type: 'button', class: 'primary', disabled: '' }, 'Analyze reference video');
  const buildPlan = el('button', { type: 'button', disabled: '' }, 'Build keyframe plan from my instructions');
  const applyPlan = el('button', { type: 'button', class: 'primary', disabled: '' }, 'Apply keyframes to current project');
  const planSummary = el('pre', { class: 'ai-plan-summary', hidden: '' });
  videoPanel.append(videoInput, video, videoMeta, analyze, buildPlan, planSummary, applyPlan);

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
  function setBusy(value) {
    send.disabled = value;
    generate.disabled = value;
    analyze.disabled = value || !videoInput.files?.[0];
    buildPlan.disabled = value || !latestVideoAnalysis || !currentProject?.id;
    applyPlan.disabled = value || !currentPlan?.ops?.length;
  }

  async function ask() {
    const message = input.value.trim();
    if (!message) return;
    input.value = '';
    addMessage('user', message);
    const previousHistory = history.slice(-12);
    history.push({ role: 'user', content: message });
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
    const count = Math.min(6, Math.max(1, Math.ceil(video.duration / 2)));
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
      status.textContent = 'Sending ' + frames.length + ' sampled frames for motion analysis…';
      const result = await request('POST', '/api/ai/video/analyze', { frames, project: projectSummary() });
      const analysis = result.analysis || 'The model returned no analysis.';
      addMessage('assistant', 'REFERENCE ANALYSIS (' + result.frames_analyzed + ' frames)\n\n' + analysis);
      latestVideoAnalysis = analysis;
      currentPlan = null;
      planSummary.hidden = true;
      applyPlan.disabled = true;
      buildPlan.disabled = !currentProject?.id;
      history.push({ role: 'user', content: 'Reference video analysis follows. Use it as the source of truth for later reconstruction requests:\n' + analysis });
      history.push({ role: 'assistant', content: analysis });
      status.textContent = 'Analysis complete. Tell KAE what you want changed, then discuss the reconstruction plan.';
      input.value = 'I have reviewed the analysis. Ask me what creative changes I want before planning the reconstruction.';
      input.focus();
    } catch (error) {
      status.textContent = 'Video analysis failed: ' + error.message;
      addMessage('assistant', 'Video analysis failed: ' + error.message);
    } finally {
      setBusy(false);
    }
  });


  buildPlan.addEventListener('click', async () => {
    const direction = input.value.trim();
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
    setBusy(false);
    request('GET', '/api/ai/status').then(result => {
      status.textContent = result.configured
        ? 'KAE AI connected · chat ' + result.chat_model + ' · image model ' + result.image_model
        : 'xKiro not configured: set XKIRO_API_KEY on the server or use ignored xkiro.txt.';
    }).catch(() => { status.textContent = 'Could not check AI configuration.'; });
  });
}
