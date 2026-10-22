# KAE rigged test animation

This regression fixture exercises the native rig schema and keyframe interpolation with a three-bone test arm (`torso → upper_arm → forearm`). The arm moves between two poses over a 24-frame loop at the default 24 FPS.

## What it verifies

- Rotation keyframes use the existing `animation.schema.json` shape and `evaluateTrack` interpolation.
- Child pivots follow the evaluated rotation of their parent.
- Looping, animation start offsets, and non-looping playback resolve frames deterministically.
- Missing parents, duplicate IDs, invalid keyframes, and parent cycles fail fast instead of breaking playback.

## Run the regression test

From `kyro-anime-engine`, run:

```bash
node --test frontend/tests/bone_evaluator.test.js
```

This validates the rig-evaluation core in isolation. It does **not** claim that the current editor viewport already draws skinned character artwork from this evaluator; viewport integration and a full `.kae` round-trip are separate acceptance checks before calling the animation workflow complete.
