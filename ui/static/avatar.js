/**
 * Vanessa - Interactive Anime Maid Avatar & Auto-Sleep Engine
 * Features:
 * - High quality Anime Maid SVG with lip-sync, blinking & emotions
 * - Auto-Sleep / Fade-Out dormancy to reduce RAM and CPU usage
 * - Dynamic wake on "Vanessa" keyword or user interaction
 */

class VanessaMaidAvatar {
  constructor(containerId) {
    this.container = document.getElementById(containerId);
    this.avatarPanel = document.querySelector(".avatar-container");
    this.mood = "happy";
    this.isTalking = false;
    this.blinkTimer = null;
    this.sleepTimeout = null;
    this.isDormant = false;

    this.render();
    this.startBlinkingLoop();
    this.resetInactivityTimer();
  }

  render() {
    this.container.innerHTML = `
      <svg class="anime-svg" viewBox="0 0 280 340" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <!-- Gradients -->
          <linearGradient id="hairGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="#475569" />
            <stop offset="50%" stop-color="#334155" />
            <stop offset="100%" stop-color="#1e293b" />
          </linearGradient>
          <linearGradient id="skinGrad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stop-color="#fff5ec" />
            <stop offset="100%" stop-color="#ffe6d9" />
          </linearGradient>
          <linearGradient id="eyeGrad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stop-color="#be185d" />
            <stop offset="50%" stop-color="#ec4899" />
            <stop offset="100%" stop-color="#f472b6" />
          </linearGradient>
          <filter id="maidGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        <!-- Back Hair -->
        <g id="back-hair">
          <path d="M 50,110 Q 15,220 40,300 Q 80,260 70,180 Z" fill="url(#hairGrad)" />
          <path d="M 230,110 Q 265,220 240,300 Q 200,260 210,180 Z" fill="url(#hairGrad)" />
        </g>

        <!-- Maid Dress Body -->
        <g id="body">
          <!-- Black dress base -->
          <path d="M 95,225 L 185,225 L 215,340 L 65,340 Z" fill="#0f172a" stroke="#f472b6" stroke-width="1.5" />
          <!-- White Frilled Apron Bib -->
          <path d="M 112,225 L 168,225 L 178,340 L 102,340 Z" fill="#ffffff" />
          <!-- Apron Straps -->
          <path d="M 112,225 L 98,270" stroke="#f1f5f9" stroke-width="4" />
          <path d="M 168,225 L 182,270" stroke="#f1f5f9" stroke-width="4" />
          <!-- Maid Ribbon / Bowtie -->
          <polygon points="140,230 120,248 160,248" fill="#e11d48" />
          <circle cx="140" cy="245" r="5" fill="#f43f5e" />
          <path d="M 140,245 L 128,272 L 140,265 L 152,272 Z" fill="#e11d48" />
        </g>

        <!-- Neck -->
        <rect x="128" y="195" width="24" height="32" rx="6" fill="url(#skinGrad)" />

        <!-- Head / Face -->
        <g id="head">
          <ellipse cx="140" cy="145" rx="58" ry="64" fill="url(#skinGrad)" />

          <!-- Blush -->
          <g id="blush" opacity="0.7">
            <ellipse cx="106" cy="164" rx="11" ry="5" fill="#f472b6" />
            <ellipse cx="174" cy="164" rx="11" ry="5" fill="#f472b6" />
          </g>

          <!-- Eyes Group -->
          <g id="eyes" class="eyes">
            <!-- Left Eye -->
            <g id="eye-left">
              <ellipse cx="110" cy="140" rx="14" ry="17" fill="#ffffff" />
              <ellipse cx="111" cy="141" rx="10" ry="14" fill="url(#eyeGrad)" />
              <circle cx="108" cy="136" r="4.5" fill="#ffffff" />
              <circle cx="114" cy="146" r="2" fill="#ffffff" />
              <path d="M 95,133 Q 111,122 127,132" fill="none" stroke="#0f172a" stroke-width="3.2" stroke-linecap="round" />
            </g>

            <!-- Right Eye -->
            <g id="eye-right">
              <ellipse cx="170" cy="140" rx="14" ry="17" fill="#ffffff" />
              <ellipse cx="169" cy="141" rx="10" ry="14" fill="url(#eyeGrad)" />
              <circle cx="167" cy="136" r="4.5" fill="#ffffff" />
              <circle cx="173" cy="146" r="2" fill="#ffffff" />
              <path d="M 153,132 Q 169,122 185,133" fill="none" stroke="#0f172a" stroke-width="3.2" stroke-linecap="round" />
            </g>
          </g>

          <!-- Nose -->
          <path d="M 140,152 L 139,157" stroke="#e0a98b" stroke-width="2" stroke-linecap="round" />

          <!-- Mouth -->
          <g id="mouth-container">
            <path id="mouth" class="mouth" d="M 134,175 Q 140,181 146,175" fill="none" stroke="#e11d48" stroke-width="2.5" stroke-linecap="round" />
          </g>
        </g>

        <!-- Front Hair & Bangs -->
        <g id="front-hair">
          <path d="M 82,115 Q 105,145 102,158 Q 115,120 130,110 Q 140,150 145,160 Q 155,125 175,115 Q 180,145 178,155 Q 198,120 198,115 C 205,65 75,65 82,115 Z" fill="url(#hairGrad)" />
          
          <!-- Maid Ahoge -->
          <path d="M 140,68 Q 130,28 152,30 Q 142,44 140,68" fill="url(#hairGrad)" stroke="#f472b6" stroke-width="1.5" />
          
          <!-- Side locks -->
          <path d="M 80,120 Q 68,175 72,230 Q 82,190 86,140 Z" fill="url(#hairGrad)" />
          <path d="M 200,120 Q 212,175 208,230 Q 198,190 194,140 Z" fill="url(#hairGrad)" />
        </g>

        <!-- White Maid Headdress / Frilled Brim -->
        <g id="maid-headdress">
          <!-- Lace arc -->
          <path d="M 85,85 Q 140,45 195,85" fill="none" stroke="#ffffff" stroke-width="16" stroke-linecap="round" opacity="0.95" />
          <path d="M 85,85 Q 140,45 195,85" fill="none" stroke="#f472b6" stroke-width="3" stroke-dasharray="4,4" />
          <!-- Left & Right Black Ribbon Knots -->
          <circle cx="82" cy="90" r="7" fill="#0f172a" />
          <path d="M 82,90 L 72,110" stroke="#0f172a" stroke-width="3" />
          <circle cx="198" cy="90" r="7" fill="#0f172a" />
          <path d="M 198,90 L 208,110" stroke="#0f172a" stroke-width="3" />
        </g>

        <!-- Dynamic Emote Icon -->
        <g id="emote-badge" transform="translate(195, 65)" style="display: none;">
          <circle cx="16" cy="16" r="16" fill="rgba(30, 41, 59, 0.95)" stroke="#f472b6" stroke-width="2" />
          <text id="emote-text" x="16" y="22" font-size="16" text-anchor="middle" fill="#fff">✨</text>
        </g>
      </svg>
    `;

    this.eyesEl = this.container.querySelector("#eyes");
    this.mouthEl = this.container.querySelector("#mouth");
    this.blushEl = this.container.querySelector("#blush");
    this.emoteBadge = this.container.querySelector("#emote-badge");
    this.emoteText = this.container.querySelector("#emote-text");
  }

  resetInactivityTimer() {
    clearTimeout(this.sleepTimeout);
    if (this.isDormant) {
      this.wakeUp();
    }
    // Auto-sleep after 25 seconds of silence/inactivity
    this.sleepTimeout = setTimeout(() => {
      this.enterSleepMode();
    }, 25000);
  }

  enterSleepMode() {
    this.isDormant = true;
    if (this.avatarPanel) {
      this.avatarPanel.classList.add("dormant");
    }
    document.getElementById("character-status").textContent = "En reposo (Ahorro de RAM)";
  }

  wakeUp() {
    this.isDormant = false;
    if (this.avatarPanel) {
      this.avatarPanel.classList.remove("dormant");
    }
    document.getElementById("character-status").textContent = "Atenta a su orden, Amo";
    this.showEmote("✨");
    setTimeout(() => this.hideEmote(), 3000);
  }

  startBlinkingLoop() {
    const doBlink = () => {
      if (this.eyesEl && !this.isDormant) {
        this.eyesEl.classList.add("blinking");
        setTimeout(() => {
          this.eyesEl.classList.remove("blinking");
        }, 160);
      }
      const nextBlink = Math.random() * 3500 + 2000;
      this.blinkTimer = setTimeout(doBlink, nextBlink);
    };
    this.blinkTimer = setTimeout(doBlink, 3000);
  }

  setMood(mood) {
    this.mood = mood;
    this.resetInactivityTimer();
    if (!this.mouthEl) return;

    if (mood === "happy") {
      this.mouthEl.setAttribute("d", "M 132,173 Q 140,186 148,173");
      this.blushEl.setAttribute("opacity", "0.95");
      this.showEmote("💖");
    } else if (mood === "serious") {
      this.mouthEl.setAttribute("d", "M 134,175 L 146,175");
      this.blushEl.setAttribute("opacity", "0.2");
      this.showEmote("⚡");
    } else if (mood === "thinking") {
      this.mouthEl.setAttribute("d", "M 133,176 L 147,174");
      this.blushEl.setAttribute("opacity", "0.4");
      this.showEmote("💡");
    } else if (mood === "playful") {
      this.mouthEl.setAttribute("d", "M 134,173 Q 140,184 148,175");
      this.blushEl.setAttribute("opacity", "0.85");
      this.showEmote("🎀");
    } else if (mood === "surprised") {
      this.mouthEl.setAttribute("d", "M 136,173 A 4,6 0 1,0 144,173 A 4,6 0 1,0 136,173");
      this.blushEl.setAttribute("opacity", "0.8");
      this.showEmote("❗");
    } else {
      // idle
      this.mouthEl.setAttribute("d", "M 134,175 Q 140,180 146,175");
      this.blushEl.setAttribute("opacity", "0.5");
      this.hideEmote();
    }
  }

  showEmote(emoji) {
    if (this.emoteBadge && this.emoteText) {
      this.emoteText.textContent = emoji;
      this.emoteBadge.style.display = "block";
    }
  }

  hideEmote() {
    if (this.emoteBadge) {
      this.emoteBadge.style.display = "none";
    }
  }

  startLipSync() {
    this.isTalking = true;
    this.resetInactivityTimer();
    if (this.mouthEl) {
      this.mouthEl.classList.add("talking");
    }
  }

  stopLipSync() {
    this.isTalking = false;
    if (this.mouthEl) {
      this.mouthEl.classList.remove("talking");
      this.setMood(this.mood);
    }
  }
}

// Global WebSocket & App Controller
let ws = null;
let avatar = null;

function initApp() {
  avatar = new VanessaMaidAvatar("avatar-pedestal");
  connectWebSocket();
  setupUIHandlers();

  // Clicking on pedestal wakes Vanessa up
  document.getElementById("avatar-pedestal").addEventListener("click", () => {
    avatar.resetInactivityTimer();
  });
}

function connectWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws`;

  ws = new WebSocket(wsUrl);

  ws.onopen = () => {
    document.getElementById("server-status-dot").classList.add("active");
    document.getElementById("server-status-text").textContent = "En línea";
  };

  ws.onclose = () => {
    document.getElementById("server-status-dot").classList.remove("active");
    document.getElementById("server-status-text").textContent = "Reconectando...";
    setTimeout(connectWebSocket, 2000);
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    handleServerMessage(data);
  };
}

function handleServerMessage(data) {
  const { type, payload } = data;

  if (type === "state_update") {
    if (payload.vision) {
      const v = payload.vision;
      let text = v.description || "";
      if (v.recognized_user && v.recognized_user !== "Ninguno") {
        document.getElementById("user-identity-badge").textContent = `👤 ${v.recognized_user}`;
      }
      if (v.detected_objects && v.detected_objects.length > 0) {
        document.getElementById("objects-summary-badge").textContent = `🗄️ ${v.detected_objects.slice(0, 3).join(", ")}`;
      }
      document.getElementById("perception-text").textContent = text;
      if (v.smiling) {
        avatar.setMood("happy");
      }
    }
    if (payload.wake_word_active) {
      document.getElementById("wake-status-dot").classList.add("active");
    } else {
      document.getElementById("wake-status-dot").classList.remove("active");
    }
  } else if (type === "assistant_speech_start") {
    avatar.wakeUp();
    avatar.setMood(payload.mood || "happy");
    avatar.startLipSync();
    document.getElementById("character-status").textContent = "Hablando con su Amo...";
  } else if (type === "assistant_speech_done") {
    avatar.stopLipSync();
    avatar.setMood("idle");
    document.getElementById("character-status").textContent = "Atenta y escuchando";
  } else if (type === "chat_message") {
    avatar.wakeUp();
    addChatBubble(payload.role, payload.content, payload.mood);
  }
}

function addChatBubble(role, text, mood) {
  const history = document.getElementById("chat-history");
  const bubble = document.createElement("div");
  bubble.className = `chat-bubble ${role}`;

  const name = role === "assistant" ? "Vanessa" : "Amo Víctor";
  bubble.innerHTML = `
    <div class="bubble-author">${name}</div>
    <div class="bubble-content">${escapeHtml(text)}</div>
  `;
  history.appendChild(bubble);
  history.scrollTop = history.scrollHeight;

  if (role === "assistant" && mood) {
    avatar.setMood(mood);
  }
}

function escapeHtml(str) {
  return str.replace(/[&<>'"]/g, 
    tag => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      "'": '&#39;',
      '"': '&quot;'
    }[tag] || tag)
  );
}

function setupUIHandlers() {
  const input = document.getElementById("user-input");
  const sendBtn = document.getElementById("send-btn");
  const voiceBtn = document.getElementById("voice-btn");

  const sendMessage = () => {
    const text = input.value.trim();
    if (!text) return;
    avatar.wakeUp();
    addChatBubble("user", text);
    input.value = "";
    if (ws && ws.readyState === WebSocket.OPEN) {
      avatar.setMood("thinking");
      document.getElementById("character-status").textContent = "Pensando...";
      ws.send(JSON.stringify({ type: "user_message", payload: { text } }));
    }
  };

  sendBtn.addEventListener("click", sendMessage);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendMessage();
  });

  // Manual Voice Input
  voiceBtn.addEventListener("click", () => {
    avatar.wakeUp();
    if (ws && ws.readyState === WebSocket.OPEN) {
      avatar.setMood("playful");
      document.getElementById("character-status").textContent = "Escuchando al Amo...";
      ws.send(JSON.stringify({ type: "start_voice_capture", payload: {} }));
    }
  });

  // Action Buttons
  document.getElementById("btn-screen-analysis").addEventListener("click", () => {
    avatar.wakeUp();
    avatar.setMood("thinking");
    document.getElementById("character-status").textContent = "Analizando su pantalla...";
    sendAction("system_command", { action: "analyze_screen" });
  });

  document.getElementById("btn-gen-excel").addEventListener("click", () => {
    avatar.wakeUp();
    sendAction("system_command", { action: "generate_excel" });
  });

  document.getElementById("btn-detect-objects").addEventListener("click", () => {
    avatar.wakeUp();
    sendAction("system_command", { action: "check_objects" });
  });

  document.getElementById("btn-enroll-face").addEventListener("click", () => {
    avatar.wakeUp();
    sendAction("system_command", { action: "enroll_face" });
  });

  document.getElementById("btn-shutdown").addEventListener("click", () => {
    if (confirm("¿Amo Víctor, desea realmente apagar la computadora?")) {
      sendAction("system_command", { action: "shutdown_pc" });
    }
  });

  // Hardware Controls
  document.getElementById("btn-kbd-on").addEventListener("click", () => {
    sendAction("system_command", { action: "keyboard_light", state: "on" });
  });
  document.getElementById("btn-kbd-off").addEventListener("click", () => {
    sendAction("system_command", { action: "keyboard_light", state: "off" });
  });
  document.getElementById("btn-wifi-toggle").addEventListener("click", () => {
    sendAction("system_command", { action: "wifi_toggle" });
  });
  document.getElementById("btn-bt-toggle").addEventListener("click", () => {
    sendAction("system_command", { action: "bluetooth_toggle" });
  });
  document.getElementById("btn-youtube").addEventListener("click", () => {
    sendAction("system_command", { action: "open_youtube" });
  });

  // Toggles
  document.getElementById("mic-toggle").addEventListener("change", (e) => {
    sendAction("toggle_hardware", { device: "microphone", enabled: e.target.checked });
  });
  document.getElementById("cam-toggle").addEventListener("change", (e) => {
    sendAction("toggle_hardware", { device: "camera", enabled: e.target.checked });
  });

  // Personality Modal
  const modal = document.getElementById("personality-modal");
  document.getElementById("open-settings-btn").addEventListener("click", () => {
    modal.style.display = "flex";
  });
  document.getElementById("close-modal-btn").addEventListener("click", () => {
    modal.style.display = "none";
  });
  document.getElementById("save-personality-btn").addEventListener("click", () => {
    const newName = document.getElementById("input-char-name").value.trim();
    const newPrompt = document.getElementById("input-system-prompt").value.trim();
    const newStyle = document.getElementById("input-speech-style").value.trim();

    sendAction("update_personality", {
      name: newName,
      system_prompt: newPrompt,
      speech_style: newStyle
    });

    document.getElementById("char-name-display").textContent = newName;
    modal.style.display = "none";
  });
}

function sendAction(action, payload) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: action, payload }));
  }
}

window.addEventListener("DOMContentLoaded", initApp);
