// UBHAYA interface, screen 1: case overview (P1.5). Plain JS, no build step, no network beyond the local API.
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

let state = { caseId: null, artifacts: [], eventCounts: {} };

async function init() {
  const cases = await api("/cases");
  const sel = $("#case-select");
  sel.replaceChildren(...cases.map((c) => el("option", { value: c.id }, `${c.id}  ${c.title}`)));
  if (!cases.length) { $("#empty").hidden = false; return; }
  const remembered = (() => { try { return localStorage.getItem("ubhaya.case"); } catch { return null; } })();
  sel.value = cases.some((c) => c.id === remembered) ? remembered : cases[cases.length - 1].id;
  sel.onchange = () => loadCase(sel.value);
  await loadCase(sel.value);
}

async function loadCase(caseId) {
  state.caseId = caseId;
  try { localStorage.setItem("ubhaya.case", caseId); } catch {}
  const [c, artifacts, statements, events] = await Promise.all([
    api(`/cases/${caseId}`), api(`/cases/${caseId}/artifacts`),
    api(`/cases/${caseId}/statements`), api(`/cases/${caseId}/events`),
  ]);
  state.artifacts = artifacts;
  state.eventCounts = events.reduce((m, e) => ((m[e.artifact_id] = (m[e.artifact_id] || 0) + 1), m), {});

  $("#case-title").textContent = c.title;
  $("#case-scope").textContent = c.scope || "";
  $("#synthetic-badge").hidden = !c.synthetic;
  $("#stat-artifacts").textContent = c.artifact_count;
  $("#stat-statements").textContent = c.statement_count;
  $("#stat-events").textContent = c.event_count;
  for (const id of ["#case-head", "#artifacts-section", "#statements-section"]) $(id).hidden = false;
  renderArtifacts();
  renderStatements(statements);
  checkChain();
}

function renderArtifacts() {
  const rows = state.artifacts.map((a) => el("tr", { "data-id": a.id },
    el("td", { class: "mono" }, a.id),
    el("td", {}, el("button", { class: "link", onclick: () => openArtifact(a) }, a.filename)),
    el("td", {}, el("span", { class: "badge type" }, a.type)),
    el("td", { class: "muted" }, a.source || ""),
    el("td", { class: "num" }, fmtSize(a.size)),
    el("td", { class: "num" }, state.eventCounts[a.id] ? String(state.eventCounts[a.id]) : "-"),
    el("td", {}, el("span", { class: "hash", title: `${a.sha256}\nClick to copy`, onclick: () => navigator.clipboard?.writeText(a.sha256) }, `${a.sha256.slice(0, 12)}…`)),
    el("td", { class: "integrity" }, el("button", { class: "small", onclick: (e) => verify(a.id, e.target.closest("td")) }, "Verify")),
  ));
  $("#artifacts tbody").replaceChildren(...rows);
}

async function verify(artifactId, cell) {
  cell.replaceChildren(el("span", { class: "badge idle" }, "checking…"));
  try {
    const r = await api(`/artifacts/${artifactId}/verify`);
    cell.replaceChildren(el("span", { class: `badge ${r.ok ? "ok" : "bad"}`, title: `expected ${r.expected}\nactual   ${r.actual}` }, r.ok ? "Hash matches" : "MISMATCH"));
  } catch (err) {
    cell.replaceChildren(el("span", { class: "badge bad" }, "error"));
  }
}

async function verifyAll() {
  const btn = $("#btn-verify-all");
  btn.disabled = true;
  for (const a of state.artifacts) {
    await verify(a.id, document.querySelector(`tr[data-id="${a.id}"] td.integrity`));
  }
  btn.disabled = false;
  checkChain(); // each verification is itself written to the audit log
}

async function checkChain() {
  const out = $("#stat-chain");
  const r = await api(`/cases/${state.caseId}/audit/verify`);
  out.replaceChildren(el("span", { class: `badge ${r.ok ? "ok" : "bad"}`, title: r.reason || "" },
    r.ok ? `Intact · ${r.entries}` : `Broken at #${r.broken_at}`));
}

function renderStatements(statements) {
  $("#statements").replaceChildren(...statements.map((s) => el("div", { class: "card" },
    el("h3", {}, s.speaker),
    el("div", { class: "muted" }, `${ROLE[s.role] || s.role} · ${LANG[s.language] || s.language} · ${s.id}`),
    el("p", { lang: s.language === "hi" ? "hi" : "en" }, s.text),
  )));
}

async function openArtifact(a) {
  const body = $("#viewer-body");
  $("#viewer-title").textContent = `${a.id} · ${a.filename}`;
  const url = `/artifacts/${a.id}/content`;
  if (a.filename.endsWith(".png")) {
    body.replaceChildren(el("img", { src: url, alt: `${a.filename} (stored copy)` }));
  } else {
    const text = await (await fetch(url)).text();
    const lines = text.split("\n");
    const numbered = lines.map((l, i) => `${String(i).padStart(4)}  ${l}`).join("\n");
    body.replaceChildren(el("p", { class: "muted" }, a.filename.endsWith(".csv") ? "Line 0 is the header; row N is line N." : ""),
      el("pre", {}, numbered));
  }
  $("#viewer").hidden = false;
  $("#viewer").scrollIntoView({ behavior: "smooth" });
}

$("#btn-verify-all").onclick = verifyAll;
$("#btn-chain").onclick = checkChain;
$("#viewer-close").onclick = () => { $("#viewer").hidden = true; };
init().catch((err) => {
  $("#empty").hidden = false;
  $("#empty").textContent = `Could not reach the API: ${err.message}`;
});
