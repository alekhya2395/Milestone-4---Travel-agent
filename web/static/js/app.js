(function () {
  "use strict";

  const AGENTS = [
    "request_parser",
    "destination_research",
    "accommodation",
    "transport",
    "budget",
    "itinerary_composer",
    "validator",
  ];

  const $ = (sel) => document.querySelector(sel);

  const stubMode = $("#stub-mode");
  const tripRequest = $("#trip-request");
  const planBtn = $("#plan-btn");
  const micBtn = $("#mic-btn");
  const panelToggle = $("#trip-ai-panel-toggle");
  const closePanel = $("#close-panel");
  const tripAiPanel = $("#trip-ai-panel");
  const loading = $("#loading");
  const loadingText = $("#loading-text");
  const planStatus = $("#plan-status");
  const tripSummary = $("#trip-summary");
  const itinerarySummary = $("#itinerary-summary");
  const mainEl = $(".main");
  const transcript = $("#transcript");
  const tripAiHint = $("#trip-ai-hint");
  const agentProgress = $("#agent-progress");
  const agentList = $("#agent-list");
  const voiceStatusText = $("#voice-status-text");
  const voiceDot = $("#voice-dot");
  const voiceWave = $("#voice-wave");
  const readSummaryBtn = $("#read-summary-btn");

  let lastState = null;
  let voiceAgent = null;
  let planning = false;

  function initVoiceAgent() {
    if (typeof TripVoiceAgent === "undefined") return;

    voiceAgent = new TripVoiceAgent({
      onTranscript(text, isPrompt) {
        if (isPrompt) {
          transcript.innerHTML = `<em class="voice-prompt">${escapeHtml(text)}</em>`;
        } else {
          transcript.textContent = text;
          tripRequest.value = text;
        }
      },
      onStateChange(state) {
        micBtn.classList.toggle("listening", state === "listening");
        $("#trip-ai")?.classList.toggle("speaking", state === "speaking");
        voiceWave.classList.toggle("hidden", state !== "listening");
        voiceDot.dataset.state = state;

        const labels = {
          idle: "Tap TripAI or the mic to speak",
          listening: "Listening…",
          speaking: "TripAI is speaking…",
          processing: "Processing…",
        };
        voiceStatusText.textContent = labels[state] || labels.idle;
        tripAiHint.textContent =
          state === "listening" ? "listening…" : state === "speaking" ? "speaking…" : "ask about this trip";
      },
      onConfirmed(rawRequest) {
        tripRequest.value = rawRequest;
        runPlan(rawRequest, { fromVoice: true });
      },
      onError(message) {
        voiceStatusText.textContent = message;
        openPanel();
      },
      onPipelineStep(index) {
        const li = agentList.querySelector(`[data-agent="${AGENTS[index]}"]`);
        if (li) {
          li.textContent = `● ${formatAgentName(AGENTS[index])}`;
          li.classList.add("active");
        }
        AGENTS.slice(0, index).forEach((name) => {
          const prev = agentList.querySelector(`[data-agent="${name}"]`);
          if (prev) {
            prev.textContent = `✓ ${formatAgentName(name)}`;
            prev.classList.add("done");
            prev.classList.remove("active");
          }
        });
      },
    });
  }

  async function activateVoice() {
    openPanel();
    if (!voiceAgent) initVoiceAgent();
    if (!voiceAgent?.sttSupported) {
      transcript.textContent = "Speech not supported here — type your trip below.";
      tripRequest.focus();
      return;
    }

    const existing = tripRequest.value.trim();
    if (existing && voiceAgent.analyzeRequest(existing).missing.length > 0) {
      await voiceAgent.resumeClarification(existing);
    } else if (voiceAgent.isActive()) {
      voiceAgent.stop();
    } else {
      await voiceAgent.startIntake();
    }
  }

  function openPanel() {
    const tripAi = $("#trip-ai");
    if (tripAi) {
      const rect = tripAi.getBoundingClientRect();
      tripAiPanel.style.left = `${rect.left}px`;
      tripAiPanel.style.width = `${Math.max(rect.width, 320)}px`;
      tripAiPanel.style.bottom = `${window.innerHeight - rect.top + 12}px`;
    }
    tripAiPanel.classList.remove("hidden");
  }

  function closePanelFn() {
    voiceAgent?.stop();
    tripAiPanel.classList.add("hidden");
  }

  function switchView(view) {
    document.querySelectorAll(".nav-item").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.view === view);
    });
    document.querySelectorAll(".view").forEach((sec) => {
      sec.classList.toggle("active", sec.id === `view-${view}`);
    });
    if (mainEl) {
      mainEl.scrollTop = 0;
    }
  }

  function showLoading(msg) {
    loadingText.textContent = msg || "Seven agents are planning your trip…";
    loading.classList.remove("hidden");
  }

  function hideLoading() {
    loading.classList.add("hidden");
  }

  function showStatus(msg, isError) {
    planStatus.textContent = msg;
    planStatus.classList.remove("hidden", "error");
    if (isError) planStatus.classList.add("error");
  }

  function resetAgentProgress() {
    agentProgress.classList.remove("hidden");
    agentList.innerHTML = AGENTS.map(
      (a) => `<li data-agent="${a}">○ ${formatAgentName(a)}</li>`
    ).join("");
  }

  function markAgentsComplete() {
    AGENTS.forEach((name) => {
      const li = agentList.querySelector(`[data-agent="${name}"]`);
      if (li) {
        li.textContent = `✓ ${formatAgentName(name)}`;
        li.classList.add("done");
        li.classList.remove("active");
      }
    });
  }

  function formatAgentName(name) {
    return name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }

  async function runPlan(request, opts = {}) {
    if (planning) return;
    const text = (request || tripRequest.value).trim();
    if (!text) return;

    planning = true;
    tripRequest.value = text;
    closePanelFn();
    showLoading();
    resetAgentProgress();
    readSummaryBtn.classList.add("hidden");

    if (opts.fromVoice && voiceAgent) {
      voiceAgent.startPipelineNarration((i) => {
        loadingText.textContent = `Agent ${i + 1} of 7 working…`;
      });
    } else {
      AGENTS.forEach((name, i) => {
        setTimeout(() => {
          const li = agentList.querySelector(`[data-agent="${name}"]`);
          if (li) {
            li.textContent = `✓ ${formatAgentName(name)}`;
            li.classList.add("done");
          }
        }, 400 + i * 350);
      });
    }

    try {
      const res = await fetch("/api/plan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ request: text, stub: stubMode.checked }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(
          typeof data.detail === "string" ? data.detail : "Planning failed"
        );
      }

      lastState = data;
      renderAll(data);
      markAgentsComplete();

      const dests = data.trip_spec?.destinations?.join(", ") || "your trip";
      showStatus(
        `Plan ready — ${dests} (${data.metadata?.run_id?.slice(0, 8) || "demo"})`
      );
      switchView("itinerary");
      readSummaryBtn.classList.remove("hidden");
    } catch (err) {
      showStatus(err.message || "Something went wrong", true);
    } finally {
      voiceAgent?.stopPipelineNarration();
      hideLoading();
      planning = false;
    }
  }

  function renderAll(state) {
    renderOverview(state);
    renderItinerary(state);
    renderAccommodation(state);
    renderTransport(state);
    renderBudget(state);
  }

  function renderTripSummaryHtml(state) {
    const spec = state.trip_spec;
    const draft = state.draft_itinerary;
    if (!spec && !draft) return null;

    const dests = spec?.destinations?.join(" → ") || "—";
    const days = spec?.duration_days || draft?.days?.length || "—";
    const budget = spec?.budget_amount
      ? `$${spec.budget_amount.toLocaleString()} ${spec.budget_currency || "USD"}`
      : "—";
    const summary = draft?.summary || "";

    return `
      <h3>${escapeHtml(dests)}</h3>
      <p><strong>${days} days</strong> · Budget ${escapeHtml(String(budget))}</p>
      ${summary ? `<p style="margin-top:12px">${escapeHtml(summary)}</p>` : ""}
      <p style="margin-top:8px;font-size:0.8rem;color:var(--text-muted)">
        Validation: ${escapeHtml(state.validation_status || "—")}
      </p>
    `;
  }

  function renderOverview(state) {
    const html = renderTripSummaryHtml(state);
    if (!html) {
      tripSummary.classList.add("hidden");
      return;
    }

    tripSummary.classList.remove("hidden");
    tripSummary.innerHTML = html;
  }

  function renderItinerary(state) {
    const el = $("#itinerary-content");
    const days = state.draft_itinerary?.days || [];
    const summaryHtml = renderTripSummaryHtml(state);
    const md = state.markdown || "";

    if (itinerarySummary) {
      if (summaryHtml) {
        itinerarySummary.classList.remove("hidden");
        itinerarySummary.innerHTML = summaryHtml;
      } else {
        itinerarySummary.classList.add("hidden");
      }
    }

    if (!days.length && !md) {
      el.className = "panel-content scroll-panel empty-state";
      el.textContent = "Plan a trip to see your day-by-day schedule.";
      return;
    }

    el.className = "panel-content scroll-panel";
    const daySection = extractMarkdownSection(md, "Day-by-day plan") || md;
    el.innerHTML = `
      ${renderDayCards(days)}
      <div class="markdown-body">${markdownToHtml(daySection)}</div>
    `;
  }

  function renderAccommodation(state) {
    const el = $("#accommodation-content");
    const cities = state.accommodation_options?.cities || [];
    const md = extractMarkdownSection(state.markdown || "", "Where to stay");

    let html = "";
    if (cities.length) {
      html += cities.map((c) => {
        const tiers = (c.lodging_tiers || [])
          .map((t) => `<span class="tag">${escapeHtml(t.tier)}: $${t.estimated_nightly_min}–$${t.estimated_nightly_max}/night</span>`)
          .join("");
        return `
        <div class="city-block">
          <h4>${escapeHtml(c.city)}</h4>
          <div class="tag-list">${(c.neighborhoods || []).map((n) => `<span class="tag">${escapeHtml(n)}</span>`).join("")}</div>
          <div class="tag-list">${tiers}</div>
          ${c.notes ? `<p style="font-size:0.875rem;color:var(--text-variant)">${escapeHtml(c.notes)}</p>` : ""}
        </div>`;
      }).join("");
    }
    if (md) html += `<div class="markdown-body">${markdownToHtml(md)}</div>`;

    if (!html) {
      el.className = "panel-content scroll-panel empty-state";
      el.textContent = "Neighborhood and lodging recommendations appear here.";
      return;
    }
    el.className = "panel-content scroll-panel";
    el.innerHTML = html;
  }

  function renderTransport(state) {
    const el = $("#transport-content");
    const plan = state.transport_plan;
    const md = extractMarkdownSection(state.markdown || "", "Getting around");

    let html = "";
    if (plan) {
      const legs = [...(plan.inter_city_legs || []), ...(plan.airport_transfers || [])];
      html += legs.map((l) => `
      <div class="leg-row">
        <div>
          <strong>${escapeHtml(l.from_location)} → ${escapeHtml(l.to_location)}</strong>
          <div style="font-size:0.85rem;color:var(--text-muted)">${escapeHtml(l.mode)} · ${escapeHtml(l.estimated_duration)}</div>
        </div>
        <span class="amount" style="color:var(--secondary)">$${l.estimated_cost}</span>
      </div>`).join("");
      (plan.local_transit || []).forEach((n) => {
        html += `<div class="city-block"><h4>${escapeHtml(n.city)}</h4><ul>${(n.notes || []).map((x) => `<li>${escapeHtml(x)}</li>`).join("")}</ul></div>`;
      });
    }
    if (md) html += `<div class="markdown-body">${markdownToHtml(md)}</div>`;

    if (!html) {
      el.className = "panel-content scroll-panel empty-state";
      el.textContent = "Inter-city and local transport plans appear here.";
      return;
    }
    el.className = "panel-content scroll-panel";
    el.innerHTML = html;
  }

  function renderBudget(state) {
    const el = $("#budget-content");
    const budget = state.budget_breakdown;
    const md = extractMarkdownSection(state.markdown || "", "Budget");

    let html = "";
    if (budget?.line_items?.length) {
      const lines = budget.line_items.map((item) => `
      <div class="budget-line">
        <span>${escapeHtml(item.category)}${item.notes ? ` — ${escapeHtml(item.notes)}` : ""}</span>
        <span class="amount">$${item.amount.toLocaleString()}</span>
      </div>`).join("");
      html = `
      <div class="budget-total">$${budget.total_estimated.toLocaleString()} ${budget.currency || "USD"}</div>
      ${lines}
      ${budget.over_budget ? `<p class="over-budget">Over budget ceiling</p>` : ""}
      ${(budget.tradeoff_suggestions || []).map((s) => `<p style="font-size:0.85rem;color:var(--text-variant)">• ${escapeHtml(s)}</p>`).join("")}`;
    }
    if (md) html += `<div class="markdown-body">${markdownToHtml(md)}</div>`;

    if (!html) {
      el.className = "panel-content scroll-panel empty-state";
      el.textContent = "Budget breakdown appears here.";
      return;
    }
    el.className = "panel-content scroll-panel";
    el.innerHTML = html;
  }

  function escapeHtml(str) {
    const d = document.createElement("div");
    d.textContent = str == null ? "" : String(str);
    return d.innerHTML;
  }

  function inlineMarkdown(text) {
    return String(text).split(/(\*\*.+?\*\*)/g).map((part) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return `<strong>${escapeHtml(part.slice(2, -2))}</strong>`;
      }
      return escapeHtml(part);
    }).join("");
  }

  function markdownToHtml(md) {
    if (!md) return "";
    let html = "";
    let inList = false;
    for (const raw of md.split("\n")) {
      const line = raw.trimEnd();
      if (line.startsWith("## ")) {
        if (inList) { html += "</ul>"; inList = false; }
        html += `<h3 class="md-h2">${inlineMarkdown(line.slice(3))}</h3>`;
      } else if (line.startsWith("### ")) {
        if (inList) { html += "</ul>"; inList = false; }
        html += `<h4 class="md-h3">${inlineMarkdown(line.slice(4))}</h4>`;
      } else if (line.startsWith("- ")) {
        if (!inList) { html += '<ul class="md-list">'; inList = true; }
        html += `<li>${inlineMarkdown(line.slice(2))}</li>`;
      } else if (line.trim() === "") {
        if (inList) { html += "</ul>"; inList = false; }
      } else {
        if (inList) { html += "</ul>"; inList = false; }
        html += `<p class="md-p">${inlineMarkdown(line)}</p>`;
      }
    }
    if (inList) html += "</ul>";
    return html;
  }

  function extractMarkdownSection(md, title) {
    if (!md) return "";
    const re = new RegExp(`## ${title}[\\s\\S]*?(?=\\n## |$)`, "i");
    const m = md.match(re);
    return m ? m[0] : "";
  }

  function renderDayCards(days) {
    if (!days.length) return "";
    return `<div class="day-cards">${days.map((d) => `
      <div class="day-card">
        <h4>Day ${d.day} — ${escapeHtml(d.city)} · ${escapeHtml(d.theme)}</h4>
        ${d.logistics ? `<p class="day-logistics">${escapeHtml(d.logistics)}</p>` : ""}
        <ul>${(d.activities || []).map((a) => `<li>${escapeHtml(a)}</li>`).join("")}</ul>
      </div>`).join("")}</div>`;
  }

  document.querySelectorAll(".nav-item").forEach((btn) => {
    btn.addEventListener("click", () => {
      closePanelFn();
      switchView(btn.dataset.view);
    });
  });

  document.querySelectorAll(".dest-card").forEach((card) => {
    card.addEventListener("click", () => {
      const prompt = card.dataset.prompt;
      if (prompt) {
        tripRequest.value = prompt;
        runPlan(prompt);
      }
    });
  });

  planBtn.addEventListener("click", () => {
    const text = tripRequest.value.trim();
    if (text && voiceAgent?.analyzeRequest(text).missing.length > 0) {
      openPanel();
      void voiceAgent.resumeClarification(text);
      return;
    }
    runPlan();
  });

  micBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    void activateVoice();
  });

  $("#trip-ai").addEventListener("click", (e) => {
    if (e.target.closest(".trip-ai-mic") || e.target.closest(".trip-ai-expand")) return;
    void activateVoice();
  });

  panelToggle.addEventListener("click", (e) => {
    e.stopPropagation();
    openPanel();
  });

  closePanel.addEventListener("click", closePanelFn);

  readSummaryBtn.addEventListener("click", () => {
    if (lastState && voiceAgent) {
      void voiceAgent.readSummary(lastState);
    }
  });

  $("#global-search").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && e.target.value.trim()) {
      tripRequest.value = e.target.value.trim();
      runPlan(e.target.value.trim());
    }
  });

  initVoiceAgent();
})();
