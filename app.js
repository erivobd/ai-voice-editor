
'use strict';

let currentJobId = null;
let currentReport = null;
let currentEditingReport = null;
let currentAssets = [];
let pollTimeout = null;

const el = id => document.getElementById(id);

function formatTime(sec) {
  const n = Math.max(0, Number(sec) || 0);
  const m = Math.floor(n / 60);
  const s = (n % 60).toFixed(1).padStart(4, '0');
  return `${String(m).padStart(2, '0')}:${s}`;
}

function formatBytes(bytes) {
  const n = Number(bytes) || 0;

  if (n < 1048576) {
    return `${(n / 1024).toFixed(1)} KB`;
  }

  return `${(n / 1048576).toFixed(2)} MB`;
}

function assetUrl(jobId, name, download = false) {
  return `/api/jobs/${encodeURIComponent(jobId)}/assets/${encodeURIComponent(name)}${download ? '?download=1' : ''}`;
}

function clearPollTimer() {
  if (pollTimeout) {
    clearTimeout(pollTimeout);
    pollTimeout = null;
  }
}

function schedulePoll(ms = 5000) {
  clearPollTimer();
  pollTimeout = setTimeout(pollJobStatus, ms);
}

function showPinPrompt(retry = false) {
  clearPollTimer();

  el('pin-card').classList.remove('hidden');
  el('upload-card').classList.add('hidden');

  el('pin-error').classList.toggle('hidden', !retry);
  el('pin-input').focus();
}

function hidePinPrompt() {
  el('pin-card').classList.add('hidden');
  el('pin-error').classList.add('hidden');
}

async function apiAuth() {
  const pin = el('pin-input').value.trim();

  if (!pin) {
    throw new Error('পাসওয়ার্ড লিখো।');
  }

  const response = await fetch('/api/auth', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ pin })
  });

  if (!response.ok) {
    throw new Error('পাসওয়ার্ড সঠিক নয়।');
  }

  hidePinPrompt();
  el('pin-input').value = '';

  if (currentJobId) {
    await loadJob(currentJobId);
  } else {
    el('upload-card').classList.remove('hidden');

    if (!el('history-card').classList.contains('hidden')) {
      await loadHistory();
    }
  }
}

async function init() {
  try {
    const response = await fetch('/api/config');
    const config = await response.json();

    if (config.pinRequired) {
      el('btn-lock-pin').classList.remove('hidden');

      const check = await fetch('/api/jobs');

      if (check.status === 401) {
        showPinPrompt(false);
      }
    }
  } catch (error) {
    console.error(error);
  }

  el('pin-form').addEventListener('submit', event => {
    event.preventDefault();

    apiAuth().catch(error => {
      el('pin-error').textContent = error.message;
      el('pin-error').classList.remove('hidden');
    });
  });

  el('btn-lock-pin').addEventListener('click', async () => {
    await fetch('/api/logout', { method: 'POST' });

    currentJobId = null;
    currentReport = null;
    currentEditingReport = null;
    currentAssets = [];

    clearPollTimer();
    showPinPrompt(false);
  });

  el('audio-input').addEventListener('change', event => {
    const file = event.target.files[0];

    el('audio-meta').textContent = file
      ? `${file.name} (${formatBytes(file.size)})`
      : 'MP3, WAV, M4A, AAC, FLAC, OGG, OPUS ইত্যাদি';
  });

  el('script-input').addEventListener('change', event => {
    const file = event.target.files[0];

    el('script-meta').textContent = file
      ? `${file.name} (${formatBytes(file.size)})`
      : 'TXT ফাইল দিলে স্ক্রিপ্টের সঙ্গে মিলিয়ে দেখা হবে।';
  });

  el('upload-form').addEventListener('submit', handleUpload);

  el('btn-history-toggle').addEventListener('click', () => {
    el('history-card').classList.remove('hidden');
    loadHistory();
  });

  el('btn-close-history').addEventListener('click', () => {
    el('history-card').classList.add('hidden');
  });

  el('btn-retry-status').addEventListener('click', pollJobStatus);

  const reset = () => {
    clearPollTimer();

    currentJobId = null;
    currentReport = null;
    currentEditingReport = null;
    currentAssets = [];

    [
      'status-card',
      'download-card',
      'history-card'
    ].forEach(id => el(id).classList.add('hidden'));

    el('upload-card').classList.remove('hidden');
    el('upload-form').reset();

    el('audio-meta').textContent =
      'MP3, WAV, M4A, AAC, FLAC, OGG, OPUS ইত্যাদি';

    el('script-meta').textContent =
      'TXT ফাইল দিলে স্ক্রিপ্টের সঙ্গে মিলিয়ে দেখা হবে।';
  };

  el('btn-status-new-job').addEventListener('click', reset);
  el('btn-download-new-job').addEventListener('click', reset);

  el('final-player').addEventListener('error', () => {
    el('final-player-error').textContent =
      'অডিও Preview লোড হয়নি। নিচের Download লিংক ব্যবহার করো।';

    el('final-player-error').classList.remove('hidden');
  });
}

function handleUpload(event) {
  event.preventDefault();

  const audio = el('audio-input').files[0];

  if (!audio) {
    alert('প্রথমে অডিও ফাইল নির্বাচন করো।');
    return;
  }

  const formData = new FormData();

  formData.append('audio', audio);

  const script = el('script-input').files[0];

  if (script) {
    formData.append('script', script);
  }

  const button = el('btn-upload');

  button.disabled = true;

  el('upload-progress-wrap').classList.remove('hidden');
  el('upload-percent').textContent = '0%';
  el('upload-bar-fill').style.width = '0%';
  el('upload-status-text').textContent = 'আপলোড শুরু হচ্ছে...';

  const xhr = new XMLHttpRequest();

  xhr.open('POST', '/api/jobs');

  xhr.upload.onprogress = event => {
    if (!event.lengthComputable) return;

    const percent = Math.min(
      100,
      Math.round((event.loaded / event.total) * 100)
    );

    el('upload-percent').textContent = `${percent}%`;
    el('upload-bar-fill').style.width = `${percent}%`;

    el('upload-status-text').textContent =
      percent === 100 ? 'সার্ভারে পাঠানো হয়েছে...' : 'আপলোড হচ্ছে...';
  };

  xhr.onload = () => {
    button.disabled = false;

    el('upload-progress-wrap').classList.add('hidden');

    if (xhr.status === 401) {
      showPinPrompt(true);
      return;
    }

    if (xhr.status >= 200 && xhr.status < 300) {
      try {
        const result = JSON.parse(xhr.responseText);

        if (!result.job_id) {
          throw new Error('Job ID পাওয়া যায়নি।');
        }

        loadJob(result.job_id);
      } catch (error) {
        alert(error.message || 'সার্ভারের উত্তর বোঝা যায়নি।');
      }

      return;
    }

    let message = 'Upload failed';

    try {
      message = JSON.parse(xhr.responseText).error || message;
    } catch {}

    alert(message);
  };

  xhr.onerror = () => {
    button.disabled = false;
    el('upload-progress-wrap').classList.add('hidden');

    alert('Network error during upload.');
  };

  xhr.send(formData);
}

async function loadJob(id) {
  currentJobId = id;

  currentReport = null;
  currentEditingReport = null;
  currentAssets = [];

  clearPollTimer();

  [
    'upload-card',
    'history-card',
    'download-card'
  ].forEach(name => el(name).classList.add('hidden'));

  el('status-card').classList.remove('hidden');

  el('status-spinner').classList.remove('hidden');
  el('status-actions').classList.add('hidden');

  el('status-job-id').textContent = `Job ID: ${id}`;

  el('status-title').textContent = 'অডিও প্রসেস হচ্ছে';
  el('status-message').textContent = 'একটু অপেক্ষা করো...';

  await pollJobStatus();
}

async function pollJobStatus() {
  if (!currentJobId) return;

  try {
    const response = await fetch(
      `/api/jobs/${encodeURIComponent(currentJobId)}`
    );

    if (response.status === 401) {
      showPinPrompt(true);
      return;
    }

    if (!response.ok) {
      throw new Error(`Server ${response.status}`);
    }

    const data = await response.json();

    currentAssets = data.assets || [];
    currentReport = data.report || null;
    currentEditingReport = data.editingReport || null;

    const status = data.status || {};
    const stage = status.stage || 'processing';

    el('status-title').textContent = status.message ||
      `Stage: ${stage.toUpperCase()}`;

    el('status-message').textContent =
      status.message || 'অডিও বিশ্লেষণ ও এডিট চলছে...';

    el('status-stage-text').textContent =
      `বর্তমান ধাপ: ${stage}`;

    // A final MP3 means the automatic render has completed.
    const hasFinalAudio = currentAssets.some(
      asset => asset.name === 'final_edited.mp3'
    );

    if (hasFinalAudio) {
      clearPollTimer();

      el('status-spinner').classList.add('hidden');
      el('status-card').classList.add('hidden');

      openDownloadScreen();
      return;
    }

    if (
      status.status === 'failed' ||
      stage === 'error' ||
      stage === 'failed'
    ) {
      clearPollTimer();

      el('status-spinner').classList.add('hidden');
      el('status-actions').classList.remove('hidden');

      el('status-title').textContent = 'প্রসেসিং ব্যর্থ হয়েছে';

      return;
    }

    // Show approximate stage information, not fake percentage progress.
    if (currentReport) {
      el('status-percent').textContent = 'বিশ্লেষণ সম্পন্ন';
      el('status-progress-fill').style.width = '65%';
    } else {
      el('status-percent').textContent = 'বিশ্লেষণ চলছে';
      el('status-progress-fill').style.width = '25%';
    }

    if (stage === 'rendering') {
      el('status-percent').textContent = 'এডিট Render হচ্ছে';
      el('status-progress-fill').style.width = '85%';
    }

    schedulePoll(7000);

  } catch (error) {
    el('status-title').textContent = 'Status check delayed';

    el('status-message').textContent =
      `${error.message}; আবার চেষ্টা করছি।`;

    el('status-actions').classList.remove('hidden');

    schedulePoll(10000);
  }
}

function originalAsset() {
  return currentAssets.find(
    asset => asset.name.startsWith('original_audio.')
  )?.name || 'original_audio.m4a';
}

function openDownloadScreen() {
  el('status-card').classList.add('hidden');
  el('download-card').classList.remove('hidden');

  el('final-player-error').classList.add('hidden');

  el('final-player').src =
    assetUrl(currentJobId, 'final_edited.mp3');

  el('dl-mp3').href =
    assetUrl(currentJobId, 'final_edited.mp3', true);

  el('dl-wav').href =
    assetUrl(currentJobId, 'final_edited.wav', true);

  el('dl-report').href =
    assetUrl(currentJobId, 'editing_report.json', true);

  el('dl-original').href =
    assetUrl(currentJobId, originalAsset(), true);

  const report = currentEditingReport;

  if (report) {
    el('final-stats').textContent =
      `Job ${currentJobId} • ${report.merged_cuts_count}টি কাট • ` +
      `${report.time_saved_sec} সেকেন্ড কমানো • ` +
      `Noise reduction: ${report.noise_reduction_applied} • ` +
      'কণ্ঠের pitch ও speed অপরিবর্তিত।';
  } else {
    el('final-stats').textContent =
      `Job ${currentJobId} • Download ready`;
  }
}

async function loadHistory() {
  const box = el('history-list');

  box.textContent = 'লোড হচ্ছে...';

  try {
    const response = await fetch('/api/jobs');

    if (response.status === 401) {
      showPinPrompt(true);
      box.textContent = 'PIN দিয়ে Unlock করো।';
      return;
    }

    if (!response.ok) {
      throw new Error('History load failed');
    }

    const data = await response.json();

    box.replaceChildren();

    if (!(data.jobs || []).length) {
      box.textContent = 'এখনও কোনো কাজ নেই।';
      return;
    }

    data.jobs.forEach(job => {
      const button = document.createElement('button');

      button.className = 'history-item';

      button.textContent =
        `${job.original_filename} · ${job.stage}`;

      button.addEventListener('click', () => {
        loadJob(job.job_id);
      });

      box.append(button);
    });

  } catch (error) {
    box.textContent = error.message;
  }
}

init();
