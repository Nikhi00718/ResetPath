import assert from "node:assert/strict";
import { test } from "node:test";

import { PRESETS, SOUNDS, renderSound } from "../web/js/noise.js";

const RATE = 8000; // Low rate keeps the test fast; the generators are rate-agnostic.

for (const { id } of SOUNDS.filter((sound) => sound.id !== "wind")) {
  test(`${id} renders a finite, bounded, seamless loop`, () => {
    const channels = renderSound(id, RATE, 4);
    assert.ok(channels.length >= 1);
    for (const data of channels) {
      assert.equal(data.length, 4 * RATE);
      let peak = 0;
      let energy = 0;
      for (const value of data) {
        assert.ok(Number.isFinite(value));
        peak = Math.max(peak, Math.abs(value));
        energy += value * value;
      }
      assert.ok(peak < 1.6, `${id} peak ${peak}`);
      assert.ok(energy / data.length > 1e-5, `${id} is silent`);
      // The jump across the loop point should look like any other step.
      const seam = Math.abs(data[0] - data[data.length - 1]);
      assert.ok(seam < Math.max(0.5, peak), `${id} seam ${seam}`);
    }
  });
}

test("presets only reference known sounds", () => {
  const ids = new Set(SOUNDS.map((sound) => sound.id));
  for (const preset of PRESETS) {
    for (const id of Object.keys(preset.mix)) assert.ok(ids.has(id), `${preset.id} uses ${id}`);
  }
});
