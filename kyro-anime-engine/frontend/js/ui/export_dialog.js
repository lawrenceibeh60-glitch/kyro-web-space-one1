// frontend/js/ui/export_dialog.js - Export dialog: PNG sequence / GIF / sprite sheet.
import { Exports } from '../api/exports.js';
import { state } from '../core/state_manager.js';
import { stop as stopPlay } from '../animation/playback.js';
import { makeFrameRenderer, recordVideo } from '../rendering/frame_exporter.js';
import { toast } from './notifications.js';

const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const nextTick = () => new Promise(r => setTimeout(r, 0));

export function initExportDialog() {
  const $ = id => document.getElementById(id);
  let fmt = 'png', busy = false, caps = null;

  function range() {
    const total = state.project.settings.duration_frames;
    const a = clamp((parseInt($('exStart').value, 10) || 1) - 1, 0, total - 1);
    const b = clamp((parseInt($('exEnd').value, 10) || total) - 1, a, total - 1);
    return { a, b, n: b - a + 1 };
  }

  function sync() {
    const { width, height } = state.project.settings, scale = +$('exScale').value / 100, { n } = range();
    $('exScaleV').textContent = $('exScale').value + '%';
    document.querySelectorAll('#exFormat button').forEach(b => {
      const needsPil = ['gif', 'sprite'].includes(b.dataset.f);
      const needsRecorder = b.dataset.f === 'webm';
      const recorderAvailable = window.MediaRecorder
        && HTMLCanvasElement.prototype.captureStream
        && ['video/webm;codecs=vp9', 'video/webm;codecs=vp8', 'video/webm']
          .some(type => MediaRecorder.isTypeSupported(type));
      b.disabled = (needsPil && caps && !caps.pillow) || (needsRecorder && !recorderAvailable);
      b.title = needsPil && b.disabled ? 'Install Pillow: pip install pillow'
        : needsRecorder && b.disabled ? 'WebM recording is not supported by this browser' : '';
      b.classList.toggle('on', b.dataset.f === fmt);
    });
    document.querySelectorAll('#exportDlg [data-fmt]').forEach(el => { el.hidden = !el.dataset.fmt.split(' ').includes(fmt); });
    $('exInfo').textContent = `${Math.round(width * scale)}\u00D7${Math.round(height * scale)} px \u00B7 ${n} frame${n > 1 ? 's' : ''} \u00B7 ${state.project.settings.fps} fps`;
  }

  function message(text, isErr = false) { $('exMsg').textContent = text; $('exMsg').classList.toggle('err', isErr); }
  function progress(p) { $('exBar').style.width = Math.round(p * 100) + '%'; }
  function lock(on) { busy = on; $('exGo').disabled = on; $('exClose').disabled = on; }

  async function open() {
    if (!state.project) return;
    stopPlay();
    const total = state.project.settings.duration_frames;
    $('exStart').value = 1; $('exEnd').value = total; $('exStart').max = $('exEnd').max = total;
    $('exportDlg').hidden = false;
    message(''); progress(0);
    if (!caps) { try { caps = await Exports.capabilities(); } catch (_) { caps = { pillow: false }; } }
    if (fmt !== 'png' && !caps.pillow) fmt = 'png';
    sync();
  }

  function close() { if (!busy) $('exportDlg').hidden = true; }

  function download(url, filename) {
    const a = document.createElement('a');
    a.href = url; a.download = filename;
    document.body.append(a); a.click(); a.remove();
  }

  async function run() {
    if (busy) return;
    const p = JSON.parse(JSON.stringify(state.project)), sceneId = state.sceneId;
    const { a, n } = range(), scale = +$('exScale').value / 100, transparent = $('exTransp').checked;
    lock(true); progress(0); message('Starting\u2026');
    try {
      if (fmt === 'webm') {
        message('Recording WebM\u2026');
        const blob = await recordVideo(
          p, sceneId, scale, p.settings.fps, a, n,
          (done, total) => {
            progress(done / total);
            message(`Recording frame ${done} / ${total}`);
          },
          p.audio || [],
        );
        const filename = `${p.name || 'animation'}.webm`;
        const url = URL.createObjectURL(blob);
        download(url, filename);
        setTimeout(() => URL.revokeObjectURL(url), 60_000);
        progress(1);
        message(`Done: ${filename} (${Math.max(1, Math.round(blob.size / 1024))} KB)`);
        toast('Video export ready', 'ok');
        return;
      }
      const job = await Exports.create({
        project_id: state.projectId, name: p.name, format: fmt, frames: n, fps: p.settings.fps, transparent,
        loop: $('exLoop').checked, columns: Math.max(0, parseInt($('exCols').value, 10) || 0),
        padding: Math.max(0, parseInt($('exPad').value, 10) || 0),
      });
      const render = makeFrameRenderer(p, sceneId, scale, transparent);
      for (let i = 0; i < n; i++) {
        message(`Rendering frame ${i + 1} / ${n}`);
        await Exports.putFrame(job.job_id, i, await render(a + i));
        progress(((i + 1) / n) * 0.9);
        await nextTick();
      }
      message('Building file\u2026');
      const res = await Exports.finish(job.job_id);
      progress(1);
      message(`Done: ${res.filename} (${Math.max(1, Math.round(res.size / 1024))} KB)`);
      download(res.url, res.filename);
      toast('Export ready', 'ok');
    } catch (e) {
      message(e.message + (e.details?.length ? ': ' + e.details.join(', ') : ''), true);
    } finally {
      lock(false);
    }
  }

  document.querySelectorAll('#exFormat button').forEach(b => { b.onclick = () => { fmt = b.dataset.f; sync(); }; });
  ['exScale', 'exStart', 'exEnd'].forEach(id => { $(id).oninput = sync; });
  $('exClose').onclick = close;
  $('exGo').onclick = run;
  $('exportDlg').addEventListener('pointerdown', e => { if (e.target === $('exportDlg')) close(); });
  return { open, close };
}
