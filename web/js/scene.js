// The living background: a soft noise-displaced orb, drifting particles, and
// a progress ring, drawn with three.js behind the UI. Each screen sets a mode
// and the scene eases between modes, so nothing jumps.

import * as THREE from "./vendor/three.module.min.js";

const NOISE_GLSL = /* glsl */ `
vec3 mod289(vec3 x){return x-floor(x*(1.0/289.0))*289.0;}
vec4 mod289(vec4 x){return x-floor(x*(1.0/289.0))*289.0;}
vec4 permute(vec4 x){return mod289(((x*34.0)+1.0)*x);}
vec4 taylorInvSqrt(vec4 r){return 1.79284291400159-0.85373472095314*r;}
float snoise(vec3 v){
  const vec2 C=vec2(1.0/6.0,1.0/3.0);
  const vec4 D=vec4(0.0,0.5,1.0,2.0);
  vec3 i=floor(v+dot(v,C.yyy));
  vec3 x0=v-i+dot(i,C.xxx);
  vec3 g=step(x0.yzx,x0.xyz);
  vec3 l=1.0-g;
  vec3 i1=min(g.xyz,l.zxy);
  vec3 i2=max(g.xyz,l.zxy);
  vec3 x1=x0-i1+C.xxx;
  vec3 x2=x0-i2+C.yyy;
  vec3 x3=x0-D.yyy;
  i=mod289(i);
  vec4 p=permute(permute(permute(i.z+vec4(0.0,i1.z,i2.z,1.0))+i.y+vec4(0.0,i1.y,i2.y,1.0))+i.x+vec4(0.0,i1.x,i2.x,1.0));
  float n_=0.142857142857;
  vec3 ns=n_*D.wyz-D.xzx;
  vec4 j=p-49.0*floor(p*ns.z*ns.z);
  vec4 x_=floor(j*ns.z);
  vec4 y_=floor(j-7.0*x_);
  vec4 x=x_*ns.x+ns.yyyy;
  vec4 y=y_*ns.x+ns.yyyy;
  vec4 h=1.0-abs(x)-abs(y);
  vec4 b0=vec4(x.xy,y.xy);
  vec4 b1=vec4(x.zw,y.zw);
  vec4 s0=floor(b0)*2.0+1.0;
  vec4 s1=floor(b1)*2.0+1.0;
  vec4 sh=-step(h,vec4(0.0));
  vec4 a0=b0.xzyw+s0.xzyw*sh.xxyy;
  vec4 a1=b1.xzyw+s1.xzyw*sh.zzww;
  vec3 p0=vec3(a0.xy,h.x);
  vec3 p1=vec3(a0.zw,h.y);
  vec3 p2=vec3(a1.xy,h.z);
  vec3 p3=vec3(a1.zw,h.w);
  vec4 norm=taylorInvSqrt(vec4(dot(p0,p0),dot(p1,p1),dot(p2,p2),dot(p3,p3)));
  p0*=norm.x;p1*=norm.y;p2*=norm.z;p3*=norm.w;
  vec4 m=max(0.6-vec4(dot(x0,x0),dot(x1,x1),dot(x2,x2),dot(x3,x3)),0.0);
  m=m*m;
  return 42.0*dot(m*m,vec4(dot(p0,x0),dot(p1,x1),dot(p2,x2),dot(p3,x3)));
}`;

const MODES = {
  today: { x: 0, y: 0.1, size: 0.3, amp: 0.12, speed: 0.35, ring: 0 },
  focus: { x: 0, y: 0.3, size: 0.62, amp: 0.08, speed: 0.25, ring: 1 },
  sounds: { x: 0, y: 0.1, size: 0.3, amp: 0.1, speed: 0.3, ring: 0 },
  breathe: { x: 0, y: 0.3, size: 0.62, amp: 0.07, speed: 0.2, ring: 0 },
  // Small orb tucked in the top-right corner for text-heavy screens.
  mini: { x: 0.3, y: 0.075, size: 0.2, amp: 0.14, speed: 0.35, ring: 0 },
};

export class Scene {
  constructor(canvas, { motion = "full", getLevel = () => 0 } = {}) {
    this.canvas = canvas;
    this.getLevel = getLevel;
    this.motion = motion;
    this.mode = MODES.today;
    this.state = { x: 0, y: 0.13, size: 0.42, amp: 0.16, speed: 0.35, ring: 0, scroll: 0 };
    this.breath = null;
    this.ringProgress = 0;
    this.pulseValue = 0;
    this.scroll = 0;
    this.time = 0;
    this.last = performance.now();
    this.frame = 0;
    this.running = false;

    try {
      this.renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: false, powerPreference: "low-power" });
    } catch {
      this.renderer = null;
      canvas.remove();
      return;
    }
    this.renderer.setClearColor(0x000000, 0);
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(40, 1, 0.1, 50);
    this.camera.position.z = 7;

    this.uniforms = {
      uTime: { value: 0 },
      uAmp: { value: 0.16 },
      uColorA: { value: new THREE.Color() },
      uColorB: { value: new THREE.Color() },
      uColorC: { value: new THREE.Color() },
    };
    this.#buildOrb();
    this.#buildGlow();
    this.#buildParticles();
    this.#buildRing();

    this.resize();
    addEventListener("resize", () => this.resize());
    document.addEventListener("visibilitychange", () => (document.hidden ? this.stop() : this.start()));
  }

  get ok() {
    return Boolean(this.renderer);
  }

  #buildOrb() {
    const detail = this.motion === "full" ? 28 : 14;
    const material = new THREE.ShaderMaterial({
      uniforms: this.uniforms,
      transparent: true,
      vertexShader: /* glsl */ `
        uniform float uTime; uniform float uAmp;
        varying float vNoise; varying vec3 vNormal; varying vec3 vView;
        ${NOISE_GLSL}
        void main(){
          float n = snoise(position * 0.9 + vec3(0.0, uTime * 0.5, uTime * 0.25));
          n += 0.35 * snoise(position * 2.0 - vec3(uTime * 0.35));
          vNoise = n;
          vec3 displaced = position + normal * n * uAmp;
          vec4 world = modelViewMatrix * vec4(displaced, 1.0);
          vNormal = normalize(normalMatrix * normal);
          vView = normalize(-world.xyz);
          gl_Position = projectionMatrix * world;
        }`,
      fragmentShader: /* glsl */ `
        uniform vec3 uColorA; uniform vec3 uColorB; uniform vec3 uColorC;
        varying float vNoise; varying vec3 vNormal; varying vec3 vView;
        void main(){
          float facing = max(dot(vNormal, vView), 0.0);
          float fresnel = pow(1.0 - facing, 3.0);
          vec3 color = mix(uColorA, uColorB, smoothstep(-0.9, 1.0, vNoise * 0.6 + vNormal.y * 0.8));
          vec3 light = normalize(vec3(-0.4, 0.7, 0.6));
          float spec = pow(max(dot(reflect(-light, vNormal), vView), 0.0), 24.0);
          color += spec * 0.35;
          color = mix(color, uColorC, fresnel * 0.6);
          gl_FragColor = vec4(color, 0.96);
        }`,
    });
    this.orb = new THREE.Mesh(new THREE.IcosahedronGeometry(1, detail), material);
    this.scene.add(this.orb);
  }

  #buildGlow() {
    const size = 128;
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = size;
    const ctx = canvas.getContext("2d");
    const gradient = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
    gradient.addColorStop(0, "rgba(255,255,255,0.55)");
    gradient.addColorStop(0.4, "rgba(255,255,255,0.18)");
    gradient.addColorStop(1, "rgba(255,255,255,0)");
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, size, size);
    this.glowMaterial = new THREE.SpriteMaterial({
      map: new THREE.CanvasTexture(canvas),
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
    });
    this.glow = new THREE.Sprite(this.glowMaterial);
    this.scene.add(this.glow);
  }

  #buildParticles() {
    const count = this.motion === "full" ? 420 : 160;
    const positions = new Float32Array(count * 3);
    const seeds = new Float32Array(count);
    for (let i = 0; i < count; i += 1) {
      positions[i * 3] = (Math.random() - 0.5) * 9;
      positions[i * 3 + 1] = (Math.random() - 0.5) * 14;
      positions[i * 3 + 2] = (Math.random() - 0.5) * 5 - 1;
      seeds[i] = Math.random();
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute("seed", new THREE.BufferAttribute(seeds, 1));
    this.particleUniforms = {
      uTime: this.uniforms.uTime,
      uColor: this.uniforms.uColorC,
      uScale: { value: 1 },
      uLevel: { value: 0 },
    };
    const material = new THREE.ShaderMaterial({
      uniforms: this.particleUniforms,
      transparent: true,
      depthWrite: false,
      blending: THREE.AdditiveBlending,
      vertexShader: /* glsl */ `
        uniform float uTime; uniform float uScale; uniform float uLevel;
        attribute float seed; varying float vAlpha;
        void main(){
          vec3 p = position;
          p.y = mod(p.y + uTime * (0.12 + seed * 0.25) + 7.0, 14.0) - 7.0;
          p.x += sin(uTime * 0.3 + seed * 6.28) * 0.25;
          vec4 mv = modelViewMatrix * vec4(p, 1.0);
          gl_PointSize = (2.0 + seed * 3.5) * uScale * (1.0 + uLevel * 1.5) * (6.0 / -mv.z);
          vAlpha = 0.25 + 0.55 * seed;
          gl_Position = projectionMatrix * mv;
        }`,
      fragmentShader: /* glsl */ `
        uniform vec3 uColor; varying float vAlpha;
        void main(){
          float d = length(gl_PointCoord - 0.5);
          if (d > 0.5) discard;
          gl_FragColor = vec4(uColor, vAlpha * smoothstep(0.5, 0.0, d));
        }`,
    });
    this.particles = new THREE.Points(geometry, material);
    this.scene.add(this.particles);
  }

  #buildRing() {
    this.ringUniforms = { uProgress: { value: 0 }, uOpacity: { value: 0 }, uColor: this.uniforms.uColorC };
    const material = new THREE.ShaderMaterial({
      uniforms: this.ringUniforms,
      transparent: true,
      depthWrite: false,
      vertexShader: /* glsl */ `
        varying vec2 vUv;
        void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
      fragmentShader: /* glsl */ `
        uniform float uProgress; uniform float uOpacity; uniform vec3 uColor; varying vec2 vUv;
        void main(){
          float done = step(vUv.x, uProgress);
          gl_FragColor = vec4(uColor, uOpacity * mix(0.16, 1.0, done));
        }`,
    });
    this.ring = new THREE.Mesh(new THREE.TorusGeometry(1.45, 0.035, 8, 180), material);
    // Start at twelve o'clock and run clockwise.
    this.ring.rotation.z = Math.PI / 2;
    this.ring.scale.x = -1;
    this.scene.add(this.ring);
  }

  setColors({ a, b, c }) {
    if (!this.ok) return;
    this.uniforms.uColorA.value.set(a);
    this.uniforms.uColorB.value.set(b);
    this.uniforms.uColorC.value.set(c);
    this.glowMaterial.color.set(b);
    this.renderOnce();
  }

  setMode(name) {
    this.mode = MODES[name] ?? MODES.today;
    this.scroll = 0;
    this.renderOnce();
  }

  setMotion(motion) {
    this.motion = motion;
    this.resize();
    if (motion === "off") {
      this.stop();
      this.renderOnce();
    } else {
      this.start();
    }
  }

  setScroll(pixels) {
    this.scroll = pixels;
    if (this.motion === "off") this.renderOnce();
  }

  setBreath(value) {
    this.breath = value;
  }

  setRing(progress) {
    this.ringProgress = progress;
  }

  pulse(strength = 1) {
    this.pulseValue = Math.min(1.5, this.pulseValue + strength);
    if (this.motion === "off") this.renderOnce();
  }

  resize() {
    if (!this.ok) return;
    const width = innerWidth;
    const height = innerHeight;
    const ratio = Math.min(devicePixelRatio || 1, this.motion === "full" ? 1.75 : 1);
    this.renderer.setPixelRatio(ratio);
    this.renderer.setSize(width, height, false);
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.viewHeight = 2 * Math.tan(THREE.MathUtils.degToRad(this.camera.fov / 2)) * this.camera.position.z;
    this.viewWidth = this.viewHeight * this.camera.aspect;
    this.pixelsToWorld = this.viewHeight / height;
    this.particleUniforms.uScale.value = ratio * Math.min(1.4, height / 700);
    this.renderOnce();
  }

  start() {
    if (!this.ok || this.running || this.motion === "off" || document.hidden) return;
    this.running = true;
    this.last = performance.now();
    const loop = (now) => {
      if (!this.running) return;
      requestAnimationFrame(loop);
      this.frame += 1;
      // Low motion renders at half rate to save battery.
      if (this.motion === "low" && this.frame % 2) return;
      const dt = Math.min(0.1, (now - this.last) / 1000);
      this.last = now;
      this.#update(dt);
      this.renderer.render(this.scene, this.camera);
    };
    requestAnimationFrame(loop);
  }

  stop() {
    this.running = false;
  }

  renderOnce() {
    if (!this.ok || this.running) return;
    this.#update(1);
    this.renderer.render(this.scene, this.camera);
  }

  #update(dt) {
    const s = this.state;
    const m = this.mode;
    const ease = 1 - Math.exp(-dt * 3.2);
    for (const key of ["x", "y", "size", "amp", "speed", "ring"]) s[key] += (m[key] - s[key]) * ease;
    s.scroll += (this.scroll - s.scroll) * Math.min(1, ease * 2);

    const level = this.getLevel();
    this.pulseValue *= Math.exp(-dt * 2.5);
    this.time += dt * (s.speed + level * 0.8 + this.pulseValue * 0.6);
    this.uniforms.uTime.value = this.time;
    this.uniforms.uAmp.value = s.amp + level * 0.07 + this.pulseValue * 0.18;
    this.particleUniforms.uLevel.value = level;

    const fit = Math.min(this.viewWidth * 0.5, this.viewHeight * 0.28);
    let scale = fit * s.size;
    if (this.breath !== null) scale *= 0.72 + 0.42 * this.breath;
    scale *= 1 + this.pulseValue * 0.08 + level * 0.06;

    const x = s.x * this.viewWidth;
    const y = (0.5 - s.y) * this.viewHeight + s.scroll * this.pixelsToWorld * 0.6;
    this.orb.position.set(x, y, 0);
    this.orb.scale.setScalar(scale);
    this.orb.rotation.y += dt * 0.12;
    this.orb.rotation.x = Math.sin(this.time * 0.2) * 0.2;
    this.glow.position.set(x, y, -0.5);
    this.glow.scale.setScalar(scale * 4.2);
    this.glowMaterial.opacity = 0.55 + level * 0.4 + this.pulseValue * 0.3;

    this.ring.position.set(x, y, 0);
    this.ring.scale.set(-scale, scale, scale);
    this.ringUniforms.uOpacity.value = s.ring;
    this.ringUniforms.uProgress.value = this.ringProgress;
    this.particles.position.y = s.scroll * this.pixelsToWorld * 0.25;
  }
}
