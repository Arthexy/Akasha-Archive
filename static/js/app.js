"use strict";
const $ = (id) => document.getElementById(id);
const csrf = document.querySelector('meta[name="csrf-token"]').content;
const state = {config: null, characters: [], rankings: [], uid: "", loadedUid: "", view: "overview", generation: 0, notesGeneration: 0, loading: false, rankingsLoading: false, rankingRequest: 0, rankPage: 1, charPage: 1, pageSize: 10, sortDirection: 1, rankSort: "rank", rankDir: 1};
const cooldowns = {};
function rememberCooldown(source,seconds) { if(seconds>0) cooldowns[source]=Date.now()+seconds*1000; }
function waitSeconds(source) {return Math.max(0,Math.ceil(((cooldowns[source]||0)-Date.now())/1000));}
const paths = {overview:"/", showcase:"/showcase", rankings:"/rankings", explore:"/explore", notes:"/notes", settings:"/settings"};
const views = {
  overview: ["01", "Lihat showcase akun Genshin", "Gunakan UID publik. Showcase dapat dibuka tanpa koneksi HoYoLAB."],
  showcase: ["02", "Showcase karakter", "Karakter yang dipublikasikan, statistik build, dan artifact yang digunakan."],
  rankings: ["03", "Ranking build", "Posisi per kategori. Baca asumsi sebelum membandingkan build."],
  explore: ["", "Explore World", "Progres eksplorasi, reputasi, dan offering dari akun HoYoLAB yang dipilih."],
  notes: ["04", "Catatan harian", "Resource dari akun HoYoLAB yang dipilih; terpisah dari UID publik."],
  settings: ["05", "Pengaturan", "Preferensi, koneksi HoYoLAB, dan akun catatan harian."],
  detail: ["", "Detail build", "Snapshot showcase publik dari Enka.Network."]
};
const escape = (v) => String(v ?? "—").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const number = (v) => v == null ? t("Belum tersedia") : Number(v).toLocaleString(language==="en" ? "en-US" : "id-ID", {maximumFractionDigits: Number(v)>0 && Number(v)<0.1 ? 4 : 1});
const statValue = (s) => `${number(s.value)}${s.percent ? "%" : ""}`;
const rankValue = v => v == null ? t("Belum tersedia") : `#${number(v)}`;
const resourceValue = v => v == null ? t('<span class="unavailable">Belum tersedia</span>') : number(v);
const topPercent = v => v == null ? t("Belum tersedia") : v>0 && v<0.0001 ? "<0,0001%" : `${number(v)}%`;
const help = (text) => html`<button type="button" class="info-tip" aria-label="${escape(t(text))}" aria-expanded="false" data-tip="${escape(t(text))}">i</button>`;
function portrait(icon, name, large=false) {
  return html`<span class="portrait${large ? " portrait-large" : ""}" aria-hidden="true"><span>${escape((name || "?").slice(0,1))}</span>${icon ? html`<img src="/api/v1/image?src=${encodeURIComponent(icon)}" alt="" loading="lazy">` : ""}</span>`;
}

function gameImage(icon, className="equipment-image") {
  const local = {"https://enka.network/ui/UI_ItemIcon_210.png":"resin", "https://enka.network/ui/UI_ItemIcon_204.png":"realm-currency"};
  return icon ? html`<img class="game-image ${className}" src="${local[icon] ? `/static/images/${local[icon]}.png` : /^\/static\/images\/explore\/[\w-]+\.png$/.test(icon) ? icon : `/api/v1/image?src=${encodeURIComponent(icon)}`}" alt="" aria-hidden="true" loading="lazy" decoding="async">` : "";
}
function statIcon(label) {
  const key=String(label).toLowerCase();
  const props={pyro:"FIRE",hydro:"WATER",electro:"ELEC",dendro:"GRASS",anemo:"WIND",geo:"ROCK",cryo:"ICE",physical:"PHYSICAL"};
  let prop=/hp/.test(key) ? "HP" : /def/.test(key) ? "DEFENSE" : /crit.*(dmg|hurt)/.test(key) ? "CRITICAL_HURT" : /crit/.test(key) ? "CRITICAL" : /recharge|charge/.test(key) ? "CHARGE_EFFICIENCY" : /mastery|master/.test(key) ? "ELEMENT_MASTERY" : /heal/.test(key) ? "HEAL_ADD" : /atk|attack/.test(key) ? "ATTACK" : null;
  if(!prop) for(const [element,name] of Object.entries(props)) if(key.includes(element)) {prop=name+"_ADD_HURT";break;}
  return prop ? html`<img class="stat-icon game-image" src="/static/images/stats/FIGHT_PROP_${prop}.png" alt="" aria-hidden="true" loading="lazy">` : "";
}
function readAccounts() {
  try { const data=JSON.parse(localStorage.getItem("hoyo-public-accounts") || "[]"); return Array.isArray(data) ? data.filter(a=>a && /^[0-9]{9,10}$/.test(a.uid) && typeof a.nickname==="string").slice(0,20) : []; } catch { return []; }
}
function renderAccounts() {
  const accounts=readAccounts();
  $("recent-accounts").innerHTML='<option value="" hidden></option>'+accounts.map(a=>html`<option value="${escape(a.uid)}">${escape(a.nickname)} / ${escape(a.uid)}</option>`).join("");
  $("recent-accounts").value=accounts.some(a=>a.uid===state.loadedUid) ? state.loadedUid : "";
  $("recent-accounts").disabled=!accounts.length;
  $("forget-accounts").disabled=!accounts.length;
}
function rememberAccount(profile) {
  const accounts=[{uid:String(profile.uid),nickname:String(profile.nickname || profile.uid)},...readAccounts().filter(a=>a.uid!==String(profile.uid))].slice(0,20);
  try {localStorage.setItem("hoyo-public-accounts",JSON.stringify(accounts));} catch {notice("Profil dimuat, tetapi browser tidak dapat menyimpan riwayat akun.");}
  renderAccounts();
}
function compactSets(sets=[]) {
  const parsed=sets.map(text=>({text,count:Number(text.match(/\((\d+)pc\)$/)?.[1] || 0)}));
  const four=parsed.find(x=>x.count>=4);
  return (four ? [four] : parsed.filter(x=>x.count>=2)).map(x=>x.text).join(" + ") || "—";
}
async function openAkashaBuild(index, remember=true) {
  const row=state.rankings[Number(index)]; if(!row?.build_hash) return;
  const uid=state.uid, generation=state.generation, hash=row.build_hash;
  state.buildHash=hash; state.detailSource="akasha"; state.selectedCharacter=null;
  show("detail",false);
  $("character-detail").hidden=false;
  $("back-showcase").textContent=t("Kembali ke ranking");
  $("page-description").textContent=t("Snapshot build dari Akasha · equipment sesuai hash ranking.");
  $("character-detail").innerHTML=html`<p role="status">Memuat snapshot Akasha…</p>`;
  if(remember) history.pushState({view:"detail",build:hash},"",`/rankings#build-${hash}`);
  try {
    const result=await api(`/akasha-build/${uid}/${hash}`);
    if(uid!==state.uid || generation!==state.generation || state.buildHash!==hash || state.view!=="detail") return;
    detail(result.data.character.id,false,result.data.character,row);
    window.scrollTo(0,0); $("character-detail").focus({preventScroll:true});
  } catch(error) {
    if(uid===state.uid && state.buildHash===hash && state.view==="detail") $("character-detail").innerHTML=html`<p class="error-text">${escape(t(error.message))}</p><button data-akasha-build="${index}">Coba lagi</button>`;
  }
}


function updateLoadButton() {
  $("load-account").textContent = state.loading && $("uid").value.trim() === state.uid ? "Memuat…" : $("uid").value.trim() === state.loadedUid && state.loadedUid ? "Perbarui Enka & Akasha" : "Muat akun";
  $("load-account").disabled = state.loading && $("uid").value.trim() === state.uid;
  $("fetch-rankings").disabled = state.loading || state.rankingsLoading;
  const uid = $("uid").value.trim();
  const wait = Math.max(waitSeconds(`showcase:${uid}`),waitSeconds(`rankings:${uid}`));
  if(uid === state.loadedUid && wait) {$("load-account").disabled=true;$("load-account").textContent=`Perbarui lagi dalam ${wait} dtk`;}
  const rankWait=waitSeconds(`rankings:${state.uid}`);
  if(rankWait){$("fetch-rankings").disabled=true;$("fetch-rankings").textContent=`Ranking: tunggu ${rankWait} dtk`;}else $("fetch-rankings").textContent=t("Perbarui ranking");
  const notesWait=waitSeconds("notes");
  $("refresh-notes").disabled=!!state.notesLoading || !!notesWait;
  $("refresh-notes").textContent=t(notesWait ? `Catatan: tunggu ${notesWait} dtk` : "Perbarui catatan");
  const exploreWait=waitSeconds("explore");
  $("refresh-explore").disabled=!!state.exploreLoading || !!exploreWait || !state.config?.hoyolab.enabled || !state.config?.hoyolab.game_uid;
  $("refresh-explore").textContent=exploreWait ? t(`Dapat diperbarui lagi dalam ${exploreWait} detik.`) : t("Perbarui eksplorasi");
  for(const id of ["load-account","fetch-rankings"]) $(id).textContent=t($(id).textContent);
}
function notice(message, error=false) { $("notice").textContent = t(message); $("notice").hidden = !message; $("notice").classList.toggle("error", error); }
async function api(path, method="GET", body) {
  const source=path.startsWith("/showcase/") ? `showcase:${path.split("/")[2]}` : path.startsWith("/rankings/") ? `rankings:${path.split("/")[2]}` : ["/notes","/explore"].includes(path) ? path.slice(1) : path==="/refresh" ? ["notes","explore"].includes(body.source) ? body.source : `${body.source}:${body.uid}` : null;
  if(source && waitSeconds(source) && (method==="POST" || source==="notes")) throw new Error(`Dapat diperbarui lagi dalam ${waitSeconds(source)} detik.`);
  const response = await fetch(`/api/v1${path}`, {method, headers: {"Content-Type":"application/json", "X-CSRF-Token":csrf}, body: body === undefined ? undefined : JSON.stringify(body)});
  const result = await response.json();
  if(source) rememberCooldown(source,result.error?.retry_after_seconds ?? result.meta?.refresh_after_seconds);
  const currentSource = ["notes","explore"].includes(source) ? String(result.data?.uid)===String(state.config?.hoyolab.game_uid) : !source || source.endsWith(`:${state.uid}`);
  if(result.meta && currentSource) {
    const stamp=$(`source-${result.meta.source}-time`);
    if(stamp) stamp.textContent=freshness(result);
  }
  if (!response.ok) throw new Error(result.error?.retry_after_seconds ? `Dapat diperbarui lagi dalam ${Math.ceil(result.error.retry_after_seconds)} detik.` : result.error?.message || `Request gagal (${response.status})`);
  return result;
}
function show(view, push=true) {
  if (!views[view]) view = "overview";
  state.view = view;
  document.querySelectorAll(".view").forEach(el => el.hidden = el.id !== `view-${view}`);
  document.querySelectorAll(".nav-item").forEach(el => el.classList.toggle("active", el.dataset.view === (view==="detail" ? state.detailSource==="akasha" ? "rankings" : "showcase" : view)));
  document.querySelectorAll(".nav-item").forEach(el => el.setAttribute("aria-current", el.dataset.view === (view==="detail" ? state.detailSource==="akasha" ? "rankings" : "showcase" : view) ? "page" : "false"));
  $("navigation-dialog").close();
  $("view-code").textContent = views[view][0];
  $("page-title").textContent = t(view==="overview" && state.loadedUid ? "Ringkasan akun" : views[view][1]);
  $("page-description").textContent = t(views[view][2]);
  $("uid-form").hidden = view === "detail" || view === "settings" || view === "notes" || view === "explore";
  $("uid-help").hidden = $("uid-form").hidden;
  if (push && (location.pathname !== paths[view] || location.hash)) history.pushState({view}, "", paths[view] || "/showcase");
  if(push) {window.scrollTo(0,0); $("main-content").focus({preventScroll:true});}
  if(view === "explore" && state.config && !state.explore) loadExplore();
}
function freshness(result) {
  const m = result.meta;
  return t(`${m.stale ? "Snapshot lama" : m.cached ? "Snapshot tersimpan" : "Diperbarui"} · ${new Date(m.fetched_at).toLocaleString(language==="en" ? "en-US" : "id-ID")}`);
}
function table(headers, rows, rawHeaders=false) {
  return html`<div class="table-wrap"><table><thead><tr>${headers.map(h=>html`<th>${rawHeaders ? h : escape(t(h))}</th>`).join("")}</tr></thead><tbody>${rows.join("")}</tbody></table></div>`;
}
function renderCharacters() {
  const focusedCharacter=document.activeElement?.dataset?.character;
  const selected = $("element-filter").value;
  const query = $("showcase-search").value.trim().toLowerCase();
  const chars = state.characters.filter(c=> (!selected || c.element === selected) && (!query || [c.name,c.element,c.weapon?.name].some(v=>String(v||"").toLowerCase().includes(query)))).sort((a,b)=>state.sortDirection * ($("sort").value === "level" ? a.level-b.level || a.name.localeCompare(b.name) : a.name.localeCompare(b.name)));
  const pages = Math.max(1, Math.ceil(chars.length/state.pageSize));
  state.charPage = Math.min(pages, Math.max(1,state.charPage));
  const start = (state.charPage-1)*state.pageSize;
  const pager = html`<nav class="pagination"><button data-char-page="${state.charPage-1}" ${state.charPage===1 ? "disabled" : ""}>Sebelumnya</button><label>Halaman <input type="number" inputmode="numeric" min="1" max="${pages}" step="1" value="${state.charPage}" data-char-select aria-label="Showcase page"> / ${pages}</label><span class="muted">${chars.length ? start+1 : 0}–${Math.min(start+state.pageSize,chars.length)} dari ${chars.length}</span><button data-char-page="${state.charPage+1}" ${state.charPage===pages ? "disabled" : ""}>Berikutnya</button></nav>`;
  const card = c => html`<article class="character-card">${portrait(c.icon,c.name,true)}<div class="character-card-content"><h3>${escape(c.name)}</h3><p>${escape(c.element)} · Level ${number(c.level)}${c.build_available === false ? "" : ` · C${number(c.constellation)}`}</p>${c.build_available === false ? t('<p class="incomplete">Detail build belum dipublikasikan. Aktifkan “Show Character Details” di showcase dalam game.</p>') : html`<button data-character="${c.id}">Lihat build</button>`}</div></article>`;
  $("filter-state").innerHTML = html`<span>${chars.length} karakter${selected ? ` · ${escape(selected)}` : ""}${query ? ` · “${escape(query)}”` : ""}</span>${selected || query ? t('<button id="clear-filters">Hapus filter</button>') : ""}`;
  $("showcase-table").innerHTML = chars.length ? pager + html`<div class="character-grid">${chars.slice(start,start+state.pageSize).map(card).join("")}</div>` + pager : t('<p>Tidak ada karakter yang cocok. Hapus filter atau aktifkan detail showcase dalam game.</p>');
  $("showcase-preview").innerHTML = state.characters.length ? html`<div class="character-grid">${state.characters.slice(0,4).map(card).join("")}</div>` : t('<p>Belum ada karakter publik tersedia.</p>');
  if(focusedCharacter) document.querySelector(`#showcase-table [data-character="${focusedCharacter}"]`)?.focus({preventScroll:true});
}
let showcaseReturn = {scroll:0,id:null};
function detail(id, remember=true, snapshot=null, ranking=null) {
  const c = snapshot || state.characters.find(c=>c.id === Number(id));
  if (!c) return;
  if (remember) showcaseReturn = {scroll:window.scrollY,id:c.id};
  state.detailSource = snapshot ? "akasha" : "enka";
  if(!snapshot) state.buildHash=null;
  state.selectedCharacter = snapshot ? null : c.id;
  $("character-detail").hidden = false;
  show("detail",false);
  if (remember) history.pushState({view:"detail",character:c.id},"",`/showcase#character-${c.id}`);
  $("page-description").textContent=snapshot ? t("Snapshot build dari Akasha · equipment sesuai hash ranking.") : t(views.detail[2]);
  $("back-showcase").textContent=snapshot ? t("Kembali ke ranking") : t("Kembali ke showcase");
  const ranks = ranking ? [ranking] : state.rankings.filter(r=>r.character_id === c.id);
  const statRows = stats => stats.map(s=>html`<div class="stat-row"><span class="stat-label">${statIcon(s.label)}${escape(s.label)}</span><span>${statValue(s)}</span></div>`).join("");
  const core = c.stats.filter(s=>/^(Max HP|HP|ATK|DEF|Elemental Mastery|CRIT Rate|CRIT DMG|Energy Recharge)$|DMG Bonus/i.test(s.label));
  $("character-detail").innerHTML = html`<div class="detail-header"><h3>${escape(c.name)}</h3><span class="badge">${escape(c.element)} · Level ${number(c.level)} · C${number(c.constellation)}</span></div><div class="build-layout"><aside class="build-art">${portrait(c.icon,c.name,true)}<p>${escape(snapshot ? `Akasha · ${c.snapshot_updated_at || "Snapshot ranking"}` : $("profile-freshness").textContent)}<br>Ascension ${number(c.ascension)} · Friendship ${number(c.friendship)}</p></aside><div class="build-data"><h2>Ringkasan statistik</h2><div class="core-stats">${statRows(core)}</div><details><summary>Semua statistik</summary>${statRows(c.stats)}</details><div class="detail-columns"><section class="weapon-section"><h2>Weapon</h2><div class="weapon-layout">${gameImage(c.weapon?.icon)}<div><h3>${escape(c.weapon?.name)}</h3><p>Level ${number(c.weapon?.level)} · R${number(c.weapon?.refinement)}${c.weapon?.rarity ? ` · ${number(c.weapon.rarity)} ${t("bintang")}` : ""}</p>${statRows(c.weapon?.stats || [])}</div></div></section><section><h2>Talents</h2>${Object.entries(c.talents).map(([label,level],i)=>html`<div class="stat-row"><span>${/^[0-9]+$/.test(label) ? `Talent ${i+1}` : escape(({normalAttacks:"Normal Attack",elementalSkill:"Elemental Skill",elementalBurst:"Elemental Burst"})[label] || label)}</span><span>Level ${number(level)}</span></div>`).join("") || t('<p>Belum tersedia.</p>')}</section></div></div></div><div class="section-label"><h2>Artifact per slot</h2></div><p class="explanation">CV = 2 × CRIT Rate + CRIT DMG dari substats artifact saja. Main stat dan weapon tidak dihitung.</p>${c.artifacts.map(a=>html`<article class="artifact">${gameImage(a.icon)}<h3>${escape(a.name)}<span class="muted">${escape(a.slot)} · ${escape(a.set_name)}</span></h3><p>+${number(a.level)} · ${number(a.rarity)} bintang</p><div class="stat-row"><span>${statIcon(a.main_stat?.label || "")}Main stat: ${escape(a.main_stat?.label)}</span><span>${a.main_stat ? statValue(a.main_stat) : t("Belum tersedia")}</span></div><div class="artifact-stats">${statRows(a.substats)}</div><p class="accent">CV artifact ${number(a.crit_value)} · ${snapshot ? "Akasha" : t("dihitung lokal")}</p></article>`).join("") || t('<p>Artifact belum tersedia.</p>')}<div class="section-label"><h2>Konteks ranking</h2></div><p class="explanation">${t(snapshot ? "Equipment berasal dari snapshot Akasha yang menghasilkan ranking ini." : "Snapshot Akasha bisa berbeda dari showcase Enka.")}</p>${ranks.map(r=>html`<div class="stat-row"><button data-ranking="${state.rankings.indexOf(r)}" class="text-button">${escape(r.category)}</button><span>${rankValue(r.rank)} / ${number(r.population)}</span></div>`).join("") || t('<p>Ranking karakter ini belum tersedia.</p>')}`;
  if (remember) {window.scrollTo(0,0);$("character-detail").focus({preventScroll:true});}
}
function returnToShowcase() {
  if(state.detailSource==="akasha") {state.buildHash=null;show("rankings");return;}
  show("showcase");
  window.scrollTo(0,showcaseReturn.scroll);
  document.querySelector(`#showcase-table [data-character="${showcaseReturn.id}"]`)?.focus({preventScroll:true});
}

async function statuses() {
  try {
    const result = await api("/status");
    Object.entries(result.data.sources).forEach(([source,status])=>{
      const el = $(`source-${source}`); el.textContent = t(({ok:"Tersedia",cached:"Tersimpan",connected:"Terhubung",idle:"Belum dimuat",disabled:"Dinonaktifkan",needs_configuration:"Perlu pengaturan",network_error:"Gagal terhubung",stale:"Snapshot lama",rate_limited:"Cooldown",authentication_failed:"Cookie tidak valid",verification_required:"Perlu verifikasi"})[status] || status.replaceAll("_", " "));
      el.className = `badge ${["ok","cached","connected"].includes(status) ? "good" : ["idle","disabled","needs_configuration"].includes(status) ? "" : "bad"}`;
    });
  } catch (error) { notice(error.message, true); }
}
async function loadPublic(refresh=false) {
  if(state.loading && $("uid").value.trim() === state.uid) return;
  const uid = $("uid").value.trim();
  if (!/^[0-9]{9,10}$/.test(uid)) { notice("Masukkan UID Genshin berisi 9 atau 10 digit.", true); return; }
  state.buildHash=null;
  state.loading = true; state.uid = uid; state.loadedUid = ""; const generation = ++state.generation;
  state.rankingRequest++; state.rankingsLoading = false;
  state.characters = []; state.rankings = []; state.rankPage = 1; if(!refresh) state.charPage = 1; $("character-detail").hidden = true;
  $("info-dialog").close(); updateLoadButton();
  notice("");
  $("profile").innerHTML = t('<div class="empty">Memuat profil publik…</div>');
  $("showcase-preview").textContent = $("showcase-table").textContent = t("Memuat showcase…");
  $("rankings").textContent = t("Memuat snapshot ranking…");
  $("rank-freshness").textContent = t("Memuat");
  $("profile-freshness").textContent = t("Memuat");
  const fetchShowcase = () => refresh ? api("/refresh", "POST", {source:"showcase",uid}) : api(`/showcase/${uid}`);
  const showcaseTask = (async()=>{try {
      const result = await fetchShowcase(); if (generation !== state.generation) return;
      state.characters = result.data.characters; state.loadedUid = uid;
      if (state.config?.public_account.uid !== uid) {
        state.config.public_account.uid = uid; $("default-uid").value = uid;
        api("/config","PATCH",{public_account:{uid}}).catch(()=>{});
      }
      const p = result.data.profile; rememberAccount(p);
      $("profile").innerHTML = html`<div class="profile-record">${gameImage(p.namecard,"profile-namecard")}<div class="profile-identity">${portrait(p.icon,p.nickname,true)}<div><div class="eyebrow">Akun publik / ${escape(p.uid)}</div><div class="player-name">${escape(p.nickname)}</div><p>${escape(p.signature || t("Tidak ada signature."))}</p></div></div><div class="profile-stats"><div class="metric"><div class="eyebrow">Adventure Rank</div><strong>${number(p.level)}</strong></div><div class="metric"><div class="eyebrow">World Level</div><strong>${number(p.world_level)}</strong></div><div class="metric"><div class="eyebrow">Karakter showcase </div><strong>${state.characters.length.toString().padStart(2,"0")}</strong></div></div></div>`;
      $("profile-freshness").textContent = freshness(result); renderCharacters(); renderRankings();
      $("overview-secondary").hidden=false;
      if(state.view==="overview") $("page-title").textContent=t("Ringkasan akun");
      if (state.view === "detail" && state.selectedCharacter) detail(state.selectedCharacter,false);
      if (location.hash.match(/^#character-(\d+)$/)) detail(location.hash.slice(11),false);
      if (result.warning) notice(result.warning.message, true);
    } catch(error) { if (generation !== state.generation) return; $("profile").innerHTML = html`<div class="empty error-text">${escape(t(error.message))}</div>`; $("profile-freshness").textContent = t("Belum tersedia"); $("showcase-table").textContent = $("showcase-preview").textContent = t("Showcase gagal dimuat. Periksa UID lalu coba lagi."); }})();
  const rankingTask = fetchRankings(uid, generation, refresh);
  await Promise.all([showcaseTask, rankingTask]);
  if (generation !== state.generation) return;
  state.loading = false; updateLoadButton(); await statuses();
  const build=location.hash.match(/^#build-([a-f0-9]{32})$/)?.[1];
  if(build) openAkashaBuild(state.rankings.findIndex(r=>r.build_hash===build),false);
}
async function fetchRankings(uid, generation, forceRefresh=false) {
  const request = ++state.rankingRequest;
  if (!state.config?.akasha.enabled) {
    $("rankings").textContent = t("Ranking Akasha dinonaktifkan di Pengaturan.");
    $("rank-freshness").textContent = t("Dinonaktifkan"); return;
  }
  state.rankingsLoading = true; updateLoadButton();
  try {
    const result = forceRefresh ? await api("/refresh", "POST", {source:"rankings",uid}) : await api(`/rankings/${uid}`);
    if (generation !== state.generation || request !== state.rankingRequest) return;
    state.rankings = result.data; $("rank-freshness").textContent = freshness(result);
    renderRankings();
    if (result.warning) notice(result.warning.message, true);
  } catch(error) { if (generation !== state.generation || request !== state.rankingRequest) return; $("rankings").textContent = t(error.message); $("rank-freshness").textContent = t("Belum tersedia"); }
  finally { if (request === state.rankingRequest) { state.rankingsLoading = false; updateLoadButton(); } }
}

function renderRankings() {
  $("ranking-sort").value=state.rankSort;
  $("ranking-direction").textContent=t(state.rankDir===1 ? "Urutan naik" : "Urutan turun");
  const query = $("ranking-search").value.trim().toLowerCase();
  const data = query ? state.rankings.filter(r=>[r.character,r.element,r.category,r.weapon,r.variant,r.details,...(r.artifact_sets||[])].some(v=>String(v||"").toLowerCase().includes(query))) : [...state.rankings];
  const sorters = {character:r=>r.character, level:r=>r.level, rank:r=>r.rank, population:r=>r.population, top:r=>r.top_percent, cv:r=>r.crit_value};
  data.sort((a,b)=>{const av=sorters[state.rankSort](a), bv=sorters[state.rankSort](b); if(av == null) return bv == null ? 0 : 1; if(bv == null) return -1; return state.rankDir * (typeof av === "string" ? av.localeCompare(bv) : av-bv);});
  const total = data.length, pages = Math.max(1, Math.ceil(total/state.pageSize));
  state.rankPage = Math.min(pages, Math.max(1,state.rankPage));
  if (!total) { $("rankings").innerHTML = t('<p class="muted">Ranking untuk akun ini belum tersedia.</p>'); return; }
  const start = (state.rankPage-1)*state.pageSize;
  const pager = position => html`<nav class="pagination" aria-label="Rankings pages ${position}"><button data-rank-page="${state.rankPage-1}" ${state.rankPage===1 ? "disabled" : ""} aria-label="Previous rankings page">Sebelumnya</button><label>Halaman <input type="number" inputmode="numeric" min="1" max="${pages}" step="1" value="${state.rankPage}" data-rank-select aria-label="Rankings page ${position}"> / ${pages}</label><span class="muted">${start+1}–${Math.min(start+state.pageSize,total)} dari ${total}</span><button data-rank-page="${state.rankPage+1}" ${state.rankPage===pages ? "disabled" : ""} aria-label="Next rankings page">Berikutnya</button></nav>`;
  const rows = data.slice(start,start+state.pageSize).map(r=>html`<tr><td><div class="rank-character character-name">${portrait(r.icon,r.character)}<span>${escape(r.character)}<small class="rank-build-links muted">${escape(r.element || "")} · ${r.build_hash && r.build_snapshot ? html`<a href="/rankings#build-${escape(r.build_hash)}" data-akasha-build="${state.rankings.indexOf(r)}" aria-label="See Detail: ${escape(r.character)}">See Detail ↗</a>` : html`<span title="${escape(t("Snapshot build belum tersedia"))}">See Detail</span>`} · <a href="https://akasha.cv/profile/${encodeURIComponent(state.uid)}${r.build_hash ? `?build=${encodeURIComponent(r.build_hash)}` : ""}" target="_blank" rel="noopener noreferrer" aria-label="Akasha: ${escape(r.character)}">Akasha ↗</a></small></span></div></td><td class="numeric">${escape(r.level)}</td><td><button class="category-button" data-ranking="${state.rankings.indexOf(r)}" aria-label="${escape(`${t("Buka kategori")}: ${r.category}`)}"><span title="${escape(r.category)}">${escape(r.category)}</span><small>${escape(r.weapon || t("Asumsi kategori"))} ↗</small></button></td><td class="numeric">${rankValue(r.rank)}</td><td class="numeric">${number(r.population)}</td><td class="numeric">${topPercent(r.top_percent)}</td><td class="numeric accent">${number(r.crit_value)}</td><td class="rank-sets"><span class="set-label" tabindex="0" aria-label="${escape((r.artifact_sets||[]).join(" + "))}" title="${escape((r.artifact_sets||[]).join(" + "))}">${escape(compactSets(r.artifact_sets))}</span></td></tr>`);
  const arrow = key => state.rankSort === key ? (state.rankDir === 1 ? " ↑" : " ↓") : " ↕";
  const headers = [["character","Karakter"],["level","Level"],["category","Kategori"],["rank","Rank"],["population","Populasi"],["top","Top %"],["cv","CV"],["sets","Set"]].map(([key,label])=>sorters[key] ? html`<button class="sort-head" data-rank-sort="${key}">${t(label)}${arrow(key)}</button>` : t(label));
  $("rankings").innerHTML = rows.length ? pager("top") + table(headers,rows,true) + pager("bottom") : t('<p class="muted">Tidak ada ranking yang cocok.</p>');
  $("rankings").querySelectorAll("th").forEach(th=>{const key=th.querySelector("[data-rank-sort]")?.dataset.rankSort;if(key) th.setAttribute("aria-sort",key===state.rankSort ? state.rankDir===1 ? "ascending" : "descending" : "none");});
}
function rankingDetail(index) {
  const r = state.rankings[Number(index)]; if (!r) return;
  $("dialog-title").textContent = `${r.character} / ${t("Asumsi kategori")}`;
  $("dialog-content").innerHTML = html`<h3>${escape(r.category)}</h3><dl>${[["Weapon",r.weapon],["Bracket",r.variant || t("Bracket default")],["Asumsi",r.details || t("Detail tambahan belum tersedia")],["Rank",`${rankValue(r.rank)} / ${number(r.population)}`],["Set artifact",(r.artifact_sets||[]).join(", ") || t("Belum tersedia")]].map(([label,value])=>html`<div class="assumption-group"><dt>${escape(t(label))}</dt><dd>${escape(value)}</dd></div>`).join("")}</dl><p>Snapshot Akasha bisa berbeda dari showcase Enka. Equipment ranking dibuka dari area karakter.</p>`;
  $("dialog-content").insertAdjacentHTML("beforeend",html`<p>${escape($("rank-freshness").textContent)}</p>`);
  $("dialog-content").insertAdjacentHTML("beforeend",html`<dl><dt>Element / Level</dt><dd>${escape(r.element)} / ${number(r.level)}</dd><dt>Top %</dt><dd>${topPercent(r.top_percent)}</dd><dt>CV artifact</dt><dd>${number(r.crit_value)}</dd></dl>`);

  $("info-dialog").showModal();
}
function countdown(target) {
  if (!target || !Number.isFinite(Date.parse(target))) return t("Belum tersedia");
  const seconds = Math.max(0, Math.floor((Date.parse(target)-Date.now())/1000));
  return seconds ? `${Math.floor(seconds/3600)}h ${Math.floor(seconds%3600/60)}m ${seconds%60}s` : t("Siap");
}
function exploreSelection(data) {
  try {
    const saved=JSON.parse(localStorage.getItem(`hoyo-explore-regions:${data.uid}`));
    if(Array.isArray(saved)) return new Set(saved.filter(id=>data.groups.some(g=>g.id===id)));
  } catch {}
  return new Set(data.groups.map(g=>g.id));
}
function explorationTotal(data, selected) {
  const values=data.groups.filter(g=>selected.has(g.id) && g.progress!=null).map(g=>g.progress);
  return values.length ? values.reduce((sum,p)=>sum+p,0)/values.length : null;
}
function exploreProgress(value, label) {
  return value == null ? html`<span class="muted">Belum tersedia</span>` : html`<span class="explore-progress" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Number(value)}" aria-label="${escape(label)}"><span></span></span>`;
}
function exploreProgressSnapshot() {
  return new Map([...document.querySelectorAll(".explore-progress")].map(bar=>[bar.getAttribute("aria-label"),bar.firstElementChild.getBoundingClientRect().width/(bar.getBoundingClientRect().width || 1)]));
}
function animateExploreProgress(previous) {
  const reduced=window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  document.querySelectorAll(".explore-progress").forEach(bar=>{
    const from=previous.get(bar.getAttribute("aria-label")), to=Number(bar.getAttribute("aria-valuenow"))/100;
    bar.firstElementChild.style.transform=`scaleX(${to})`;
    if(!reduced && from!=null && Math.abs(from-to)>.001) bar.firstElementChild.animate([{transform:`scaleX(${from})`},{transform:`scaleX(${to})`}],{duration:480,easing:"cubic-bezier(.16,1,.3,1)"});
  });
}
function renderExploreTotal(previous=exploreProgressSnapshot()) {
  const data=state.explore; if(!data) return;
  const value=explorationTotal(data,state.exploreSelected);
  $("explore-total").innerHTML=html`<div><h2>Total eksplorasi</h2><p>${number(state.exploreSelected.size)} / ${number(data.groups.length)} region dipilih</p></div><strong>${value==null ? "—" : number(value)+"%"}</strong>${exploreProgress(value,t("Total eksplorasi"))}<p class="muted explore-method">Rata-rata region terpilih. Progres region adalah rata-rata main area dan map khusus terkait. Setiap map dihitung sekali; area yang sudah termasuk main area tidak ditambahkan lagi.</p>`;
  animateExploreProgress(previous);
}
function renderExplore() {
  const previous=exploreProgressSnapshot();
  const data=state.explore; if(!data) return;
  function card(region) {
    const group=data.groups.find(g=>g.id===region.group_id);
    const own=region.group_id===region.id;
    const related=data.regions.filter(r=>r.group_id===region.group_id && r.special && r.id!==region.id);
    const levels=[...(region.reputation_level!=null ? [{name:t("Reputasi"),level:region.reputation_level}] : []),...region.tribes,...region.offerings];
    const logo=region.local_icon ? html`<img src="${escape(region.local_icon)}" class="explore-logo" alt="" loading="lazy">` : gameImage(region.icon || region.offerings.find(o=>o.icon)?.icon,"explore-logo");
    return html`<article class="explore-region${region.special ? " explore-special" : ""}"><header class="explore-region-header">${gameImage(region.local_background || region.background,"explore-background")}<div class="explore-region-identity">${logo}<div><h2>${escape(region.name)}</h2>${region.special && region.group_name!==region.name ? html`<small>${escape(region.group_name)}</small>` : ""}</div>${group ? html`<label class="explore-select" title="${escape(t("Hitung di total"))}"><input type="checkbox" aria-label="${escape(region.name)} / ${escape(t("Hitung di total"))}" data-explore-region="${escape(group.id)}" ${state.exploreSelected.has(group.id) ? "checked" : ""}></label>` : ""}</div></header><div class="explore-region-body"><div class="explore-progress-line"><span>${t(region.special ? "Eksplorasi map" : "Main area")}</span><strong>${region.progress==null ? "—" : number(region.progress)+"%"}</strong></div>${exploreProgress(region.progress,region.name)}${region.statue_level!=null ? html`<p class="explore-statue">${t(region.name==="Nod-Krai" ? "Statue of New Moon" : "Statue of The Seven")} <strong>Lv. ${number(region.statue_level)}</strong></p>` : ""}${own && related.length ? html`<p class="explore-combined">${t("Dengan map khusus")}: <strong>${group.progress==null ? "—" : number(group.progress)+"%"}</strong></p>` : ""}${region.included_in_main ? html`<p class="muted explore-included">Sudah termasuk dalam main area.</p>` : ""}${levels.length ? html`<details class="explore-details"><summary>Reputasi & offering <span>${number(levels.length)}</span></summary><ul class="explore-offerings">${levels.map(o=>html`<li>${gameImage(o.icon,"explore-offering-icon")}<span>${escape(o.name)}</span><strong>${o.locked ? t("Terkunci") : o.level==null ? "—" : "Lv. "+number(o.level)}</strong></li>`).join("")}</ul></details>` : ""}${region.areas.length ? html`<details class="explore-details" open><summary>Detail area <span>${number(region.areas.length)}</span></summary><ul class="explore-areas">${region.areas.map(a=>html`<li><span>${escape(a.name)}</span><strong>${a.progress==null ? "—" : number(a.progress)+"%"}</strong></li>`).join("")}</ul></details>` : ""}</div></article>`;
  }
  $("explore").innerHTML=html`<p class="explanation">${escape(data.nickname)} / ${escape(data.uid)} / ${escape(data.server)}<br>${escape(freshness(state.exploreResult))}</p><section id="explore-total" class="explore-total" aria-live="polite"></section><div class="explore-grid">${data.regions.filter(r=>!r.special).map(card).join("")}</div><div class="section-label explore-special-heading"><h2>Map khusus</h2><p class="muted">Tetap dihitung bersama region terkait.</p></div><div class="explore-grid explore-special-grid">${data.regions.filter(r=>r.special).map(card).join("")}</div>`;
  renderExploreTotal(previous);
}
async function loadExplore(refresh=false) {
  if(state.exploreLoading) return;
  if(refresh && waitSeconds("explore")) return;
  const account=state.config?.hoyolab.game_uid, generation=state.exploreGeneration||0;
  if(!state.config?.hoyolab.enabled || !account) {
    $("explore").innerHTML=html`<div class="empty"><h3>Hubungkan akun HoYoLAB.</h3><p>Pilih akun di Pengaturan untuk melihat progres eksplorasi.</p><button data-view="settings">Buka pengaturan</button></div>`;
    $("refresh-explore").disabled=true; return;
  }
  state.exploreLoading=true; $("refresh-explore").disabled=true;
  if(!state.explore) $("explore").innerHTML=html`<p class="empty-line" role="status">Memuat eksplorasi…</p>`;
  try {
    const result=refresh ? await api("/refresh","POST",{source:"explore"}) : await api("/explore");
    if(account!==state.config?.hoyolab.game_uid || generation!==(state.exploreGeneration||0)) return;
    if(String(result.data.uid)!==String(account)) throw new Error("Exploration account mismatch.");
    state.explore=result.data; state.exploreResult=result; state.exploreSelected=exploreSelection(result.data);
    if(!result.data.regions.length) $("explore").innerHTML=html`<p class="empty-line">Data eksplorasi belum tersedia.</p>`;
    else renderExplore();
    if(result.warning) notice(result.warning.message,true);
  } catch(error) {
    if(account===state.config?.hoyolab.game_uid && generation===(state.exploreGeneration||0))
      $("explore").innerHTML=html`<div class="empty"><h3>Eksplorasi belum tersedia.</h3><p>${escape(t(error.message))}</p><button id="retry-explore">Coba lagi</button><button data-view="settings">Buka pengaturan</button></div>`;
  } finally {
    state.exploreLoading=false; updateLoadButton();
    if(generation!==(state.exploreGeneration||0) && state.view==="explore") loadExplore();
  }
}
async function loadNotes(refresh=false) {
  if (state.notesLoading) return;
  if(waitSeconds("notes")) return;
  const generation = ++state.notesGeneration;
  const account = state.config?.hoyolab.game_uid;
  if (!state.config?.hoyolab.enabled) {
    $("notes").innerHTML = t('<div class="empty"><h3>HoYoLAB belum diaktifkan.</h3><p>Hubungkan akun di Pengaturan untuk melihat catatan harian.</p><button data-view="settings">Buka pengaturan</button></div>');
    $("notes-summary").innerHTML = t('<div class="large-number">—<span> / —</span></div><div class="eyebrow">Original Resin</div><p class="muted">Hubungkan HoYoLAB untuk melihat catatan harian.</p><button data-view="settings">Buka pengaturan koneksi</button>');
    return;
  }
  state.notesLoading = true;
  $("refresh-notes").disabled = true;
  try {
    const result = refresh ? await api("/refresh", "POST", {source:"notes"}) : await api("/notes");
    if (generation !== state.notesGeneration || account !== state.config?.hoyolab.game_uid) return;
    const n = result.data;
    if (String(n.uid) !== String(account)) return;
    $("notes-summary").innerHTML = html`<div class="resource-heading">${gameImage("https://enka.network/ui/UI_ItemIcon_210.png","resource-icon")}<div class="eyebrow">Original Resin / ${escape(n.uid)}</div></div><div class="large-number">${resourceValue(n.resin.current)}<span> / ${number(n.resin.max)}</span></div><p data-countdown="${escape(n.resin.full_at || "")}">${countdown(n.resin.full_at)}</p><p class="muted">${escape(freshness(result))}</p>`;
    $("notes").className = "";
    $("notes").innerHTML = html`<p class="explanation">Akun HoYoLAB untuk catatan harian / ${escape(n.nickname)} / ${escape(n.uid)} / ${escape(n.server)}<br>${escape(freshness(result))}</p><div class="resources"><div class="resource"><div class="resource-heading">${gameImage("https://enka.network/ui/UI_ItemIcon_210.png","resource-icon")}<div class="eyebrow">Original Resin</div></div><div class="large-number">${resourceValue(n.resin.current)}<span> / ${number(n.resin.max)}</span></div><p>Perkiraan penuh dalam <span data-countdown="${escape(n.resin.full_at || "")}">${countdown(n.resin.full_at)}</span></p></div><div class="resource"><div class="resource-heading"><img class="game-image resource-icon" src="/static/images/daily-commission.png" alt="" aria-hidden="true"><div class="eyebrow">Daily Commissions</div></div><div class="large-number">${resourceValue(n.commissions.completed)}<span> / ${number(n.commissions.total)}</span></div><p>Hadiah: ${t(n.commissions.reward_claimed == null ? "Belum tersedia" : n.commissions.reward_claimed ? "Sudah diklaim" : "Belum diklaim")}</p></div><div class="resource"><div class="resource-heading">${gameImage("https://enka.network/ui/UI_ItemIcon_204.png","resource-icon")}<div class="eyebrow">Realm Currency</div></div><div class="large-number">${resourceValue(n.realm_currency.current)}</div><p>Kapasitas ${number(n.realm_currency.max)}</p></div></div><div class="mini-resources"><div class="resource resource-mini"><img src="/static/images/weekly-boss.png" alt="" class="resource-icon"><div><span>Diskon weekly boss tersisa</span><strong>${number(n.weekly_discounts_remaining)}</strong></div></div><div class="resource resource-mini"><img src="/static/images/parametric-transformer.png" alt="" class="resource-icon"><div><span>Parametric Transformer</span><strong>${n.transformer?.recovery_time?.reached === true ? t("Siap") : n.transformer?.recovery_time ? escape(`${n.transformer.recovery_time.Day ?? 0}d ${n.transformer.recovery_time.Hour ?? 0}h`) : t("Belum tersedia")}</strong></div></div></div><div class="section-label"><h2>Expeditions</h2></div>${n.expeditions.length ? html`<div class="expedition-cards">${table(["Karakter","Status","Sisa waktu"],n.expeditions.map(e=>html`<tr tabindex="0"><td><div class="character-name">${portrait(e.icon,e.name || e.character)}<span>${escape(e.name || e.character)}</span></div></td><td>${escape(e.status)}</td><td data-countdown="${escape(e.finishes_at || "")}">${countdown(e.finishes_at)}</td></tr>`))}</div>` : t('<p class="empty-line">Tidak ada expedition aktif.</p>')}`;
    const commissions = $("notes").querySelectorAll(".resource")[1];
    commissions.querySelector(".eyebrow").innerHTML = `Daily Commissions ${help("Progress menggabungkan commissions dan Encounter Points. Poin siap klaim tetap perlu diklaim di game. Poin jangka panjang tidak dihitung sebelum dikonversi.")}`;
    if(n.resin.current != null && n.resin.max > 0) $("notes").querySelector(".resource .large-number").insertAdjacentHTML("afterend",html`<meter min="0" max="${Number(n.resin.max)}" value="${Number(n.resin.current)}" aria-label="Original Resin ${Number(n.resin.current)} dari ${Number(n.resin.max)}"></meter>`);
    commissions.insertAdjacentHTML("beforeend", html`<p>Commissions: ${number(n.commissions.commissions_completed)}<br>Encounter Points diklaim: ${number(n.commissions.encounter_claimed)}<br>Encounter Points siap diklaim: ${number(n.commissions.encounter_available)}</p>`);
    if (result.warning) notice(result.warning.message, true);
  } catch(error) {
    if (generation !== state.notesGeneration) return;
    $("notes").innerHTML = html`<div class="empty"><h3>Catatan harian belum tersedia.</h3><p>${escape(t(error.message))}</p><button data-view="settings">Buka pengaturan</button></div>`;
    $("notes-summary").textContent = t(error.message);
  } finally {
    state.notesLoading=false; updateLoadButton(); await statuses();
    if((account !== state.config?.hoyolab.game_uid || generation !== state.notesGeneration) && state.config?.hoyolab.enabled) loadNotes();
  }
}
async function loadConfig() {
  const previousAccount=state.config?.hoyolab.game_uid;
  const previousEnabled=state.config?.hoyolab.enabled;
  state.config = (await api("/config")).data;
  setLanguage(state.config.ui.language);
  if(previousAccount !== state.config.hoyolab.game_uid || previousEnabled !== state.config.hoyolab.enabled || state.resetNotes) {
    state.exploreGeneration=(state.exploreGeneration||0)+1; state.explore=null; delete cooldowns.explore;
    $("explore").textContent=t("Pilih akun di Pengaturan untuk melihat progres eksplorasi.");
    delete cooldowns.notes; state.notesGeneration++; state.resetNotes=false;
    $("notes").textContent = t("Akun catatan harian: ") + (state.config.hoyolab.game_uid || t("belum dipilih"));
    $("notes-summary").textContent = t(state.config.hoyolab.enabled ? "Memuat catatan akun privat…" : "Hubungkan HoYoLAB di Pengaturan untuk melihat catatan harian.");
  }
  const c = state.config;
  if (!state.loadedUid && !state.loading) $("uid").value = c.public_account.uid; $("default-uid").value = c.public_account.uid;
  updateLoadButton();
  setLanguage(c.ui.language); $("language").value=language;
  $("akasha-enabled").checked = c.akasha.enabled; $("accent").value = c.ui.accent;
  $("hoyo-enabled").checked = c.hoyolab.enabled; $("region").value = c.hoyolab.region;
  $("auth-status").textContent = t(c.hoyolab.configured ? "Cookie tersimpan · perlu uji koneksi" : "Belum ada cookie");
  document.documentElement.dataset.accent = c.ui.accent;
  if (c.hoyolab.game_uid) $("bound-account").innerHTML = html`<option value="${escape(c.hoyolab.game_uid)}">${escape(c.hoyolab.game_uid)}</option>`;
}
async function listAccounts() {
  const result = await api("/auth/hoyolab/test", "POST", {});
  $("bound-account").innerHTML = result.data.map(a=>html`<option value="${escape(a.uid)}">${escape(a.nickname)} / ${escape(a.uid)} / ${escape(a.server)}</option>`).join("") || t('<option value="">Tidak ada akun Genshin terikat</option>');
  if (result.data.some(a=>a.uid === state.config.hoyolab.game_uid)) $("bound-account").value = state.config.hoyolab.game_uid;
  $("auth-status").textContent=t("Koneksi diuji · pilih akun catatan harian");
  notice(`Koneksi berhasil diuji. ${result.data.length} akun Genshin ditemukan.`);
  await statuses();
}
async function action(fn) {try {await fn();} catch(error) {notice(error.message,true);}}
document.addEventListener("click", event=>{
  if(event.target.closest("#retry-explore")) loadExplore();
  const view = event.target.closest("[data-view]"); if(view) show(view.dataset.view);
  const character = event.target.closest("[data-character]"); if(character) detail(character.dataset.character);
  const rankCharacter=event.target.closest("[data-akasha-build]"); if(rankCharacter) {event.preventDefault();openAkashaBuild(rankCharacter.dataset.akashaBuild);}
  const rank = event.target.closest("[data-ranking]"); if(rank) rankingDetail(rank.dataset.ranking);
  const page = event.target.closest("[data-rank-page]"); if(page) changeRankPage(Number(page.dataset.rankPage));
  const charPage = event.target.closest("[data-char-page]"); if(charPage) changeCharPage(Number(charPage.dataset.charPage));
  const rankSort = event.target.closest("[data-rank-sort]"); if(rankSort) { const key = rankSort.dataset.rankSort; state.rankDir = state.rankSort === key ? -state.rankDir : 1; state.rankSort = key; state.rankPage = 1; renderRankings(); fadeList("rankings"); }
  const tip = event.target.closest(".info-tip");
  document.querySelectorAll(".info-tip.is-open").forEach(el=>{if(el !== tip) {el.classList.remove("is-open"); el.setAttribute("aria-expanded","false");}});
  if(tip) tip.setAttribute("aria-expanded",String(tip.classList.toggle("is-open")));
  const eye = event.target.closest("[data-reveal]");
  if(eye) {
    const input = $(eye.dataset.reveal), reveal = input.type === "password";
    input.type = reveal ? "text" : "password";
    eye.setAttribute("aria-pressed",String(reveal));
    eye.setAttribute("aria-label",`${t(reveal ? "Sembunyikan" : "Tampilkan")} ${eye.dataset.label}`);
    eye.title = eye.getAttribute("aria-label");
    eye.classList.toggle("revealed",reveal);
  }
});
document.addEventListener("error",event=>{if(event.target.matches?.(".portrait img, .game-image")) event.target.hidden = true;},true);
document.addEventListener("change",event=>{if(event.target.matches("[data-rank-select]")) changeRankPage(Number(event.target.value)); if(event.target.matches("[data-char-select]")) changeCharPage(Number(event.target.value));});
document.addEventListener("keydown",event=>{if(event.key === "Enter" && event.target.matches("[data-rank-select], [data-char-select]")){event.preventDefault();event.target.dispatchEvent(new Event("change",{bubbles:true}));return;}if(event.key === "Escape") document.querySelectorAll(".info-tip.is-open").forEach(el=>{el.classList.remove("is-open");el.setAttribute("aria-expanded","false");el.blur();});});
function fadeList(id) {
  const list=$(id).querySelector(".character-grid, .table-wrap");
  if(list && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) list.animate([{opacity:.35,transform:"translateY(6px)"},{opacity:1,transform:"translateY(0)"}],{duration:300,easing:"cubic-bezier(.16,1,.3,1)"});
}
function changeRankPage(page) {
  state.rankPage = Number.isFinite(page) ? Math.trunc(page) : 1; renderRankings(); fadeList("rankings");

  $("rankings").querySelector("[data-rank-select]")?.focus({preventScroll:true});
}
function changeCharPage(page) { state.charPage = Number.isFinite(page) ? Math.trunc(page) : 1; renderCharacters(); fadeList("showcase-table"); }
$("close-dialog").addEventListener("click",()=>$("info-dialog").close());
$("info-dialog").addEventListener("click",event=>{if(event.target === $("info-dialog")) {const r=event.target.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom) event.target.close();}});
$("uid").addEventListener("input",updateLoadButton);
$("uid-form").addEventListener("submit", e=>{e.preventDefault();loadPublic($("uid").value.trim() === state.loadedUid);});
$("fetch-rankings").addEventListener("click", async ()=>{
  if (state.loading || state.rankingsLoading) return;
  const uid = $("uid").value.trim();
  if (!/^[0-9]{9,10}$/.test(uid)) { notice("Muat UID publik yang valid terlebih dahulu.", true); return; }
  if (uid !== state.uid) { await loadPublic(); return; }
  await fetchRankings(uid, state.generation, true);
  await statuses();
});
$("refresh-notes").addEventListener("click", ()=>loadNotes(true));
$("refresh-explore").addEventListener("click", ()=>loadExplore(true));
document.addEventListener("change", event=>{
  const input=event.target.closest("[data-explore-region]");
  if(!input || !state.explore) return;
  input.checked ? state.exploreSelected.add(input.dataset.exploreRegion) : state.exploreSelected.delete(input.dataset.exploreRegion);
  try {localStorage.setItem(`hoyo-explore-regions:${state.explore.uid}`,JSON.stringify([...state.exploreSelected]));} catch {}
  document.querySelectorAll("[data-explore-region]").forEach(control=>{control.checked=state.exploreSelected.has(control.dataset.exploreRegion);});
  renderExploreTotal();
});
$("element-filter").addEventListener("change",()=>{state.charPage=1;renderCharacters();}); $("sort").addEventListener("change",()=>{state.charPage=1;renderCharacters();fadeList("showcase-table");});
$("showcase-search").addEventListener("input",()=>{state.charPage=1;renderCharacters();});
$("ranking-search").addEventListener("input",()=>{state.rankPage=1;renderRankings();fadeList("rankings");});
$("ranking-sort").addEventListener("change",()=>{state.rankSort=$("ranking-sort").value;state.rankPage=1;renderRankings();fadeList("rankings");});
$("ranking-direction").addEventListener("click",()=>{state.rankDir*=-1;state.rankPage=1;renderRankings();fadeList("rankings");});
$("sort-direction").addEventListener("click",()=>{
  state.sortDirection *= -1;
  const ascending = state.sortDirection === 1;
  $("sort-direction").textContent = ascending ? "↑" : "↓";
  $("sort-direction").title = ascending ? "Urutan naik; ubah ke turun" : "Urutan turun; ubah ke naik";
  $("sort-direction").setAttribute("aria-label",$("sort-direction").title);
  state.charPage = 1; renderCharacters(); fadeList("showcase-table");
});
$("settings-form").addEventListener("submit", e=>{e.preventDefault();action(async()=>{
  await api("/config","PATCH",{public_account:{uid:$("default-uid").value.trim()},akasha:{enabled:$("akasha-enabled").checked},ui:{accent:$("accent").value,language:$("language").value}});
  await loadConfig(); location.reload();
});});
$("auth-form").addEventListener("submit", e=>{e.preventDefault();action(async()=>{
  const cookies = {ltuid_v2:$("ltuid").value,ltoken_v2:$("ltoken").value};
  if ($("ltmid").value) cookies.ltmid_v2 = $("ltmid").value;
  if ($("cookie-token").value) cookies.cookie_token_v2 = $("cookie-token").value;
  await api("/auth/hoyolab","POST",{cookies,region:$("region").value});
  state.resetNotes=true;
  for (const id of ["ltuid","ltoken","ltmid","cookie-token"]) {
    $(id).value = "";
    if ($(id).type === "text") document.querySelector(`[data-reveal="${id}"]`).click();
  }
  await loadConfig(); notice("Cookie tersimpan. Uji koneksi, lalu pilih akun catatan harian.");
});});
$("test-auth").addEventListener("click",()=>action(listAccounts));
$("delete-auth").addEventListener("click",()=>action(async()=>{
  if (!confirm(t("Hapus cookie dari config.json lokal? Koneksi HoYoLAB dan catatan harian akan dinonaktifkan. Kredensial dari environment perlu dihapus terpisah."))) return;
  await api("/auth/hoyolab","DELETE"); await loadConfig(); await statuses();
  $("notes").textContent = $("notes-summary").textContent = t("HoYoLAB dinonaktifkan. Cookie dihapus dari konfigurasi lokal.");
  $("bound-account").innerHTML = t('<option value="">Belum ada akun dipilih</option>');
  notice("Cookie lokal dihapus. Jika ada kredensial environment, hapus secara terpisah.");
}));
$("save-account").addEventListener("click",()=>action(async()=>{
  await api("/config","PATCH",{hoyolab:{enabled:$("hoyo-enabled").checked,game_uid:$("bound-account").value}});
  await loadConfig(); await loadNotes(); await statuses(); notice("Pilihan akun tersimpan.");
}));
function setupHints() {
  const hints = {
    "#uid-form label":"UID publik untuk showcase dan ranking. HoYoLAB diperlukan untuk catatan harian dan eksplorasi.",
    "#view-overview .section-label h2":"Profil berasal dari Enka. Avatar mengikuti pilihan pemain di dalam game.",
    "#view-showcase h2":"Hanya karakter dalam showcase publik tersedia. Aktifkan Show Character Details untuk membagikan build.",
    "#view-rankings h2":"Setiap row punya kategori dan asumsi sendiri. Top % = rank ÷ populasi × 100. CV berasal dari substats artifact.",
    "#view-notes h2":"Snapshot akun HoYoLAB terikat. Diperbarui saat tab terlihat dan cooldown memungkinkan.",
    "#auth-form h3":"Masukkan cookie, simpan, uji koneksi, lalu pilih akun. Tombol tampilkan hanya memperlihatkan nilai yang baru diketik.",
  };
  Object.entries(hints).forEach(([selector,text])=>document.querySelector(selector)?.insertAdjacentHTML("beforeend",help(text)));
  for (const id of ["ltuid","ltoken","ltmid","cookie-token"]) {
    const input = $(id), label = input.parentElement.firstChild.textContent.trim();
    const wrapper = document.createElement("span"); wrapper.className = "secret-field";
    input.before(wrapper); wrapper.append(input); input.type = "password";
    wrapper.insertAdjacentHTML("beforeend",html`<button type="button" class="eye-button" data-reveal="${id}" data-label="${escape(label)}" aria-label="Show ${escape(label)}" title="Show ${escape(label)}" aria-controls="${id}" aria-pressed="false"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/><path class="eye-slash" d="m3 3 18 18"/></svg></button>`);
  }
}
$("sidebar-toggle").addEventListener("click",()=>{
  const collapsed=$("primary-sidebar").classList.toggle("is-collapsed");
  $("sidebar-toggle").setAttribute("aria-expanded",String(!collapsed));
  document.querySelectorAll("#primary-sidebar .nav-item").forEach(el=>{el.title=collapsed ? el.textContent.trim() : "";});
  $("sidebar-toggle").setAttribute("aria-label",t(collapsed ? "Buka sidebar" : "Tutup sidebar"));
});
$("recent-accounts").addEventListener("change",()=>{if($("recent-accounts").value){$("uid").value=$("recent-accounts").value;loadPublic();}});
$("forget-accounts").addEventListener("click",()=>{try{localStorage.removeItem("hoyo-public-accounts");renderAccounts();notice("Riwayat akun publik dihapus.");}catch{notice("Browser tidak dapat menghapus riwayat akun.",true);}});
renderAccounts();
$("close-navigation").addEventListener("click",()=>$("navigation-dialog").close());
$("back-showcase").addEventListener("click",returnToShowcase);
document.addEventListener("click",e=>{if(e.target.closest("#clear-filters")){$("element-filter").value="";$("showcase-search").value="";state.charPage=1;renderCharacters();}});
setupHints(); captureStaticLabels();
setInterval(()=>{
  updateLoadButton();
  $("clock").textContent = new Date().toLocaleTimeString("en-GB");
  if (!document.hidden) document.querySelectorAll("[data-countdown]").forEach(el=>el.textContent=countdown(el.dataset.countdown));
},1000);
setInterval(()=>{if(!document.hidden && state.config?.hoyolab.enabled) loadNotes();},60000);
window.addEventListener("popstate",()=>{const hash=location.hash.match(/^#build-([a-f0-9]{32})$/)?.[1];if(hash){openAkashaBuild(state.rankings.findIndex(r=>r.build_hash===hash),false);return;}const id=location.hash.match(/^#character-(\d+)$/)?.[1];if(id) detail(id,false);else {show(Object.entries(paths).find(([,p])=>p===location.pathname)?.[0] || "overview", false);if(state.view==="showcase"){window.scrollTo(0,showcaseReturn.scroll);document.querySelector(`#showcase-table [data-character="${showcaseReturn.id}"]`)?.focus({preventScroll:true});}}});
action(async()=>{await loadConfig(); $("overview-secondary").hidden=!$("uid").value; await statuses(); show(Object.entries(paths).find(([,p])=>p===location.pathname)?.[0] || "overview", false); if($("uid").value) loadPublic(); await loadNotes();});

// Keep the native disclosure open until its closing animation finishes.
const disclosureAnimations=new WeakMap();
document.addEventListener("click",event=>{
  const summary=event.target.closest("#source-details > summary, .explore-details > summary");
  if(!summary) return;
  event.preventDefault();
  const panel=summary.parentElement, content=summary.nextElementSibling;
  const previous=disclosureAnimations.get(panel);
  const expanded=previous ? !previous.expanded : !panel.open;
  const height=panel.open ? content.getBoundingClientRect().height : 0;
  previous?.animation.cancel();
  if(window.matchMedia("(prefers-reduced-motion: reduce)").matches){panel.open=expanded;disclosureAnimations.delete(panel);return;}
  panel.open=true;
  const animation=content.animate([{height:`${height}px`,opacity:height ? 1 : 0},{height:`${expanded ? content.scrollHeight : 0}px`,opacity:expanded ? 1 : 0}],{duration:250,easing:"cubic-bezier(.16,1,.3,1)",fill:"both"});
  disclosureAnimations.set(panel,{animation,expanded});
  animation.onfinish=()=>{panel.open=expanded;animation.cancel();disclosureAnimations.delete(panel);};
});
