# KAE rigged arm idle — engine smoke test

Open `examples/rigged-arm-idle.kae` in the KAE editor. It is a native KAE project: three drawing layers, a three-bone hierarchy, and keyed upper-arm/forearm rotations. The timeline is 24 FPS × 24 frames (one second). Scrub frames 0 → 6 → 12 → 23; the arm should swing out and return to its starting pose.

## Automated verification

From `kyro-anime-engine`, run:

```bash
node --test frontend/tests/rigged_arm_idle.test.js
```

The smoke test runs the fixture through KAE's actual `renderFrame` renderer, checks that keyframes produce different poses, confirms the final keyed pose returns to the start pose, and checks a JSON save/reopen round-trip. It uses a canvas-context stub, so this is a renderer regression test rather than a pixel-image comparison.
