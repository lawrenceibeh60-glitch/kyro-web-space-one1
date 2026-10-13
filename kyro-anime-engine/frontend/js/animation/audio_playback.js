import { bus } from '../core/event_bus.js';
import { state } from '../core/state_manager.js';
import { toast } from '../ui/notifications.js';

let players = [];
let playing = false;
let audioSnapshot = '';

function clearPlayers() {
  for (const player of players) {
    player.audio.pause();
    player.audio.removeAttribute('src');
    player.audio.load();
  }
  players = [];
}

function loadPlayers() {
  clearPlayers();
  audioSnapshot = JSON.stringify(state.project?.audio || []);
  const projectId = state.projectId;
  players = (state.project?.audio || []).map(clip => {
    const audio = new Audio(clip.url || `/api/projects/${encodeURIComponent(projectId)}/audio/${encodeURIComponent(clip.id)}`);
    audio.preload = 'auto';
    const player = { clip, audio, reported: false, requesting: false, pendingTime: null };
    audio.addEventListener('loadedmetadata', () => {
      if (player.pendingTime !== null) {
        audio.currentTime = player.pendingTime;
        player.pendingTime = null;
      }
    });
    audio.addEventListener('error', () => {
      if (!player.reported) {
        player.reported = true;
        toast(`Audio preview could not load: ${clip.name}`, 'err', 5000);
      }
    });
    return player;
  });
}

function seek(player, time) {
  const { audio } = player;
  if (audio.readyState < 1) {
    player.pendingTime = Math.max(0, time);
    return;
  }
  if (Math.abs(audio.currentTime - time) > 0.18) audio.currentTime = Math.max(0, time);
}

function syncPlayers() {
  if (!state.project) return;
  const fps = state.project.settings.fps;
  for (const player of players) {
    const { clip, audio } = player;
    const offsetFrames = state.frame - clip.start_frame;
    const target = clip.offset_seconds + offsetFrames / fps;
    const pastEnd = clip.duration_frames && offsetFrames >= clip.duration_frames;
    const active = offsetFrames >= 0 && !pastEnd;
    if (!active) {
      audio.pause();
      player.requesting = false;
      if (offsetFrames < 0) seek(player, clip.offset_seconds);
      continue;
    }
    if (Number.isFinite(audio.duration) && target >= audio.duration) {
      audio.pause();
      continue;
    }
    seek(player, target);
    audio.volume = Math.max(0, Math.min(1, clip.volume ?? 1));
    if (playing && audio.paused && !player.requesting) {
      player.requesting = true;
      audio.play().then(() => { player.requesting = false; }).catch(error => {
        player.requesting = false;
        if (!player.reported) {
          player.reported = true;
          toast(`Audio preview could not start: ${error.message}`, 'err', 5000);
        }
      });
    } else if (!playing) {
      audio.pause();
    }
  }
}

export function initAudioPlayback() {
  bus.on('state', patch => {
    if ('project' in patch || 'projectId' in patch) loadPlayers();
    if ('frame' in patch || 'project' in patch || 'sceneId' in patch) syncPlayers();
  });
  bus.on('playback', event => {
    playing = event.playing;
    syncPlayers();
  });
  bus.on('project:changed', () => {
    const current = JSON.stringify(state.project?.audio || []);
    if (current !== audioSnapshot) {
      audioSnapshot = current;
      loadPlayers();
    }
    syncPlayers();
  });
}
