'use strict';
const DATA = JSON.parse(document.getElementById('data').textContent);
const $ = id => document.getElementById(id);
const canvas = $('spectrogram'), ctx = canvas.getContext('2d'), audio = $('audio');
const DURATION = DATA.render.duration_s, PX_PER_SECOND = 1200 / DURATION;
const KEY = 'avian-tfbox-v1:' + DATA.grouping_sha256;
let reviews = {}, storageError = '', current = 0, selected = 0, mode = 'merged';
let timeStart = 0, timeEnd = DURATION, stopAt = null, token = 0, ready = false;
let low = new Image(), full = new Image(), wide = new Image();
if (DATA.render.frequency_views_hz.includes(24000)) $('freq').add(new Option('24 kHz', '24000'));
const labels = {unreviewed:'Unreviewed', usable:'Grouping looks usable', overmerged:'Overmerged',
  undermerged:'Undermerged', boundary:'Adjust boundaries', uncertain:'Uncertain'};
try {
  const stored = JSON.parse(localStorage.getItem(KEY) || '{}');
  if (stored && typeof stored === 'object' && !Array.isArray(stored)) reviews = stored;
} catch { storageError = 'Browser storage unavailable. Export feedback JSON.'; }
const item = () => DATA.items[current];
const boxes = () => item()[mode + '_boxes'];
const active = () => boxes()[selected];
const sum = key => DATA.items.reduce((n, r) => n + r[key].length, 0);
$('totals').textContent = `${sum('original_boxes')} original → ${sum('merged_boxes')} merged boxes`;
DATA.items.forEach((r,i) => $('recordings').add(new Option(r.id, String(i))));

function refreshProgress() {
  const count = DATA.items.filter(r => reviews[r.id] && reviews[r.id].rating !== 'unreviewed').length;
  $('progress').textContent = `${current+1} / ${DATA.items.length} · Reviewed ${count} / ${DATA.items.length}`;
  [...$('recordings').options].forEach((o,i) => {
    const r=DATA.items[i], v=reviews[r.id];
    o.textContent = `${String(i+1).padStart(2,'0')} · ${r.scientific_name} · ${r.original_boxes.length}→${r.merged_boxes.length}${v && v.rating !== 'unreviewed' ? ' · reviewed' : ''}`;
  });
}
function save() {
  reviews[item().id] = {rating:$('rating').value, notes:$('notes').value,
    target:'merged_gap_le_0.5s', updated_at:new Date().toISOString()};
  let ok = true;
  try { localStorage.setItem(KEY, JSON.stringify(reviews)); storageError=''; }
  catch { storageError='Not saved in browser. Export feedback JSON.'; ok=false; }
  $('saved').textContent=storageError || 'Feedback saved in this browser';
  $('saved').className='status '+(ok?'save':'failure');
  refreshProgress();
  return ok;
}
function load(index) {
  audio.pause(); stopAt=null; current=index; selected=0; timeStart=0; timeEnd=DURATION; ready=false;
  const own=++token, r=item();
  $('recordings').value=String(index);
  $('prev').disabled=index===0; $('next').disabled=index===DATA.items.length-1;
  $('save-next-label').textContent=index===DATA.items.length-1?'Save feedback':'Save and next';
  $('xc').textContent=r.id; $('species').textContent=r.scientific_name;
  $('meta').textContent=`Quality ${r.quality} · ${r.country} · Source label ${r.raw_type} · Local file ${r.clip_start_s.toFixed(3)}–${(r.clip_start_s+DURATION).toFixed(3)} s`;
  $('source').href=r.recording_url || '#'; $('source').hidden=!r.recording_url;
  $('candidate-count').textContent=`${r.original_boxes.length} original → ${r.merged_boxes.length} merged boxes`;
  $('reason').textContent=r.reason; $('limits').textContent=r.limits;
  $('credit').textContent=`Recorded by: ${r.recordist} · ${r.date} · ${r.license}`;
  $('location').textContent=`Location: ${r.location}`;
  $('provenance').textContent=`Standard ${DATA.standard}; mode ${DATA.provenance.mode}; proposal hash ${DATA.source_data_sha256}; grouping ${DATA.grouping_sha256}`;
  const saved=reviews[r.id];
  $('rating').value=saved && labels[saved.rating]?saved.rating:'unreviewed';
  $('notes').value=saved?.notes || '';
  $('saved').textContent=storageError || (saved?'Saved feedback restored':'Unreviewed');
  $('saved').className='status '+(storageError?'failure':'');
  $('notice').textContent='Cyan: original boxes. Orange dashed: merged boxes.';
  // Start with enough frequency context for the candidates, without hiding their tops.
  const maxF=Math.max(0,...r.original_boxes.map(b=>b.f_high_hz));
  $('freq').value=String(maxF ? [750,1500,3000,12000].find(f=>f>=maxF*1.2) || 12000 : 3000);
  audio.src=r.audio; low=new Image(); full=new Image(); wide=new Image();
  let loaded=0;
  const onload=()=>{if(own!==token)return; ready=++loaded===(r.wide_image?3:2); draw();};
  low.onload=onload; full.onload=onload; wide.onload=onload;
  low.onerror=full.onerror=wide.onerror=()=>{if(own===token)$('notice').textContent='Spectrogram failed to load.';};
  low.src=r.image; full.src=r.full_image; if(r.wide_image)wide.src=r.wide_image;
  refreshProgress(); rows();
}
function rows() {
  $('rows').replaceChildren();
  $('table-title').textContent=(mode==='merged'?'Merged coordinates':'Original coordinates')+' · unreviewed';
  $('mode-merged').setAttribute('aria-pressed',mode==='merged');
  $('mode-original').setAttribute('aria-pressed',mode==='original');
  boxes().forEach((b,i)=>{
    const tr=document.createElement('tr');
    if(i===selected)tr.className='selected';
    const td=document.createElement('td'), button=document.createElement('button');
    button.textContent=b.box_id+(b.boundary_truncated?'*':'');
    button.setAttribute('aria-label','Select '+b.box_id);
    button.title=b.boundary_truncated?'Truncated at clip edge':'Select candidate';
    button.onclick=()=>{selected=i; rows();};
    td.append(button); tr.append(td);
    for(const value of [b.t_start_s.toFixed(3),b.t_end_s.toFixed(3),b.f_low_hz,b.f_high_hz]) {
      const cell=document.createElement('td'); cell.textContent=value; tr.append(cell);
    }
    $('rows').append(tr);
  });
  $('empty').hidden=!!boxes().length;
  $('play-box').disabled=$('focus-box').disabled=$('export-raven').disabled=!active();
  const b=active();
  $('members').textContent=!b?'No candidate boxes.':mode==='merged'
    ?`${b.box_id} ← ${b.members.join(' + ')}`
    :`${b.box_id} · original visual proposal`;
  $('group-note').textContent=!b?'Abstained. No boxes does not mean no vocalizations.':mode==='merged'
    ?`${b.members.length} original boxes; maximum internal gap ${b.max_internal_gap_s.toFixed(3)} s。${b.no_shared_frequency_band?'No shared frequency band; check for different sources. ':''}${b.boundary_truncated?'Truncated at clip edge.':''}`
    :`Annotation unit: ${item().unit}。${b.boundary_truncated?'Truncated at clip edge.':''}`;
  draw();
}
function geometry() {
  const w=canvas.clientWidth,h=canvas.clientHeight;
  return {w,h,l:48,r:w-15,t:22,b:h-30,maxF:Number($('freq').value)};
}
function draw() {
  const g=geometry(), dpr=devicePixelRatio||1;
  canvas.width=Math.round(g.w*dpr); canvas.height=Math.round(g.h*dpr);
  ctx.setTransform(dpr,0,0,dpr,0,0); ctx.fillStyle='#11191b'; ctx.fillRect(0,0,g.w,g.h);
  const x=t=>g.l+(t-timeStart)/(timeEnd-timeStart)*(g.r-g.l);
  const y=f=>g.b-f/g.maxF*(g.b-g.t);
  const im=g.maxF<=3000?low:g.maxF<=12000?full:wide, imMax=g.maxF<=3000?3000:g.maxF<=12000?12000:24000;
  if(im.complete && im.naturalWidth)
    ctx.drawImage(im,timeStart*PX_PER_SECOND,600*(1-g.maxF/imMax),(timeEnd-timeStart)*PX_PER_SECOND,
      600*g.maxF/imMax,g.l,g.t,g.r-g.l,g.b-g.t);
  ctx.font='11px -apple-system,sans-serif'; ctx.fillStyle='#ccd6d1'; ctx.textAlign='right';
  for(let i=0;i<=4;i++){const f=g.maxF*i/4;ctx.fillText((f/1000).toFixed(2)+'k',g.l-6,y(f)+4);}
  ctx.textAlign='center';
  for(let i=0;i<=5;i++){const t=timeStart+(timeEnd-timeStart)*i/5;ctx.fillText(t.toFixed(2),x(t),g.b+18);}
  ctx.textAlign='left';ctx.fillText('Hz',6,13);ctx.fillText('s',g.r,g.b+27);
  ctx.save();ctx.beginPath();ctx.rect(g.l,g.t,g.r-g.l,g.b-g.t);ctx.clip();
  const drawLayer=(list,layer,ghost)=>{
    list.forEach((b,i)=>{
      const xx=x(b.t_start_s),yy=y(b.f_high_hz),ww=x(b.t_end_s)-xx,hh=y(b.f_low_hz)-yy;
      ctx.strokeStyle=layer==='merged'?'#ffb875':'#49e4ce';
      ctx.lineWidth=!ghost && i===selected?2.8:1.3;
      ctx.setLineDash(layer==='merged'?[5,4]:[]);
      if(!ghost){ctx.fillStyle=layer==='merged'?'#ffb87516':'#49e4ce16';ctx.fillRect(xx,yy,ww,hh);}
      ctx.strokeRect(xx,yy,ww,hh);
      if(!ghost){ctx.fillStyle=ctx.strokeStyle;ctx.fillText(b.box_id,xx+2,Math.max(g.t+12,yy-5));}
    });
  };
  if($('overlay').checked){const other=mode==='merged'?'original':'merged';drawLayer(item()[other+'_boxes'],other,true);}
  drawLayer(boxes(),mode,false);ctx.setLineDash([]);
  ctx.strokeStyle='#ffffffaa';ctx.lineWidth=1;ctx.beginPath();
  ctx.moveTo(x(audio.currentTime),g.t);ctx.lineTo(x(audio.currentTime),g.b);ctx.stroke();ctx.restore();
  canvas.dataset.ready=String(ready);
}
function changeMode(next) {
  audio.pause();stopAt=null;mode=next;selected=0;rows();
  $('notice').textContent=mode==='merged'?'Orange dashed: merged boxes (≤0.5 s).':'Cyan solid: original boxes. Feedback still targets merged grouping.';
}
$('mode-merged').onclick=()=>changeMode('merged');
$('mode-original').onclick=()=>changeMode('original');
$('recordings').onchange=e=>load(Number(e.target.value));
$('prev').onclick=()=>load(current-1);$('next').onclick=()=>load(current+1);
$('rating').onchange=save;$('notes').oninput=save;
$('save-next').onclick=()=>{if(!save())return;if(current<DATA.items.length-1)load(current+1);else $('notice').textContent='Saved in this browser. Export feedback JSON for a separate copy.';};
$('freq').onchange=$('overlay').onchange=draw;
$('reset').onclick=()=>{timeStart=0;timeEnd=DURATION;draw();};
$('focus-box').onclick=()=>{
  const b=active();if(!b)return;const pad=Math.max(.15,(b.t_end_s-b.t_start_s)*.2);
  timeStart=Math.max(0,b.t_start_s-pad);timeEnd=Math.min(DURATION,b.t_end_s+pad);draw();
};
$('play-box').onclick=async()=>{
  const b=active();if(!b)return;audio.pause();audio.currentTime=Math.max(0,b.t_start_s-.06);
  stopAt=Math.min(DURATION,b.t_end_s+.06);
  try {await audio.play();$('notice').textContent=`Playing ${b.box_id}, including internal gaps, without frequency filtering.`;}
  catch {stopAt=null;$('notice').textContent='Playback failed. Retry using the audio controls.';}
};
audio.addEventListener('timeupdate',()=>{$('cursor').textContent=audio.currentTime.toFixed(3)+' s';draw();});
audio.addEventListener('play',()=>{
  function tick(){if(audio.paused)return;if(stopAt!==null && audio.currentTime>=stopAt){stopAt=null;audio.pause();}
    draw();if(!audio.paused)requestAnimationFrame(tick);}
  requestAnimationFrame(tick);
});
audio.addEventListener('error',()=>{$('notice').textContent='Audio failed to load.';});
canvas.onclick=e=>{
  const g=geometry(),r=canvas.getBoundingClientRect(),px=e.clientX-r.left,py=e.clientY-r.top;
  if(px<g.l||px>g.r||py<g.t||py>g.b)return;
  const t=timeStart+(px-g.l)/(g.r-g.l)*(timeEnd-timeStart),f=(g.b-py)/(g.b-g.t)*g.maxF;
  const hit=boxes().findIndex(b=>t>=b.t_start_s && t<=b.t_end_s && f>=b.f_low_hz && f<=b.f_high_hz);
  if(hit>=0){selected=hit;rows();}
};
function download(blob,name) {
  const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
  $('notice').textContent=`Download requested: ${name}. Check your browser downloads.`;
}
$('export-raven').onclick=()=>download(new Blob([item()[mode+'_tsv']],{type:'text/plain;charset=utf-8'}),
  `${item().id}.${mode}.selections.txt`);
$('export-audio').onclick=()=>{
  const a=document.createElement('a');a.href=item().audio;a.download=item().id+'.wav';a.click();
  $('notice').textContent=`Download requested: ${item().id}.wav.`;
};
$('export-review').onclick=()=>{
  save();
  const result={version:DATA.version,standard:DATA.standard,provenance:DATA.provenance,exported_at:new Date().toISOString(),gap_threshold_s:.5,
    grouping_sha256:DATA.grouping_sha256,source_data_sha256:DATA.source_data_sha256,
    scope:'merged recording-level feedback; not box acceptance',
    items:DATA.items.map(r=>({recording_id:r.id,scientific_name:r.scientific_name,
      original_count:r.original_boxes.length,merged_count:r.merged_boxes.length,
      ...(reviews[r.id]||{rating:'unreviewed',notes:'',target:'merged_gap_le_0.5s'})}))};
  download(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}),'tfbox_gap05_feedback.json');
};
new ResizeObserver(draw).observe(canvas);
lucide.createIcons();
load(0);
