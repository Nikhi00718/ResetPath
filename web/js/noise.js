// Ambient sound engine. Every sound is synthesized on the device with the Web
// Audio API (no audio files), so the app stays small and works offline.

export const SOUNDS = [
  { id: "rain", name: "Rain", icon: "🌧️" },
  { id: "ocean", name: "Ocean", icon: "🌊" },
  { id: "stream", name: "Stream", icon: "💧" },
  { id: "wind", name: "Wind", icon: "🍃" },
  { id: "fire", name: "Fire", icon: "🔥" },
  { id: "night", name: "Night", icon: "🦗" },
  { id: "fan", name: "Fan", icon: "🌀" },
  { id: "white", name: "White", icon: "⚪" },
  { id: "pink", name: "Pink", icon: "🌸" },
  { id: "brown", name: "Brown", icon: "🟤" },
];

export const PRESETS = [
  { id: "focus", name: "Deep focus", mix: { brown: 0.55, rain: 0.25 } },
  { id: "rainy", name: "Rainy study", mix: { rain: 0.7, fire: 0.25 } },
  { id: "sleep", name: "Sleep", mix: { ocean: 0.55, pink: 0.2 } },
  { id: "forest", name: "Forest night", mix: { night: 0.45, stream: 0.45, wind: 0.2 } },
  { id: "fan", name: "Fan + white", mix: { fan: 0.6, white: 0.15 } },
];

const rand = () => Math.random() * 2 - 1;

function onePoleCoeff(cutoff, sampleRate) {
  return Math.exp((-2 * Math.PI * cutoff) / sampleRate);
}

function lowpass(data, cutoff, sampleRate) {
  const a = onePoleCoeff(cutoff, sampleRate);
  let y = 0;
  for (let i = 0; i < data.length; i += 1) {
    y = (1 - a) * data[i] + a * y;
    data[i] = y;
  }
  return data;
}

function highpass(data, cutoff, sampleRate) {
  const a = onePoleCoeff(cutoff, sampleRate);
  let y = 0;
  for (let i = 0; i < data.length; i += 1) {
    y = (1 - a) * data[i] + a * y;
    data[i] -= y;
  }
  return data;
}

function white(length, gain = 1) {
  const data = new Float32Array(length);
  for (let i = 0; i < length; i += 1) data[i] = rand() * gain;
  return data;
}

function pink(length, gain = 1) {
  const data = new Float32Array(length);
  let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0;
  for (let i = 0; i < length; i += 1) {
    const w = rand();
    b0 = 0.99886 * b0 + w * 0.0555179;
    b1 = 0.99332 * b1 + w * 0.0750759;
    b2 = 0.969 * b2 + w * 0.153852;
    b3 = 0.8665 * b3 + w * 0.3104856;
    b4 = 0.55 * b4 + w * 0.5329522;
    b5 = -0.7616 * b5 - w * 0.016898;
    data[i] = (b0 + b1 + b2 + b3 + b4 + b5 + b6 + w * 0.5362) * 0.11 * gain;
    b6 = w * 0.115926;
  }
  return data;
}

function brown(length, gain = 1) {
  const data = new Float32Array(length);
  let last = 0;
  for (let i = 0; i < length; i += 1) {
    last = (last + 0.02 * rand()) / 1.02;
    data[i] = last * 3.5 * gain;
  }
  return data;
}

// Short decaying noise bursts: rain drops, fire crackles.
function scatterBursts(data, sampleRate, perSecond, { minMs, maxMs, amp, shape = 2 }) {
  const count = Math.round((data.length / sampleRate) * perSecond);
  for (let n = 0; n < count; n += 1) {
    const start = Math.floor(Math.random() * data.length);
    const length = Math.floor(((minMs + Math.random() * (maxMs - minMs)) / 1000) * sampleRate);
    const level = amp * Math.random() ** shape;
    for (let k = 0; k < length; k += 1) {
      data[(start + k) % data.length] += level * rand() * Math.exp((-5 * k) / length);
    }
  }
}

// Short rising sine "blips": water bubbles in a stream.
function scatterBubbles(data, sampleRate, perSecond) {
  const count = Math.round((data.length / sampleRate) * perSecond);
  for (let n = 0; n < count; n += 1) {
    const start = Math.floor(Math.random() * data.length);
    const length = Math.floor((0.015 + Math.random() * 0.03) * sampleRate);
    const f0 = 350 + Math.random() * 1100;
    const level = 0.03 + Math.random() * 0.09;
    let phase = 0;
    for (let k = 0; k < length; k += 1) {
      const t = k / length;
      phase += (2 * Math.PI * f0 * (1 + 0.6 * t)) / sampleRate;
      data[(start + k) % data.length] += level * Math.sin(phase) * Math.sin(Math.PI * t) * Math.exp(-3 * t);
    }
  }
}

function crickets(data, sampleRate, pitch, gain) {
  let time = Math.random() * 0.5;
  const seconds = data.length / sampleRate;
  while (time < seconds) {
    const pulses = 3 + Math.floor(Math.random() * 2);
    for (let p = 0; p < pulses; p += 1) {
      const start = Math.floor((time + p * 0.045) * sampleRate);
      const length = Math.floor(0.022 * sampleRate);
      for (let k = 0; k < length; k += 1) {
        const t = k / length;
        data[(start + k) % data.length] += gain * Math.sin((2 * Math.PI * pitch * k) / sampleRate) * Math.sin(Math.PI * t);
      }
    }
    time += 0.55 + Math.random() * 0.6;
  }
}

const GENERATORS = {
  white: (L) => [white(L, 0.22), white(L, 0.22)],
  pink: (L) => [pink(L, 0.9), pink(L, 0.9)],
  brown: (L) => [brown(L, 0.9), brown(L, 0.9)],
  rain: (L, sr) =>
    [0, 1].map(() => {
      const data = highpass(pink(L, 0.55), 400, sr);
      scatterBursts(data, sr, 140, { minMs: 2, maxMs: 9, amp: 0.55 });
      return highpass(data, 250, sr);
    }),
  ocean: (L, sr) => {
    // Two or three uneven waves per loop, a low body plus a hiss on the break.
    const env = new Float32Array(L);
    const seconds = L / sr;
    const crests = [0, seconds * (0.42 + Math.random() * 0.1)];
    for (let i = 0; i < L; i += 1) {
      const t = i / sr;
      let value = 0.18;
      for (const crest of crests) {
        for (const shift of [0, seconds, -seconds]) {
          const dt = t - (crest + shift);
          value += dt < 0 ? Math.exp(-((dt / 2.6) ** 2)) * 0.85 : Math.exp(-dt / 1.8) * 0.85;
        }
      }
      env[i] = Math.min(1, value);
    }
    return [0, 1].map(() => {
      const body = lowpass(brown(L, 1.1), 500, sr);
      const hiss = highpass(pink(L, 0.5), 1200, sr);
      for (let i = 0; i < L; i += 1) body[i] = body[i] * env[i] + hiss[i] * env[i] ** 3;
      return body;
    });
  },
  stream: (L, sr) =>
    [0, 1].map(() => {
      const data = lowpass(highpass(pink(L, 0.5), 300, sr), 3500, sr);
      scatterBubbles(data, sr, 70);
      return data;
    }),
  fire: (L, sr) =>
    [0, 1].map(() => {
      const bed = lowpass(brown(L, 1.2), 220, sr);
      const crackle = new Float32Array(L);
      scatterBursts(crackle, sr, 22, { minMs: 1, maxMs: 4, amp: 0.9, shape: 3 });
      scatterBursts(crackle, sr, 2, { minMs: 15, maxMs: 40, amp: 0.4 });
      highpass(crackle, 900, sr);
      for (let i = 0; i < L; i += 1) bed[i] += crackle[i];
      return bed;
    }),
  fan: (L, sr) =>
    [0, 1].map((channel) => {
      const data = lowpass(brown(L, 1.3), 260, sr);
      for (let i = 0; i < L; i += 1) {
        const t = i / sr;
        const blade = 1 + 0.06 * Math.sin(2 * Math.PI * 12 * t + channel);
        data[i] = data[i] * blade + 0.025 * Math.sin(2 * Math.PI * 100 * t) + 0.012 * Math.sin(2 * Math.PI * 200 * t);
      }
      return data;
    }),
  night: (L, sr) => {
    const left = lowpass(pink(L, 0.08), 1200, sr);
    const right = lowpass(pink(L, 0.08), 1200, sr);
    crickets(left, sr, 4300, 0.07);
    crickets(right, sr, 4700, 0.06);
    const both = new Float32Array(L);
    crickets(both, sr, 3900, 0.035);
    for (let i = 0; i < L; i += 1) {
      left[i] += both[i];
      right[i] += both[i];
    }
    return [left, right];
  },
};

const LOOP_SECONDS = { ocean: 17, rain: 9, stream: 9, fire: 10, night: 12 };

// Equal-power crossfade of the tail into the head so the loop has no click.
function seamless(channelData, fadeLength) {
  const length = channelData.length - fadeLength;
  const out = channelData.subarray(0, length);
  for (let i = 0; i < fadeLength; i += 1) {
    const x = i / fadeLength;
    out[i] = channelData[i] * Math.sin((x * Math.PI) / 2) + channelData[length + i] * Math.cos((x * Math.PI) / 2);
  }
  return out;
}

export function renderSound(id, sampleRate, seconds = LOOP_SECONDS[id] ?? 8) {
  const fade = Math.floor(sampleRate * 0.5);
  const length = Math.floor(seconds * sampleRate) + fade;
  return GENERATORS[id](length, sampleRate).map((channel) => seamless(channel, fade));
}

export class NoiseEngine {
  constructor() {
    this.ctx = null;
    this.voices = new Map();
    this.buffers = new Map();
    this.master = null;
    this.analyser = null;
    this.timeData = null;
    this.masterLevel = 0.8;
    this.sleepEndsAt = 0;
    this.sleepTimer = null;
    this.onchange = () => {};
  }

  ensure() {
    if (this.ctx) return this.ctx;
    const Context = globalThis.AudioContext || globalThis.webkitAudioContext;
    this.ctx = new Context({ latencyHint: "playback" });
    this.master = this.ctx.createGain();
    this.master.gain.value = this.masterLevel;
    this.analyser = this.ctx.createAnalyser();
    this.analyser.fftSize = 512;
    this.timeData = new Float32Array(this.analyser.fftSize);
    // Gentle limiter so stacking several loud sounds never clips.
    const limiter = this.ctx.createDynamicsCompressor();
    limiter.threshold.value = -6;
    limiter.knee.value = 6;
    limiter.ratio.value = 8;
    this.master.connect(limiter).connect(this.analyser).connect(this.ctx.destination);
    return this.ctx;
  }

  get playing() {
    return Boolean(this.ctx && this.ctx.state === "running" && this.voices.size);
  }

  volumeOf(id) {
    return this.voices.get(id)?.volume ?? 0;
  }

  setVolume(id, volume) {
    const ctx = this.ensure();
    if (ctx.state === "suspended") ctx.resume();
    let voice = this.voices.get(id);
    if (volume <= 0.001) {
      if (voice) {
        this.#release(id, voice);
        this.onchange();
      }
      return;
    }
    const created = !voice;
    if (created) voice = this.#createVoice(id);
    voice.volume = volume;
    voice.gain.gain.setTargetAtTime(volume ** 1.6, ctx.currentTime, 0.25);
    // Volume drags do not notify, so sliders are not re-rendered mid-drag.
    if (created) this.onchange();
  }

  setMaster(level) {
    this.masterLevel = level;
    if (this.master) this.master.gain.setTargetAtTime(level, this.ctx.currentTime, 0.1);
  }

  applyMix(mix) {
    for (const id of [...this.voices.keys()]) if (!(id in mix)) this.setVolume(id, 0);
    for (const [id, volume] of Object.entries(mix)) this.setVolume(id, volume);
  }

  mix() {
    return Object.fromEntries([...this.voices].map(([id, voice]) => [id, voice.volume]));
  }

  async pause() {
    if (this.ctx?.state !== "running") return;
    await this.ctx.suspend();
    this.onchange();
  }

  async resume() {
    this.ensure();
    if (this.ctx.state === "running") return;
    await this.ctx.resume();
    this.onchange();
  }

  stopAll() {
    for (const [id, voice] of [...this.voices]) this.#release(id, voice);
    this.cancelSleepTimer();
    this.onchange();
  }

  level() {
    if (!this.playing) return 0;
    this.analyser.getFloatTimeDomainData(this.timeData);
    let sum = 0;
    for (const value of this.timeData) sum += value * value;
    return Math.min(1, Math.sqrt(sum / this.timeData.length) * 2.5);
  }

  startSleepTimer(minutes) {
    this.cancelSleepTimer();
    this.sleepEndsAt = Date.now() + minutes * 60000;
    this.sleepTimer = setInterval(() => {
      const left = this.sleepEndsAt - Date.now();
      if (!this.master) return;
      if (left <= 0) {
        this.stopAll();
        this.master.gain.value = this.masterLevel;
      } else if (left < 60000) {
        // Fade out over the final minute.
        this.master.gain.setTargetAtTime(this.masterLevel * (left / 60000), this.ctx.currentTime, 0.5);
      }
    }, 1000);
    this.onchange();
  }

  cancelSleepTimer() {
    if (this.sleepTimer) clearInterval(this.sleepTimer);
    this.sleepTimer = null;
    this.sleepEndsAt = 0;
    if (this.master) this.master.gain.setTargetAtTime(this.masterLevel, this.ctx.currentTime, 0.2);
  }

  sleepRemaining() {
    return this.sleepEndsAt ? Math.max(0, this.sleepEndsAt - Date.now()) : 0;
  }

  // A soft two-tone bell for the end of a focus block.
  chime() {
    const ctx = this.ensure();
    if (ctx.state === "suspended") ctx.resume();
    const now = ctx.currentTime;
    for (const [freq, delay] of [[659.25, 0], [987.77, 0.18], [1318.5, 0.36]]) {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.frequency.value = freq;
      gain.gain.setValueAtTime(0, now + delay);
      gain.gain.linearRampToValueAtTime(0.18, now + delay + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + delay + 2.2);
      osc.connect(gain).connect(ctx.destination);
      osc.start(now + delay);
      osc.stop(now + delay + 2.3);
    }
  }

  #buffer(id) {
    if (!this.buffers.has(id)) {
      const channels = renderSound(id, this.ctx.sampleRate);
      const buffer = this.ctx.createBuffer(channels.length, channels[0].length, this.ctx.sampleRate);
      channels.forEach((data, index) => buffer.copyToChannel(data, index));
      this.buffers.set(id, buffer);
    }
    return this.buffers.get(id);
  }

  #createVoice(id) {
    const ctx = this.ctx;
    const gain = ctx.createGain();
    gain.gain.value = 0;
    gain.connect(this.master);
    const nodes = [];
    if (id === "wind") {
      // Live filter sweeps give wind its gusts.
      const source = ctx.createBufferSource();
      source.buffer = this.#buffer("white");
      source.loop = true;
      const filter = ctx.createBiquadFilter();
      filter.type = "bandpass";
      filter.frequency.value = 450;
      filter.Q.value = 0.9;
      const gust = ctx.createGain();
      gust.gain.value = 1.6;
      const sweep = ctx.createOscillator();
      sweep.frequency.value = 0.07;
      const sweepDepth = ctx.createGain();
      sweepDepth.gain.value = 260;
      const swell = ctx.createOscillator();
      swell.frequency.value = 0.11;
      const swellDepth = ctx.createGain();
      swellDepth.gain.value = 0.9;
      sweep.connect(sweepDepth).connect(filter.frequency);
      swell.connect(swellDepth).connect(gust.gain);
      source.connect(filter).connect(gust).connect(gain);
      for (const node of [source, sweep, swell]) node.start();
      nodes.push(source, sweep, swell);
    } else {
      const source = ctx.createBufferSource();
      source.buffer = this.#buffer(id);
      source.loop = true;
      source.connect(gain);
      source.start(0, Math.random() * source.buffer.duration);
      nodes.push(source);
    }
    const voice = { gain, nodes, volume: 0 };
    this.voices.set(id, voice);
    return voice;
  }

  #release(id, voice) {
    this.voices.delete(id);
    const now = this.ctx.currentTime;
    voice.gain.gain.setTargetAtTime(0, now, 0.2);
    for (const node of voice.nodes) node.stop(now + 1.2);
    setTimeout(() => voice.gain.disconnect(), 1400);
  }
}
