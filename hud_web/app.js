// Limbo — avatar engine asli + chat bubble minimalis.
import {
  makeConfig,
  createRuntime,
  createStateMachine,
  buildModel,
  makeMorphGenerators,
  makeTrail,
  createRenderer,
} from "./vendor/grok-player.js";

const stage = document.getElementById("stage");
const chat = document.getElementById("chat");
const chatAvatar = document.getElementById("chatAvatar");
const avatarHost = document.getElementById("avatar");
const logBox = document.getElementById("log");
const input = document.getElementById("input");
const form = document.getElementById("form");

const SIZE = 220;
// Hitam putih: badan hitam, mata putih. Glow biru tipis tetap dipakai supaya
// avatar tidak tenggelam di desktop gelap (shadow saja tidak cukup).
const THEME = { ink: [0, 0, 0], spot: [1, 1, 1], cutout: false };
const STATE_MAP = {
  idle: "idle", pending: "thinking", thinking: "thinking",
  tool: "working", working: "working", confirm: "waiting",
  cloud: "thinking", local_llm: "thinking", reject: "alerting",
  offline: "failed", error: "failed",
};

let runtime = null;
let machine = null;

/* ---------- chat ---------- */
function bubble(text, kind = "") {
  const line = document.createElement("div");
  line.className = `bubble ${kind}`.trim();
  line.textContent = text;
  logBox.appendChild(line);
  logBox.scrollTop = logBox.scrollHeight;
}

function toggleChat(force) {
  const open = force ?? chat.classList.contains("hidden");
  chat.classList.toggle("hidden", !open);
  stage.classList.toggle("hidden", open);
  if (open) {
    chatAvatar.appendChild(avatarHost);
    input.focus();
  } else {
    stage.appendChild(avatarHost);
  }
}
window.limboToggleChat = toggleChat;

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  bubble(text, "user");
  applyState("thinking");
  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const data = await response.json();
    const kind = data.route === "reject" ? "warn" : data.route === "offline" ? "error" : "";
    bubble(data.reply || "(kosong)", kind);
    applyState(data.route || "working");
  } catch (error) {
    bubble(`Gagal: ${error.message}`, "error");
    applyState("error");
  }
});

bubble("Halo. Ada yang bisa saya bantu?", "system");

/* ---------- avatar ---------- */
function applyState(name) {
  if (!machine) return;
  machine.setState(STATE_MAP[name] || "idle");
}

async function boot() {
  const response = await fetch("./vendor/grok-recipes.json");
  if (!response.ok) throw new Error(`recipes HTTP ${response.status}`);
  const recipes = await response.json();
  const config = makeConfig(recipes);
  const morph = makeMorphGenerators(config);
  const trail = makeTrail(config);
  runtime = createRuntime(config, { zoomMul: 1 });
  machine = createStateMachine(config, runtime, "idle", { seed: 1 });

  const renderer = createRenderer(document, "limbo", SIZE, config);
  avatarHost.appendChild(renderer.svg);

  const render = () => {
    renderer.render(buildModel(runtime.frame(), THEME, SIZE, config, morph, trail));
  };

  let last = performance.now();
  const loop = (now) => {
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    machine.advance(dt);
    runtime.advance(dt);
    render();
    requestAnimationFrame(loop);
  };
  requestAnimationFrame(loop);

  window.addEventListener("pointermove", (event) => {
    const rect = renderer.svg.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    const y = ((event.clientY - rect.top) / rect.height) * 2 - 1;
    runtime.setGaze([Math.max(-1, Math.min(1, x)), Math.max(-1, Math.min(1, y))]);
  }, { passive: true });

  // Animasi mengikuti status AI saja (tidak diputar bergiliran).
  pollState();
}

async function pollState() {
  try {
    const response = await fetch("/api/state");
    const data = await response.json();
    applyState(data.state || data.route || "idle");
  } catch (_error) { /* abaikan */ }
  setTimeout(pollState, 400);
}

boot().catch((error) => bubble(`Avatar error: ${error.message}`, "error"));
