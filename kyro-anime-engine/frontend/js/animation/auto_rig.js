// Deterministic first-pass rig generation for arbitrary vector character parts.
const labelOf = part => `${part?.id || ''} ${part?.name || ''}`.toLowerCase().replace(/[_-]+/g, ' ');
const includesAny = (label, terms) => terms.some(term => label.includes(term));

function coordinatesOfPart(part) {
  const points = [];
  for (const stroke of part?.strokes || []) {
    for (const point of stroke.points || []) {
      if (Array.isArray(point) && Number.isFinite(point[0]) && Number.isFinite(point[1])) points.push(point);
    }
    for (const command of stroke.commands || []) {
      if (!Array.isArray(command) || command[0] === 'Z') continue;
      for (let i = 1; i + 1 < command.length; i += 2) {
        if (Number.isFinite(command[i]) && Number.isFinite(command[i + 1])) {
          points.push([command[i], command[i + 1]]);
        }
      }
    }
  }
  return points;
}

function pivotOf(part, canvas) {
  const points = coordinatesOfPart(part);
  if (!points.length) return { x: canvas.width / 2, y: canvas.height / 2 };
  const xs = points.map(point => point[0]), ys = points.map(point => point[1]);
  const minX = Math.min(...xs), maxX = Math.max(...xs);
  const minY = Math.min(...ys), maxY = Math.max(...ys);
  const label = labelOf(part);
  const centerX = (minX + maxX) / 2;
  const height = maxY - minY;
  let y = minY + height * 0.5;
  if (includesAny(label, ['head', 'hair', 'face', 'eye'])) y = maxY;
  else if (includesAny(label, ['arm', 'shoulder', 'thigh', 'leg', 'shin', 'calf'])) y = minY;
  else if (includesAny(label, ['torso', 'body', 'chest', 'coat', 'pelvis', 'hip'])) y = minY + height * 0.22;
  else if (includesAny(label, ['hand', 'foot', 'shoe'])) y = minY;
  return {
    x: Math.max(-8192, Math.min(8192, centerX)),
    y: Math.max(-8192, Math.min(8192, y)),
  };
}

function chooseParent(part, parts) {
  const label = labelOf(part);
  const find = terms => parts.find(candidate => candidate.id !== part.id && includesAny(labelOf(candidate), terms));
  const torso = find(['torso', 'body', 'chest', 'coat', 'pelvis', 'hip']);
  const head = find(['head', 'face']);
  const neck = find(['neck']);
  const sameSide = terms => {
    const side = /\bleft\b/.test(label) ? 'left' : /\bright\b/.test(label) ? 'right' : '';
    const matches = parts.filter(candidate => candidate.id !== part.id
      && includesAny(labelOf(candidate), terms)
      && (!side || new RegExp(`\\b${side}\\b`).test(labelOf(candidate))));
    return matches[0] || null;
  };
  if (includesAny(label, ['eye', 'hair', 'face', 'brow', 'nose', 'mouth'])) return head || neck || torso;
  if (includesAny(label, ['head'])) return neck || torso;
  if (includesAny(label, ['neck'])) return torso;
  if (includesAny(label, ['hand', 'wrist'])) {
    return sameSide(['forearm', 'lower arm']) || sameSide(['upper arm', 'arm', 'shoulder']) || torso;
  }
  if (includesAny(label, ['forearm', 'lower arm', 'elbow'])) {
    return sameSide(['upper arm', 'shoulder', 'arm']) || torso;
  }
  if (includesAny(label, ['upper arm', 'shoulder', 'arm'])) return torso;
  if (includesAny(label, ['foot', 'shoe', 'ankle'])) return sameSide(['shin', 'calf', 'lower leg']) || sameSide(['thigh', 'upper leg', 'leg']) || torso;
  if (includesAny(label, ['shin', 'calf', 'lower leg', 'knee'])) return sameSide(['thigh', 'upper leg', 'leg']) || torso;
  if (includesAny(label, ['thigh', 'upper leg', 'leg'])) return torso;
  if (includesAny(label, ['torso', 'body', 'chest', 'pelvis', 'hip'])) return null;
  return torso;
}

function safeBoneId(partId, used) {
  const base = `auto_${String(partId || 'part').replace(/[^A-Za-z0-9_-]/g, '_')}`.slice(0, 58);
  let id = base, suffix = 1;
  while (used.has(id)) {
    const tail = `_${suffix++}`;
    id = base.slice(0, 64 - tail.length) + tail;
  }
  used.add(id);
  return id;
}

export function buildAutoRig(character, existingRig = null, canvas = { width: 1280, height: 720 }) {
  const parts = Array.isArray(character?.parts) ? character.parts.filter(part => part && typeof part.id === 'string') : [];
  if (!parts.length) throw new Error('The character has no parts to rig.');
  const rig = existingRig
    ? structuredClone(existingRig)
    : { id: `rig_${String(character.id || 'character').slice(0, 55)}`, name: `${character.name || character.id || 'Character'} Rig`, character_id: character.id, bones: [] };
  rig.character_id = character.id;
  rig.bones = Array.isArray(rig.bones) ? rig.bones : [];
  const byPart = new Map();
  for (const bone of rig.bones) {
    if (bone.character_part_id && !byPart.has(bone.character_part_id)) byPart.set(bone.character_part_id, bone);
  }
  const used = new Set(rig.bones.map(bone => bone.id));
  const added = [];
  for (const part of parts) {
    if (byPart.has(part.id)) continue;
    const bone = {
      id: safeBoneId(part.id, used),
      name: part.name || part.id,
      character_part_id: part.id,
      pivot: pivotOf(part, canvas),
      rotation: 0,
    };
    byPart.set(part.id, bone);
    added.push({ part, bone });
  }
  for (const { part, bone } of added) {
    const parentPart = chooseParent(part, parts);
    const parentBone = parentPart && byPart.get(parentPart.id);
    if (parentBone && parentBone.id !== bone.id) bone.parent_id = parentBone.id;
  }
  rig.bones = [...rig.bones, ...added.map(item => item.bone)];
  return { rig, addedCount: added.length, totalCount: rig.bones.length };
}
