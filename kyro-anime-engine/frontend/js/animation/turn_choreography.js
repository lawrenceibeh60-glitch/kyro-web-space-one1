// Reusable 2.5D front-to-profile choreography for characters with alternate pose layers.
const poseKind = layer => {
  const label = `${layer?.name || ''} ${layer?.id || ''}`.toLowerCase();
  if (/\bfront\b/.test(label)) return 'front';
  if (/\bprofile\b/.test(label)) return 'profile';
  return null;
};

const poseKey = layer => layer.character_part_id
  || String(layer.id || '').replace(/front|profile/ig, '').replace(/[_-]+$/, '');

export function countTurnPairs(layers, characterId) {
  const pairs = new Map();
  for (const layer of layers || []) {
    if (layer.character_id !== characterId) continue;
    const kind = poseKind(layer);
    if (!kind) continue;
    const key = poseKey(layer);
    if (!pairs.has(key)) pairs.set(key, new Set());
    pairs.get(key).add(kind);
  }
  return [...pairs.values()].filter(kinds => kinds.has('front') && kinds.has('profile')).length;
}

function mergeInterval(track, start, end, replacement) {
  const outside = (Array.isArray(track) ? track : []).filter(key => key.t < start || key.t > end);
  return [...outside, ...replacement].sort((a, b) => a.t - b.t);
}

export function buildTurnChoreography(layers, characterId, startFrame, durationFrames, maxFrame = Infinity) {
  const start = Math.max(0, Math.floor(Number(startFrame) || 0));
  const maxDuration = Number.isFinite(maxFrame) ? Math.max(0, Math.floor(maxFrame) - start) : Infinity;
  const duration = Math.max(4, Math.min(Math.floor(Number(durationFrames) || 12), maxDuration));
  if (!Number.isFinite(duration) || duration < 4) {
    throw new RangeError('The selected timeline does not have at least four frames for a turn.');
  }
  const middle = start + Math.round(duration / 2);
  const end = start + duration;
  const pairCount = countTurnPairs(layers, characterId);
  if (!pairCount) throw new Error('This character needs matching front and profile layers for a turn.');

  const nextLayers = (layers || []).map(layer => {
    if (layer.character_id !== characterId) return layer;
    const kind = poseKind(layer);
    if (!kind) return layer;
    const key = poseKey(layer);
    const hasPair = (layers || []).some(candidate =>
      candidate.character_id === characterId && poseKey(candidate) === key && poseKind(candidate) !== kind);
    if (!hasPair) return layer;
    const tracks = { ...(layer.tracks || {}) };
    if (kind === 'front') {
      tracks.rotation_y = mergeInterval(tracks.rotation_y, start, end, [
        { t: start, v: 0, ease: 'ease_in_out' },
        { t: middle, v: 45, ease: 'ease_in_out' },
        { t: end, v: 90, ease: 'ease_in_out' },
      ]);
      tracks.opacity = mergeInterval(tracks.opacity, start, end, [
        { t: start, v: 1, ease: 'ease_in_out' },
        { t: middle, v: 0.5, ease: 'ease_in_out' },
        { t: end, v: 0, ease: 'ease_in_out' },
      ]);
    } else {
      tracks.rotation_y = mergeInterval(tracks.rotation_y, start, end, [
        { t: start, v: 0, ease: 'ease_in_out' },
        { t: end, v: 0, ease: 'ease_in_out' },
      ]);
      tracks.opacity = mergeInterval(tracks.opacity, start, end, [
        { t: start, v: 0, ease: 'ease_in_out' },
        { t: middle, v: 0.5, ease: 'ease_in_out' },
        { t: end, v: 1, ease: 'ease_in_out' },
      ]);
    }
    return { ...layer, tracks };
  });
  return { layers: nextLayers, pairCount, startFrame: start, middleFrame: middle, endFrame: end };
}
