'use strict';

/* SUAY neural fabric — nodes as neurons, links as synapses, signals as pulses. */

const canvas = document.getElementById('fabric');
const ctx = canvas.getContext('2d');
const tooltip = document.getElementById('tooltip');
const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

const ZONE_COLORS = ['#7c5cff', '#22d3ee', '#34d399', '#f472b6', '#fbbf24', '#60a5fa'];
const STATUS_COLOR = { live: '#34d399', stale: '#fbbf24', offline: '#fb7185' };

const state = {
  nodes: [],
  links: [],
  zones: [],
  stats: {},
  hub: { x: 0, y: 0 },
  pulses: [],
  focus: null,
  pointer: { x: -999, y: -999, inside: false },
  lastHeartbeats: null,
  lastSampleAt: 0,
  rate: 0,
  width: 0,
  height: 0,
  dpr: 1,
};

/* ---------- data ---------- */

async function loadTopology() {
  try {
    const response = await fetch('/api/topology', { headers: { 'X-SUAY-Request': '1' } });
    if (!response.ok) throw new Error('HTTP ' + response.status);
    const data = await response.json();
    applyTopology(data);
    document.getElementById('stat-status').textContent =
      'อัปเดต ' + new Date().toLocaleTimeString('th-TH', { hour12: false });
  } catch (error) {
    document.getElementById('stat-status').textContent = 'โหลดข้อมูลไม่ได้: ' + error.message;
  }
}

function applyTopology(data) {
  const previous = new Map(state.nodes.map((node) => [node.id, node]));
  const zones = (data.zones || []).map((zone) => zone.name);
  state.zones = zones;
  state.links = data.links || [];
  state.stats = data.stats || {};

  state.nodes = (data.nodes || []).map((node, index) => {
    const zoneIndex = Math.max(0, zones.indexOf(node.zone));
    const siblings = (data.nodes || []).filter((other) => other.zone === node.zone);
    const slot = siblings.findIndex((other) => other.id === node.id);
    const old = previous.get(node.id);
    return {
      ...node,
      zoneIndex,
      slot,
      count: siblings.length,
      color: ZONE_COLORS[zoneIndex % ZONE_COLORS.length],
      x: old ? old.x : state.hub.x,
      y: old ? old.y : state.hub.y,
      seed: index * 0.618,
      phase: (old ? old.phase : Math.random() * Math.PI * 2),
    };
  });

  const live = state.nodes.filter((node) => node.status === 'live').length;
  document.getElementById('stat-live').textContent = String(live);
  document.getElementById('stat-total').textContent = String(state.nodes.length);

  const beats = Number(state.stats.heartbeats || 0);
  const now = performance.now();
  if (state.lastHeartbeats !== null && now > state.lastSampleAt) {
    const delta = Math.max(0, beats - state.lastHeartbeats);
    state.rate = delta / ((now - state.lastSampleAt) / 1000);
  }
  state.lastHeartbeats = beats;
  state.lastSampleAt = now;
  document.getElementById('stat-rate').textContent = state.rate ? state.rate.toFixed(1) : '0.0';
  document.getElementById('stat-zones').textContent = String(zones.length);
}

/* ---------- layout ---------- */

function resize() {
  state.dpr = Math.min(window.devicePixelRatio || 1, 2);
  state.width = canvas.clientWidth;
  state.height = canvas.clientHeight;
  canvas.width = Math.round(state.width * state.dpr);
  canvas.height = Math.round(state.height * state.dpr);
  ctx.setTransform(state.dpr, 0, 0, state.dpr, 0, 0);
  state.hub.x = state.width / 2;
  state.hub.y = state.height / 2;
}

function ringRadius(zoneIndex, zoneCount) {
  const base = Math.min(state.width, state.height) * 0.19;
  const step = Math.min(state.width, state.height) * 0.105;
  const spread = zoneCount > 1 ? Math.min(zoneIndex, 3) : 0;
  return base + step * spread;
}

function jitter(seed, index, spread) {
  const value = Math.abs(Math.sin(seed * 12.9898 + index * 78.233) * 43758.5453) % 1;
  return (value - 0.5) * 2 * spread;
}

function placeNodes(time) {
  const zoneCount = Math.max(1, state.zones.length);
  const spin = reduceMotion ? 0 : time * 0.00004;
  for (const node of state.nodes) {
    const baseRadius = ringRadius(node.zoneIndex, zoneCount);
    const radius = baseRadius + jitter(node.seed, 1, 10);
    const angle = (node.slot / Math.max(1, node.count)) * Math.PI * 2
      + node.zoneIndex * 0.55
      + jitter(node.seed, 2, 0.05)
      + spin * (node.zoneIndex % 2 === 0 ? 1 : -1)
      + Math.sin(time * 0.00025 + node.phase) * 0.012;
    node.x = state.hub.x + Math.cos(angle) * radius;
    node.y = state.hub.y + Math.sin(angle) * radius * 0.86;
  }
}

/* ---------- drawing ---------- */

function nodeColor(node) {
  if (node.status !== 'live') return STATUS_COLOR[node.status] || STATUS_COLOR.stale;
  return node.color;
}

function alphaFor(node) {
  if (!state.focus) return 1;
  if (node.id === state.focus) return 1;
  return isNeighbour(node.id) ? 0.75 : 0.14;
}

function isNeighbour(id) {
  return state.links.some((link) =>
    (link.source === state.focus && link.target === id) ||
    (link.target === state.focus && link.source === id));
}

function drawBackdrop(time) {
  const gradient = ctx.createRadialGradient(state.hub.x, state.hub.y, 0, state.hub.x, state.hub.y,
    Math.max(state.width, state.height) * 0.55);
  gradient.addColorStop(0, 'rgba(124, 92, 255, 0.10)');
  gradient.addColorStop(0.5, 'rgba(34, 211, 238, 0.03)');
  gradient.addColorStop(1, 'rgba(5, 7, 15, 0)');
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, state.width, state.height);

  const pulse = 1 + Math.sin(time * 0.0012) * 0.06;
  ctx.strokeStyle = 'rgba(124, 92, 255, 0.07)';
  ctx.lineWidth = 1;
  for (let ring = 1; ring <= 4; ring += 1) {
    ctx.beginPath();
    ctx.ellipse(state.hub.x, state.hub.y, ring * 46 * pulse, ring * 40 * pulse, 0, 0, Math.PI * 2);
    ctx.stroke();
  }
}

function hubPoint() {
  return state.hub;
}

function curveFor(node) {
  const hub = hubPoint();
  const midX = (node.x + hub.x) / 2;
  const midY = (node.y + hub.y) / 2;
  const dx = hub.x - node.x;
  const dy = hub.y - node.y;
  const length = Math.hypot(dx, dy) || 1;
  const bend = Math.min(46, length * 0.18) * (node.slot % 2 === 0 ? 1 : -1);
  return {
    x1: node.x,
    y1: node.y,
    cx: midX + (-dy / length) * bend,
    cy: midY + (dx / length) * bend,
    x2: hub.x,
    y2: hub.y,
  };
}

function quadPoint(curve, t) {
  const inv = 1 - t;
  return {
    x: inv * inv * curve.x1 + 2 * inv * t * curve.cx + t * t * curve.x2,
    y: inv * inv * curve.y1 + 2 * inv * t * curve.cy + t * t * curve.y2,
  };
}

function drawMesh() {
  ctx.save();
  ctx.setLineDash([2, 5]);
  ctx.lineWidth = 1;
  const groups = new Map();
  for (const node of state.nodes) {
    if (!groups.has(node.zone)) groups.set(node.zone, []);
    groups.get(node.zone).push(node);
  }
  for (const members of groups.values()) {
    members.sort((a, b) => a.slot - b.slot);
    const total = members.length;
    for (let index = 0; index < total; index += 1) {
      for (const step of [1, 2]) {
        if (total <= step) continue;
        const a = members[index];
        const b = members[(index + step) % total];
        const alpha = (0.26 / step) * Math.min(alphaFor(a), alphaFor(b));
        ctx.strokeStyle = hexToRgba(a.color, alpha);
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.quadraticCurveTo((a.x + b.x) / 2, (a.y + b.y) / 2 - 18, b.x, b.y);
        ctx.stroke();
      }
    }
  }
  // A few long-range fibres between zones: the cortex is not only local.
  for (let index = 0; index < state.nodes.length; index += 6) {
    const a = state.nodes[index];
    const b = state.nodes[(index * 13 + 7) % state.nodes.length];
    if (!a || !b || a.zone === b.zone) continue;
    ctx.strokeStyle = `rgba(148, 163, 255, ${(0.09 * Math.min(alphaFor(a), alphaFor(b))).toFixed(3)})`;
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.bezierCurveTo(a.x * 0.7 + b.x * 0.3, a.y * 0.7 + b.y * 0.3,
      a.x * 0.3 + b.x * 0.7, a.y * 0.3 + b.y * 0.7, b.x, b.y);
    ctx.stroke();
  }
  ctx.restore();
}

function drawUplinks() {
  ctx.save();
  ctx.setLineDash([5, 6]);
  for (const node of state.nodes) {
    const curve = curveFor(node);
    const focus = state.focus === node.id;
    const base = focus ? 0.9 : 0.34;
    const alpha = base * alphaFor(node);
    // Fade the fibre as it approaches the core: brighter at the neuron, softer at the hub.
    const gradient = ctx.createLinearGradient(curve.x1, curve.y1, curve.x2, curve.y2);
    gradient.addColorStop(0, hexToRgba(nodeColor(node), alpha));
    gradient.addColorStop(1, `rgba(124, 92, 255, ${(alpha * 0.35).toFixed(3)})`);
    ctx.strokeStyle = gradient;
    ctx.lineWidth = focus ? 1.8 : 1.15;
    ctx.beginPath();
    ctx.moveTo(curve.x1, curve.y1);
    ctx.quadraticCurveTo(curve.cx, curve.cy, curve.x2, curve.y2);
    ctx.stroke();
  }
  ctx.restore();
}

function spawnPulse() {
  if (reduceMotion || state.nodes.length === 0) return;
  const live = state.nodes.filter((node) => node.status === 'live');
  const pool = live.length ? live : state.nodes;
  const node = pool[Math.floor(Math.random() * pool.length)];
  state.pulses.push({
    nodeId: node.id,
    t: 0,
    speed: 0.35 + Math.random() * 0.45,
    inward: Math.random() > 0.28,
    size: 1.4 + Math.random() * 1.3,
  });
  if (state.pulses.length > 90) state.pulses.shift();
}

function drawPulses(dt) {
  ctx.save();
  for (const pulse of state.pulses) {
    const node = state.nodes.find((item) => item.id === pulse.nodeId);
    if (!node) { pulse.t = 2; continue; }
    pulse.t += dt * pulse.speed;
    if (pulse.t > 1) continue;
    const curve = curveFor(node);
    const point = quadPoint(curve, pulse.inward ? pulse.t : 1 - pulse.t);
    const alpha = Math.sin(pulse.t * Math.PI) * alphaFor(node);
    ctx.fillStyle = `rgba(180, 200, 255, ${(alpha * 0.9).toFixed(3)})`;
    ctx.shadowColor = node.color;
    ctx.shadowBlur = 10;
    ctx.beginPath();
    ctx.arc(point.x, point.y, pulse.size, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.restore();
  state.pulses = state.pulses.filter((pulse) => pulse.t <= 1);
}

function drawHub(time) {
  const { x, y } = state.hub;
  const breathe = 1 + Math.sin(time * 0.0016) * 0.08;
  const halo = ctx.createRadialGradient(x, y, 0, x, y, 74 * breathe);
  halo.addColorStop(0, 'rgba(124, 92, 255, 0.55)');
  halo.addColorStop(0.45, 'rgba(124, 92, 255, 0.18)');
  halo.addColorStop(1, 'rgba(124, 92, 255, 0)');
  ctx.fillStyle = halo;
  ctx.beginPath();
  ctx.arc(x, y, 74 * breathe, 0, Math.PI * 2);
  ctx.fill();

  const core = ctx.createRadialGradient(x, y, 0, x, y, 15);
  core.addColorStop(0, '#f4f0ff');
  core.addColorStop(0.35, '#b9a6ff');
  core.addColorStop(1, '#5b3df0');
  ctx.fillStyle = core;
  ctx.beginPath();
  ctx.arc(x, y, 13, 0, Math.PI * 2);
  ctx.fill();

  ctx.strokeStyle = 'rgba(233, 237, 255, 0.22)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.arc(x, y, 21, 0, Math.PI * 2);
  ctx.stroke();

  ctx.font = '10px "Segoe UI", "Noto Sans Thai", system-ui, sans-serif';
  ctx.textAlign = 'center';
  ctx.fillStyle = 'rgba(233, 237, 255, 0.5)';
  ctx.fillText('SUAY CORE', x, y + 38);
}

function drawNodes(time) {
  for (const node of state.nodes) {
    const alpha = alphaFor(node);
    const color = nodeColor(node);
    const radius = node.status === 'live' ? 3.4 : 2.6;
    const halo = ctx.createRadialGradient(node.x, node.y, 0, node.x, node.y, 13);
    halo.addColorStop(0, hexToRgba(color, 0.5 * alpha));
    halo.addColorStop(1, hexToRgba(color, 0));
    ctx.fillStyle = halo;
    ctx.beginPath();
    ctx.arc(node.x, node.y, 13, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = hexToRgba(color, alpha);
    ctx.beginPath();
    ctx.arc(node.x, node.y, radius, 0, Math.PI * 2);
    ctx.fill();

    if (node.status === 'live' && !reduceMotion) {
      const pulse = (Math.sin(time * 0.002 + node.phase) + 1) / 2;
      ctx.strokeStyle = hexToRgba(color, 0.22 * pulse * alpha);
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(node.x, node.y, 6 + pulse * 4, 0, Math.PI * 2);
      ctx.stroke();
    }
  }
}

function hexToRgba(hex, alpha) {
  const value = hex.replace('#', '');
  const r = parseInt(value.slice(0, 2), 16);
  const g = parseInt(value.slice(2, 4), 16);
  const b = parseInt(value.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha.toFixed(3)})`;
}

function drawZoneLabels() {
  ctx.save();
  ctx.font = '11px "Segoe UI", "Noto Sans Thai", system-ui, sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  state.zones.forEach((zone, index) => {
    const radius = ringRadius(index, state.zones.length) - 14;
    const x = state.hub.x;
    const y = state.hub.y - radius * 0.86 + 2;
    const width = ctx.measureText(zone).width + 14;
    ctx.fillStyle = 'rgba(5, 7, 15, 0.82)';
    ctx.beginPath();
    if (ctx.roundRect) ctx.roundRect(x - width / 2, y - 9, width, 18, 9);
    else ctx.rect(x - width / 2, y - 9, width, 18);
    ctx.fill();
    ctx.fillStyle = 'rgba(180, 190, 225, 0.72)';
    ctx.fillText(zone, x, y);
  });
  ctx.restore();
}

/* ---------- interaction ---------- */

function hitTest(px, py) {
  let best = null;
  let bestDistance = 18;
  for (const node of state.nodes) {
    const distance = Math.hypot(node.x - px, node.y - py);
    if (distance < bestDistance) {
      best = node;
      bestDistance = distance;
    }
  }
  return best;
}

canvas.addEventListener('mousemove', (event) => {
  const rect = canvas.getBoundingClientRect();
  state.pointer.x = event.clientX - rect.left;
  state.pointer.y = event.clientY - rect.top;
  const node = hitTest(state.pointer.x, state.pointer.y);
  if (!node) {
    tooltip.hidden = true;
    canvas.style.cursor = 'crosshair';
    return;
  }
  canvas.style.cursor = 'pointer';
  tooltip.hidden = false;
  tooltip.style.left = event.clientX + 'px';
  tooltip.style.top = event.clientY + 'px';
  const statusText = node.status === 'live' ? 'ออนไลน์' : node.status === 'stale' ? 'สัญญาณขาด' : 'ออฟไลน์';
  tooltip.innerHTML = '';
  const title = document.createElement('strong');
  title.textContent = node.id;
  const line1 = document.createElement('span');
  line1.textContent = `โซน · ${node.zone} · ${statusText}`;
  const line2 = document.createElement('span');
  line2.textContent = ` heartbeat ${node.beats} ครั้ง · ล่าสุด ${node.age_s}s ที่แล้ว`;
  tooltip.append(title, line1, document.createElement('br'), line2);
});

canvas.addEventListener('mouseleave', () => {
  tooltip.hidden = true;
  state.pointer.inside = false;
});

canvas.addEventListener('click', () => {
  const node = hitTest(state.pointer.x, state.pointer.y);
  state.focus = node ? (state.focus === node.id ? null : node.id) : null;
});

window.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') state.focus = null;
});

/* ---------- loop ---------- */

let lastFrame = performance.now();
let lastSpawn = 0;

function frame(now) {
  const dt = Math.min(0.05, (now - lastFrame) / 1000);
  lastFrame = now;
  ctx.clearRect(0, 0, state.width, state.height);
  placeNodes(now);
  drawBackdrop(now);
  drawMesh();
  drawUplinks();
  if (now - lastSpawn > 120) { spawnPulse(); lastSpawn = now; }
  drawPulses(dt);
  drawHub(now);
  drawNodes(now);
  drawZoneLabels();
  requestAnimationFrame(frame);
}

resize();
window.addEventListener('resize', resize);
loadTopology();
setInterval(loadTopology, 3000);
requestAnimationFrame(frame);
