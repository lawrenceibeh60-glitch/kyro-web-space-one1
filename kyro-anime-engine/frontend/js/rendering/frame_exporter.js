// frontend/js/rendering/frame_exporter.js - renders project frames to PNG blobs with the SAME renderer as the editor.
import { renderFrame } from './renderer.js';

export function makeFrameRenderer(project, sceneId, scale = 1, transparent = false) {
  const { width, height } = project.settings;
  const w = Math.max(1, Math.round(width * scale)), h = Math.max(1, Math.round(height * scale));
  const canvas = document.createElement('canvas');
  canvas.width = w; canvas.height = h;
  const ctx = canvas.getContext('2d');
  const render = frame => new Promise((resolve, reject) => {
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, w, h);
    ctx.scale(w / width, h / height);
    renderFrame(ctx, project, sceneId, frame, null, { transparent });
    canvas.toBlob(b => (b ? resolve(b) : reject(new Error('PNG encoding failed (image too large?)'))), 'image/png');
  });
  render.width = w; render.height = h;
  return render;
}

export async function recordVideo(project, sceneId, scale, fps, startFrame, frameCount, onProgress, audioClips = []) {
  if (!window.MediaRecorder || !HTMLCanvasElement.prototype.captureStream) {
    throw new Error('WebM recording is not supported by this browser');
  }
  const mimeTypes = audioClips.length
    ? ['video/webm;codecs=vp9,opus', 'video/webm;codecs=vp8,opus', 'video/webm;codecs=vp9', 'video/webm;codecs=vp8', 'video/webm']
    : ['video/webm;codecs=vp9', 'video/webm;codecs=vp8', 'video/webm'];
  const mimeType = mimeTypes
    .find(type => MediaRecorder.isTypeSupported(type));
  if (!mimeType) throw new Error('This browser does not have a supported WebM video encoder');

  const { width, height } = project.settings;
  const canvas = document.createElement('canvas');
  canvas.width = Math.max(1, Math.round(width * scale));
  canvas.height = Math.max(1, Math.round(height * scale));
  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('Could not create the video rendering canvas');
  ctx.scale(canvas.width / width, canvas.height / height);

  let audioContext = null;
  const audioSources = [];
  let audioDestination = null;
  if (audioClips.length) {
    const AudioContextType = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextType) throw new Error('This browser cannot mix audio into WebM exports');
    audioContext = new AudioContextType();
    audioDestination = audioContext.createMediaStreamDestination();
    try {
      for (const clip of audioClips) {
        if (clip.start_frame >= startFrame + frameCount) continue;
        const audioUrl = clip.url
          || `/api/projects/${encodeURIComponent(project.id)}/audio/${encodeURIComponent(clip.id)}`;
        const response = await fetch(audioUrl);
        if (!response.ok) throw new Error(`Could not load audio "${clip.name}": ${response.statusText}`);
        const buffer = await audioContext.decodeAudioData(await response.arrayBuffer());
        const elapsedBeforeExport = Math.max(0, startFrame - clip.start_frame) / fps;
        const offset = (clip.offset_seconds || 0) + elapsedBeforeExport;
        const exportDelay = Math.max(0, clip.start_frame - startFrame) / fps;
        const clipLimit = clip.duration_frames
          ? clip.duration_frames / fps - elapsedBeforeExport
          : Number.POSITIVE_INFINITY;
        const exportLimit = frameCount / fps - exportDelay;
        const duration = Math.min(buffer.duration - offset, clipLimit, exportLimit);
        if (duration <= 0) continue;
        const source = audioContext.createBufferSource();
        const gain = audioContext.createGain();
        source.buffer = buffer;
        gain.gain.value = Math.max(0, Math.min(1, clip.volume ?? 1));
        source.connect(gain);
        gain.connect(audioDestination);
        audioSources.push({ source, delay: exportDelay, offset, duration });
      }
    } catch (error) {
      await audioContext.close();
      throw error;
    }
    try {
      await audioContext.resume();
    } catch (error) {
      await audioContext.close();
      throw new Error(`Could not start audio mixing: ${error.message}`);
    }
  }

  let stream = canvas.captureStream(0);
  let track = stream.getVideoTracks()[0];
  if (typeof track.requestFrame !== 'function') {
    stream.getTracks().forEach(item => item.stop());
    stream = canvas.captureStream(fps);
    track = stream.getVideoTracks()[0];
  }
  if (audioDestination) {
    for (const audioTrack of audioDestination.stream.getAudioTracks()) stream.addTrack(audioTrack);
  }
  let recorder;
  try {
    recorder = new MediaRecorder(stream, { mimeType });
  } catch (error) {
    stream.getTracks().forEach(item => item.stop());
    if (audioContext) await audioContext.close();
    throw new Error(`Could not start WebM recording: ${error.message}`);
  }
  const chunks = [];
  recorder.addEventListener('dataavailable', event => {
    if (event.data.size) chunks.push(event.data);
  });
  const stopped = new Promise((resolve, reject) => {
    recorder.addEventListener('stop', resolve, { once: true });
    recorder.addEventListener('error', event => reject(event.error || new Error('WebM recording failed')), { once: true });
  });
  try {
    recorder.start(1000);
    if (audioContext) {
      const origin = audioContext.currentTime;
      for (const clip of audioSources) {
        clip.source.start(origin + clip.delay, clip.offset, clip.duration);
      }
    }
  } catch (error) {
    stream.getTracks().forEach(item => item.stop());
    if (audioContext) await audioContext.close();
    throw new Error(`Could not start WebM recording: ${error.message}`);
  }

  let renderError;
  try {
    for (let index = 0; index < frameCount; index++) {
      ctx.setTransform(canvas.width / width, 0, 0, canvas.height / height, 0, 0);
      ctx.clearRect(0, 0, width, height);
      renderFrame(ctx, project, sceneId, startFrame + index, null, { transparent: false });
      track.requestFrame?.();
      onProgress?.(index + 1, frameCount);
      await new Promise(resolve => setTimeout(resolve, 1000 / fps));
    }
  } catch (error) {
    renderError = error;
  }
  if (recorder.state !== 'inactive') recorder.stop();
  try {
    await stopped;
  } finally {
    stream.getTracks().forEach(item => item.stop());
    if (audioContext) await audioContext.close();
  }
  if (renderError) throw renderError;
  return new Blob(chunks, { type: recorder.mimeType || mimeType });
}
