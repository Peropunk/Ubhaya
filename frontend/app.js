// UBHAYA case workspace. Served locally with no frontend build step.
"use strict";

const $ = (sel) => document.querySelector(sel);
const api = async (path) => {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json();
};
const el = (tag, attrs = {}, ...kids) => {
  const n = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") n.className = v;
    else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
    else n.setAttribute(k, v);
  }
  for (const k of kids) n.append(k instanceof Node ? k : document.createTextNode(k ?? ""));
  return n;
};
const fmtSize = (b) => (b < 1024 ? `${b} B` : b < 1048576 ? `${(b / 1024).toFixed(1)} KB` : `${(b / 1048576).toFixed(1)} MB`);
const ROLE = { complainant: "Complainant", suspect: "Suspect", witness: "Witness" };
const LANG = { en: "English", "hi-Latn": "Hinglish", hi: "Hindi" };
const caseTitle = (c) => c.synthetic ? c.title.replace(/ \(synthetic demo\)$/i, "") : c.title;

const VERDICT = {supported:"Supported", contradicted:"Contradicted", uncertain:"Uncertain", no_evidence:"No evidence"};
const TYPES = {door_log:"Door log", pc_event_log:"PC event log", bank_upi:"UPI statement",
  chat_export:"Chat export", cctv_still:"CCTV still", calibration:"Calibration",
  site_config:"Site configuration", statement:"Statement"};
const tabs = [...document.querySelectorAll(".tab")];
const views = tabs.map(tab => tab.dataset.view);
let loaded = false;

function showView() {
  const hash = location.hash.slice(1);
  const view = views.includes(hash) ? hash : hash.startsWith("request-") ? "requests" : "overview";
  for (const id of views) document.getElementById(id).hidden = !loaded || id !== view;
  for (const tab of tabs) {
    if (tab.dataset.view === view) {
      tab.setAttribute("aria-current", "page");
    } else tab.removeAttribute("aria-current");
  }
  window.scrollTo(0, 0);
  if (view === "requests" && hash.startsWith("request-")) document.getElementById(hash)?.scrollIntoView();
}
window.addEventListener("hashchange", showView);

let artifactViewRequest = 0;
let claimViewRequest = 0;
let state = { caseId: null, artifacts: [], eventCounts: {} };

async function init() {
  $("#empty").hidden = true;
  $("#case-loading").hidden = false;
  $("#case-select").disabled = true;
  const cases = await api("/cases");
  const sel = $("#case-select");
  sel.replaceChildren(...cases.map((c) => el("option", { value: c.id }, `${c.id} ${caseTitle(c)}`)));
  if (!cases.length) {
    $("#case-loading").hidden = true;
    $("#empty").hidden = false;
    $("#retry-case").hidden = true;
    $("#case-message").textContent = "No case loaded. Run python manage.py load-demo and refresh.";
    return;
  }
  const remembered = (() => { try { return localStorage.getItem("ubhaya.case"); } catch { return null; } })();
  sel.value = cases.some((c) => c.id === remembered) ? remembered : cases[cases.length - 1].id;
  sel.onchange = () => loadCase(sel.value).catch(showError);
  await loadCase(sel.value);
}

async function loadCase(caseId) {
  artifactViewRequest++;
  claimViewRequest++;
  state.caseId = caseId;
  loaded = false;
  showView();
  $("#viewer").close();
  $("#detail").close();
  $("#case-select").disabled = true;
  $("#empty").hidden = true;
  $("#case-loading").hidden = false;
  try { localStorage.setItem("ubhaya.case", caseId); } catch {}
  const [c, artifacts, statements, events] = await Promise.all([
    api(`/cases/${caseId}`), api(`/cases/${caseId}/artifacts`),
    api(`/cases/${caseId}/statements`), api(`/cases/${caseId}/events`),
  ]);
  if (state.caseId !== caseId) return;
  state.statements = statements;
  $("#analysis-status").textContent = "";
  $("#verify-status").textContent = "";
  $("#stat-chain").textContent = "Checking…";
  state.artifacts = artifacts;
  state.eventCounts = events.reduce((m, e) => ((m[e.artifact_id] = (m[e.artifact_id] || 0) + 1), m), {});

  $("#case-title").textContent = caseTitle(c);
  $("#case-scope").textContent = c.scope || "";
  $("#synthetic-badge").hidden = !c.synthetic;
  $("#stat-artifacts").textContent = c.artifact_count;
  $("#stat-statements").textContent = c.statement_count;
  $("#stat-events").textContent = c.event_count;
  renderArtifacts();
  await refreshAnalysis(caseId);
  if (state.caseId !== caseId) return;
  loaded = true;
  $("#case-loading").hidden = true;
  $("#case-select").disabled = false;
  showView();
  checkChain();
}

function renderArtifacts() {
  const rows = state.artifacts.map((a) => el("tr", { "data-id": a.id },
    el("td", {class:"file-cell"}, el("button", {class:"link", onclick:() => openArtifact(a)}, a.filename),
      el("small", {class:"muted"}, TYPES[a.type] || a.type)),
    el("td", { class: "num" }, state.eventCounts[a.id] || "—"),
    el("td", { class: "integrity" }, el("button", { class: "small", onclick: async (e) => { await verify(a.id, e.target.closest("td")); checkChain(); } }, "Verify")),
  ));
  if (!rows.length) rows.push(el("tr", {}, el("td", {colspan:"3"}, "This case has no evidence files.")));
  $("#artifacts tbody").replaceChildren(...rows);
  $("#btn-verify-all").disabled = !state.artifacts.length;
}

async function verify(artifactId, cell) {
  cell.replaceChildren(el("span", { class: "badge idle" }, "Checking…"));
  try {
    const r = await api(`/artifacts/${artifactId}/verify`);
    cell.replaceChildren(el("span", { class: `badge ${r.ok ? "ok" : "bad"}`, title: `expected ${r.expected}\nactual   ${r.actual}` }, r.ok ? "Hash matches" : "Mismatch"));
    return r.ok;
  } catch (err) {
    cell.replaceChildren(el("button", {class:"small bad", onclick:() => verify(artifactId, cell)}, "Retry check"));
    return false;
  }
}

async function verifyAll() {
  const btn = $("#btn-verify-all");
  btn.disabled = true;
  const cid = state.caseId;
  const status = $("#verify-status");
  status.textContent = "Checking evidence hashes…";
  let matches = 0;
  const total = state.artifacts.length;
  try {
    for (const a of state.artifacts) {
      const cell = document.querySelector(`tr[data-id="${a.id}"] td.integrity`);
      if (cid !== state.caseId || !cell) break;
      if (await verify(a.id, cell)) matches++;
    }
  } finally {
    btn.disabled = !state.artifacts.length;
  }
  if (cid === state.caseId) {
    status.textContent = `${matches} of ${total} hashes match.`;
    checkChain();
  }
}

async function checkChain() {
  const out = $("#stat-chain");
  const cid = state.caseId;
  out.textContent = "Checking…";
  let r;
  try { r = await api(`/cases/${cid}/audit/verify`); }
  catch {
    if (cid === state.caseId) out.textContent = "Check failed";
    return;
  }
  if (cid !== state.caseId) return;
  out.replaceChildren(el("span", { class: `badge ${r.ok ? "ok" : "bad"}`, title: r.ok ? r.entries + " audit entries" : r.reason || "" },
    r.ok ? "Intact" : `Broken at entry ${r.broken_at}`));
}

async function openArtifact(a, locator, event) {
  const request = ++artifactViewRequest;
  const viewer = $("#viewer");
  const body = $("#viewer-body");
  $("#viewer-title").textContent = a.filename;
  const copied = el("span", {role:"status"});
  const copy = el("button", {onclick:async () => {
    try { await navigator.clipboard.writeText(a.sha256); copied.textContent = "Copied"; }
    catch { copied.textContent = "Select the digest to copy it."; }
  }}, "Copy SHA-256");
  const meta = el("div", {}, el("p", {class:"muted"}, [a.id, a.source, fmtSize(a.size)].filter(Boolean).join(" · ")),
    el("p", {}, el("code", {}, a.sha256)), copy, " ", copied);
  if (event?.t_min && event?.t_max) meta.append(el("p", {class:"muted"},
    "Normalized interval ", el("code", {}, event.t_min), " to ", el("code", {}, event.t_max)));
  const content = el("div", {role:"status"}, "Loading source…");
  body.replaceChildren(meta, content);
  if (!viewer.open) viewer.showModal();
  const url = `/artifacts/${a.id}/content`;
  if (a.filename.endsWith(".png")) {
    const image = el("img", {src:url, alt:`Stored CCTV frame from ${a.filename}`,
      onerror:() => { content.textContent = "Could not open this frame. Close the viewer and try again."; }});
    content.replaceChildren(image);
  } else {
    let text;
    try {
      const response = await fetch(url);
      if (!response.ok) throw Error("Source unavailable (HTTP "+response.status+")");
      text = await response.text();
    } catch (error) {
      if (request === artifactViewRequest) {
        content.textContent = "Could not open the source file. Close the viewer and try again.";
      }
      return;
    }
    if (request !== artifactViewRequest) return;
    const lines = text.split("\n");
    const numbered = lines.map((l, i) => `${String(a.filename.endsWith(".csv") ? i : i+1).padStart(4)}  ${l}`).join("\n");
    content.replaceChildren(el("p", { class: "muted" }, a.filename.endsWith(".csv") ? "Line 0 is the header; row N is line N." : ""),
      el("pre", {}, numbered));
  }
  if (!state.artifacts.some(art => art.id === a.id)) return;
  if (locator) {
    const pre = content.querySelector("pre");
    if (pre) {
      const rows = pre.textContent.split("\n");
      const idx = Number(locator.split(" ")[1]) - (locator.startsWith("line") ? 1 : 0);
      if (!Number.isInteger(idx) || idx < 0 || idx >= rows.length) return;
      const marked = el("mark", {}, rows[idx]);
      pre.replaceChildren(rows.slice(0,idx).join("\n")+"\n", marked, "\n"+rows.slice(idx+1).join("\n"));
      requestAnimationFrame(() => marked.scrollIntoView({block:"center"}));
    }
  }
}

$("#btn-verify-all").onclick = verifyAll;
$("#btn-chain").onclick = checkChain;
$("#viewer-close").onclick = () => { artifactViewRequest++; $("#viewer").close(); };
$("#detail-close").onclick = () => { claimViewRequest++; $("#detail").close(); };
$("#viewer").addEventListener("cancel", () => artifactViewRequest++);
$("#detail").addEventListener("cancel", () => claimViewRequest++);
function showError(err) {
  $("#case-loading").hidden = true;
  $("#empty").hidden = false;
  $("#retry-case").hidden = false;
  $("#case-message").textContent = "Could not load case data. Check that UBHAYA is still running, then retry.";
  $("#case-message").title = err.message;
}
$("#retry-case").onclick = () => init().catch(showError);
init().catch(showError);

async function submit(path, body) {
  const options = {method:"POST"};
  if (body) Object.assign(options,{headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
  const response = await fetch(path,options);
  if (!response.ok) throw Error((await response.json()).detail || response.statusText);
  return response.json();
}

function labeled(label, input) {
  input.setAttribute("aria-label", label);
  return el("label", {class:"field"}, el("span", {}, label), input);
}

function reviewForm(target) {
  const reviewer = el("input",{required:"",autocomplete:"name"});
  const reason = el("input",{required:""});
  const decision = el("select",{},...["accept","reject","edit"].map(v=>el("option",{value:v},v)));
  const status = el("span",{role:"status"});
  return el("form",{onsubmit:async ev=>{
    ev.preventDefault();
    const button = ev.submitter;
    if (button) button.disabled = true;
    status.textContent = "Saving review…";
    try {
      await submit("/reviews",{target_id:target,reviewer:reviewer.value,reason:reason.value,decision:decision.value,
        edit:decision.value==="edit"?{annotation:reason.value}:null});
      status.textContent="Review recorded";
    } catch(err) {status.textContent = "Could not save the review. " + err.message;}
    finally { if (button) button.disabled = false; }
  }},labeled("Reviewer", reviewer),labeled("Decision", decision),labeled("Reason", reason),el("button",{type:"submit"},"Save review"),status);
}

async function openClaim(id) {
  const cid=state.caseId;
  const request = ++claimViewRequest;
  const panel = $("#detail");
  const content = panel.querySelector(".drawer-content");
  content.replaceChildren(el("p", {role:"status"}, "Loading claim…"));
  if (!panel.open) panel.showModal();
  panel.scrollTop = 0;
  let data;
  try { data = await api("/claims/"+id); }
  catch (err) {
    if (request === claimViewRequest) content.textContent = "Could not load the claim. Close the panel and try again.";
    return;
  }
  if (state.caseId!==cid || request!==claimViewRequest) return;
  const f=data.finding;
  if (!f) {
    content.replaceChildren(el("blockquote",{},data.claim.quote),el("p",{},"Analyze this case to see a finding."));
    return;
  }
  const why = el("details",{},el("summary",{},"Why this finding?"),el("p",{},data.rationale.summary));
  if (data.claim.t_min && data.claim.t_max) {
    why.append(el("p",{},"Claim window in IST ", el("code", {}, data.claim.t_min), " to ", el("code", {}, data.claim.t_max)));
  }
  for (const rule of data.rationale.rules) why.append(el("p",{},el("code", {}, rule.id), " ", rule.reason));
  if (!data.rationale.rules.length) why.append(el("p",{},"No contradiction rule fired."));
  if (data.rationale.unresolved) why.append(el("p",{},el("strong",{},"Open question "),data.rationale.unresolved));
  const next = state.requests?.find(r=>r.claim_ids.includes(id));
  if (next) why.append(el("a",{href:"#request-"+next.catalogue_id, onclick:()=>panel.close()},"View request for "+next.title));
  const sources = el("section", {class:"sources"}, el("h3", {}, "Cited evidence"));
  const records = data.events.flatMap(event => {
    const artifact = state.artifacts.find(file => file.id === event.artifact_id);
    if (!artifact) return [];
    const locator = el("span", {class:"locator mono"}, event.locator);
    const file = el("span", {class:"source-file"}, artifact.filename, locator);
    const recorded = el("time", {}, event.original_time + " " + event.original_tz);
    return [el("li", {}, el("button", {class:"source-row", onclick:() => openArtifact(artifact, event.locator, event)}, file, recorded))];
  });
  sources.append(records.length ? el("ul", {class:"source-list"}, ...records) : el("p", {class:"muted"}, "No records cited for this finding."));
  content.replaceChildren(
    el("blockquote", {}, data.claim.quote),
    el("p", {}, el("span", {class:"badge "+f.verdict}, VERDICT[f.verdict]),
      f.strength ? " Evidence strength: " + f.strength : ""),
    why, sources,
    ...data.reviews.map(r => el("p", {}, r.reviewer + " (" + r.decision + "): " + r.reason)),
    el("h3", {}, "Record a review"), reviewForm(f.id));
  const more=el("div",{});
  for(const alt of data.alternatives) more.append(el("p",{},(alt.ai_generated ? "AI suggestion · " : "Template suggestion · ")+alt.text+" · "+alt.event_ids.join(", ")));
  if (["uncertain","contradicted"].includes(f.verdict)) {
    more.append(el("button",{onclick:async ev=>{
      ev.target.disabled=true;
      try{await submit("/claims/"+id+"/alternatives");if (request===claimViewRequest) await openClaim(id);}
      catch(err){more.append(el("p",{},err.message));ev.target.disabled=false;}
    }},"Suggest alternatives"));
  }
  content.append(more);
}

async function refreshAnalysis(cid) {
  const base="/cases/"+cid;
  const [claims,board,requests,events,alerts]=await Promise.all([
    api(base+"/claims"),api(base+"/accounts"),api(base+"/requests"),
    api(base+"/timeline?calibrated="+$("#calibrated").checked),api(base+"/observations?calibrated="+$("#calibrated").checked)]);
  if (state.caseId!==cid) return;
  const findings = claims.filter(c => c.finding);
  $("#analysis-status").textContent = findings.length
    ? findings.length + " findings"
    : "Run analysis to check claims against the evidence.";
  $("#verdict-summary").replaceChildren(...(findings.length ? Object.entries(VERDICT).map(([key, label]) =>
    el("span", {class:"badge "+key}, findings.filter(c => c.finding.verdict === key).length+" "+label.toLowerCase())) : []));
  state.requests=requests;
  const statements=$("#statements");
  statements.replaceChildren(...state.statements.map(s=>{
    const content=el("p",{lang:s.language});
    const chars=Array.from(s.text);
    let end=0;
    for(const c of claims.filter(c=>c.statement_id===s.id)) {
      content.append(chars.slice(end,c.char_start).join(""),el("button",{class:"claim "+(c.finding?.verdict||""),onclick:()=>c.finding&&openClaim(c.id)},c.quote));
      end=c.char_end;
    }
    content.append(chars.slice(end).join(""));
    const quote=el("textarea",{required:"","aria-label":"Exact claim quote"});
    const kind=el("select",{"aria-label":"Claim type"},...["presence","absence","time","action","amount","identity","relationship"].map(k=>el("option",{value:k},k)));
    const action=el("input",{placeholder:"Action (e.g. file_copy)","aria-label":"Claim action"});
    const status=el("span",{role:"status"});
    const manual=el("details",{},el("summary",{},"Add manual claim"),el("form",{onsubmit:async e=>{
      e.preventDefault();try{await submit(base+"/statements/"+s.id+"/manual-claims",{quote:quote.value,type:kind.value,action:action.value});await refreshAnalysis(cid);}
      catch(err){status.textContent=err.message;}
    }},labeled("Exact claim quote", quote),labeled("Claim type", kind),labeled("Claim action", action),el("button",{},"Save exact quote"),status));
    return el("article",{},el("h2",{},s.speaker),
      el("small",{class:"muted"},[ROLE[s.role] || s.role, LANG[s.language] || s.language].join(", ")),content,manual);
  }));
  if (!state.statements.length) statements.append(el("p", {class:"muted"}, "This case has no statements."));
  $("#timeline > .panel-list").replaceChildren(...alerts.map(a=>el("article",{},el("p",{},a.certainty+" · "+a.explanation),...a.reviews.map(r=>el("p",{},r.decision+" · "+r.reviewer+" · "+r.reason)),reviewForm(a.id))),
    ...state.artifacts.filter(a=>a.type==="cctv_still"&&!events.some(e=>e.artifact_id===a.id)).map(a=>{
      const timestamp=el("input",{type:"datetime-local",step:"1",required:"","aria-label":"Observed local time"});
      const reviewer=el("input",{placeholder:"Reviewer",required:"","aria-label":"Reviewer"});
      const status=el("span",{role:"status"});
      return el("form",{onsubmit:async e=>{e.preventDefault();try{
        await submit("/artifacts/"+a.id+"/manual-time?"+new URLSearchParams({timestamp:timestamp.value,reviewer:reviewer.value}));await refreshAnalysis(cid);
      }catch(err){status.textContent=err.message;}}},
      el("button",{type:"button",class:"link",onclick:()=>openArtifact(a)},a.filename),el("strong",{},"Manual time required"),labeled("Observed local time",timestamp),labeled("Reviewer",reviewer),el("button",{},"Record time"),status);
    }),
    el("details",{},el("summary",{},events.length+" events"),...events.map(e=>el("p",{},e.original_time+" "+e.original_tz+" → "+e.t_min+" – "+e.t_max+" · "+e.action+" · "+e.locator+(e.calibration?" · "+e.calibration.source_id:"")))));
  $("#accounts > .cards").replaceChildren(...Object.entries(board).map(([speaker,groups])=>el("article",{},el("h3",{},speaker),
    ...Object.entries(groups).map(([name,list])=>el("details",{},el("summary",{},name+" ("+list.length+")"),
      ...list.map(c=>el("p",{},el("button",{class:"link",onclick:()=>openClaim(c.id)},c.quote))))))));
  if (!Object.keys(board).length) $("#accounts > .cards").append(el("p", {class:"muted"}, "Analyze the case to see findings by account."));
  const exports = el("article", {}, el("h2", {}, "Case report"),
    el("div", {class:"export-actions"},
      el("a", {class:"action", href:base+"/report.json", download:"report.json"}, "Download JSON"),
      el("a", {class:"action", href:base+"/report.pdf", download:"report.pdf"}, "Download PDF")));
  const drafts = requests.map(r => el("article", {id:"request-"+r.catalogue_id},
    el("h3", {}, r.title), el("p", {class:"muted"}, "Priority score "+r.score),
    el("details", {}, el("summary", {}, "Score breakdown"), el("p", {}, Object.entries(r.score_parts)
      .map(([label, value]) => label.replaceAll("_", " ")+" "+value).join(" · "))),
    el("textarea", {"aria-label":"Request draft"}, r.draft_text)));
  $("#requests > .panel-list").replaceChildren(exports, ...drafts);
  if (!drafts.length) $("#requests > .panel-list").append(el("p", {class:"muted"}, "Run analysis to see ranked evidence requests."));
}
$("#calibrated").onchange=()=>refreshAnalysis(state.caseId).catch(showError);
async function analyzeCase() {
  const cid=state.caseId;
  const buttons = [$("#analyze"), $("#analyze-statements")];
  const status = $("#analysis-status");
  for (const button of buttons) button.disabled = true;
  location.hash = "statements-section";
  status.textContent = "Checking statements against the evidence…";
  try {
    await submit("/cases/"+cid+"/analyze");
    if (cid === state.caseId) {
      await refreshAnalysis(cid);
      checkChain();
    }
  } catch(err) {
    if (cid === state.caseId) status.textContent = "Could not analyze the case. " + err.message;
  } finally {
    for (const button of buttons) button.disabled = false;
  }
}
$("#analyze").onclick = analyzeCase;
$("#analyze-statements").onclick = analyzeCase;
