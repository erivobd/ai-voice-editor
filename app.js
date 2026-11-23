'use strict';
let currentJobId=null, currentReport=null, currentEditingReport=null, currentAssets=[];
let pollTimeout=null, pendingSeekTime=null, segmentStopTime=null, accessPin=sessionStorage.getItem('voice_editor_pin')||'';
const el=id=>document.getElementById(id);
function authHeaders(extra={}){return {...extra};}
function assetUrl(jobId,name,download=false){return `/api/jobs/${encodeURIComponent(jobId)}/assets/${encodeURIComponent(name)}${download?'?download=1':''}`;}
function formatTime(sec){const n=Math.max(0,Number(sec)||0),m=Math.floor(n/60),s=(n%60).toFixed(1).padStart(4,'0');return `${String(m).padStart(2,'0')}:${s}`;}
function formatBytes(bytes){const n=Number(bytes)||0;return n<1048576?`${(n/1024).toFixed(1)} KB`:`${(n/1048576).toFixed(2)} MB`;}
function clearPollTimer(){if(pollTimeout){clearTimeout(pollTimeout);pollTimeout=null;}}
function showPinPrompt(retry=false){clearPollTimer();el('pin-card').classList.remove('hidden');el('pin-error').classList.toggle('hidden',!retry);el('pin-input').focus();}
function hidePinPrompt(){el('pin-card').classList.add('hidden');el('pin-error').classList.add('hidden');}
async function apiAuth(){
  const pin=el('pin-input').value.trim();
  const r=await fetch('/api/auth',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pin})});
  if(!r.ok) throw new Error('PIN সঠিক নয়।');
  accessPin=pin;sessionStorage.setItem('voice_editor_pin','set');hidePinPrompt();
  if(currentJobId)loadJob(currentJobId);else if(!el('history-card').classList.contains('hidden'))loadHistory();
}
async function init(){
  try{const r=await fetch('/api/config');const c=await r.json();if(c.pinRequired){el('btn-lock-pin').classList.remove('hidden');const check=await fetch('/api/jobs');if(check.status===401)showPinPrompt(false);else hidePinPrompt();}}catch(e){console.error(e);}
  el('btn-save-pin').addEventListener('click',()=>apiAuth().catch(e=>{el('pin-error').textContent=e.message;el('pin-error').classList.remove('hidden');}));
  el('btn-lock-pin').addEventListener('click',async()=>{await fetch('/api/logout',{method:'POST'});sessionStorage.removeItem('voice_editor_pin');accessPin='';showPinPrompt(false);});
  el('audio-input').addEventListener('change',e=>{const f=e.target.files[0];el('audio-meta').textContent=f?`${f.name} (${formatBytes(f.size)})`:'MP3/WAV/M4A/AAC/FLAC';});
  el('script-input').addEventListener('change',e=>{const f=e.target.files[0];el('script-meta').textContent=f?`${f.name} (${formatBytes(f.size)})`:'ঐচ্ছিক TXT স্ক্রিপ্ট';});
  el('upload-form').addEventListener('submit',handleUpload);
  el('btn-history-toggle').addEventListener('click',()=>{el('history-card').classList.remove('hidden');loadHistory();});
  el('btn-close-history').addEventListener('click',()=>el('history-card').classList.add('hidden'));
  el('btn-approve-all').addEventListener('click',()=>{if(!currentReport)return;currentReport.suggested_edits.forEach(x=>{if(x.type==='long_pause')x.approved=true;});renderEditCards();});
  el('btn-reject-all').addEventListener('click',()=>{if(!currentReport)return;currentReport.suggested_edits.forEach(x=>x.approved=false);renderEditCards();});
  el('btn-preview-nr').addEventListener('click',()=>{if(!currentJobId)return;const p=el('audio-player');pendingSeekTime=null;segmentStopTime=null;el('player-label').textContent='Gentle Noise Reduction Preview';p.src=assetUrl(currentJobId,'nr_preview.wav');p.play().catch(showPlayerError);});
  el('btn-render-final').addEventListener('click',submitFinalRender);
  el('btn-retry-status').addEventListener('click',pollJobStatus);
  const reset=()=>{clearPollTimer();currentJobId=null;currentReport=null;currentEditingReport=null;currentAssets=[];['review-card','download-card','status-card'].forEach(x=>el(x).classList.add('hidden'));el('upload-card').classList.remove('hidden');};
  el('btn-new-job').addEventListener('click',reset);el('btn-status-new-job').addEventListener('click',reset);el('btn-download-new-job').addEventListener('click',reset);
  el('btn-back-to-review').addEventListener('click',()=>{el('download-card').classList.add('hidden');el('review-card').classList.remove('hidden');});
  const p=el('audio-player');
  p.addEventListener('loadedmetadata',()=>{if(pendingSeekTime!==null){p.currentTime=Math.min(pendingSeekTime,Math.max(0,(p.duration||0)-.1));pendingSeekTime=null;p.play().catch(showPlayerError);}});
  p.addEventListener('timeupdate',()=>{el('player-time').textContent=formatTime(p.currentTime);if(segmentStopTime!==null&&p.currentTime>=segmentStopTime){p.pause();segmentStopTime=null;}});
  p.addEventListener('error',()=>showPlayerError(new Error('অডিও লোড হয়নি। আবার Play করো বা নেটওয়ার্ক পরীক্ষা করো।')));
  el('final-player').addEventListener('error',()=>{el('final-player-error').textContent='Preview লোড হয়নি। নিচের Download লিংক ব্যবহার করো।';el('final-player-error').classList.remove('hidden');});
}
function showPlayerError(e){el('player-error').textContent=e.message||'Playback error';el('player-error').classList.remove('hidden');}
function handleUpload(e){
  e.preventDefault();const audio=el('audio-input').files[0];if(!audio)return;
  const fd=new FormData();fd.append('audio',audio);const script=el('script-input').files[0];if(script)fd.append('script',script);
  const btn=el('btn-upload');btn.disabled=true;el('upload-progress-wrap').classList.remove('hidden');
  const xhr=new XMLHttpRequest();xhr.open('POST','/api/jobs');
  xhr.upload.onprogress=ev=>{if(ev.lengthComputable){const pct=Math.min(98,Math.round(ev.loaded/ev.total*100));el('upload-percent').textContent=pct+'%';el('upload-bar-fill').style.width=pct+'%';}};
  xhr.onload=()=>{btn.disabled=false;el('upload-progress-wrap').classList.add('hidden');if(xhr.status===401){showPinPrompt(true);return;}if(xhr.status>=200&&xhr.status<300){try{loadJob(JSON.parse(xhr.responseText).job_id);}catch{alert('সার্ভারের উত্তর বোঝা যায়নি।');}}else{let m='Upload failed';try{m=JSON.parse(xhr.responseText).error||m;}catch{}alert(m);}};
  xhr.onerror=()=>{btn.disabled=false;el('upload-progress-wrap').classList.add('hidden');alert('Network error during upload.');};xhr.send(fd);
}
function schedulePoll(ms=5000){clearPollTimer();pollTimeout=setTimeout(pollJobStatus,ms);}
async function loadJob(id){
  currentJobId=id;currentReport=null;currentEditingReport=null;currentAssets=[];clearPollTimer();
  ['upload-card','history-card','review-card','download-card'].forEach(x=>el(x).classList.add('hidden'));
  el('status-card').classList.remove('hidden');el('status-spinner').classList.remove('hidden');el('status-actions').classList.add('hidden');el('status-job-id').textContent=id;
  await pollJobStatus();
}
async function pollJobStatus(){
  if(!currentJobId)return;
  try{
    const r=await fetch(`/api/jobs/${encodeURIComponent(currentJobId)}`,{headers:authHeaders()});
    if(r.status===401){showPinPrompt(true);return;}
    if(!r.ok)throw new Error(`Server ${r.status}`);
    const d=await r.json();currentAssets=d.assets||[];currentEditingReport=d.editingReport||null;
    const s=d.status||{},stage=s.stage||'processing';
    el('status-title').textContent=`Stage: ${stage.toUpperCase()}`;el('status-message').textContent=s.message||'Working...';
    if(s.status==='failed'||stage==='error'){el('status-spinner').classList.add('hidden');el('status-actions').classList.remove('hidden');clearPollTimer();return;}
    if(stage==='review_ready'&&d.report){clearPollTimer();currentReport=d.report;currentReport.job_id=currentJobId;(currentReport.suggested_edits||[]).forEach(x=>{x.approved=false;});el('status-card').classList.add('hidden');openReviewScreen();return;}
    if(stage==='completed'){clearPollTimer();if(d.report){currentReport=d.report;currentReport.job_id=currentJobId;}el('status-card').classList.add('hidden');openDownloadScreen();return;}
    schedulePoll(5000);
  }catch(e){el('status-title').textContent='Status check delayed';el('status-message').textContent=e.message+'; আবার চেষ্টা করছি।';el('status-actions').classList.remove('hidden');schedulePoll(7000);}
}
function originalAsset(){return currentAssets.find(a=>a.name.startsWith('original_audio.'))?.name||'original_audio.mp3';}
function openReviewScreen(){
  el('download-card').classList.add('hidden');el('review-card').classList.remove('hidden');el('player-error').classList.add('hidden');
  const p=el('audio-player');p.src=assetUrl(currentJobId,originalAsset());
  const s=currentReport.summary||{};el('review-summary-text').textContent=`Duration: ${formatTime(s.total_duration||0)} • ${s.total_suggestions||0}টি যাচাইযোগ্য প্রস্তাব`;
  const missing=currentReport.missing_script_lines||[];
  el('missing-lines-box').classList.toggle('hidden',!missing.length);
  el('missing-lines-list').replaceChildren(...missing.map(m=>{const li=document.createElement('li');li.textContent=`লাইন ${m.line_number}: ${m.script_text}`;return li;}));
  renderEditCards();
}
function renderEditCards(){
  const box=el('edits-list'),edits=currentReport?.suggested_edits||[];
  if(!edits.length){box.textContent='কোনো কাটের প্রস্তাব পাওয়া যায়নি।';return;}
  box.innerHTML='';
  edits.forEach((ed,i)=>{
    const card=document.createElement('article');card.className=`edit-item ${ed.approved?'approved':''}`;
    const head=document.createElement('div');head.className='edit-top';
    const time=document.createElement('strong');time.textContent=`${formatTime(ed.start)} → ${formatTime(ed.end)} (${Number(ed.duration||ed.end-ed.start).toFixed(1)}s)`;
    const badge=document.createElement('span');badge.className='tag';badge.textContent=ed.type==='long_pause'?'দীর্ঘ বিরতি':'সম্ভাব্য অমিল';
    head.append(time,badge);
    const reason=document.createElement('p');reason.textContent=ed.reason||'শুনে যাচাই করো।';
    const transcript=document.createElement('p');transcript.className='muted';transcript.textContent=ed.transcript||'';
    const actions=document.createElement('div');actions.className='edit-actions';
    const preview=document.createElement('button');preview.className='ghost';preview.textContent='▶ অংশটি শুনি';preview.addEventListener('click',()=>previewSegment(Number(ed.start),Number(ed.end)));
    const label=document.createElement('label');const check=document.createElement('input');check.type='checkbox';check.checked=Boolean(ed.approved);check.addEventListener('change',()=>{ed.approved=check.checked;renderEditCards();});
    label.append(check,document.createTextNode(' কাট অনুমোদন'));actions.append(preview,label);card.append(head,reason,transcript,actions);box.append(card);
  });
}
function previewSegment(start,end){
  const p=el('audio-player');el('player-error').classList.add('hidden');const seek=Math.max(0,start-.5);segmentStopTime=end+.5;
  el('player-label').textContent=`Preview ${formatTime(start)} – ${formatTime(end)}`;
  if(!p.src||!p.src.includes(encodeURIComponent(originalAsset()))){pendingSeekTime=seek;p.src=assetUrl(currentJobId,originalAsset());p.load();}
  else if(p.readyState>=1){p.currentTime=Math.min(seek,Math.max(0,(p.duration||0)-.1));p.play().catch(showPlayerError);}
  else{pendingSeekTime=seek;}
}
async function submitFinalRender(){
  if(!currentJobId||!currentReport)return;
  const btn=el('btn-render-final');if(btn.disabled)return;
  const cuts=(currentReport.suggested_edits||[]).filter(x=>x.approved).map(x=>({edit_id:x.edit_id,start:x.start,end:x.end,reason:x.reason}));
  const nr=document.querySelector('input[name="nr_mode"]:checked')?.value==='gentle'?'gentle':'original';
  btn.disabled=true;
  try{
    const r=await fetch(`/api/jobs/${encodeURIComponent(currentJobId)}/render`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({approved_cuts:cuts,noise_reduction:nr})});
    if(r.status===401){showPinPrompt(true);return;}
    if(!r.ok){const e=await r.json().catch(()=>({}));throw new Error(e.error||'Render শুরু করা যায়নি।');}
    el('review-card').classList.add('hidden');el('status-card').classList.remove('hidden');el('status-spinner').classList.remove('hidden');el('status-title').textContent='Stage: RENDERING';el('status-message').textContent='অনুমোদিত কাট দিয়ে Render হচ্ছে...';schedulePoll(5000);
  }catch(e){alert(e.message);btn.disabled=false;}
}
function openDownloadScreen(){
  el('review-card').classList.add('hidden');el('download-card').classList.remove('hidden');el('final-player-error').classList.add('hidden');
  el('final-player').src=assetUrl(currentJobId,'final_edited.mp3');
  el('dl-mp3').href=assetUrl(currentJobId,'final_edited.mp3',true);el('dl-wav').href=assetUrl(currentJobId,'final_edited.wav',true);
  el('dl-report').href=assetUrl(currentJobId,'editing_report.json',true);el('dl-original').href=assetUrl(currentJobId,originalAsset(),true);
  const r=currentEditingReport;
  el('final-stats').textContent=r?`Job ${currentJobId} • ${r.merged_cuts_count}টি কাট • ${r.time_saved_sec}s কমানো • Noise reduction: ${r.noise_reduction_applied} • কণ্ঠের pitch ও speed অপরিবর্তিত`:`Job ${currentJobId} • Download ready`;
}
async function loadHistory(){
  const box=el('history-list');box.textContent='লোড হচ্ছে...';
  try{const r=await fetch('/api/jobs');if(r.status===401){showPinPrompt(true);box.textContent='PIN দিয়ে Unlock করো।';return;}if(!r.ok)throw new Error('History load failed');const d=await r.json();box.innerHTML='';
    if(!(d.jobs||[]).length){box.textContent='এখনও কোনো কাজ নেই।';return;}
    d.jobs.forEach(j=>{const b=document.createElement('button');b.className='history-item';b.textContent=`${j.original_filename} · ${j.stage}`;b.addEventListener('click',()=>loadJob(j.job_id));box.append(b);});
  }catch(e){box.textContent=e.message;}
}
init();
