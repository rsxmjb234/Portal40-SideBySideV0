"""
Reusable "Missing data" reconciliation widget injected into both portal views.

Top-bar button -> modal that first asks the DIRECTION of the discrepancy:

  1) "QE has it - PDR does not"
       We capture the source keys to go find it: QE, Source, MRN, plus the
       data element (labels adapt to the screen: Lab / Medication / ...),
       Date, Result and free-text notes.

  2) "PDR has it - QE does not"
       The data is on this PDR screen. Each data row gets a small copy icon;
       clicking it copies a Data ID to the clipboard. The user pastes that ID
       into the form so the ticket records exactly which element is missing.

On "Go" it shows that, at this point, we'd store the ticket as JSON in S3.

Injected by string replacement so page f-string brace escaping is irrelevant.
"""

BUG_CSS = """<style>
  .bug-btn { background:#f97316; color:#fff; border:none; font-weight:700; font-size:13.5px;
    padding:9px 16px; border-radius:8px; cursor:pointer; margin-right:14px;
    box-shadow:0 2px 6px rgba(0,0,0,.18); font-family:inherit; white-space:nowrap; }
  .bug-btn:hover { background:#ea580c; }
  .mrn-btn { background:#f97316; color:#fff; border:none; font-weight:700; font-size:13.5px;
    padding:9px 16px; border-radius:8px; cursor:pointer; margin-right:10px;
    box-shadow:0 2px 6px rgba(0,0,0,.18); font-family:inherit; white-space:nowrap; }
  .mrn-btn:hover { background:#ea580c; }
  .bug-overlay { position:fixed; inset:0; background:rgba(15,23,42,.5); display:none;
    align-items:center; justify-content:center; z-index:9999; }
  .bug-card { background:#fff; width:540px; max-width:94vw; max-height:92vh; overflow:auto;
    border-radius:14px; box-shadow:0 20px 60px rgba(0,0,0,.3);
    font-family:system-ui,"Segoe UI",Arial,sans-serif; color:#1f2a37; }
  .bug-head { background:#f97316; color:#fff; font-weight:700; font-size:16px; padding:14px 18px;
    position:sticky; top:0; display:flex; align-items:center; justify-content:space-between; }
  .bug-x { cursor:pointer; font-size:22px; line-height:1; opacity:.85; padding:0 2px; font-weight:400; }
  .bug-x:hover { opacity:1; }
  .bug-ctx { background:#fff7ed; color:#9a3412; font-size:12px; padding:8px 18px; border-bottom:1px solid #fde4cf; }
  .bug-body { padding:16px 18px; }
  .md-q { font-weight:700; font-size:14px; margin:4px 0 14px; }
  .md-choice { display:block; width:100%; text-align:left; background:#f8fafc; border:1px solid #e5e9ee;
    border-radius:10px; padding:14px 16px; margin-bottom:12px; cursor:pointer; font-family:inherit; }
  .md-choice:hover { border-color:#0ea5a4; background:#f0fdfa; }
  .md-choice b { display:block; font-size:14px; color:#0b7c7b; margin-bottom:4px; }
  .md-choice span { display:block; font-size:12px; color:#6b7280; line-height:1.45; }
  .bug-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px 14px; }
  .bug-row { display:flex; align-items:center; }
  .bug-row span { width:66px; color:#6b7280; font-size:10.5px; text-transform:uppercase; letter-spacing:.4px; }
  .bug-row input { flex:1; padding:7px 10px; border:1px solid #e5e9ee; border-radius:7px;
    background:#f1f5f9; color:#1f2a37; font-size:13px; min-width:0; }
  .bug-row input.edit { background:#fff; border-color:#cfd8dc; }
  .bug-row.mrnrow { align-items:flex-start; }
  .bug-row.mrnrow span { margin-top:7px; }
  .mrnbox { flex:1; min-width:0; font-family:ui-monospace,Menlo,Consolas,monospace; font-size:12px;
    line-height:1.5; background:#f1f5f9; border:1px solid #e5e9ee; border-radius:7px; padding:7px 9px;
    color:#1f2a37; resize:vertical; min-height:92px; }
  .bug-sep { margin:16px 0 10px; font-weight:700; font-size:12px; color:#0b7c7b;
    text-transform:uppercase; letter-spacing:.5px; border-top:1px solid #eef1f4; padding-top:12px; }
  .bug-label { display:block; margin:12px 0 6px; font-weight:600; font-size:13px; }
  .bug-body textarea { width:100%; min-height:70px; padding:9px 11px; border:1px solid #cfd8dc;
    border-radius:8px; font-size:13px; font-family:inherit; resize:vertical; }
  .bug-foot { display:flex; justify-content:space-between; gap:10px; padding:14px 0 0; }
  .bug-primary { background:#0ea5a4; color:#fff; border:none; font-weight:700; padding:9px 20px;
    border-radius:8px; cursor:pointer; font-size:13.5px; }
  .bug-primary:hover { background:#0b7c7b; }
  .bug-secondary { background:#eef2f6; color:#475467; border:1px solid #e5e9ee; font-weight:600;
    padding:9px 16px; border-radius:8px; cursor:pointer; font-size:13.5px; }
  .bug-done { padding:16px 18px 20px; }
  .bug-ok { color:#067647; font-weight:700; font-size:15px; margin-bottom:8px; }
  .bug-done p { color:#475467; font-size:12.5px; margin:6px 0; line-height:1.5; }
  .bug-done pre { background:#0f172a; color:#d1fae5; padding:12px; border-radius:8px;
    font-size:12px; overflow:auto; margin:0; }
  /* per-row copy affordance */
  .pdr-copy { display:inline-block; width:14px; color:#94a3b8; cursor:pointer; margin-right:6px;
    opacity:0; transition:opacity .1s; user-select:none; font-size:12px; }
  tr:hover .pdr-copy, ul.mini li:hover .pdr-copy { opacity:1; }
  .pdr-copy:hover { color:#0ea5a4; }
  .pdr-toast { position:fixed; left:50%; bottom:26px; transform:translateX(-50%);
    background:#0f172a; color:#e2f5f1; padding:9px 16px; border-radius:999px; font-size:12.5px;
    font-family:system-ui,Arial,sans-serif; opacity:0; transition:opacity .2s; z-index:10000;
    pointer-events:none; box-shadow:0 6px 20px rgba(0,0,0,.3); }
  /* drill-in detail modal (IMAT-style blue header) */
  .dtl-head { background:#2196f3; color:#fff; font-weight:700; font-size:16px; padding:14px 18px;
    display:flex; align-items:center; justify-content:space-between; }
  .dtl-sub { background:#e3f2fd; color:#0d47a1; font-size:12.5px; padding:8px 18px; border-bottom:1px solid #bbdefb; }
  table.dtl-tbl { width:100%; border-collapse:collapse; }
  table.dtl-tbl th { text-align:left; width:190px; color:#607d8b; font-weight:600; font-size:12.5px;
    padding:9px 12px; border-bottom:1px solid #eef1f2; vertical-align:top; }
  table.dtl-tbl td { padding:9px 12px; border-bottom:1px solid #eef1f2; vertical-align:top; font-size:13px; }
  .patient tbody tr { cursor:pointer; }
  .patient tbody tr.grp, .patient tbody tr.grouphdr, .patient tbody tr.oru-grp { cursor:default; }
</style>"""

BUG_BTN = '<button type="button" id="bugBtn" class="bug-btn">&#9888; Missing data</button>'
MRN_BTN = '<button type="button" id="mrnBtn" class="mrn-btn">&#9776; MRN Array</button>'

BUG_MODAL = """
<div id="bugModal" class="bug-overlay">
  <div class="bug-card">
    <div class="bug-head"><span>Missing data</span><span class="bug-x" id="bugX" title="Close">&times;</span></div>
    <div class="bug-ctx" id="mdCtx"></div>

    <div class="bug-body md-step" id="step0">
      <p class="md-q">Where is the data missing?</p>
      <button type="button" class="md-choice" id="mdQe">
        <b>QE has it &mdash; PDR does not</b>
        <span>It's in the QE / source feed but not in PDR. We'll capture QE, Source, MRN and the data element so the team can go find it.</span>
      </button>
      <button type="button" class="md-choice" id="mdPdr">
        <b>PDR has it &mdash; QE does not</b>
        <span>It's on this PDR screen but the QE is missing it. Copy the Data ID from the row (hover a row, click the copy icon) and paste it here.</span>
      </button>
    </div>

    <div class="bug-body md-step" id="stepA" style="display:none">
      <div class="bug-grid">
        <div class="bug-row"><span>First</span><input id="aFirst" readonly></div>
        <div class="bug-row"><span>Last</span><input id="aLast" readonly></div>
        <div class="bug-row"><span>DOB</span><input id="aDob" readonly></div>
        <div class="bug-row"><span>Screen</span><input id="aScreen" readonly></div>
      </div>
      <div class="bug-sep">Which QE / source has it? (if known &mdash; it's likely not this screen's source)</div>
      <div class="bug-grid">
        <div class="bug-row"><span>QE</span><input id="aQe" class="edit" placeholder="if known"></div>
        <div class="bug-row"><span>Source</span><input id="aSource" class="edit" placeholder="if known"></div>
        <div class="bug-row"><span>MRN</span><input id="aMrn" class="edit" placeholder="if known"></div>
      </div>
      <div class="bug-sep">What does the QE show that's missing from PDR?</div>
      <div class="bug-grid">
        <div class="bug-row"><span id="aItemLbl">Item</span><input id="aItem" class="edit"></div>
        <div class="bug-row"><span>Date</span><input id="aDate" class="edit" placeholder="MM/DD/YYYY"></div>
        <div class="bug-row" style="grid-column:1 / -1"><span id="aResultLbl">Result</span><input id="aResult" class="edit"></div>
      </div>
      <label class="bug-label" id="aNotesLbl">Describe what you see in the QE we don't show here</label>
      <textarea id="aNotes" placeholder="Optional extra detail..."></textarea>
      <div class="bug-sep">Auto-captured on every ticket</div>
      <div class="bug-row"><span>Date</span><input id="aRptDate" readonly></div>
      <div class="bug-row mrnrow"><span>MRN array</span><textarea id="aMrnArr" class="mrnbox" readonly></textarea></div>
      <div class="bug-foot">
        <button type="button" class="bug-secondary md-back">&larr; Back</button>
        <button type="button" class="bug-primary" id="bugGoA">Go</button>
      </div>
    </div>

    <div class="bug-body md-step" id="stepB" style="display:none">
      <div class="bug-grid">
        <div class="bug-row"><span>First</span><input id="bFirst" readonly></div>
        <div class="bug-row"><span>Last</span><input id="bLast" readonly></div>
        <div class="bug-row"><span>DOB</span><input id="bDob" readonly></div>
        <div class="bug-row"><span>Screen</span><input id="bScreen" readonly></div>
        <div class="bug-row"><span>QE</span><input id="bQe" readonly></div>
        <div class="bug-row"><span>Source</span><input id="bSource" readonly></div>
        <div class="bug-row"><span>MRN</span><input id="bMrn" readonly></div>
      </div>
      <div class="bug-sep">Which PDR element is the QE (<span id="bQeInline"></span>) missing?</div>
      <label class="bug-label">Data ID (copied from a row on the screen)</label>
      <textarea id="bPaste" class="edit" placeholder="Hover a row on the screen, click the copy icon, then paste here..."></textarea>
      <button type="button" class="bug-secondary" id="bUseLast" style="margin-top:8px">Use last copied Data ID</button>
      <label class="bug-label">Notes</label>
      <textarea id="bNotes" placeholder="Anything else the QE should pull in..."></textarea>
      <div class="bug-sep">Auto-captured on every ticket</div>
      <div class="bug-row"><span>Date</span><input id="bRptDate" readonly></div>
      <div class="bug-row mrnrow"><span>MRN array</span><textarea id="bMrnArr" class="mrnbox" readonly></textarea></div>
      <div class="bug-foot">
        <button type="button" class="bug-secondary md-back">&larr; Back</button>
        <button type="button" class="bug-primary" id="bugGoB">Go</button>
      </div>
    </div>

    <div class="bug-done" id="bugDone" style="display:none"></div>
  </div>
</div>
<div id="mrnModal" class="bug-overlay">
  <div class="bug-card" style="width:460px">
    <div class="bug-head"><span>MRN array</span><span class="bug-x" id="mrnX" title="Close">&times;</span></div>
    <div class="bug-ctx" id="mrnCtx"></div>
    <div class="bug-body">
      <p style="margin:0 0 8px;color:#475467;font-size:12.5px">The <b>QE|Source|MRN</b> identifiers that define this person (one per line):</p>
      <textarea id="mrnText" class="mrnbox" readonly style="min-height:160px"></textarea>
      <div class="bug-foot" style="justify-content:flex-end">
        <button type="button" class="bug-secondary" id="mrnDone">Close</button>
        <button type="button" class="bug-primary" id="mrnCopy">Copy</button>
      </div>
    </div>
  </div>
</div>
<div id="dtlModal" class="bug-overlay">
  <div class="bug-card" style="width:580px">
    <div class="dtl-head"><span id="dtlTitle">Detail</span><span class="bug-x" id="dtlX" title="Close">&times;</span></div>
    <div class="dtl-sub" id="dtlPt"></div>
    <div class="bug-body" style="padding:4px 6px"><table class="dtl-tbl" id="dtlBody"></table></div>
    <div class="bug-foot" style="justify-content:flex-end"><button type="button" class="bug-primary" id="dtlClose">Close</button></div>
  </div>
</div>
<div id="pdrToast" class="pdr-toast"></div>
<script>
(function(){
  var MAP={
    'Lab Results':{noun:'Lab', res:'Result', item:'e.g. Hemoglobin A1c', re:'e.g. 7.2 %'},
    'Medications':{noun:'Medication', res:'Dose / Status', item:'e.g. Metformin 500 mg', re:'e.g. Active'},
    'Conditions':{noun:'Condition', res:'Status', item:'e.g. Type 2 diabetes', re:'e.g. Active'},
    'Vitals':{noun:'Vital', res:'Value', item:'e.g. Blood pressure', re:'e.g. 128/82'},
    'Vital Signs':{noun:'Vital', res:'Value', item:'e.g. Blood pressure', re:'e.g. 128/82'},
    'Immunizations':{noun:'Immunization', res:'Status', item:'e.g. Influenza', re:'e.g. Completed'},
    'Allergies':{noun:'Allergy', res:'Reaction', item:'e.g. Penicillin', re:'e.g. Hives'},
    'Procedures':{noun:'Procedure', res:'Outcome', item:'e.g. Appendectomy', re:''},
    'Encounters':{noun:'Encounter', res:'Type', item:'e.g. Hospital admission', re:''},
    'Demographics':{noun:'Demographic', res:'Value', item:'e.g. Phone number', re:''},
    'Summary':{noun:'Item', res:'Value', item:'', re:''},
    'Clinical Summary':{noun:'Item', res:'Value', item:'', re:''}
  };
  var modal=document.getElementById('bugModal');
  function g(id){ return document.getElementById(id); }
  function visiblePatient(){
    var all=Array.prototype.slice.call(document.querySelectorAll('.patient'));
    return all.filter(function(p){ return p.style.display!=='none'; })[0] || all[0];
  }
  function screenOf(p){
    var t=p.querySelector('.tab.active'); if(t) return t.textContent.trim();
    var n=p.querySelector('.nav-item.sel'); if(n) return n.textContent.trim();
    var h=p.querySelector('.viewTitle'); if(h) return h.textContent.trim();
    return 'Summary';
  }
  function parseMrns(p){
    var raw=p.getAttribute('data-mrns')||''; if(!raw) return [];
    return raw.split(';').map(function(e){ var i=e.indexOf(':'); var aa=e.slice(0,i);
      var mrn=e.slice(i+1); var pr=aa.split('|');
      return {qe:pr[0]||'', source:pr[1]||'', mrn:mrn}; });
  }
  function mrnsDisplay(a){ return a.map(function(m){
    return m.qe+(m.source?'|'+m.source:'')+'|'+m.mrn; }).join('\\n'); }
  var curP=null, curScr='';
  function steps(id){
    ['step0','stepA','stepB','bugDone'].forEach(function(s){ g(s).style.display=(s===id?'':'none'); });
  }
  function close(){ modal.style.display='none'; }

  g('bugBtn').addEventListener('click',function(){
    curP=visiblePatient(); if(!curP) return;
    curScr=screenOf(curP);
    var m=MAP[curScr] || {noun:'Item', res:'Value', item:'', re:''};
    g('mdCtx').textContent=(curP.getAttribute('data-first')||'')+' '+(curP.getAttribute('data-last')||'')+'  -  '+curScr;
    // step A fields
    g('aFirst').value=curP.getAttribute('data-first')||'';
    g('aLast').value=curP.getAttribute('data-last')||'';
    g('aDob').value=curP.getAttribute('data-dob')||'';
    g('aScreen').value=curScr;
    // QE defaults to the QE whose portal/view you are in; Source/MRN from the matching identifier
    var viewQe=document.body.getAttribute('data-view-qe')||'';
    var _vm=null, _ml=parseMrns(curP);
    for(var _j=0;_j<_ml.length;_j++){ if(_ml[_j].qe===viewQe){ _vm=_ml[_j]; break; } }
    g('aQe').value=viewQe; g('aSource').value=_vm?_vm.source:''; g('aMrn').value=_vm?_vm.mrn:'';
    g('aItemLbl').textContent=m.noun; g('aResultLbl').textContent=m.res;
    g('aItem').placeholder=m.item; g('aResult').placeholder=m.re;
    g('aItem').value=''; g('aDate').value=''; g('aResult').value=''; g('aNotes').value='';
    g('aNotesLbl').textContent='Describe what '+m.noun.toLowerCase()+' you see in the QE we don\\'t show here';
    // step B (PDR has it / QE doesn't): the patient's own QE IS the one missing it -> prefill
    g('bFirst').value=g('aFirst').value; g('bLast').value=g('aLast').value;
    g('bDob').value=g('aDob').value; g('bScreen').value=curScr;
    g('bQe').value=viewQe||(curP.getAttribute('data-qe')||''); g('bSource').value=_vm?_vm.source:(curP.getAttribute('data-source')||'');
    g('bMrn').value=_vm?_vm.mrn:(curP.getAttribute('data-mrn')||'');
    g('bQeInline').textContent=(viewQe||curP.getAttribute('data-qe')||'QE');
    g('bPaste').value=''; g('bNotes').value='';
    // auto-captured metadata for every ticket, regardless of direction
    var _mrns=parseMrns(curP); var _disp=mrnsDisplay(_mrns); var _today=new Date().toLocaleDateString();
    window.__mrnArr=_mrns; window.__today=_today;
    g('aRptDate').value=_today; g('aMrnArr').value=_disp;
    g('bRptDate').value=_today; g('bMrnArr').value=_disp;
    steps('step0');
    modal.style.display='flex';
  });
  g('mdQe').addEventListener('click',function(){ steps('stepA'); });
  g('mdPdr').addEventListener('click',function(){ steps('stepB'); });
  Array.prototype.forEach.call(document.querySelectorAll('.md-back'),function(b){
    b.addEventListener('click',function(){ steps('step0'); });
  });
  g('bUseLast').addEventListener('click',function(){
    if(window.__pdrLastId) g('bPaste').value=window.__pdrLastId;
  });
  g('bugX').addEventListener('click',close);
  document.addEventListener('keydown',function(e){ if(e.key==='Escape' && modal.style.display==='flex') close(); });
  modal.addEventListener('click',function(e){ if(e.target===modal) close(); });

  function done(payload){
    var id=payload.ticket;
    var d=g('bugDone');
    d.innerHTML='<div class="bug-ok">\\u2713 Ticket '+id+' captured</div>'+
      '<p>At this point we would store this as a ticket in S3 '+
      '(s3://nyec-synthetic-data/tickets/'+id+'.json) for the reconciliation team:</p>'+
      '<pre>'+JSON.stringify(payload,null,2).replace(/</g,'&lt;')+'</pre>'+
      '<div class="bug-foot" style="justify-content:flex-end"><button type="button" class="bug-primary" id="bugClose2">Close</button></div>';
    steps('bugDone');
    g('bugClose2').addEventListener('click',close);
  }
  function tid(){ return 'BUG-'+String(Date.now()).slice(-6); }

  g('bugGoA').addEventListener('click',function(){
    done({ ticket:tid(), direction:'QE_HAS__PDR_MISSING',
      patient:{first:g('aFirst').value,last:g('aLast').value,dob:g('aDob').value},
      qeThatHasIt:g('aQe').value, source:g('aSource').value, mrn:g('aMrn').value,
      screen:g('aScreen').value, dataType:g('aItemLbl').textContent,
      item:g('aItem').value, date:g('aDate').value, result:g('aResult').value,
      notes:g('aNotes').value,
      reportDate:window.__today, mrnArray:window.__mrnArr,
      createdAt:new Date().toISOString() });
  });
  g('bugGoB').addEventListener('click',function(){
    done({ ticket:tid(), direction:'PDR_HAS__QE_MISSING',
      patient:{first:g('bFirst').value,last:g('bLast').value,dob:g('bDob').value},
      qeMissingIt:g('bQe').value, source:g('bSource').value, mrn:g('bMrn').value,
      screen:g('bScreen').value, dataId:g('bPaste').value,
      notes:g('bNotes').value,
      reportDate:window.__today, mrnArray:window.__mrnArr,
      createdAt:new Date().toISOString() });
  });

  // ---- per-row copy affordance (for "PDR has it" direction) ----
  function toast(msg){ var t=g('pdrToast'); t.textContent=msg; t.style.opacity='1';
    clearTimeout(window.__pt); window.__pt=setTimeout(function(){ t.style.opacity='0'; },2600); }
  function elToken(host){
    var p=host.closest('.patient');
    var base='PDR|mrn='+(p?p.getAttribute('data-mrn'):'')+'|qe='+(p?p.getAttribute('data-qe'):'')+
             '|src='+(p?p.getAttribute('data-source'):'');
    var txt;
    if(host.tagName==='TR'){
      txt=Array.prototype.slice.call(host.cells).map(function(c){
        return c.innerText.replace(/\\u29C9/g,'').trim(); }).filter(Boolean).join(' | ');
    } else {
      txt=host.innerText.replace(/\\u29C9/g,'').replace(/\\s+/g,' ').trim();
    }
    return base+'|'+txt;
  }
  function addCopy(container){
    var s=document.createElement('span');
    s.className='pdr-copy'; s.title='Copy Data ID (for \u201cPDR has it, QE does not\u201d)';
    s.textContent='\\u29C9';
    container.insertBefore(s, container.firstChild);
  }
  // table rows (both views' detail tables)
  Array.prototype.forEach.call(document.querySelectorAll('.patient table tbody tr'),function(tr){
    if(!tr.cells || !tr.cells.length) return;
    if(tr.querySelector('td[colspan]')) return;          // skip group-header rows
    addCopy(tr.cells[0]);
  });
  // summary-card list items (Hixny/SMART landing cards show data as lists, not tables)
  Array.prototype.forEach.call(document.querySelectorAll('.patient ul.mini li'),function(li){
    addCopy(li);
  });
  document.addEventListener('click',function(e){
    var s=e.target.closest ? e.target.closest('.pdr-copy') : null;
    if(!s) return;
    e.stopPropagation(); e.preventDefault();
    var host=s.closest('tr') || s.closest('li');
    if(!host) return;
    var tok=elToken(host);
    window.__pdrLastId=tok;
    try { if(navigator.clipboard) navigator.clipboard.writeText(tok); } catch(err){}
    toast('Data ID copied \\u2014 open \u201cMissing data\u201d \u2192 PDR has it, then paste');
  });

  // ---- MRN Array button ----
  var mrnModal=g('mrnModal');
  function mrnClose(){ mrnModal.style.display='none'; }
  g('mrnBtn').addEventListener('click',function(){
    var p=visiblePatient(); if(!p) return;
    g('mrnCtx').textContent=(p.getAttribute('data-first')||'')+' '+(p.getAttribute('data-last')||'');
    g('mrnText').value=mrnsDisplay(parseMrns(p));
    mrnModal.style.display='flex';
  });
  g('mrnX').addEventListener('click',mrnClose);
  g('mrnDone').addEventListener('click',mrnClose);
  mrnModal.addEventListener('click',function(e){ if(e.target===mrnModal) mrnClose(); });
  g('mrnCopy').addEventListener('click',function(){
    var t=g('mrnText'); t.focus(); t.select();
    try { if(navigator.clipboard) navigator.clipboard.writeText(t.value); else document.execCommand('copy'); } catch(e){}
    toast('MRN array copied');
  });

  // ---- drill-in detail: click any data row to see its full record ----
  function _esc(s){ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;'); }
  var dtl=g('dtlModal');
  function dtlClose(){ dtl.style.display='none'; }
  function openDetail(tr){
    var table=tr.closest('table'); if(!table) return;
    var ths=table.querySelectorAll('thead th');
    var pat=tr.closest('.patient');
    var scr=pat?screenOf(pat):'';
    g('dtlTitle').textContent=(scr||'Record')+' \\u2013 detail';
    var nm=pat?((pat.getAttribute('data-first')||'')+' '+(pat.getAttribute('data-last')||'')):'';
    var dob=pat?(pat.getAttribute('data-dob')||''):'';
    var src=pat?((pat.getAttribute('data-qe')||'')+(pat.getAttribute('data-source')?'|'+pat.getAttribute('data-source'):'')+' MRN '+(pat.getAttribute('data-mrn')||'')):'';
    g('dtlPt').innerHTML='<b>'+_esc(nm)+'</b> &middot; DOB '+_esc(dob)+' &middot; '+_esc(src);
    var out='';
    for(var i=0;i<tr.cells.length;i++){
      var c=tr.cells[i];
      if(c.classList.contains('ic')) continue;
      var lbl=ths[i]?ths[i].textContent.replace(/[\\u21C5\\u2191\\u2193\\u25B2\\u25BC\\u2195]/g,'').trim():'';
      var val=c.innerText.replace(/\\u29C9/g,'').trim();
      if(!lbl && !val) continue;
      out+='<tr><th>'+_esc(lbl||'Value')+'</th><td>'+(_esc(val)||'&ndash;')+'</td></tr>';
    }
    // extra fields carried on the row but not shown as columns (data-extra JSON)
    var ex=tr.getAttribute('data-extra');
    if(ex){
      try{ var pairs=JSON.parse(ex);
        for(var k=0;k<pairs.length;k++){
          var lb=pairs[k][0], vv=pairs[k][1];
          if(vv===''||vv==null) continue;
          out+='<tr><th>'+_esc(lb)+'</th><td>'+_esc(vv)+'</td></tr>';
        }
      }catch(err){}
    }
    g('dtlBody').innerHTML=out;
    dtl.style.display='flex';
  }
  g('dtlX').addEventListener('click',dtlClose);
  g('dtlClose').addEventListener('click',dtlClose);
  dtl.addEventListener('click',function(e){ if(e.target===dtl) dtlClose(); });
  document.addEventListener('keydown',function(e){ if(e.key==='Escape' && dtl.style.display==='flex') dtlClose(); });
  document.addEventListener('click',function(e){
    if(!e.target.closest) return;
    if(e.target.closest('.pdr-copy')) return;          // copy icon has its own handler
    var tr=e.target.closest('.patient tbody tr');
    if(!tr || !tr.cells || !tr.cells.length) return;
    if(tr.querySelector('td[colspan]')) return;        // group-header row
    openDetail(tr);
  });
})();
</script>
"""


def inject(html):
    """Add the Missing-data report button, modal, and per-row copy icons."""
    html = html.replace('</head>', BUG_CSS + '\n</head>', 1)
    html = html.replace('<div class="spacer"></div>',
                        '<div class="spacer"></div>' + MRN_BTN + BUG_BTN, 1)
    html = html.replace('</body>', BUG_MODAL + '\n</body>', 1)
    return html
