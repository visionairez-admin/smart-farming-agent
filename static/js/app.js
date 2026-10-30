/**
 * KrishiMitra Smart Farming Agent — Frontend Application
 * Handles chat, dashboard, crop browser, schemes, farm profile.
 */
"use strict";

const KM = (() => {
  /* ── State ─────────────────────────────────────────────────── */
  const state = {
    currentAgent: "auto",
    language: "en",
    pendingImage: null,      // { file, dataUrl }
    currentCropForModal: null,
    isDarkMode: false,
    isLoading: false,
    cropsData: [],
  };

  /* ── DOM Refs ──────────────────────────────────────────────── */
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => [...document.querySelectorAll(sel)];

  /* ── Helpers ───────────────────────────────────────────────── */
  function formatTime(iso) {
    const d = iso ? new Date(iso) : new Date();
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }

  function escapeHtml(text) {
    return text
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /**
   * Lightweight markdown → HTML:
   * **bold**, *italic*, `code`, numbered lists, bullet lists,
   * line breaks. Safe — no XSS vectors.
   */
  function renderMarkdown(text) {
    let html = escapeHtml(text);

    // Code blocks
    html = html.replace(/```[\s\S]*?```/g, (m) => {
      const code = m.replace(/^```[^\n]*\n?/, "").replace(/```$/, "");
      return `<pre class="bg-dark text-light rounded p-2 my-2" style="font-size:.8em;overflow-x:auto"><code>${code}</code></pre>`;
    });

    // Inline code
    html = html.replace(/`([^`]+)`/g, "<code class='text-success'>$1</code>");

    // Bold
    html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

    // Italic
    html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");

    // Numbered list (lines starting with "1. " etc.)
    html = html.replace(/((?:^\d+\. .+\n?)+)/gm, (block) => {
      const items = block.trim().split("\n").map((l) =>
        `<li>${l.replace(/^\d+\. /, "")}</li>`
      ).join("");
      return `<ol class="mb-2 ps-3">${items}</ol>`;
    });

    // Bullet list
    html = html.replace(/((?:^[-•*] .+\n?)+)/gm, (block) => {
      const items = block.trim().split("\n").map((l) =>
        `<li>${l.replace(/^[-•*] /, "")}</li>`
      ).join("");
      return `<ul class="mb-2 ps-3">${items}</ul>`;
    });

    // Double newline → paragraph break
    html = html.replace(/\n{2,}/g, "</p><p>");
    html = html.replace(/\n/g, "<br>");
    html = `<p>${html}</p>`;

    // Clean empty paragraphs
    html = html.replace(/<p><\/p>/g, "");
    return html;
  }

  function agentLabel(agentId) {
    const labels = {
      auto: "Smart Auto",
      crop: "Crop Advisory",
      weather: "Weather & Irrigation",
      pest: "Pest & Disease",
      market: "Market Insights",
      scheme: "Govt. Schemes",
    };
    return labels[agentId] || agentId;
  }

  function agentEmoji(agentId) {
    const icons = {
      auto: "⭐",
      crop: "🌱",
      weather: "🌦️",
      pest: "🐛",
      market: "💰",
      scheme: "📋",
    };
    return icons[agentId] || "🤖";
  }

  /* ── Toast ─────────────────────────────────────────────────── */
  function showToast(message, type = "success") {
    const toastEl = $("#toastMsg");
    const toastText = $("#toastText");
    toastEl.className = `toast align-items-center border-0 toast-${type}`;
    toastText.textContent = message;
    const toast = new bootstrap.Toast(toastEl, { delay: 3500 });
    toast.show();
  }

  /* ── Tab Navigation ────────────────────────────────────────── */
  function goToTab(tabId) {
    $$(".tab-section").forEach((s) => s.classList.remove("active-tab"));
    $$(".nav-tab").forEach((t) => t.classList.remove("active"));

    const section = $(`#tab-${tabId}`);
    if (section) section.classList.add("active-tab");

    const navLink = $(`.nav-tab[data-tab="${tabId}"]`);
    if (navLink) navLink.classList.add("active");

    // Lazy-load tab data
    if (tabId === "dashboard") loadDashboard();
    if (tabId === "crops") loadCrops();
    if (tabId === "schemes") loadSchemes();
    if (tabId === "profile") loadProfile();
  }

  /* ── API Health Check ──────────────────────────────────────── */
  async function checkApiHealth() {
    try {
      const res = await fetch("/api/health");
      const data = await res.json();
      const dot = $("#statusDot");
      if (data.watsonx_configured) {
        dot.className = "status-dot status-ok";
        dot.title = "watsonx.ai connected";
      } else {
        dot.className = "status-dot status-error";
        dot.title = "watsonx.ai not configured — check .env file";
      }
    } catch {
      const dot = $("#statusDot");
      dot.className = "status-dot status-error";
      dot.title = "API unreachable";
    }
  }

  /* ── Chat ──────────────────────────────────────────────────── */
  function appendMessage(role, text, agentUsed = null, timestamp = null) {
    const container = $("#chatMessages");
    const isUser = role === "user";
    const div = document.createElement("div");
    div.className = `message message-${isUser ? "user" : "bot"}`;

    const avatar = `<div class="message-avatar"><i class="bi bi-${isUser ? "person-fill" : "robot"}"></i></div>`;
    const tagHtml = (!isUser && agentUsed && agentUsed !== "auto")
      ? `<div class="agent-tag">${agentEmoji(agentUsed)} ${agentLabel(agentUsed)}</div>`
      : "";
    const bubbleContent = isUser ? `<p>${escapeHtml(text)}</p>` : renderMarkdown(text);
    const time = formatTime(timestamp);

    div.innerHTML = `
      ${avatar}
      <div class="message-content">
        ${tagHtml}
        <div class="message-bubble">${bubbleContent}</div>
        <div class="message-time">${time}</div>
      </div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
  }

  function appendImageMessage(dataUrl, caption = "") {
    const container = $("#chatMessages");
    const div = document.createElement("div");
    div.className = "message message-user";
    div.innerHTML = `
      <div class="message-avatar"><i class="bi bi-person-fill"></i></div>
      <div class="message-content">
        <div class="message-bubble" style="padding:.5rem">
          <img src="${dataUrl}" alt="Uploaded" style="max-width:220px;border-radius:8px;display:block;margin-bottom:.4rem" />
          ${caption ? `<p style="font-size:.82rem;margin:0">${escapeHtml(caption)}</p>` : ""}
        </div>
        <div class="message-time">${formatTime()}</div>
      </div>
    `;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
  }

  function setTyping(visible, agentId = null) {
    const el = $("#typingIndicator");
    if (visible) {
      el.classList.remove("d-none");
      const label = agentId
        ? `${agentEmoji(agentId)} ${agentLabel(agentId)} Agent is thinking...`
        : "KrishiMitra is thinking...";
      $("#typingAgent").textContent = label;
      el.parentElement.scrollTop = el.parentElement.scrollHeight;
    } else {
      el.classList.add("d-none");
    }
  }

  async function sendMessage() {
    const input = $("#chatInput");
    const message = input.value.trim();
    if ((!message && !state.pendingImage) || state.isLoading) return;

    state.isLoading = true;
    const sendBtn = $("#sendBtn");
    sendBtn.disabled = true;
    input.value = "";
    $("#charCount").textContent = "0/2000";
    resizeTextarea(input);

    let agentGuess = state.currentAgent;

    // ── Image path ─────────────────────────────────────────────
    if (state.pendingImage) {
      appendImageMessage(state.pendingImage.dataUrl, message || "Identify the pest or disease in this image");
      setTyping(true, "pest");

      const formData = new FormData();
      formData.append("image", state.pendingImage.file);
      formData.append("message", message || "Identify the pest or disease in this image");
      formData.append("language", state.language);

      clearImagePreview();

      try {
        const res = await fetch("/api/chat/image", { method: "POST", body: formData });
        const data = await res.json();
        setTyping(false);
        appendMessage("assistant", data.response || data.error, "pest", data.timestamp);
      } catch (err) {
        setTyping(false);
        appendMessage("assistant", "⚠️ Network error. Please try again.", "pest");
      }
      state.isLoading = false;
      sendBtn.disabled = false;
      input.focus();
      return;
    }

    // ── Text path ──────────────────────────────────────────────
    appendMessage("user", message);
    setTyping(true, agentGuess);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message,
          agent: state.currentAgent,
          language: state.language,
        }),
      });
      const data = await res.json();
      setTyping(false);

      if (data.error) {
        appendMessage("assistant", `⚠️ ${data.error}`, null);
      } else {
        appendMessage("assistant", data.response, data.agent_used, data.timestamp);
        // Update active agent label if auto-routed
        if (state.currentAgent === "auto" && data.agent_used) {
          $("#activeAgentLabel").textContent =
            `Smart Farming Assistant • ${agentLabel(data.agent_used)} Agent`;
        }
      }
    } catch (err) {
      setTyping(false);
      appendMessage(
        "assistant",
        "⚠️ I couldn't reach the server. Please check your connection and try again.",
        null
      );
    }

    state.isLoading = false;
    sendBtn.disabled = false;
    input.focus();
  }

  function resizeTextarea(el) {
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 140) + "px";
  }

  /* ── Image Handling ────────────────────────────────────────── */
  function handleImageUpload(file, previewContainer) {
    if (!file || !file.type.startsWith("image/")) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      state.pendingImage = { file, dataUrl: e.target.result };
      const container = document.getElementById(previewContainer);
      if (container) {
        container.innerHTML = `
          <div class="d-flex align-items-center gap-2">
            <img src="${e.target.result}" alt="preview" style="height:60px;border-radius:4px;object-fit:cover" />
            <div>
              <div style="font-size:.8rem;font-weight:600">${file.name}</div>
              <button class="btn btn-xs btn-outline-danger" style="font-size:.75rem;padding:.1rem .4rem" onclick="KM.clearImagePreview()">Remove</button>
            </div>
          </div>
        `;
        container.classList.remove("d-none");
      }
      // Also show in chat input hint
      const mPreview = $("#mobileImagePreview");
      if (mPreview) {
        mPreview.innerHTML = `
          <div class="d-flex align-items-center gap-2">
            <img src="${e.target.result}" alt="preview" style="height:50px;border-radius:4px" />
            <small class="text-success">📷 Image ready — ask about pests/diseases</small>
            <button class="btn btn-sm btn-outline-danger ms-auto" onclick="KM.clearImagePreview()">✕</button>
          </div>
        `;
        mPreview.classList.remove("d-none");
      }
    };
    reader.readAsDataURL(file);
  }

  function clearImagePreview() {
    state.pendingImage = null;
    const sidebarPreview = $("#imagePreview");
    if (sidebarPreview) { sidebarPreview.innerHTML = ""; sidebarPreview.classList.add("d-none"); }
    const mPreview = $("#mobileImagePreview");
    if (mPreview) { mPreview.innerHTML = ""; mPreview.classList.add("d-none"); }
    if ($("#imageUpload")) $("#imageUpload").value = "";
    if ($("#mobileImageUpload")) $("#mobileImageUpload").value = "";
  }

  /* ── Quick Ask ─────────────────────────────────────────────── */
  function askQuick(question) {
    goToTab("chat");
    const input = $("#chatInput");
    if (input) {
      input.value = question;
      resizeTextarea(input);
      $("#charCount").textContent = `${question.length}/2000`;
    }
    setTimeout(sendMessage, 100);
  }

  /* ── Agent Selection ───────────────────────────────────────── */
  function setAgent(agentId) {
    state.currentAgent = agentId;
    $$(".agent-btn").forEach((b) => {
      b.classList.toggle("active", b.dataset.agent === agentId);
    });
    const labels = {
      auto: "Smart Farming Assistant • Auto Mode",
      crop: "Crop Advisory Agent",
      weather: "Weather & Irrigation Agent",
      pest: "Pest & Disease Detection Agent",
      market: "Market Insights Agent",
      scheme: "Government Schemes Agent",
    };
    $("#activeAgentLabel").textContent = labels[agentId] || "Smart Farming Assistant";
  }

  /* ── Dashboard ─────────────────────────────────────────────── */
  async function loadDashboard() {
    try {
      const res = await fetch("/api/dashboard");
      const data = await res.json();

      $("#statTotalCrops").textContent = data.total_crops || 0;
      $("#statTotalSchemes").textContent = data.total_schemes || 0;
      $("#statCurrentSeason").textContent = data.current_season || "—";
      $("#statLocation").textContent = (data.farm_profile?.location || "—").split(",")[0];

      // Season crops chips
      const chipContainer = $("#seasonCropCards");
      chipContainer.innerHTML = "";
      (data.season_crops || []).forEach((crop) => {
        const chip = document.createElement("span");
        chip.className = "season-chip";
        chip.textContent = crop;
        chip.onclick = () => askQuick(`Tell me about growing ${crop} this season`);
        chipContainer.appendChild(chip);
      });

      // Farm profile summary
      const profile = data.farm_profile || {};
      const summaryEl = $("#farmProfileSummary");
      summaryEl.innerHTML = [
        ["👤 Name", profile.name],
        ["📍 Location", profile.location],
        ["🏞️ Land", `${profile.land_size} acres`],
        ["🌍 Soil", profile.soil_type],
        ["💧 Water", profile.water_source],
        ["🌾 Crops", profile.current_crops],
      ].map(([k, v]) => `
        <div class="ps-row">
          <span class="ps-key">${k}</span>
          <span class="ps-val">${v || "—"}</span>
        </div>
      `).join("");

      // MSP table
      const tbody = $("#mspTableBody");
      tbody.innerHTML = "";
      (data.msp_highlights || []).forEach((item) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td class="fw-semibold">${item.crop}</td>
          <td class="text-success fw-bold">₹${item.msp?.toLocaleString()}</td>
          <td>—</td>
          <td>—</td>
        `;
        tr.style.cursor = "pointer";
        tr.onclick = () => askQuick(`What is the MSP and market outlook for ${item.crop}?`);
        tbody.appendChild(tr);
      });

      // Enrich MSP table with season info if crops loaded
      if (state.cropsData.length > 0) enrichMspTable(data.msp_highlights || []);

    } catch (err) {
      console.error("Dashboard load error:", err);
    }
  }

  function enrichMspTable(highlights) {
    const rows = $$("#mspTableBody tr");
    rows.forEach((row, i) => {
      const crop = state.cropsData.find((c) =>
        c.name.toLowerCase().includes((highlights[i]?.crop || "").toLowerCase())
      );
      if (crop) {
        const cells = row.querySelectorAll("td");
        if (cells[2]) cells[2].textContent = crop.market_price_range || "—";
        if (cells[3]) cells[3].textContent = crop.season || "—";
      }
    });
  }

  /* ── Crop Browser ──────────────────────────────────────────── */
  async function loadCrops() {
    if (state.cropsData.length > 0) { renderCropCards(state.cropsData); return; }
    try {
      const res = await fetch("/api/crops");
      const data = await res.json();
      state.cropsData = data.crops || [];
      renderCropCards(state.cropsData);
    } catch (err) {
      console.error("Crops load error:", err);
    }
  }

  function renderCropCards(crops) {
    const container = $("#cropCards");
    if (!container) return;
    container.innerHTML = "";
    crops.forEach((crop) => {
      const col = document.createElement("div");
      col.className = "col-12 col-sm-6 col-md-4 col-xl-3";
      const seasonBadgeClass = {
        Kharif: "kharif-badge",
        Rabi: "rabi-badge",
        Annual: "annual-badge",
        Zaid: "zaid-badge",
      }[crop.season] || "kharif-badge";

      col.innerHTML = `
        <div class="crop-card h-100" data-crop="${escapeHtml(crop.name)}">
          <div class="d-flex align-items-start justify-content-between mb-2">
            <div>
              <div class="crop-card-name">${crop.name}</div>
              <div class="crop-card-local">${crop.hindi || ""} ${crop.marathi ? "/ " + crop.marathi : ""}</div>
            </div>
            <span class="crop-badge-season ${seasonBadgeClass}">${crop.season}</span>
          </div>
          <div class="crop-detail-row">
            <i class="bi bi-thermometer-half crop-detail-icon"></i>
            <span>${crop.temperature_range}</span>
          </div>
          <div class="crop-detail-row">
            <i class="bi bi-droplet-fill crop-detail-icon"></i>
            <span>${crop.water_requirement_mm} mm water</span>
          </div>
          <div class="crop-detail-row">
            <i class="bi bi-graph-up crop-detail-icon"></i>
            <span>Yield: ${crop.yield_qtl_ha} qtl/ha</span>
          </div>
          ${crop.msp_2024 ? `
          <div class="crop-detail-row">
            <i class="bi bi-currency-rupee crop-detail-icon"></i>
            <span>MSP: ₹${crop.msp_2024.toLocaleString()}/qtl</span>
          </div>` : ""}
          <div class="mt-2 pt-1 border-top" style="font-size:.78rem;color:var(--text-muted)">
            <i class="bi bi-info-circle me-1"></i>Click for full details
          </div>
        </div>
      `;
      col.querySelector(".crop-card").addEventListener("click", () => showCropModal(crop));
      container.appendChild(col);
    });
  }

  function filterCrops() {
    const searchVal = ($("#cropSearch")?.value || "").toLowerCase();
    const seasonVal = $("#seasonFilter")?.value || "";
    const filtered = state.cropsData.filter((c) => {
      const matchSearch = !searchVal ||
        c.name.toLowerCase().includes(searchVal) ||
        (c.hindi || "").includes(searchVal) ||
        (c.marathi || "").toLowerCase().includes(searchVal);
      const matchSeason = !seasonVal || c.season === seasonVal;
      return matchSearch && matchSeason;
    });
    renderCropCards(filtered);
  }

  function showCropModal(crop) {
    state.currentCropForModal = crop;
    $("#cropModalTitle").textContent = `${crop.name} (${crop.hindi || ""})`;

    const fertSched = crop.fertilizer_schedule || {};
    const fertRows = Object.entries(fertSched)
      .map(([k, v]) => `<li><strong>${k.replace(/_/g, " ")}:</strong> ${v}</li>`)
      .join("");

    const varieties = (crop.varieties || []).map((v) => `<span class="badge bg-light text-dark border me-1 mb-1">${v}</span>`).join("");
    const pests = (crop.pests || []).join(", ") || "—";
    const diseases = (crop.diseases || []).join(", ") || "—";
    const states = (crop.states || []).join(", ") || "—";

    $("#cropModalBody").innerHTML = `
      <div class="row g-3">
        <div class="col-12 col-md-6">
          <div class="detail-section">
            <h6><i class="bi bi-info-circle me-2"></i>Basic Info</h6>
            <table class="table table-sm table-bordered mb-0">
              <tr><th>Season</th><td>${crop.season}</td></tr>
              <tr><th>Duration</th><td>${crop.duration_days} days</td></tr>
              <tr><th>Temperature</th><td>${crop.temperature_range}</td></tr>
              <tr><th>Rainfall</th><td>${crop.rainfall_mm} mm</td></tr>
              <tr><th>Water Req.</th><td>${crop.water_requirement_mm} mm</td></tr>
              <tr><th>Soil Type</th><td>${(crop.soil_type || []).join(", ")}</td></tr>
            </table>
          </div>
          <div class="detail-section">
            <h6><i class="bi bi-geo-alt me-2"></i>Growing States</h6>
            <p class="mb-0" style="font-size:.88rem">${states}</p>
          </div>
        </div>
        <div class="col-12 col-md-6">
          <div class="detail-section">
            <h6><i class="bi bi-currency-rupee me-2"></i>Economics</h6>
            <table class="table table-sm table-bordered mb-0">
              <tr><th>MSP 2024</th><td class="text-success fw-bold">${crop.msp_2024 ? "₹" + crop.msp_2024.toLocaleString() + "/qtl" : "Not notified"}</td></tr>
              <tr><th>Market Range</th><td>${crop.market_price_range || "—"}</td></tr>
              <tr><th>Yield</th><td>${crop.yield_qtl_ha} qtl/ha</td></tr>
            </table>
          </div>
          <div class="detail-section">
            <h6><i class="bi bi-flower1 me-2"></i>Varieties</h6>
            <div>${varieties}</div>
          </div>
        </div>
        <div class="col-12">
          <div class="detail-section">
            <h6><i class="bi bi-capsule me-2"></i>Fertilizer Schedule</h6>
            <ul class="mb-0" style="font-size:.88rem">${fertRows}</ul>
          </div>
        </div>
        <div class="col-12 col-md-6">
          <div class="detail-section">
            <h6><i class="bi bi-droplet me-2"></i>Irrigation</h6>
            <p class="mb-0" style="font-size:.88rem">${crop.irrigation || "—"}</p>
          </div>
          <div class="detail-section">
            <h6><i class="bi bi-scissors me-2"></i>Harvesting Tips</h6>
            <p class="mb-0" style="font-size:.88rem">${crop.harvesting_tips || "—"}</p>
          </div>
        </div>
        <div class="col-12 col-md-6">
          <div class="detail-section">
            <h6><i class="bi bi-bug me-2"></i>Major Pests</h6>
            <p class="mb-0" style="font-size:.88rem">${pests}</p>
          </div>
          <div class="detail-section">
            <h6><i class="bi bi-virus me-2"></i>Major Diseases</h6>
            <p class="mb-0" style="font-size:.88rem">${diseases}</p>
          </div>
          <div class="detail-section">
            <h6><i class="bi bi-box-seam me-2"></i>Storage</h6>
            <p class="mb-0" style="font-size:.88rem">${crop.storage || "—"}</p>
          </div>
        </div>
      </div>
    `;

    const modal = new bootstrap.Modal($("#cropModal"));
    modal.show();
  }

  /* ── Scheme Cards ──────────────────────────────────────────── */
  async function loadSchemes() {
    const container = $("#schemeCards");
    if (!container || container.children.length > 0) return;
    try {
      const res = await fetch("/api/schemes");
      const data = await res.json();
      (data.schemes || []).forEach((scheme) => {
        const col = document.createElement("div");
        col.className = "col-12 col-md-6 col-xl-4";
        const docs = (scheme.documents || []).map((d) => `<span class="badge bg-light text-dark border me-1 mb-1">${d}</span>`).join("");

        col.innerHTML = `
          <div class="scheme-card h-100">
            <div class="scheme-card-header">
              <div class="scheme-icon"><i class="bi bi-bank2"></i></div>
              <div>
                <div class="scheme-name">${scheme.name}</div>
                <span class="scheme-type-badge">${scheme.type}</span>
              </div>
            </div>
            <div class="scheme-benefit">💰 ${scheme.benefit}</div>
            ${scheme.eligibility ? `<div class="scheme-detail"><i class="bi bi-check-circle-fill text-success me-2"></i><strong>Eligibility:</strong> ${scheme.eligibility}</div>` : ""}
            ${scheme.how_to_apply ? `<div class="scheme-detail"><i class="bi bi-arrow-right-circle me-2 text-primary"></i><strong>Apply:</strong> ${scheme.how_to_apply}</div>` : ""}
            ${scheme.helpline ? `<div class="scheme-detail"><i class="bi bi-telephone-fill me-2 text-warning"></i><strong>Helpline:</strong> ${scheme.helpline}</div>` : ""}
            ${docs ? `<div class="mt-2"><small class="text-muted d-block mb-1">Documents needed:</small>${docs}</div>` : ""}
            <button class="btn btn-sm btn-outline-success mt-3 w-100"
              onclick="KM.askQuick('How do I apply for ${scheme.name} and what are the requirements?')">
              <i class="bi bi-chat-dots-fill me-2"></i>Ask KrishiMitra
            </button>
          </div>
        `;
        container.appendChild(col);
      });
    } catch (err) {
      console.error("Schemes load error:", err);
    }
  }

  /* ── Farm Profile ──────────────────────────────────────────── */
  async function loadProfile() {
    try {
      const res = await fetch("/api/profile");
      const profile = await res.json();
      if ($("#pName")) $("#pName").value = profile.name || "";
      if ($("#pLocation")) $("#pLocation").value = profile.location || "";
      if ($("#pLandSize")) $("#pLandSize").value = profile.land_size || "";
      if ($("#pSoilType")) $("#pSoilType").value = profile.soil_type || "Black Cotton Soil";
      if ($("#pWaterSource")) $("#pWaterSource").value = profile.water_source || "Borewell";
      if ($("#pCurrentCrops")) $("#pCurrentCrops").value = profile.current_crops || "";
      if ($("#pSeason")) $("#pSeason").value = profile.season || "Kharif";
      if ($("#pFarmingType")) $("#pFarmingType").value = profile.farming_type || "Conventional";
      if ($("#pBudget")) $("#pBudget").value = profile.budget || "Medium";
      if ($("#pHasAadhaar")) $("#pHasAadhaar").value = profile.has_aadhaar || "Yes";
    } catch (err) {
      console.error("Profile load error:", err);
    }
  }

  async function saveProfile(e) {
    e.preventDefault();
    const profile = {
      name: $("#pName")?.value.trim() || "Farmer",
      location: $("#pLocation")?.value.trim() || "India",
      land_size: $("#pLandSize")?.value.trim() || "5",
      soil_type: $("#pSoilType")?.value || "Black Cotton Soil",
      water_source: $("#pWaterSource")?.value || "Borewell",
      current_crops: $("#pCurrentCrops")?.value.trim() || "",
      season: $("#pSeason")?.value || "Kharif",
      farming_type: $("#pFarmingType")?.value || "Conventional",
      budget: $("#pBudget")?.value || "Medium",
      has_aadhaar: $("#pHasAadhaar")?.value || "Yes",
      has_bank_account: "Yes",
    };

    try {
      const res = await fetch("/api/profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(profile),
      });
      const data = await res.json();
      if (data.success) {
        showToast("✅ Farm profile saved! Your recommendations will now be personalised.", "success");
        goToTab("dashboard");
      }
    } catch (err) {
      showToast("❌ Failed to save profile. Please try again.", "error");
    }
  }

  /* ── Dark Mode ─────────────────────────────────────────────── */
  function toggleTheme() {
    state.isDarkMode = !state.isDarkMode;
    document.documentElement.setAttribute("data-theme", state.isDarkMode ? "dark" : "light");
    const icon = $("#themeToggle i");
    if (icon) icon.className = state.isDarkMode ? "bi bi-sun-fill" : "bi bi-moon-stars-fill";
    localStorage.setItem("km-dark", state.isDarkMode ? "1" : "0");
  }

  function loadTheme() {
    const saved = localStorage.getItem("km-dark");
    if (saved === "1") toggleTheme();
  }

  /* ── Init ──────────────────────────────────────────────────── */
  function init() {
    loadTheme();
    checkApiHealth();

    // Tab navigation
    $$(".nav-tab").forEach((link) => {
      link.addEventListener("click", (e) => {
        e.preventDefault();
        goToTab(link.dataset.tab);
      });
    });

    // Theme toggle
    $("#themeToggle")?.addEventListener("click", toggleTheme);

    // Language selector
    $("#langSelect")?.addEventListener("change", (e) => {
      state.language = e.target.value;
    });

    // Agent buttons (all — sidebar + mobile off-canvas)
    document.addEventListener("click", (e) => {
      const btn = e.target.closest(".agent-btn");
      if (btn) {
        setAgent(btn.dataset.agent);
        // close off-canvas if open
        const offcanvas = bootstrap.Offcanvas.getInstance($("#mobileAgentPanel"));
        if (offcanvas) offcanvas.hide();
      }
    });

    // Quick buttons
    document.addEventListener("click", (e) => {
      const btn = e.target.closest(".quick-btn");
      if (btn) askQuick(btn.dataset.q);
    });

    // Mobile agent toggle
    $("#mobileAgentToggle")?.addEventListener("click", () => {
      const el = $("#mobileAgentPanel");
      if (el) new bootstrap.Offcanvas(el).show();
    });

    // Chat send button
    $("#sendBtn")?.addEventListener("click", sendMessage);

    // Chat input — auto-resize + char count + Ctrl+Enter
    const chatInput = $("#chatInput");
    if (chatInput) {
      chatInput.addEventListener("input", () => {
        resizeTextarea(chatInput);
        $("#charCount").textContent = `${chatInput.value.length}/2000`;
      });
      chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
          e.preventDefault();
          sendMessage();
        }
      });
    }

    // Clear chat
    $("#clearChatBtn")?.addEventListener("click", async () => {
      await fetch("/api/history/clear", { method: "POST" });
      const msgs = $("#chatMessages");
      if (msgs) msgs.innerHTML = "";
      appendMessage(
        "assistant",
        "Chat cleared. Jai Kisan! 🌾 How can I help you today?",
        null
      );
    });

    // Image uploads
    const imageUpload = $("#imageUpload");
    if (imageUpload) {
      imageUpload.addEventListener("change", (e) => {
        if (e.target.files[0]) handleImageUpload(e.target.files[0], "imagePreview");
      });
    }
    const mobileImageUpload = $("#mobileImageUpload");
    if (mobileImageUpload) {
      mobileImageUpload.addEventListener("change", (e) => {
        if (e.target.files[0]) handleImageUpload(e.target.files[0], "mobileImagePreview");
        // Switch to pest agent
        setAgent("pest");
      });
    }

    // Crop search / filter
    $("#cropSearch")?.addEventListener("input", filterCrops);
    $("#seasonFilter")?.addEventListener("change", filterCrops);

    // Crop modal "Ask" button
    $("#cropAskBtn")?.addEventListener("click", () => {
      if (state.currentCropForModal) {
        const cropName = state.currentCropForModal.name;
        bootstrap.Modal.getInstance($("#cropModal"))?.hide();
        askQuick(`Give me complete cultivation guide for ${cropName} including fertilizer schedule, irrigation, and harvesting`);
      }
    });

    // Profile form
    $("#profileForm")?.addEventListener("submit", saveProfile);
  }

  /* ── Public API ────────────────────────────────────────────── */
  return { init, goToTab, askQuick, clearImagePreview };
})();

/* ── Bootstrap ─────────────────────────────────────────────── */
document.addEventListener("DOMContentLoaded", KM.init);
