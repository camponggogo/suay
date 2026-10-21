'use strict';

document.documentElement.dataset.boot = 'started';

const debugLines = [];
const debugNode = document.createElement('pre');
debugNode.className = 'debuglog';
if (DEBUG && document.body) document.body.appendChild(debugNode);
else if (DEBUG) document.addEventListener('DOMContentLoaded', () => document.body.appendChild(debugNode));
function trace(...parts) {
  if (!DEBUG) return;
  debugLines.push(parts.map((part) => (typeof part === 'object' ? JSON.stringify(part) : String(part))).join(' '));
  debugNode.textContent = debugLines.slice(-6).join('\n');
}
window.addEventListener('error', (event) => {
  document.documentElement.dataset.error =
    (event.message || 'unknown') + ' @ ' + (event.filename || '') + ':' + (event.lineno || 0);
  const status = document.getElementById('stat-status');
  if (status) status.textContent = 'ERROR: ' + (event.message || 'unknown') + ' :' + (event.lineno || 0);
});
window.addEventListener('unhandledrejection', (event) => {
  document.documentElement.dataset.error = 'rejection: ' + String(event.reason);
  const status = document.getElementById('stat-status');
  if (status) status.textContent = 'REJECT: ' + String(event.reason);
});

/* SUAY neural fabric, 3D — neurons as dots, synapses as dashed fibres, signals as travelling pulses. */

import * as THREE from './vendor/three.module.js';

const container = document.getElementById('fabric');
const tooltip = document.getElementById('tooltip');
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const params = new URLSearchParams(window.location.search);
const STATIC = params.get('static') === '1' || reduceMotion;
const DEBUG = params.get('debug') === '1';

const ZONE_COLORS = ['#7c5cff', '#22d3ee', '#34d399', '#f472b6', '#fbbf24', '#60a5fa'];
const STATUS_COLOR = { live: '#34d399', stale: '#fbbf24', offline: '#fb7185' };

let renderer;
try {
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
} catch (error) {
  document.getElementById('stat-status').textContent = 'เบราว์เซอร์นี้ไม่รองรับ WebGL — สลับเป็นมุมมอง 2 มิติ';
  window.setTimeout(() => window.location.replace('/neural-flat'), 1200);
  throw error;
}
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.setClearColor(0x05070f, 0);
container.appendChild(renderer.domElement);
trace('renderer', renderer.domElement.width + 'x' + renderer.domElement.height);

const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x05070f, 0.028);

const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 220);
const cameraState = { theta: 0.65, phi: 1.15, radius: 10.8, goal: 10.8 };

const root = new THREE.Group();
scene.add(root);

const state = {
  nodes: [],
  data: null,
  signature: '',
  focus: null,
  pool: [],
  eventTimes: [],
  lastEventId: 0,
  hubFlash: 0,
  primed: false,
  pointer: { x: -999, y: -999 },
  hovered: null,
  dragging: false,
  idle: 10,
  rate: 0,
  lastBeats: null,
  lastSampleAt: 0,
};

/* ---------- textures ---------- */

function glowTexture() {
  const size = 128;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');
  const gradient = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  gradient.addColorStop(0, 'rgba(255,255,255,1)');
  gradient.addColorStop(0.18, 'rgba(255,255,255,0.92)');
  gradient.addColorStop(0.42, 'rgba(255,255,255,0.28)');
  gradient.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, size, size);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

const GLOW = glowTexture();

function sprite(color, scale, opacity) {
  const material = new THREE.SpriteMaterial({
    map: GLOW, color: new THREE.Color(color), transparent: true, opacity,
    blending: THREE.AdditiveBlending, depthWrite: false, sizeAttenuation: true,
  });
  const item = new THREE.Sprite(material);
  item.scale.setScalar(scale);
  return item;
}

/* ---------- static scenery ---------- */

const starGeometry = new THREE.BufferGeometry();
const starPositions = [];
for (let index = 0; index < 420; index += 1) {
  const radius = 18 + Math.random() * 30;
  const theta = Math.random() * Math.PI * 2;
  const phi = Math.acos(2 * Math.random() - 1);
  starPositions.push(
    radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta));
}
starGeometry.setAttribute('position', new THREE.Float32BufferAttribute(starPositions, 3));
scene.add(new THREE.Points(starGeometry, new THREE.PointsMaterial({
  color: 0x8b93b8, size: 0.055, transparent: true, opacity: 0.5, depthWrite: false,
})));

function makePool() {
  for (let index = 0; index < 150; index += 1) {
    const item = sprite('#ffffff', 0.5, 0);
    item.visible = false;
    scene.add(item);
    state.pool.push({ sprite: item, active: false, node: null, dir: 1, t: 0, duration: 0.4, strength: 1 });
  }
}

function activate(node, dir, duration, strength) {
  if (!node || !node.curve) return;
  const slot = state.pool.find((entry) => !entry.active);
  if (!slot) return;
  slot.active = true;
  slot.node = node;
  slot.dir = dir;
  slot.t = 0;
  slot.duration = duration;
  slot.strength = strength;
  slot.sprite.visible = true;
  slot.sprite.material.color.set(node.color).lerp(new THREE.Color('#ffffff'), 0.62);
  slot.sprite.position.copy(node.curve.getPoint(dir === 1 ? 0 : 1));
}

const EVENT_STYLE = {
  heartbeat: { dir: 1, duration: 0.42, strength: 1.0 },
  ack: { dir: -1, duration: 0.30, strength: 0.55 },
  dispatch: { dir: -1, duration: 0.46, strength: 1.35 },
  result: { dir: 1, duration: 0.46, strength: 1.2 },
};

function handleEvent(event) {
  const peer = event.target === 'hub' ? event.source : event.target;
  const node = state.nodes.find((item) => item.id === peer);
  const style = EVENT_STYLE[event.kind];
  if (style && node) {
    // Travel time follows the measured round trip: a slow machine visibly glows slower.
    const measured = typeof event.rtt_ms === 'number' ? event.rtt_ms : null;
    const duration = measured === null
      ? style.duration
      : Math.min(style.duration + 0.55, 0.22 + measured / 400);
    activate(node, style.dir, duration, style.strength);
    node.flashUntil = performance.now() + 430;
  }
  if (event.kind === 'request' || event.kind === 'response' || event.kind === 'dispatch') {
    state.hubFlash = 1;
  }
  state.eventTimes.push(performance.now());
}

async function primeEvents() {
  try {
    const response = await fetch('/api/events', { headers: { 'X-SUAY-Request': '1' } });
    if (!response.ok) return;
    const data = await response.json();
    state.lastEventId = data.latest || 0;
    state.primed = true;
  } catch (error) {
    /* the view still works without the stream */
  }
}

async function pullEvents() {
  if (!state.primed) return;
  try {
    const response = await fetch('/api/events?since=' + state.lastEventId, { headers: { 'X-SUAY-Request': '1' } });
    if (!response.ok) return;
    const data = await response.json();
    for (const event of data.events || []) {
      state.lastEventId = Math.max(state.lastEventId, event.id);
      handleEvent(event);
    }
    const cutoff = performance.now() - 2000;
    state.eventTimes = state.eventTimes.filter((stamp) => stamp > cutoff);
    const rate = state.eventTimes.length / 2;
    document.getElementById('stat-rate').textContent = rate ? rate.toFixed(1) : '0.0';
  } catch (error) {
    /* transient fetch failures are expected while the hub restarts */
  }
}

const hub = new THREE.Group();
const hubCore = new THREE.Mesh(
  new THREE.SphereGeometry(0.34, 32, 24),
  new THREE.MeshBasicMaterial({ color: 0xded4ff }));
hub.add(hubCore);
const hubHalo = sprite('#7c5cff', 7.2, 0.55);
hub.add(hubHalo);
const ringA = new THREE.Mesh(
  new THREE.TorusGeometry(0.72, 0.006, 8, 96),
  new THREE.MeshBasicMaterial({ color: 0xb9a6ff, transparent: true, opacity: 0.55 }));
ringA.rotation.x = Math.PI / 2.4;
hub.add(ringA);
const ringB = new THREE.Mesh(
  new THREE.TorusGeometry(1.02, 0.004, 8, 96),
  new THREE.MeshBasicMaterial({ color: 0x22d3ee, transparent: true, opacity: 0.32 }));
ringB.rotation.x = Math.PI / 1.7;
ringB.rotation.y = 0.6;
hub.add(ringB);
scene.add(hub);
makePool();

/* ---------- topology ---------- */

function signatureOf(nodes) {
  return nodes.map((node) => node.id + ':' + node.status).join('|');
}

function positionFor(node, zoneIndex, zoneCount) {
  const shell = 2.7 + Math.min(zoneIndex, 3) * 1.45;
  const count = Math.max(1, node.count);
  const angle = (node.slot / count) * Math.PI * 2 + zoneIndex * 0.7 + (node.seed % 0.18);
  const wobble = (Math.abs(Math.sin(node.seed * 91.7)) % 1 - 0.5) * 0.55;
  const tilt = 0.5 + zoneIndex * 0.16;
  return new THREE.Vector3(
    Math.cos(angle) * shell,
    Math.sin(angle + zoneIndex * 1.3) * tilt + (zoneIndex - 1) * 0.9 + wobble,
    Math.sin(angle) * shell);
}

function disposeGroup(group) {
  group.traverse((child) => {
    if (child.geometry) child.geometry.dispose();
    if (child.material) {
      if (child.material.map && child.material.map !== GLOW) child.material.map.dispose();
      child.material.dispose();
    }
  });
}

function build(data) {
  for (const child of [...root.children]) {
    root.remove(child);
    disposeGroup(child);
  }
  state.pulses = [];

  const zones = (data.zones || []).map((zone) => zone.name);
  const byZone = new Map();
  for (const node of data.nodes || []) {
    if (!byZone.has(node.zone)) byZone.set(node.zone, []);
    byZone.get(node.zone).push(node);
  }
  state.nodes = (data.nodes || []).map((node, index) => {
    const zoneIndex = Math.max(0, zones.indexOf(node.zone));
    const members = byZone.get(node.zone) || [node];
    return {
      ...node,
      zoneIndex,
      slot: Math.max(0, members.findIndex((item) => item.id === node.id)),
      count: members.length,
      seed: index * 0.618 + 0.17,
      color: node.status === 'live' ? ZONE_COLORS[zoneIndex % ZONE_COLORS.length] : STATUS_COLOR[node.status],
    };
  });

  const shellGroup = new THREE.Group();
  for (const node of state.nodes) {
    node.position = positionFor(node, node.zoneIndex, zones.length);
    node.sprite = sprite(node.color, node.status === 'live' ? 1.75 : 1.2, 1);
    node.sprite.position.copy(node.position);
    node.flashUntil = 0;
    shellGroup.add(node.sprite);
    node.line = null;
  }

  const lineGroup = new THREE.Group();
  for (const node of state.nodes) {
    const control = node.position.clone().multiplyScalar(0.45);
    control.y += 0.5;
    const curve = new THREE.QuadraticBezierCurve3(node.position.clone(), control, new THREE.Vector3(0, 0, 0));
    node.curve = curve;
    const geometry = new THREE.BufferGeometry().setFromPoints(curve.getPoints(30));
    const material = new THREE.LineDashedMaterial({
      color: new THREE.Color(node.color), transparent: true, opacity: 0.5,
      dashSize: 0.22, gapSize: 0.26, depthWrite: false,
    });
    const line = new THREE.Line(geometry, material);
    line.computeLineDistances();
    lineGroup.add(line);
    node.line = line;
  }

  const grouped = new Map();
  for (const node of state.nodes) {
    if (!grouped.has(node.zone)) grouped.set(node.zone, []);
    grouped.get(node.zone).push(node);
  }
  for (const members of grouped.values()) {
    members.sort((a, b) => a.slot - b.slot);
    for (let index = 0; index < members.length; index += 1) {
      const a = members[index];
      const b = members[(index + 1) % members.length];
      if (a === b) continue;
      const middle = a.position.clone().add(b.position).multiplyScalar(0.5).multiplyScalar(1.06);
      const curve = new THREE.QuadraticBezierCurve3(a.position.clone(), middle, b.position.clone());
      const geometry = new THREE.BufferGeometry().setFromPoints(curve.getPoints(16));
      const material = new THREE.LineDashedMaterial({
        color: new THREE.Color(a.color), transparent: true, opacity: 0.16,
        dashSize: 0.1, gapSize: 0.24, depthWrite: false,
      });
      const line = new THREE.Line(geometry, material);
      line.computeLineDistances();
      lineGroup.add(line);
    }
  }

  for (let index = 0; index < state.nodes.length; index += 6) {
    const a = state.nodes[index];
    const b = state.nodes[(index * 7 + 3) % state.nodes.length];
    if (!a || !b || a.zone === b.zone) continue;
    const middle = a.position.clone().add(b.position).multiplyScalar(0.5).multiplyScalar(0.72);
    const curve = new THREE.QuadraticBezierCurve3(a.position.clone(), middle, b.position.clone());
    const geometry = new THREE.BufferGeometry().setFromPoints(curve.getPoints(22));
    const material = new THREE.LineDashedMaterial({
      color: 0x94a3ff, transparent: true, opacity: 0.1, dashSize: 0.12, gapSize: 0.34, depthWrite: false,
    });
    const line = new THREE.Line(geometry, material);
    line.computeLineDistances();
    lineGroup.add(line);
  }

  root.add(lineGroup, shellGroup);
  state.lines = lineGroup;
  state.signature = signatureOf(state.nodes);
  updateStats(data);
  trace('built', state.nodes.length, 'nodes', 'lines', state.nodes.filter((n) => n.line).length);
  if (STATIC) renderStatic();
}

function updateStats(data) {
  const zones = data.zones || [];
  const live = state.nodes.filter((node) => node.status === 'live').length;
  document.getElementById('stat-live').textContent = String(live);
  document.getElementById('stat-total').textContent = String(state.nodes.length);
  document.getElementById('stat-zones').textContent = String(zones.length);

  const beats = Number((data.stats || {}).heartbeats || 0);
  const now = performance.now();
  if (state.lastBeats !== null && now > state.lastSampleAt) {
    state.rate = Math.max(0, beats - state.lastBeats) / ((now - state.lastSampleAt) / 1000);
  }
  state.lastBeats = beats;
  state.lastSampleAt = now;
  document.getElementById('stat-rate').textContent = state.rate ? state.rate.toFixed(1) : '0.0';
}

async function load() {
  try {
    const response = await fetch('/api/topology', { headers: { 'X-SUAY-Request': '1' } });
    if (!response.ok) throw new Error('HTTP ' + response.status);
    const data = await response.json();
    state.data = data;
    if (signatureOf(data.nodes || []) !== state.signature) build(data);
    else updateStats(data);
    document.getElementById('stat-status').textContent =
      'อัปเดต ' + new Date().toLocaleTimeString('th-TH', { hour12: false });
  } catch (error) {
    document.getElementById('stat-status').textContent = 'โหลดข้อมูลไม่ได้: ' + error.message;
    console.error('SUAY 3D load failed', error);
  }
}

/* ---------- interaction ---------- */

function resize() {
  const width = Math.max(1, window.innerWidth);
  const height = Math.max(1, window.innerHeight);
  renderer.setSize(width, height, true);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
}

let lastPointer = null;

renderer.domElement.addEventListener('pointerdown', (event) => {
  state.dragging = true;
  state.idle = 0;
  lastPointer = { x: event.clientX, y: event.clientY };
  renderer.domElement.setPointerCapture(event.pointerId);
});

renderer.domElement.addEventListener('pointermove', (event) => {
  const rect = renderer.domElement.getBoundingClientRect();
  state.pointer.x = event.clientX - rect.left;
  state.pointer.y = event.clientY - rect.top;
  if (!state.dragging || !lastPointer) return;
  cameraState.theta -= (event.clientX - lastPointer.x) * 0.006;
  cameraState.phi = Math.min(Math.PI - 0.22, Math.max(0.22, cameraState.phi - (event.clientY - lastPointer.y) * 0.006));
  lastPointer = { x: event.clientX, y: event.clientY };
  state.idle = 0;
});

renderer.domElement.addEventListener('pointerup', (event) => {
  if (state.dragging && lastPointer) {
    const moved = Math.hypot(event.clientX - lastPointer.x, event.clientY - lastPointer.y);
    if (moved < 5) {
      const node = state.hovered;
      state.focus = node ? (state.focus === node.id ? null : node.id) : null;
    }
  }
  state.dragging = false;
  lastPointer = null;
});

renderer.domElement.addEventListener('pointerleave', () => {
  state.dragging = false;
  state.hovered = null;
  tooltip.hidden = true;
});

renderer.domElement.addEventListener('wheel', (event) => {
  event.preventDefault();
  cameraState.goal = Math.min(34, Math.max(5.5, cameraState.goal * (1 + event.deltaY * 0.0012)));
  state.idle = 0;
}, { passive: false });

window.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') state.focus = null;
});

const projected = new THREE.Vector3();

function pickNode(width, height) {
  let best = null;
  let bestDistance = 22;
  for (const node of state.nodes) {
    projected.copy(node.position).project(camera);
    if (projected.z > 1) continue;
    const x = (projected.x * 0.5 + 0.5) * width;
    const y = (-projected.y * 0.5 + 0.5) * height;
    const distance = Math.hypot(x - state.pointer.x, y - state.pointer.y);
    if (distance < bestDistance) {
      best = node;
      bestDistance = distance;
    }
  }
  return best;
}

function neighboursOf(id) {
  const members = state.nodes.filter((node) => node.zone === (state.nodes.find((n) => n.id === id) || {}).zone);
  members.sort((a, b) => a.slot - b.slot);
  const index = members.findIndex((node) => node.id === id);
  if (index < 0) return new Set();
  return new Set([members[(index + 1) % members.length].id, members[(index - 1 + members.length) % members.length].id]);
}

/* ---------- animation ---------- */

const clock = new THREE.Clock();

function placeCamera() {
  const { theta, phi, radius } = cameraState;
  camera.position.set(
    radius * Math.sin(phi) * Math.sin(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.cos(theta));
  camera.lookAt(0, 0, 0);
}

function renderStatic() {
  placeCamera();
  hubHalo.material.opacity = 0.5;
  renderer.render(scene, camera);
  trace('frame calls=' + renderer.info.render.calls, 'tris=' + renderer.info.render.triangles,
    'canvas=' + renderer.domElement.width + 'x' + renderer.domElement.height,
    'cam=' + camera.position.toArray().map((v) => v.toFixed(1)).join(','));
}

function animate() {
  const dt = Math.min(0.05, clock.getDelta());
  state.idle += dt;

  if (!state.dragging && state.idle > 3.5 && !reduceMotion) cameraState.theta += dt * 0.075;
  cameraState.radius += (cameraState.goal - cameraState.radius) * Math.min(1, dt * 6);
  placeCamera();

  hubHalo.material.opacity = 0.45 + Math.sin(performance.now() * 0.0016) * 0.12;
  ringA.rotation.z += dt * 0.35;
  ringB.rotation.z -= dt * 0.22;

  const width = renderer.domElement.clientWidth;
  const height = renderer.domElement.clientHeight;
  const found = pickNode(width, height);
  state.hovered = found;

  if (found) {
    tooltip.hidden = false;
    tooltip.style.left = (state.pointer.x + renderer.domElement.getBoundingClientRect().left) + 'px';
    tooltip.style.top = (state.pointer.y + renderer.domElement.getBoundingClientRect().top) + 'px';
    const statusText = found.status === 'live' ? 'ออนไลน์' : found.status === 'stale' ? 'สัญญาณขาด' : 'ออฟไลน์';
    tooltip.replaceChildren();
    const title = document.createElement('strong');
    title.textContent = found.id;
    const first = document.createElement('span');
    first.textContent = `โซน · ${found.zone} · ${statusText}`;
    const second = document.createElement('span');
    second.textContent = ` heartbeat ${found.beats} ครั้ง · ล่าสุด ${found.age_s}s ที่แล้ว`;
    tooltip.append(title, first, document.createElement('br'), second);
    renderer.domElement.style.cursor = 'pointer';
  } else {
    tooltip.hidden = true;
    renderer.domElement.style.cursor = state.dragging ? 'grabbing' : 'grab';
  }

  const neighbours = state.focus ? neighboursOf(state.focus) : null;
  for (const node of state.nodes) {
    let alpha = 1;
    if (state.focus) {
      alpha = node.id === state.focus ? 1 : (neighbours.has(node.id) ? 0.8 : 0.18);
    }
    const hovered = found && found.id === node.id;
    node.sprite.material.opacity = alpha;
    node.sprite.scale.setScalar((node.status === 'live' ? 1.75 : 1.2) * (hovered ? 1.25 : 1));
    if (node.line) {
      const flash = Math.max(0, ((node.flashUntil || 0) - performance.now()) / 430);
      node.line.material.opacity = ((state.focus === node.id ? 0.95 : 0.5) + flash * 0.45) * (state.focus ? alpha : 1);
    }
  }

  if (!reduceMotion) {
    for (const pulse of state.pool) {
      if (!pulse.active) continue;
      pulse.t += dt / pulse.duration;
      if (pulse.t >= 1) {
        pulse.active = false;
        pulse.sprite.visible = false;
        continue;
      }
      const point = pulse.node.curve.getPoint(pulse.dir === 1 ? pulse.t : 1 - pulse.t);
      pulse.sprite.position.copy(point);
      const fade = Math.sin(pulse.t * Math.PI);
      pulse.sprite.material.opacity = 0.2 + 0.8 * fade;
      pulse.sprite.scale.setScalar((0.42 + 0.4 * fade) * pulse.strength);
    }
  }

  state.hubFlash = Math.max(0, state.hubFlash - dt * 2.4);
  ringA.scale.setScalar(1 + state.hubFlash * 0.28);
  hubHalo.material.opacity = 0.45 + Math.sin(performance.now() * 0.0016) * 0.12 + state.hubFlash * 0.3;

  renderer.render(scene, camera);
  requestAnimationFrame(animate);
}

resize();
window.addEventListener('resize', resize);
load();
primeEvents();
setInterval(load, 3000);
setInterval(pullEvents, 200);
if (STATIC) {
  placeCamera();
  renderer.render(scene, camera);
} else {
  requestAnimationFrame(animate);
}
