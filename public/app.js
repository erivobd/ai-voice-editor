(() => {
  const STAGE_ORDER = [
    "uploading_audio",
    "analyzing_voice",
    "generating_transcript",
    "creating_scene_plan",
    "collecting_footage",
    "creating_graphics",
    "editing_video",
    "rendering_final_video",
    "completed"
  ];

  const $ = (id) => document.getElementById(id);
  let accessPin = sessionStorage.getItem("doc_maker_pin") || "";
  let pinRequired = true;
  let currentJobId = localStorage.getItem("doc_maker_active_job") || "";
  let pollTimer = null;
  const activeBlobUrls = [];

  function registerBlobUrl(url) {
    activeBlobUrls.push(url);
    return url;
  }

  function cleanupBlobUrls() {
    while (activeBlobUrls.length) {
      const u = activeBlobUrls.pop();
      try { URL.revokeObjectURL(u); } catch (_e) {}
    }
  }

  const themeGrid = $("theme-grid");
  if (themeGrid) {
    themeGrid.addEventListener("click", (e) => {
      const card = e.target.closest(".theme-card");
      if (!card) return;
      themeGrid.querySelectorAll(".theme-card").forEach((c) => c.classList.remove("active"));
      card.classList.add("active");
      const themeInput = $("opt-theme");
      if (themeInput) themeInput.value = card.getAttribute("data-theme") || "crimson_noir";
    });
  }

  function refreshSrtBadge() {
    const badge = $("srt-mode-badge");
    if (!badge) return;
    const textVal = ($("srt-text-input")?.value || "").trim();
    const fileVal = $("srt-file-input")?.files?.[0];
    if (textVal) {
      badge.textContent = "মোড: কাস্টম SRT টেক্সট ব্যবহৃত হবে (Whisper স্কিপ হবে)";
    } else if (fileVal) {
      badge.textContent = `মোড: কাস্টম ফাইল (${fileVal.name}) ব্যবহৃত হবে (Whisper স্কিপ হবে)`;
    } else {
      badge.textContent = "মোড: Whisper অটো-ট্রান্সক্রিপশন (বাংলা)";
    }
  }

  $("srt-file-input")?.addEventListener("change", refreshSrtBadge);
  $("srt-text-input")?.addEventListener("input", refreshSrtBadge);

  function showOnly(cardId) {
    ["pin-card", "upload-card", "history-card", "status-card", "result-card"].forEach((id) => {
      $(id).classList.toggle("hidden", id !== cardId);
    });
  }

  function authHeaders() {
    return accessPin ? { "X-Access-Pin": accessPin } : {};
  }

  async function fetchProtectedAssetBlob(jobId, name) {
    const res = await fetch(
      `/api/jobs/${encodeURIComponent(jobId)}/asset/${encodeURIComponent(name)}`,
      { headers: authHeaders() }
    );
    if (!res.ok) {
      throw new Error(`Failed loading ${name} (${res.status})`);
    }
    return res.blob();
  }

  async function bindProtectedDownload(anchorEl, jobId, name, fallbackFilename) {
    anchorEl.removeAttribute("href");
    anchorEl.onclick = async (ev) => {
      ev.preventDefault();
      try {
        const blob = await fetchProtectedAssetBlob(jobId, name);
        const url = registerBlobUrl(URL.createObjectURL(blob));
        const link = document.createElement("a");
        link.href = url;
        link.download = fallbackFilename;
        document.body.appendChild(link);
        link.click();
        link.remove();
      } catch (err) {
        alert(err.message || "ডাউনলোড করা যায়নি।");
      }
    };
  }

  async function init() {
    try {
      const res = await fetch("/api/health");
      const data = await res.json();
      pinRequired = data.pinRequired !== false;
    } catch (_e) {}

    if (pinRequired) {
      if (accessPin) {
        const ok = await verifyPin(accessPin);
        if (ok) {
          $("btn-lock-pin").classList.remove("hidden");
          enterApp();
          return;
        }
      }
      showOnly("pin-card");
    } else {
      enterApp();
    }
  }

  async function verifyPin(pin) {
    try {
      const res = await fetch("/api/auth/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pin })
      });
      return res.ok;
    } catch (_e) {
      return false;
    }
  }

  function enterApp() {
    if (currentJobId) {
      openJob(currentJobId);
    } else {
      showOnly("upload-card");
    }
  }

  $("btn-save-pin").addEventListener("click", async () => {
    const val = $("pin-input").value.trim();
    $("pin-error").classList.add("hidden");
    const ok = await verifyPin(val);
    if (!ok) {
      $("pin-error").classList.remove("hidden");
      return;
    }
    accessPin = val;
    sessionStorage.setItem("doc_maker_pin", accessPin);
    $("btn-lock-pin").classList.remove("hidden");
    enterApp();
  });

  $("btn-lock-pin").addEventListener("click", () => {
    stopPolling();
    cleanupBlobUrls();
    accessPin = "";
    sessionStorage.removeItem("doc_maker_pin");
    $("pin-input").value = "";
    $("btn-lock-pin").classList.add("hidden");
    showOnly("pin-card");
  });

  $("upload-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const file = $("audio-input").files[0];
    if (!file) return;

    $("upload-error").classList.add("hidden");
    $("btn-generate").disabled = true;
    $("upload-progress-wrap").classList.remove("hidden");
    $("upload-bar-fill").style.width = "0%";
    $("upload-percent").textContent = "0%";
    $("upload-status-text").textContent = "অডিও আপলোড হচ্ছে...";

    const formData = new FormData();
    formData.append("audio", file);
    formData.append("title", $("title-input").value.trim());
    formData.append("subtitles", $("opt-subtitles").checked ? "true" : "false");
    formData.append("bg_music", $("opt-music").checked ? "true" : "false");
    formData.append("video_theme", ($("opt-theme") && $("opt-theme").value) || "crimson_noir");

    const srtTextVal = ($("srt-text-input")?.value || "").trim();
    const srtFileVal = $("srt-file-input")?.files?.[0];
    if (srtTextVal) {
      formData.append("srt_text", srtTextVal);
    } else if (srtFileVal) {
      formData.append("srt_file", srtFileVal);
    }

    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/jobs");
    if (accessPin) xhr.setRequestHeader("X-Access-Pin", accessPin);

    xhr.upload.onprogress = (ev) => {
      if (ev.lengthComputable) {
        const pct = Math.round((ev.loaded / ev.total) * 100);
        $("upload-bar-fill").style.width = `${pct}%`;
        $("upload-percent").textContent = `${pct}%`;
      }
    };

    xhr.onload = () => {
      $("btn-generate").disabled = false;
      $("upload-progress-wrap").classList.add("hidden");
      let data = {};
      try { data = JSON.parse(xhr.responseText); } catch (_e) {}
      if (xhr.status >= 200 && xhr.status < 300 && data.job_id) {
        currentJobId = data.job_id;
        localStorage.setItem("doc_maker_active_job", currentJobId);
        openJob(currentJobId);
      } else {
        $("upload-error").textContent = data.error || "আপলোড ব্যর্থ হয়েছে।";
        $("upload-error").classList.remove("hidden");
      }
    };

    xhr.onerror = () => {
      $("btn-generate").disabled = false;
      $("upload-progress-wrap").classList.add("hidden");
      $("upload-error").textContent = "নেটওয়ার্ক সমস্যা হয়েছে। আবার চেষ্টা করুন।";
      $("upload-error").classList.remove("hidden");
    };

    xhr.send(formData);
  });

  function stopPolling() {
    if (pollTimer) {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  }

  function openJob(jobId) {
    currentJobId = jobId;
    localStorage.setItem("doc_maker_active_job", jobId);
    $("status-job-id").textContent = `Job ID: ${jobId}`;
    $("status-error-box").classList.add("hidden");
    $("status-spinner").classList.remove("hidden");
    showOnly("status-card");
    pollStatus();
    stopPolling();
    pollTimer = setInterval(pollStatus, 5000);
  }

  function updateStageChecklist(stageKey) {
    const activeIdx = STAGE_ORDER.indexOf(stageKey);
    document.querySelectorAll("#stage-list li").forEach((li) => {
      const key = li.getAttribute("data-stage");
      const idx = STAGE_ORDER.indexOf(key);
      li.classList.remove("done", "active");
      if (activeIdx >= 0) {
        if (idx < activeIdx) li.classList.add("done");
        else if (idx === activeIdx) li.classList.add("active");
      }
    });
  }

  async function pollStatus() {
    if (!currentJobId) return;
    try {
      const res = await fetch(`/api/jobs/${encodeURIComponent(currentJobId)}/status`, {
        headers: authHeaders()
      });
      if (!res.ok) return;
      const data = await res.json();

      const pct = Number(data.percent || 0);
      $("status-stage-title").textContent = data.stage || "Processing";
      $("status-message").textContent = data.message || "";
      $("status-percent").textContent = `${pct}%`;
      $("job-bar-fill").style.width = `${pct}%`;
      updateStageChecklist(data.stage_key);

      if (data.stage_key === "completed" && data.has_video) {
        stopPolling();
        await showResult(data);
      } else if (data.stage_key === "failed") {
        stopPolling();
        $("status-spinner").classList.add("hidden");
        $("status-error-text").textContent = data.error || "অজানা ত্রুটি ঘটেছে।";
        $("status-error-box").classList.remove("hidden");
      }
    } catch (_e) {}
  }

  async function showResult(data) {
    cleanupBlobUrls();
    const stats = [];
    if (data.duration_sec) stats.push(`দৈর্ঘ্য: ${Math.round(data.duration_sec)} সেকেন্ড`);
    if (data.scene_count) stats.push(`দৃশ্য: ${data.scene_count}টি`);
    if (data.video_size_mb) stats.push(`সাইজ: ${data.video_size_mb} MB`);
    $("result-stats").textContent = stats.join(" • ") || "1080p MP4 প্রস্তুত";

    const videoEl = $("final-video-player");
    try {
      const vidBlob = await fetchProtectedAssetBlob(currentJobId, "final_documentary.mp4");
      videoEl.src = registerBlobUrl(URL.createObjectURL(vidBlob));
    } catch (_e) {
      videoEl.removeAttribute("src");
    }

    await bindProtectedDownload($("dl-mp4"), currentJobId, "final_documentary.mp4", `${currentJobId}_final_documentary.mp4`);
    await bindProtectedDownload($("dl-plan"), currentJobId, "scene_plan.json", `${currentJobId}_scene_plan.json`);
    await bindProtectedDownload($("dl-transcript"), currentJobId, "transcript.json", `${currentJobId}_transcript.json`);
    await bindProtectedDownload($("dl-srt"), currentJobId, "subtitles.srt", `${currentJobId}_subtitles.srt`);

    showOnly("result-card");
  }

  function startNewJob() {
    stopPolling();
    cleanupBlobUrls();
    currentJobId = "";
    localStorage.removeItem("doc_maker_active_job");
    $("audio-input").value = "";
    if ($("srt-file-input")) $("srt-file-input").value = "";
    if ($("srt-text-input")) $("srt-text-input").value = "";
    refreshSrtBadge();
    showOnly("upload-card");
  }

  $("btn-refresh-status").addEventListener("click", pollStatus);
  $("btn-status-new-job").addEventListener("click", startNewJob);
  $("btn-result-new-job").addEventListener("click", startNewJob);

  $("btn-history-toggle").addEventListener("click", async () => {
    showOnly("history-card");
    const listEl = $("history-list");
    listEl.replaceChildren();
    const loadingP = document.createElement("p");
    loadingP.className = "muted";
    loadingP.textContent = "লোড হচ্ছে...";
    listEl.appendChild(loadingP);

    try {
      const res = await fetch("/api/jobs", { headers: authHeaders() });
      const data = await res.json();
      const jobs = data.jobs || [];
      listEl.replaceChildren();

      if (!jobs.length) {
        const emptyP = document.createElement("p");
        emptyP.className = "muted";
        emptyP.textContent = "এখনো কোনো ভিডিও তৈরি হয়নি।";
        listEl.appendChild(emptyP);
        return;
      }

      jobs.forEach((j) => {
        const btn = document.createElement("button");
        btn.className = "history-item";
        const nameSpan = document.createElement("span");
        nameSpan.textContent = String(j.name || j.job_id || "");
        const stateSpan = document.createElement("span");
        stateSpan.textContent = j.has_video ? "✅ Ready" : "⏳ In Progress";
        btn.appendChild(nameSpan);
        btn.appendChild(stateSpan);
        btn.addEventListener("click", () => openJob(j.job_id));
        listEl.appendChild(btn);
      });
    } catch (_e) {
      listEl.replaceChildren();
      const errP = document.createElement("p");
      errP.className = "error";
      errP.textContent = "লোড করা যায়নি।";
      listEl.appendChild(errP);
    }
  });

  $("btn-close-history").addEventListener("click", () => showOnly("upload-card"));

  refreshSrtBadge();
  init();
})();
