const state = {
  view: "Dashboard",
  lang: localStorage.getItem("lsm_lang") || "en",
  addType: "Institution",
  drawerMode: "create",
  currentRecord: null,
  authToken: localStorage.getItem("lsmAuthToken") || "",
  authRequired: false,
  data: {
    institutions: [],
    scholars: [],
    awards: [],
    versionLogs: [],
    auditLogs: [],
    users: [],
    currentUser: null,
    dashboard: { summary: {}, followups: [], continentCounts: {}, details: {} },
  },
  filters: {},
  sorts: {
    institutionsDate: "asc",
    scholarsDate: "asc",
  },
};

const views = ["Dashboard", "Institutions", "Scholars", "Statistics", "Users", "Audit Log"];
const vocab = {
  continents: ["AS", "EU", "AF", "NA", "SA", "OC"],
  institution_status: ["Active", "Paused", "Awaiting Agreement", "Completed"],
  scholarship_type: ["One-time", "Endowed", "Multi-year"],
  gender: ["Prefer not to say", "Female", "Male", "Other"],
  scholarship_plan: ["One-time", "Multi-year"],
};

const $ = (selector) => document.querySelector(selector);
const esc = (value) => String(value ?? "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch]);
const zhMap = {
  Dashboard: "主页",
  Institutions: "院校",
  "Partner Institutions": "院校",
  Scholars: "学者",
  Statistics: "统计",
  Users: "用户",
  "Audit Log": "操作记录",
  "Version Log": "版本记录",
  "Current Partner Institutions": "当前合作院校",
  "Partnered Institutions": "当前合作院校",
  "Scholarship Recipients": "奖学金学者",
  Countries: "覆盖国家",
  "Countries Represented": "覆盖国家",
  "Countries represented": "覆盖国家",
  "Pending Agreements": "待处理项目",
  "Pending Programs": "待处理项目",
  "Scholarships Issued": "已发放奖学金",
  "Upcoming Recipient Follow-ups": "近期学者跟进",
  "Partner Institutions by Continent": "合作院校洲别分布",
  "Export Excel": "导出Excel",
  Institution: "院校",
  Institutions: "院校",
  Scholar: "学者",
  Scholars: "学者",
  User: "用户",
  "Add Scholar": "添加学者",
  "Add User": "添加用户",
  "Add Institution": "添加院校",
  "Search institution records": "搜索院校记录",
  "Search scholar records": "搜索学者记录",
  "Search user records": "搜索用户记录",
  "No records yet. Use Add Institution to start.": "暂无记录。点击添加院校开始。",
  "No records yet. Use Add Scholar to start.": "暂无记录。点击添加学者开始。",
  "No records yet. Use Add User to start.": "暂无记录。点击添加用户开始。",
  "No follow-ups due in the next month. Active institutions with annual scholar cycles will appear here.": "未来一个月暂无跟进事项。有年度学者周期的 Active 院校会显示在这里。",
  Gender: "性别",
  Major: "专业",
  "Annual Activity": "年度活动",
  "Scholarship Map": "奖学金地图",
  "No gender data yet.": "暂无性别数据。",
  "No major data yet.": "暂无专业数据。",
  "No issued scholarship records yet.": "暂无已发放奖学金记录。",
  "No country data yet.": "暂无国家数据。",
  "No map data yet.": "暂无地图数据。",
  "welcome back": "欢迎回来",
  "Version Iteration Log": "版本迭代记录",
  "This month": "本月",
  "Next month": "下月",
  "Follow-up time": "跟进时间",
  "Agreement date": "签约时间",
  "Dep/School": "院系/项目",
  "Program / Department": "院系/项目",
  "Scholarship Announced (total)": "奖学金学者总数",
  "Scholar Name": "学者姓名",
  Country: "国家",
  Continent: "大洲",
  Type: "类型",
  Status: "状态",
  "Agreement Date": "签约日期",
  Contact: "联系方式",
  Scholarship: "奖学金",
  Actions: "操作",
  View: "查看",
  Edit: "编辑",
  Delete: "删除",
  "Issued Date": "发放日期",
  "Award Date": "获奖日期",
  Progress: "进度",
  "Next Issue": "下次发放",
  "Next issue date": "下次发放日期",
  "Schools": "院校",
  "Scholars": "学者",
  "North America": "北美洲",
  "South America": "南美洲",
  Europe: "欧洲",
  Africa: "非洲",
  Asia: "亚洲",
  Oceania: "大洋洲",
};

function t(text) {
  return state.lang === "zh" ? (zhMap[text] || text) : text;
}

function viewLabel(view) {
  return t(view);
}

function setLanguage(lang) {
  state.lang = lang === "zh" ? "zh" : "en";
  localStorage.setItem("lsm_lang", state.lang);
  document.documentElement.lang = state.lang === "zh" ? "zh-CN" : "en";
  document.body.classList.toggle("lang-zh", state.lang === "zh");
  const toggle = $("#languageToggle");
  if (toggle) {
    toggle.classList.toggle("zh", state.lang === "zh");
    toggle.classList.toggle("en", state.lang !== "zh");
    toggle.setAttribute("aria-pressed", state.lang === "zh" ? "true" : "false");
  }
}

function formatDate(value) {
  if (!value) return "—";
  const text = String(value).slice(0, 10);
  const parts = text.split("-");
  if (parts.length !== 3) return value;
  return `${parts[1]}/${parts[2]}/${parts[0]}`;
}

const el = (tag, attrs = {}, children = []) => {
  const node = document.createElement(tag);
  Object.entries(attrs).forEach(([key, value]) => {
    if (key === "class") node.className = value;
    else if (key === "html") node.innerHTML = value;
    else node.setAttribute(key, value);
  });
  children.forEach((child) => node.append(child));
  return node;
};

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (state.authToken) headers.set("Authorization", `Bearer ${state.authToken}`);
  const response = await fetch(path, { ...options, headers });
  const payload = await response.json();
  if (response.status === 401) {
    state.authRequired = true;
    renderLogin();
    throw new Error(payload.detail || "Please sign in.");
  }
  if (!response.ok) throw new Error(payload.error || payload.detail || "Something went wrong.");
  return payload;
}

async function load() {
  state.data = await api("/api/bootstrap");
  state.currentUser = state.data.currentUser || null;
  state.authRequired = false;
  setLanguage(state.lang);
  render();
}

function toast(message) {
  const node = $("#toast");
  node.textContent = message;
  node.classList.add("show");
  setTimeout(() => node.classList.remove("show"), 2200);
}

function render() {
  renderNav();
  renderUserContext();
  renderMeta();
  $("#pageTitle").textContent = viewLabel(state.view);
  const subtitle = $("#pageSubtitle");
  if (subtitle) subtitle.textContent = state.view === "Dashboard" ? t("welcome back") : "";
  const view = $("#view");
  view.innerHTML = "";
  if (state.view === "Dashboard") view.append(renderDashboard());
  if (state.view === "Institutions") view.append(renderInstitutions());
  if (state.view === "Scholars") view.append(renderScholars());
  if (state.view === "Statistics") view.append(renderStatistics());
  if (state.view === "Users") view.append(renderUsers());
  if (state.view === "Version Log") view.append(renderVersionLog());
  if (state.view === "Audit Log") view.append(renderAuditLog());
}

function renderNav() {
  const nav = $("#nav");
  nav.innerHTML = "";
  views.filter((view) => !["Audit Log", "Users"].includes(view) || isAdmin()).forEach((view) => {
    const button = el("button", { class: view === state.view ? "active" : "" }, [document.createTextNode(viewLabel(view))]);
    button.addEventListener("click", () => {
      state.view = view;
      render();
    });
    nav.append(button);
  });
}

function renderMeta() {
  const date = $("#currentDate");
  if (date) date.textContent = `New York · ${formatDate(state.data.meta?.current_date || new Date().toISOString().slice(0, 10))}`;
  const stamp = $("#versionStamp");
  if (stamp) stamp.textContent = `${state.data.meta?.version || "v2.0"} · Chirui Cheng All Rights Reserved`;
  const dot = $("#versionLogDot");
  if (dot) dot.classList.toggle("active", state.view === "Version Log");
}

function canEdit() {
  return ["admin", "editor"].includes(state.currentUser?.role);
}

function canExport() {
  return ["admin", "editor", "viewer"].includes(state.currentUser?.role);
}

function isAdmin() {
  return state.currentUser?.role === "admin";
}

function renderUserContext() {
  let node = $("#userContext");
  if (!node) {
    node = el("span", { id: "userContext", class: "user-context" });
    $(".topbar-actions")?.append(node);
  }
  node.textContent = state.currentUser ? `${state.currentUser.email} · ${state.currentUser.role}` : "";
}

function statusClass(status = "") {
  const s = status.toLowerCase();
  if (s.includes("active")) return "active";
  if (s.includes("await")) return "awaiting";
  if (s.includes("paus")) return "pending";
  if (s.includes("completed")) return "completed";
  return "";
}

function pill(status) {
  return `<span class="pill ${statusClass(status)}">${esc(status || "—")}</span>`;
}

function renderDashboard() {
  const summary = state.data.dashboard.summary || {};
  const wrap = el("div");
  wrap.innerHTML = `
    <div class="dashboard-actions">
      ${canExport() ? `<button class="primary-action" id="exportExcel">${esc(t("Export Excel"))}</button>` : ""}
    </div>
    <section class="metric-grid five">
      ${metric("Partnered Institutions", summary.institutions || 0, "institutions")}
      ${metric("Countries", summary.countries || 0, "countries")}
      ${metric("Scholarship Recipients", summary.recipients || 0, "recipients")}
      ${metric("Scholarships Issued", summary.scholarshipsIssued || 0, "scholarshipsIssued")}
      ${metric("Pending Agreements", summary.pendingPrograms || 0, "pendingPrograms")}
    </section>
    <section class="split">
      <div class="panel">
        <div class="panel-head followup-head"><h3>${esc(t("Upcoming Recipient Follow-ups"))}</h3>${followupCountersHtml()}</div>
        <div class="panel-body">${followupsHtml()}</div>
      </div>
      <div class="panel">
        <div class="panel-head"><h3>${esc(t("Partner Institutions by Continent"))}</h3></div>
        <div class="panel-body continent-grid">${continentCountsHtml()}</div>
      </div>
    </section>
  `;
  wrap.querySelector("#exportExcel")?.addEventListener("click", exportExcel);
  wrap.querySelectorAll("[data-detail]").forEach((button) => {
    button.addEventListener("click", () => openDashboardDetail(button.dataset.detail));
  });
  return wrap;
}

async function exportExcel() {
  try {
    const headers = new Headers();
    if (state.authToken) headers.set("Authorization", `Bearer ${state.authToken}`);
    const response = await fetch("/api/export.xlsx", { headers });
    if (response.status === 401) {
      state.authRequired = true;
      renderLogin();
      return;
    }
    if (!response.ok) throw new Error("Could not export Excel.");
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "lsm-scholarship-backup.xlsx";
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  } catch (error) {
    toast(error.message);
  }
}

function metric(label, value, detailKey = "") {
  const attrs = detailKey ? `class="metric metric-button" data-detail="${detailKey}" role="button" tabindex="0"` : `class="metric"`;
  return `<article ${attrs}><span>${esc(t(label))}</span><strong>${value}</strong></article>`;
}

function followupsHtml() {
  const items = state.data.dashboard.followups || [];
  if (!items.length) {
    return `<div class="empty">${esc(t("No follow-ups due in the next month. Active institutions with annual scholar cycles will appear here."))}</div>`;
  }
  return `<div class="record-list">${items.map((item) => `
    <div class="record followup-record ${item.cycle === "thisMonth" ? "this-month" : "next-month"}">
      <strong>${esc(t(item.cycle === "thisMonth" ? "This month" : "Next month"))} · ${esc(item.institution_name)} · ${esc(item.program_department || "—")}</strong>
      <span>${esc(t("Follow-up time"))}: ${esc(formatDate(item.followup_date))} · ${esc(t("Agreement date"))}: ${esc(formatDate(item.agreement_date))}</span>
    </div>
  `).join("")}</div>`;
}

function followupCountersHtml() {
  const counts = state.data.dashboard.followupCounts || {};
  return `
    <div class="followup-summary">
      <span class="this-month">${esc(t("This month"))}: <strong>${esc(counts.thisMonth || 0)}</strong></span>
      <span class="next-month">${esc(t("Next month"))}: <strong>${esc(counts.nextMonth || 0)}</strong></span>
    </div>`;
}

function continentCountsHtml() {
  const counts = state.data.dashboard.continentCounts || {};
  return vocab.continents.map((code) => `
    <div class="continent-stat">
      <strong>${esc(continentLabel(code))}</strong>
      <span>${counts[code] || 0}</span>
    </div>
  `).join("");
}

function continentLabel(code) {
  const labels = {
    AS: "Asia",
    EU: "Europe",
    AF: "Africa",
    NA: "North America",
    SA: "South America",
    OC: "Oceania",
  };
  return state.lang === "zh" ? t(labels[code] || code) : code;
}

function renderInstitutions() {
  const rows = sortByDate(filtered(state.data.institutions, ["name", "program_department", "country", "continent", "scholarship_type", "status"]), "agreement_date", state.sorts.institutionsDate);
  return listPage({
    type: "Institution",
    filterKey: "institutions",
    rows,
    columns: [
      ["Institution", (r) => esc(r.name)],
      ["Program / Department", (r) => esc(r.program_department || "—")],
      ["Country", (r) => esc(r.country)],
      ["Continent", (r) => esc(r.continent)],
      ["Type", (r) => esc(r.scholarship_type)],
      ["Status", (r) => pill(r.status)],
      ["Agreement Date", (r) => esc(formatDate(r.agreement_date))],
    ],
  });
}

function renderScholars() {
  const rows = sortByDate(filtered(state.data.scholars, ["full_name", "major", "contact", "institution_name", "award_date", "scholarship_plan"]), "award_date", state.sorts.scholarsDate);
  return listPage({
    type: "Scholar",
    filterKey: "scholars",
    rows,
    columns: [
      ["Scholar", (r) => esc(r.full_name)],
      ["Gender", (r) => esc(r.gender)],
      ["Major", (r) => esc(r.major || "—")],
      ["Contact", (r) => esc(r.contact || "—")],
      ["Issued Date", (r) => esc(formatDate(r.award_date))],
      ["Institution", (r) => esc(r.institution_name || "—")],
      ["Scholarship", (r) => scholarScholarshipCell(r)],
    ],
  });
}

function renderUsers() {
  const rows = filtered(state.data.users || [], ["email", "full_name", "role"]);
  return listPage({
    type: "User",
    filterKey: "users",
    rows,
    columns: [
      ["Email", (r) => esc(r.email)],
      ["Name", (r) => esc(r.full_name || "—")],
      ["Role", (r) => esc(r.role)],
      ["Status", (r) => r.is_active ? pill("Active") : pill("Inactive")],
    ],
  });
}

function renderVersionLog() {
  const rows = state.data.versionLogs || [];
  const wrap = el("div");
  wrap.innerHTML = rows.length ? `
    <div class="record-list version-list">
      ${rows.map((row) => `
        <div class="record version-record">
          <strong>${esc(row.version)} · ${esc(row.title)}</strong>
          <span>${esc(row.released_at)}</span>
          <p>${esc(row.notes)}</p>
        </div>
      `).join("")}
    </div>
  ` : `<div class="empty">No version log entries yet.</div>`;
  return wrap;
}

function renderAuditLog() {
  const rows = state.data.auditLogs || [];
  const wrap = el("div");
  wrap.innerHTML = rows.length ? `
    <div class="table-wrap">
      <table>
        <thead><tr><th>Time</th><th>User</th><th>Action</th><th>Record</th><th>Summary</th></tr></thead>
        <tbody>${rows.map((row) => `
          <tr>
            <td>${esc(row.created_at)}</td>
            <td>${esc(row.actor_email)}</td>
            <td>${esc(row.action)}</td>
            <td>${esc(row.entity_type)}${row.entity_id ? ` #${esc(row.entity_id)}` : ""}</td>
            <td>${esc(row.summary)}</td>
          </tr>
        `).join("")}</tbody>
      </table>
    </div>
  ` : `<div class="empty">No audit events yet.</div>`;
  return wrap;
}

function renderLogin() {
  closeDrawer();
  renderNav();
  renderUserContext();
  $("#pageTitle").textContent = "Sign In";
  const view = $("#view");
  view.innerHTML = `
    <section class="login-panel">
      <form id="loginForm" class="login-form">
        <h2>LSM Scholarship Portal</h2>
        <div class="field"><label for="loginEmail">Email</label><input id="loginEmail" name="email" type="email" required /></div>
        <div class="field"><label for="loginPassword">Password</label><input id="loginPassword" name="password" type="password" required /></div>
        <div class="form-actions"><button class="primary-action" type="submit">Sign In</button></div>
      </form>
    </section>
  `;
  $("#loginForm").addEventListener("submit", submitLogin);
}

async function submitLogin(event) {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
  try {
    const result = await api("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    state.authToken = result.token;
    localStorage.setItem("lsmAuthToken", result.token);
    closeDrawer();
    toast("Signed in");
    await load();
  } catch (error) {
    toast(error.message);
  }
}

function listPage({ type, filterKey, rows, columns }) {
  const showAddButton = ["Institution", "Scholar"].includes(type) || canManage(type);
  const wrap = el("div");
  wrap.innerHTML = `
    <div class="toolbar">
      <input class="search" id="${filterKey}Search" placeholder="${esc(t(`Search ${type.toLowerCase()} records`))}" value="${esc(state.filters[filterKey] || "")}" />
      ${showAddButton ? `<button class="primary-action add-record-button" data-add="${type}">${addButtonLabel(type)}</button>` : ""}
    </div>
    ${rows.length ? tableHtml(rows, columns, type) : `<div class="empty">${esc(t(`No records yet. Use Add ${type} to start.`))}</div>`}
  `;
  const input = wrap.querySelector(`#${filterKey}Search`);
  input.addEventListener("input", (event) => {
    state.filters[filterKey] = event.target.value;
    render();
  });
  wireAddButtons(wrap);
  wireSortButtons(wrap);
  wireRowActions(wrap, type, rows);
  return wrap;
}

function addButtonLabel(type) {
  if (state.lang === "zh" && type === "Institution") return "添加<br>院校";
  if (state.lang === "zh" && type === "Scholar") return "添加<br>学者";
  return esc(t(`Add ${type}`));
}

function tableHtml(rows, columns, type) {
  return `
    <div class="table-wrap">
      <table>
        <thead><tr>${columns.map(([label]) => headerCell(label, type)).join("")}<th class="action-col">${esc(t("Actions"))}</th></tr></thead>
        <tbody>
          ${rows.map((row) => `
            <tr>
              ${columns.map(([, get]) => `<td>${get(row)}</td>`).join("")}
              <td class="row-actions">
                <button class="secondary-action compact" data-view="${type}" data-id="${row.id}">${esc(t("View"))}</button>
                ${canManage(type) ? `<button class="secondary-action compact" data-edit="${type}" data-id="${row.id}">${esc(t("Edit"))}</button>` : ""}
                ${canManage(type) && type === "User" && row.is_active ? `<button class="danger-action compact" data-delete="${type}" data-id="${row.id}">${esc(t("Delete"))}</button>` : ""}
              </td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>`;
}

function headerCell(label, type) {
  if (type === "Institution" && label === "Agreement Date") {
    return `<th><button class="table-sort" type="button" data-sort-date="institutionsDate">${esc(t(label))} ${sortIcon(state.sorts.institutionsDate)}</button></th>`;
  }
  if (type === "Scholar" && label === "Issued Date") {
    return `<th><button class="table-sort" type="button" data-sort-date="scholarsDate">${esc(t(label))} ${sortIcon(state.sorts.scholarsDate)}</button></th>`;
  }
  return `<th>${esc(t(label))}</th>`;
}

function sortIcon(direction) {
  return direction === "asc" ? "▾" : "▴";
}

function sortByDate(rows, key, direction) {
  return [...rows].sort((a, b) => {
    const av = Date.parse(a[key] || "9999-12-31");
    const bv = Date.parse(b[key] || "9999-12-31");
    return direction === "asc" ? av - bv : bv - av;
  });
}

function wireSortButtons(root) {
  root.querySelectorAll("[data-sort-date]").forEach((button) => {
    button.addEventListener("click", () => {
      const key = button.dataset.sortDate;
      state.sorts[key] = state.sorts[key] === "asc" ? "desc" : "asc";
      render();
    });
  });
}

function wireRowActions(root, type, rows) {
  root.querySelectorAll("[data-view]").forEach((button) => {
    button.addEventListener("click", () => openRecord("view", type, rows.find((row) => String(row.id) === button.dataset.id)));
  });
  root.querySelectorAll("[data-edit]").forEach((button) => {
    button.addEventListener("click", () => openRecord("edit", type, rows.find((row) => String(row.id) === button.dataset.id)));
  });
  root.querySelectorAll("[data-delete]").forEach((button) => {
    button.addEventListener("click", () => {
      state.addType = type;
      state.currentRecord = rows.find((row) => String(row.id) === button.dataset.id);
      deleteCurrent();
    });
  });
}

function wireAddButtons(root = document) {
  root.querySelectorAll("[data-add]").forEach((button) => {
    button.addEventListener("click", () => openCreate(button.dataset.add));
  });
}

function canManage(type) {
  if (type === "User") return isAdmin();
  return canEdit();
}

function openCreate(type = "Institution") {
  state.drawerMode = "create";
  state.addType = type;
  state.currentRecord = null;
  openDrawer();
}

function openRecord(mode, type, record) {
  state.drawerMode = mode;
  state.addType = type;
  state.currentRecord = record;
  openDrawer();
}

function openDashboardDetail(kind) {
  state.drawerMode = "detail";
  state.addType = "Dashboard";
  state.currentRecord = { kind };
  openDrawer();
}

function openDrawer() {
  const modeTitle = state.drawerMode === "create" ? "Add" : state.drawerMode === "edit" ? "Edit" : "View";
  $("#drawerTitle").textContent = state.drawerMode === "detail" ? t(dashboardDetailTitle(state.currentRecord.kind)) : `${modeTitle} ${t(state.addType)}`;
  renderTypeSwitch();
  renderDrawerBody();
  $("#drawer").classList.add("open");
  $("#drawerBackdrop").classList.add("open");
  $("#drawer").setAttribute("aria-hidden", "false");
}

function closeDrawer() {
  $("#drawer").classList.remove("open");
  $("#drawerBackdrop").classList.remove("open");
  $("#drawer").setAttribute("aria-hidden", "true");
  $("#recordForm").innerHTML = "";
}

function renderTypeSwitch() {
  const switcher = $("#typeSwitch");
  switcher.innerHTML = "";
  switcher.style.display = "none";
}

function renderDrawerBody() {
  const form = $("#recordForm");
  if (state.drawerMode === "view") {
    form.innerHTML = detailHtml(state.addType, state.currentRecord);
    form.onsubmit = null;
    return;
  }
  if (state.drawerMode === "detail") {
    form.innerHTML = dashboardDetailHtml(state.currentRecord.kind);
    form.onsubmit = null;
    return;
  }
  form.innerHTML = formHtml(state.addType, state.currentRecord || {});
  form.onsubmit = submitForm;
  const plan = form.querySelector("#scholarship_plan");
  if (plan) {
    plan.addEventListener("change", () => refreshSupportYears(form));
    refreshSupportYears(form);
  }
  const type = form.querySelector("#scholarship_type");
  if (type) {
    type.addEventListener("change", () => refreshInstitutionDuration(form));
    refreshInstitutionDuration(form);
  }
}

function dashboardDetailTitle(kind) {
  return {
    institutions: "Partner Institutions",
    countries: "Countries Represented",
    pendingPrograms: "Pending Agreements",
    scholarshipsIssued: "Scholarships Issued",
    recipients: "Scholarship Recipients",
  }[kind] || "Details";
}

function dashboardDetailHtml(kind) {
  const details = state.data.dashboard.details || {};
  if (kind === "institutions") {
    const rows = (details.institutions && details.institutions.length) ? details.institutions : clientInstitutionDetails();
    return detailList(rows, ["Institution", "Dep/School", "Scholarship Announced (total)"], (row) => [
      row.name,
      row.program_department || "—",
      row.scholar_count ?? row.scholarships_issued ?? 0,
    ]);
  }
  if (kind === "countries") {
    const rows = (details.countries && details.countries.length) ? details.countries : clientCountryDetails();
    return detailList(rows, ["Country", "Partner Institutions"], (row) => [row.country, row.institution_count]);
  }
  if (kind === "scholarshipsIssued") {
    const rows = (details.scholarshipsIssued && details.scholarshipsIssued.length) ? details.scholarshipsIssued : clientScholarshipIssuedDetails();
    return detailList(rows, ["Scholar", "Institution", "Award Date", "Progress", "Next Issue"], (row) => [
      row.scholar_name,
      row.program_department ? `${row.institution_name} · ${row.program_department}` : row.institution_name,
      formatDate(row.award_date),
      row.progress,
      formatDate(row.next_issue_date),
    ]);
  }
  if (kind === "recipients") {
    const rows = details.recipients || [];
    return detailList(rows, ["Scholar Name", "Institution", "Dep/School", "Issued Date"], (row) => [
      row.scholar_name,
      row.institution_name,
      row.program_department || "—",
      formatDate(row.issued_date),
    ]);
  }
  const rows = (details.pendingPrograms && details.pendingPrograms.length) ? details.pendingPrograms : clientPendingDetails();
  return detailList(rows, ["Institution", "Program / Department", "Status", "Agreement Date"], (row) => [
    row.name,
    row.program_department || "—",
    row.status,
    formatDate(row.agreement_date),
  ]);
}

function normInstitutionName(name) {
  return String(name || "").trim().toLowerCase().replace(/\s+/g, " ");
}

function dashboardEligible(row) {
  return ["Active", "Paused", "Completed"].includes(row.status);
}

function clientInstitutionDetails() {
  return state.data.institutions.filter(dashboardEligible).sort((a, b) => a.name.localeCompare(b.name));
}

function clientCountryDetails() {
  const counts = {};
  clientInstitutionDetails().forEach((row) => {
    if (row.country) counts[row.country] = (counts[row.country] || 0) + 1;
  });
  return Object.entries(counts).sort(([a], [b]) => a.localeCompare(b)).map(([country, institution_count]) => ({ country, institution_count }));
}

function clientPendingDetails() {
  return state.data.institutions
    .filter((row) => ["Awaiting Agreement"].includes(row.status))
    .sort((a, b) => a.name.localeCompare(b.name));
}

function clientScholarshipIssuedDetails() {
  return (state.data.scholars || [])
    .filter((row) => Number(row.scholarships_issued || 0) > 0)
    .map((row) => ({
      scholar_name: row.full_name,
      institution_name: row.institution_name,
      program_department: "",
      award_date: row.award_date,
      progress: row.scholarship_progress || `${row.scholarships_issued || 0}/${row.scholarships_total || 1}`,
      next_issue_date: row.next_issue_date,
    }))
    .sort((a, b) => a.scholar_name.localeCompare(b.scholar_name));
}

function detailList(rows, headers, mapRow) {
  if (!rows.length) return `<div class="empty">No records to show.</div>`;
  return `
    <div class="table-wrap detail-table">
      <table>
        <thead><tr>${headers.map((header) => `<th>${esc(t(header))}</th>`).join("")}</tr></thead>
        <tbody>${rows.map((row) => `<tr>${mapRow(row).map((value) => `<td>${esc(value)}</td>`).join("")}</tr>`).join("")}</tbody>
      </table>
    </div>
  `;
}

function detailHtml(type, record) {
  if (!record) return `<div class="empty">Record not found.</div>`;
  const rows = type === "Institution" ? [
    ["Institution", record.name],
    ["Program / Department", record.program_department || "—"],
    ["Country", record.country],
    ["Continent", record.continent],
    ["Type", record.scholarship_type],
    ["Status", record.status],
    ["Agreement Date", formatDate(record.agreement_date)],
    ["Duration", record.scholarship_type === "Multi-year" ? record.duration_years : "—"],
    ["Scholarship Announced(total)", record.scholar_count ?? record.scholarships_issued ?? 0],
    ["Notes", record.notes || "—"],
  ] : type === "Scholar" ? [
    ["Full Name", record.full_name],
    ["Sex", record.gender],
    ["Major", record.major || "—"],
    ["Contact", record.contact || "—"],
    ["Award Date", formatDate(record.award_date)],
    ["Institution", record.institution_name || "—"],
    ["Scholarship Duration", scholarScholarshipDisplay(record)],
    ["Notes", record.notes || "—"],
  ] : [
    ["Email", record.email],
    ["Name", record.full_name || "—"],
    ["Role", record.role],
    ["Status", record.is_active ? "Active" : "Inactive"],
  ];
  return `
    <div class="detail-list">${rows.map(([label, value]) => `
      <div class="detail-row"><span>${label}</span><strong>${esc(value)}</strong></div>
    `).join("")}</div>
    <div class="form-actions">
      ${canManage(type) ? `<button class="primary-action" type="button" data-edit-current>Edit This Record</button>` : ""}
    </div>
  `;
}

function input(name, label, attrs = {}) {
  const value = attrs.value ?? "";
  const type = attrs.type || "text";
  const required = attrs.required ? "required" : "";
  const min = attrs.min ? `min="${attrs.min}"` : "";
  const max = attrs.max ? `max="${attrs.max}"` : "";
  const readonly = attrs.readonly ? "readonly" : "";
  const list = attrs.list ? `list="${attrs.list}"` : "";
  return `<div class="field"><label for="${name}">${label}</label><input id="${name}" name="${name}" type="${type}" value="${esc(value)}" ${required} ${min} ${max} ${readonly} ${list} /></div>`;
}

function select(name, label, options, attrs = {}) {
  const required = attrs.required ? "required" : "";
  const selectedValue = attrs.value ?? "";
  return `<div class="field"><label for="${name}">${label}</label><select id="${name}" name="${name}" ${required}>
    <option value="">Select</option>
    ${options.map((option) => {
      const value = option.id ?? option;
      const labelText = option.name ?? option;
      return `<option value="${esc(value)}" ${String(value) === String(selectedValue) ? "selected" : ""}>${esc(labelText)}</option>`;
    }).join("")}
  </select></div>`;
}

function textarea(name, label, value = "") {
  return `<div class="field"><label for="${name}">${label}</label><textarea id="${name}" name="${name}">${esc(value)}</textarea></div>`;
}

function normalizeSuggestion(value) {
  return String(value || "").trim().toLowerCase().replace(/\s+/g, " ");
}

function suggestions(rows, key) {
  const seen = new Set();
  return (rows || []).map((row) => row[key]).filter((value) => {
    const normalized = normalizeSuggestion(value);
    if (!normalized || seen.has(normalized)) return false;
    seen.add(normalized);
    return true;
  }).sort((a, b) => String(a).localeCompare(String(b)));
}

function datalist(id, values) {
  return `<datalist id="${id}">${values.map((value) => `<option value="${esc(value)}"></option>`).join("")}</datalist>`;
}

function scholarScholarshipDisplay(record) {
  const progress = record.scholarship_progress || `${record.scholarships_issued || 0}/${record.scholarships_total || 1}`;
  const next = record.next_issue_date ? `\n${t("Next issue date")}: ${formatDate(record.next_issue_date)}` : "";
  return `${record.scholarship_plan}\n${progress} issued${next}`;
}

function scholarScholarshipCell(record) {
  const progress = record.scholarship_progress || `${record.scholarships_issued || 0}/${record.scholarships_total || 1}`;
  const next = record.next_issue_date ? `<br><span class="subdetail">${esc(t("Next issue date"))}: ${esc(formatDate(record.next_issue_date))}</span>` : "";
  return `${esc(record.scholarship_plan)}<br><span class="subdetail">${esc(progress)} issued</span>${next}`;
}

function formHtml(type, record = {}) {
  if (type === "Institution") {
    const institutionSuggestions = datalist("institutionNameOptions", suggestions(state.data.institutions, "name"));
    const departmentSuggestions = datalist("departmentOptions", suggestions(state.data.institutions, "program_department"));
    const countrySuggestions = datalist("countryOptions", suggestions(state.data.institutions, "country"));
    return `
      ${institutionSuggestions}${departmentSuggestions}${countrySuggestions}
      ${input("name", "Institution", { required: true, value: record.name, list: "institutionNameOptions" })}
      ${input("program_department", "Dep/School", { value: record.program_department, list: "departmentOptions" })}
      <div class="form-grid">${input("country", "Country", { required: true, value: record.country, list: "countryOptions" })}${select("continent", "Continent", vocab.continents, { required: true, value: record.continent })}</div>
      <div class="form-grid">${select("scholarship_type", "Type", vocab.scholarship_type, { required: true, value: record.scholarship_type })}${select("status", "Status", vocab.institution_status, { required: true, value: record.status })}</div>
      ${input("duration_years", "Duration (years)", { type: "number", value: record.duration_years || "1", min: "1", max: "50" })}
      ${input("agreement_date", "Agreement Date", { type: "date", value: record.agreement_date })}
      ${textarea("notes", "Notes", record.notes)}
      ${actions(type)}
    `;
  }
  if (type === "Scholar") {
    const majorSuggestions = datalist("majorOptions", suggestions(state.data.scholars, "major"));
    return `
      ${majorSuggestions}
      ${input("full_name", "Full Name", { required: true, value: record.full_name })}
      <div class="form-grid">${select("gender", "Sex", vocab.gender, { required: true, value: record.gender })}${input("major", "Major", { value: record.major, list: "majorOptions" })}</div>
      ${input("contact", "Contact", { value: record.contact })}
      <div class="form-grid">${input("award_date", "Award Date", { type: "date", required: true, value: record.award_date })}${select("school_id", "Institution", state.data.institutions.map((s) => ({ id: s.id, name: s.program_department ? `${s.name} · ${s.program_department}` : s.name })), { required: true, value: record.school_id })}</div>
      <div class="form-grid">${select("scholarship_plan", "Scholarship duration", vocab.scholarship_plan, { required: true, value: record.scholarship_plan })}${input("support_years", "Number of years", { type: "number", value: record.support_years || "1", min: "1", max: "10" })}</div>
      ${textarea("notes", "Notes", record.notes)}
      ${actions(type)}
    `;
  }
  if (type === "User") {
    return `
      ${input("email", "Email", { type: "email", required: state.drawerMode !== "edit", value: record.email, readonly: state.drawerMode === "edit" })}
      ${input("full_name", "Name", { value: record.full_name })}
      <div class="form-grid">${select("role", "Role", ["admin", "editor", "viewer"], { required: true, value: record.role || "viewer" })}${select("is_active", "Status", [{ id: "true", name: "Active" }, { id: "false", name: "Inactive" }], { required: true, value: String(record.is_active ?? true) })}</div>
      ${input("password", state.drawerMode === "edit" ? "New Password (optional)" : "Password", { type: "password", required: state.drawerMode !== "edit" })}
      ${actions(type)}
    `;
  }
  return `<div class="empty">Unsupported record type.</div>`;
}

function actions(type) {
  const deleteButton = state.drawerMode === "edit" ? `<button class="danger-action" type="button" data-delete-current>Delete</button>` : "";
  return `<div class="form-actions">${deleteButton}<button class="secondary-action" type="button" id="cancelForm">Cancel</button><button class="primary-action" type="submit">Save Record</button></div>`;
}

function refreshSupportYears(form) {
  const years = form.querySelector("#support_years");
  if (!years) return;
  const multi = form.scholarship_plan.value === "Multi-year";
  years.disabled = !multi;
  years.value = multi ? Math.max(Number(years.value || 2), 2) : 1;
}

function refreshInstitutionDuration(form) {
  const duration = form.querySelector("#duration_years");
  const type = form.querySelector("#scholarship_type");
  if (!duration || !type) return;
  const multi = type.value === "Multi-year";
  duration.disabled = !multi;
  duration.value = multi ? Math.max(Number(duration.value || 1), 1) : 1;
}

async function submitForm(event) {
  event.preventDefault();
  const form = event.currentTarget;
  try {
    const payload = Object.fromEntries(new FormData(form).entries());
    if ("is_active" in payload) payload.is_active = payload.is_active === "true";
    if (!payload.password) delete payload.password;
    const base = state.addType === "Institution" ? "/api/institutions" : state.addType === "Scholar" ? "/api/scholars" : "/api/users";
      const endpoint = state.drawerMode === "edit" ? `${base}/${state.currentRecord.id}` : base;
      await api(endpoint, {
        method: state.drawerMode === "edit" ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    await load();
    closeDrawer();
    toast(`${state.addType} saved`);
  } catch (error) {
    toast(error.message);
  }
}

async function deleteCurrent() {
  if (!state.currentRecord) return;
  const type = state.addType;
  const base = type === "Institution" ? "/api/institutions" : type === "Scholar" ? "/api/scholars" : "/api/users";
  const ok = window.confirm(`Delete this ${type.toLowerCase()} record?`);
  if (!ok) return;
  try {
    await api(`${base}/${state.currentRecord.id}`, { method: "DELETE" });
    await load();
    closeDrawer();
    toast(`${type} deleted`);
  } catch (error) {
    toast(error.message);
  }
}

const genderPalette = {
  female: "#CB3B3B",
  male: "#74BEC1",
  other: "#EEF3AD",
  "prefer not to say": "#9ED763",
  unspecified: "#BEB8AF",
};
const majorPalette = ["#F0F0F0", "#0DE2EA", "#0F81C7", "#84577C", "#F3F2B4", "#38817A", "#F5587B", "#4B2C34", "#272121", "#DFBAF7", "#E16428", "#FDD043"];
const fallbackPalette = ["#8F9A8B", "#B9A99B", "#A7A6BA", "#D2B1A3", "#8EA2A6", "#C4C1AA", "#A98F86", "#D6C8A8"];

function displayValue(value) {
  return t(String(value || "—"));
}

function colorForLabel(label, index, title = "") {
  const key = String(label || "").trim().toLowerCase();
  if (String(title).toLowerCase().includes("gender")) return genderPalette[key] || genderPalette.unspecified;
  if (String(title).toLowerCase().includes("major")) return majorPalette[index % majorPalette.length];
  return fallbackPalette[index % fallbackPalette.length];
}

function topCounts(rows, limit = 7) {
  const data = (rows || []).filter((row) => Number(row.count || 0) > 0);
  if (data.length <= limit) return data;
  const head = data.slice(0, limit - 1);
  const other = data.slice(limit - 1).reduce((sum, row) => sum + Number(row.count || 0), 0);
  return [...head, { label: "Other", count: other }];
}

function polarToCartesian(cx, cy, r, angle) {
  const radians = (angle - 90) * Math.PI / 180;
  return { x: cx + (r * Math.cos(radians)), y: cy + (r * Math.sin(radians)) };
}

function describeArc(cx, cy, r, startAngle, endAngle) {
  const start = polarToCartesian(cx, cy, r, endAngle);
  const end = polarToCartesian(cx, cy, r, startAngle);
  const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";
  return `M ${cx} ${cy} L ${start.x} ${start.y} A ${r} ${r} 0 ${largeArcFlag} 0 ${end.x} ${end.y} Z`;
}

function pieChart(rows, title) {
  const data = topCounts(rows);
  const total = data.reduce((sum, row) => sum + Number(row.count || 0), 0);
  if (!total) return `<div class="empty">${esc(t(`No ${title.toLowerCase()} data yet.`))}</div>`;
  let start = -90;
  const slices = data.map((row, index) => {
    const value = Number(row.count || 0);
    const angle = (value / total) * 360;
    const end = start + angle;
    const path = describeArc(110, 110, 86, start, end);
    start = end;
    return `<path d="${path}" fill="${colorForLabel(row.label, index, title)}"><title>${esc(displayValue(row.label))}: ${value}</title></path>`;
  }).join("");
  const legend = data.map((row, index) => `<div class="legend-row"><span class="legend-swatch" style="background:${colorForLabel(row.label, index, title)}"></span><span>${esc(displayValue(row.label))}</span><strong>${row.count}</strong></div>`).join("");
  return `<div class="chart-card"><svg class="pie-svg" viewBox="0 0 220 220">${slices}<circle cx="110" cy="110" r="42" fill="var(--panel)"></circle><text x="110" y="116" text-anchor="middle" class="chart-total">${total}</text></svg><div class="legend">${legend}</div></div>`;
}

function annualChart(rows) {
  const data = rows || [];
  if (!data.length) return `<div class="empty">${esc(t("No issued scholarship records yet."))}</div>`;
  const width = 900;
  const height = 320;
  const padding = { left: 48, right: 24, top: 26, bottom: 48 };
  const maxValue = Math.max(1, ...data.flatMap((row) => [Number(row.institution_count || 0), Number(row.scholarship_count || 0)]));
  const groupWidth = (width - padding.left - padding.right) / data.length;
  const barWidth = Math.min(34, groupWidth / 4);
  const plotHeight = height - padding.top - padding.bottom;
  const bars = data.map((row, index) => {
    const x0 = padding.left + index * groupWidth + groupWidth / 2;
    const inst = Number(row.institution_count || 0);
    const scholarships = Number(row.scholarship_count || 0);
    const instH = (inst / maxValue) * plotHeight;
    const schH = (scholarships / maxValue) * plotHeight;
    return `<g>
      <rect x="${x0 - barWidth - 4}" y="${padding.top + plotHeight - instH}" width="${barWidth}" height="${instH}" fill="#FFE2B5"></rect>
      <text x="${x0 - barWidth / 2 - 4}" y="${padding.top + plotHeight - instH - 6}" text-anchor="middle" class="bar-label">${inst}</text>
      <rect x="${x0 + 4}" y="${padding.top + plotHeight - schH}" width="${barWidth}" height="${schH}" fill="#AA7766"></rect>
      <text x="${x0 + barWidth / 2 + 4}" y="${padding.top + plotHeight - schH - 6}" text-anchor="middle" class="bar-label">${scholarships}</text>
      <text x="${x0}" y="${height - 18}" text-anchor="middle" class="axis-label">${esc(row.year)}</text>
    </g>`;
  }).join("");
  return `<div class="chart-wide"><div class="chart-legend-inline"><span><i style="background:#FFE2B5"></i>${esc(t("Institutions"))}</span><span><i style="background:#AA7766"></i>${esc(t("Scholarships Issued"))}</span></div><svg class="annual-svg" viewBox="0 0 ${width} ${height}"><line x1="${padding.left}" y1="${padding.top + plotHeight}" x2="${width - padding.right}" y2="${padding.top + plotHeight}" class="axis-line"></line>${bars}</svg></div>`;
}

function continentShade(value, max) {
  if (!value) return "#E3E0DD";
  const scale = max ? value / max : 0;
  if (scale > 0.75) return "#393331";
  if (scale > 0.5) return "#7E5E58";
  if (scale > 0.25) return "#B78376";
  return "#D7B4A9";
}

function continentMap(rows) {
  const data = rows || [];
  if (!data.length) return `<div class="empty">${esc(t("No map data yet."))}</div>`;
  const byContinent = Object.fromEntries(data.map((row) => [row.continent, row]));
  const max = Math.max(1, ...data.map((row) => Number(row.scholarship_count || 0)));
  const shapes = [
    { code: "NA", label: "North America", tx: 190, ty: 188 },
    { code: "SA", label: "South America", tx: 306, ty: 374 },
    { code: "EU", label: "Europe", tx: 526, ty: 150 },
    { code: "AF", label: "Africa", tx: 548, ty: 314 },
    { code: "AS", label: "Asia", tx: 760, ty: 206 },
    { code: "OC", label: "Oceania", tx: 904, ty: 444 },
  ];
  const dotsByContinent = window.CONTINENT_DOTS || {};
  const continents = shapes.map((shape) => {
    const row = byContinent[shape.code] || { institution_count: 0, scholar_count: 0, scholarship_count: 0 };
    const title = `${shape.label}: ${row.institution_count} ${t("Schools")}, ${row.scholarship_count} ${t("Scholarships Issued")}, ${row.scholar_count} ${t("Scholars")}`;
    const fill = continentShade(Number(row.scholarship_count || 0), max);
    const points = dotsByContinent[shape.code] || [];
    const hitDots = points.map(([x, y]) => `<circle cx="${x}" cy="${y}" r="5.2"></circle>`).join("");
    const dots = points.map(([x, y]) => `<circle cx="${x}" cy="${y}" r="2.2"></circle>`).join("");
    return `<g class="world-continent" tabindex="0">
      <g class="continent-hit-dots">${hitDots}</g>
      <g class="continent-dots" fill="${fill}">${dots}</g>
      <title>${esc(title)}</title>
    </g>`;
  }).join("");
  const legend = shapes.map((shape) => {
    const row = byContinent[shape.code] || { institution_count: 0, scholar_count: 0, scholarship_count: 0 };
    return `<div class="map-stat"><strong>${esc(continentLabel(shape.code))}</strong><span>${esc(t("Schools"))}: ${row.institution_count}</span><span>${esc(t("Scholarships Issued"))}: ${row.scholarship_count}</span><span>${esc(t("Scholars"))}: ${row.scholar_count}</span></div>`;
  }).join("");
  return `<div class="world-map-wrap"><svg class="world-map-svg" viewBox="0 0 1000 588" role="img" aria-label="${esc(t("Scholarship Map"))}"><rect class="map-ocean" x="0" y="0" width="1000" height="588"></rect>${continents}</svg><div class="map-stats">${legend}</div></div>`;
}

function renderStatistics() {
  const stats = state.data.statistics || {};
  const wrap = el("div", { class: "stats-page" });
  wrap.innerHTML = `
    <section class="stats-grid">
      <div class="panel"><div class="panel-head"><h3>${esc(t("Gender"))}</h3></div><div class="panel-body">${pieChart(stats.genderCounts || [], "Gender")}</div></div>
      <div class="panel"><div class="panel-head"><h3>${esc(t("Major"))}</h3></div><div class="panel-body">${pieChart(stats.majorCounts || [], "Major")}</div></div>
    </section>
    <section class="panel stats-section"><div class="panel-head"><h3>${esc(t("Annual Activity"))}</h3></div><div class="panel-body">${annualChart(stats.annual || [])}</div></section>
    <section class="panel stats-section"><div class="panel-head"><h3>${esc(t("Scholarship Map"))}</h3></div><div class="panel-body">${continentMap(stats.continentStats || [])}</div></section>
  `;
  return wrap;
}

function currentFilterKey() {
  return {
    Institutions: "institutions",
    Scholars: "scholars",
    Users: "users",
  }[state.view];
}

function filtered(rows, keys) {
  const search = (state.filters[currentFilterKey()] || "").toLowerCase().trim();
  if (!search) return rows;
  return rows.filter((row) => keys.some((key) => String(row[key] || "").toLowerCase().includes(search)));
}

$("#versionLogDot")?.addEventListener("click", () => {
  state.view = "Version Log";
  closeDrawer();
  render();
});
$("#languageToggle")?.addEventListener("click", () => {
  setLanguage(state.lang === "zh" ? "en" : "zh");
  render();
});
$("#closeDrawer").addEventListener("click", closeDrawer);
$("#drawerBackdrop").addEventListener("click", closeDrawer);

document.addEventListener("click", (event) => {
  if (event.target && event.target.id === "cancelForm") closeDrawer();
  if (event.target && event.target.matches("[data-edit-current]")) {
    state.drawerMode = "edit";
    $("#drawerTitle").textContent = `Edit ${state.addType}`;
    renderTypeSwitch();
    renderDrawerBody();
  }
  if (event.target && event.target.matches("[data-delete-current]")) deleteCurrent();
});

load().catch((error) => {
  if (!state.authRequired) $("#view").innerHTML = `<div class="empty">${error.message}</div>`;
});
