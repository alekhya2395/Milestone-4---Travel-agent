/**
 * TripAI voice layer — front-end only.
 * Captures speech, clarifies missing fields, narrates pipeline, reads summaries.
 * Hands confirmed text to the app as raw_request (same as typed input).
 */
(function (global) {
  "use strict";

  const VoiceState = {
    IDLE: "idle",
    SPEAKING: "speaking",
    LISTENING: "listening",
    PROCESSING: "processing",
  };

  const CLARIFY_PROMPTS = {
    duration: "How many days is your trip?",
    budget: "What is your total budget in US dollars?",
  };

  const PIPELINE_NARRATION = [
    "Parsing your request.",
    "Researching destinations.",
    "Finding accommodation options.",
    "Planning transport routes.",
    "Calculating your budget.",
    "Composing your itinerary.",
    "Running final validation.",
  ];

  class TripVoiceAgent {
    /**
     * @param {object} hooks
     * @param {(text: string, isPrompt?: boolean) => void} hooks.onTranscript
     * @param {(state: string, detail?: string) => void} hooks.onStateChange
     * @param {(rawRequest: string) => void} hooks.onConfirmed
     * @param {(message: string) => void} [hooks.onError]
     * @param {(agentIndex: number) => void} [hooks.onPipelineStep]
     */
    constructor(hooks) {
      this.hooks = hooks;
      this.state = VoiceState.IDLE;
      this.pendingRequest = "";
      this.clarificationQueue = [];
      this.clarificationAnswers = {};
      this._listenMode = null;
      this._currentClarifyField = null;
      this._finalTranscript = "";
      this._pipelineTimer = null;
      this._pipelineStep = 0;
      this._recognitionStarting = false;

      this.synth = global.speechSynthesis || null;
      this.sttSupported = false;
      this._initRecognition();
    }

    _initRecognition() {
      const SR = global.SpeechRecognition || global.webkitSpeechRecognition;
      if (!SR) return;

      this.sttSupported = true;
      this.recognition = new SR();
      this.recognition.continuous = false;
      this.recognition.interimResults = true;
      this.recognition.lang = "en-US";
      this.recognition.maxAlternatives = 1;

      this.recognition.onstart = () => {
        this._recognitionStarting = false;
        this._setState(VoiceState.LISTENING);
      };

      this.recognition.onresult = (e) => this._handleResult(e);

      this.recognition.onend = () => {
        const text = this._finalTranscript.trim();
        this._finalTranscript = "";
        if (text && this._listenMode) {
          void this._handleUtterance(text);
        } else if (this._listenMode) {
          this.hooks.onError?.("I didn't catch that. Tap TripAI to try again.");
          this._listenMode = null;
          this._setState(VoiceState.IDLE);
        } else if (this.state === VoiceState.LISTENING) {
          this._setState(VoiceState.IDLE);
        }
      };

      this.recognition.onerror = (e) => {
        this._recognitionStarting = false;
        const benign = e.error === "aborted" || e.error === "no-speech";
        if (e.error === "not-allowed") {
          this.hooks.onError?.("Microphone permission denied. Allow mic access and try again.");
        } else if (!benign) {
          this.hooks.onError?.(`Voice error: ${e.error}`);
        }
        if (this.state === VoiceState.LISTENING) {
          this._setState(VoiceState.IDLE);
        }
      };
    }

    /** Heuristic check — voice layer only, backend parser still runs on submit. */
    analyzeRequest(text) {
      const hasDuration =
        /\d+\s*(-?\s*)?(day|days|night|nights|week|weeks|month|months)\b/i.test(text) ||
        /\b(weekend|long weekend|one week|a week)\b/i.test(text);
      const hasBudget =
        /(\$|€|£|₹|usd|eur|gbp|inr|dollar|dollars|budget)\b/i.test(text) ||
        /\b\d+\s*k\b/i.test(text) ||
        /\$\s*\d+/i.test(text);
      const missing = [];
      if (!hasDuration) missing.push("duration");
      if (!hasBudget) missing.push("budget");
      return { hasDuration, hasBudget, missing };
    }

    mergeRequest() {
      let text = this.pendingRequest.trim();
      if (this.clarificationAnswers.duration) {
        const d = this.clarificationAnswers.duration;
        if (!/\d+\s*day/i.test(text)) {
          text += `. ${/\d/.test(d) ? d : d + " days"}`;
        }
      }
      if (this.clarificationAnswers.budget) {
        const b = this.clarificationAnswers.budget.trim();
        if (!/\$|budget|\d{3,}/i.test(text)) {
          text += `. Budget ${/^\$/.test(b) ? b : "$" + b.replace(/[^\d.]/g, "")}`;
        }
      }
      return text.replace(/\s+/g, " ").replace(/\.\s*\./g, ".").trim();
    }

    async startIntake() {
      if (!this.sttSupported) {
        this.hooks.onError?.(
          "Speech recognition needs Chrome or Edge. You can type your trip below."
        );
        return false;
      }
      if (this.state === VoiceState.LISTENING) {
        this.stop();
        return true;
      }
      if (this.state === VoiceState.SPEAKING) {
        this.cancelSpeech();
      }

      this.pendingRequest = "";
      this.clarificationQueue = [];
      this.clarificationAnswers = {};
      this._listenMode = "intake";

      await this.speak("Tell me about your trip. Where would you like to go?");
      this._startListening();
      return true;
    }

    async resumeClarification(existingText) {
      if (!this.sttSupported) return false;
      this.pendingRequest = existingText.trim();
      const { missing } = this.analyzeRequest(this.pendingRequest);
      this.clarificationQueue = [...missing];
      this.clarificationAnswers = {};

      if (this.clarificationQueue.length === 0) {
        await this._confirmAndSubmit();
        return true;
      }
      await this._askNextClarification();
      return true;
    }

    async _handleUtterance(text) {
      this._setState(VoiceState.PROCESSING);
      this.hooks.onTranscript?.(text, false);

      if (this._listenMode === "intake") {
        this.pendingRequest = text;
        const { missing } = this.analyzeRequest(text);
        this.clarificationQueue = [...missing];
        if (missing.length === 0) {
          await this._confirmAndSubmit();
        } else {
          await this._askNextClarification();
        }
      } else if (this._listenMode === "clarify" && this._currentClarifyField) {
        this.clarificationAnswers[this._currentClarifyField] = text;
        await this._askNextClarification();
      }
    }

    async _askNextClarification() {
      const field = this.clarificationQueue.shift();
      if (!field) {
        await this._confirmAndSubmit();
        return;
      }
      this._currentClarifyField = field;
      this._listenMode = "clarify";
      const prompt = CLARIFY_PROMPTS[field];
      this.hooks.onTranscript?.(prompt, true);
      await this.speak(prompt);
      this._startListening();
    }

    async _confirmAndSubmit() {
      const final = this.mergeRequest();
      this._listenMode = null;
      this.hooks.onTranscript?.(final, false);
      await this.speak("Got it. Starting your multi-agent travel plan now.");
      this.hooks.onConfirmed?.(final);
      this._setState(VoiceState.IDLE);
    }

    _startListening() {
      if (!this.recognition || this._recognitionStarting) return;
      this._finalTranscript = "";
      this._recognitionStarting = true;

      try {
        this.recognition.start();
      } catch {
        try {
          this.recognition.stop();
        } catch {
          /* ignore */
        }
        setTimeout(() => {
          try {
            this.recognition.start();
          } catch {
            this._recognitionStarting = false;
            this.hooks.onError?.("Could not start microphone. Try again.");
          }
        }, 280);
      }
    }

    _handleResult(e) {
      let interim = "";
      let finalChunk = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript;
        if (e.results[i].isFinal) finalChunk += t;
        else interim += t;
      }
      if (finalChunk) {
        this._finalTranscript = (this._finalTranscript + " " + finalChunk).trim();
      }
      const display = this._finalTranscript || interim;
      if (display) this.hooks.onTranscript?.(display, false);
    }

    speak(text) {
      return new Promise((resolve) => {
        if (!this.synth || !text) {
          resolve();
          return;
        }
        this.cancelSpeech(false);
        const utter = new SpeechSynthesisUtterance(text);
        utter.rate = 1.02;
        utter.pitch = 1;
        utter.volume = 1;
        const voices = this.synth.getVoices();
        const preferred = voices.find(
          (v) => v.lang.startsWith("en") && /google|natural|samantha/i.test(v.name)
        );
        if (preferred) utter.voice = preferred;

        utter.onend = () => {
          if (this.state === VoiceState.SPEAKING) {
            this._setState(this._listenMode ? VoiceState.LISTENING : VoiceState.IDLE);
          }
          resolve();
        };
        utter.onerror = () => resolve();

        this._setState(VoiceState.SPEAKING, text);
        this.synth.speak(utter);
      });
    }

    cancelSpeech(resetState = true) {
      if (this.synth) this.synth.cancel();
      if (resetState && this.state === VoiceState.SPEAKING) {
        this._setState(VoiceState.IDLE);
      }
    }

    startPipelineNarration(onStep) {
      this.stopPipelineNarration();
      this._pipelineStep = 0;

      const tick = async () => {
        if (this._pipelineStep >= PIPELINE_NARRATION.length) return;
        const msg = PIPELINE_NARRATION[this._pipelineStep];
        onStep?.(this._pipelineStep);
        this._pipelineStep += 1;
        await this.speak(msg);
        if (this._pipelineTimer !== null) {
          this._pipelineTimer = setTimeout(tick, 400);
        }
      };

      this._pipelineTimer = setTimeout(tick, 300);
    }

    stopPipelineNarration() {
      if (this._pipelineTimer !== null) {
        clearTimeout(this._pipelineTimer);
        this._pipelineTimer = null;
      }
      this.cancelSpeech(false);
    }

    buildSummaryText(state) {
      const spec = state.trip_spec || {};
      const draft = state.draft_itinerary || {};
      const dests = (spec.destinations || []).join(" and ") || "your destination";
      const days = spec.duration_days || (draft.days || []).length || "";
      const budget = spec.budget_amount
        ? `$${Number(spec.budget_amount).toLocaleString()}`
        : "";

      let text = `Your ${days ? days + " day " : ""}trip to ${dests}.`;
      if (budget) text += ` Budget around ${budget}.`;
      if (draft.summary) {
        text += " " + draft.summary;
      } else if ((draft.days || []).length) {
        const d0 = draft.days[0];
        text += ` Day one in ${d0.city}: ${(d0.activities || [])[0] || d0.theme}.`;
      }
      const status = state.validation_status;
      if (status === "pass") text += " Your plan passed validation.";
      return text;
    }

    readSummary(state) {
      return this.speak(this.buildSummaryText(state));
    }

    stop() {
      this._listenMode = null;
      this.stopPipelineNarration();
      if (this.recognition) {
        try {
          this.recognition.stop();
        } catch {
          /* ignore */
        }
      }
      this.cancelSpeech();
      this._setState(VoiceState.IDLE);
    }

    isActive() {
      return this.state !== VoiceState.IDLE;
    }

    _setState(state, detail) {
      this.state = state;
      this.hooks.onStateChange?.(state, detail);
    }
  }

  global.TripVoiceAgent = TripVoiceAgent;
  global.VoiceState = VoiceState;

  if (global.speechSynthesis) {
    global.speechSynthesis.getVoices();
    global.speechSynthesis.addEventListener("voiceschanged", () => {
      global.speechSynthesis.getVoices();
    });
  }
})(window);
