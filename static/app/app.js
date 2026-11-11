const STORAGE_KEY = "mi_api_key";
const MI = window.MITerminal || {};

let localChart = null;
let localSeries = null;
let localVolume = null;
let watchlistRows = [];
let useCookieAuth = false;
let currentTvSymbol = null;
let activeChartTab = "local";

function fetchOpts(method = "GET", body) {
  const opts = {
    method,
    credentials: "include",
    headers: { Accept: "application/json" },
  };
  if (!useCookieAuth) {
    const key = sessionStorage.getItem(STORAGE_KEY);
    if (key) opts.headers["x-api-key"] = key;
  }
  if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  return opts;
}

async function apiGet(path) {
  const res = await fetch(path, fetchOpts("GET"));
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json();
}

async function apiPost(path, body = {}) {
  const res = await fetch(path, fetchOpts("POST", body));
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json();
}

function fmtNum(value, digits = 2) {
  if (value === null || value === undefined || value === "") return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return String(value);
  return n.toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

function fmtPct(value) {
  if (value === null || value === undefined) return "—";
  const n = Number(value);
  if (Number.isNaN(n)) return "—";
  return (n > 0 ? "+" : "") + n.toFixed(2) + "%";
}

function changeClass(value) {
  const n = Number(value);
  if (Number.isNaN(n) || n === 0) return "";
  return n > 0 ? "pos" : "neg";
}

function tvSymbolFor(row) {
  if (row.tv_symbol) return row.tv_symbol;
  const sym = row.symbol || "";
  if (sym) return `NSE:${sym}`;
  return "NSE:NIFTY";
}

function signalClass(signal) {
  const s = (signal || "").toLowerCase();
  if (s.includes("buy") || s.includes("long") || s.includes("bull")) return "buy";
  if (s.includes("sell") || s.includes("short") || s.includes("bear")) return "sell";
  return "hold";
}

function setChartTab(name) {
  activeChartTab = name;
  document.querySelectorAll(".chart-tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === name);
  });
  document.querySelectorAll(".chart-pane").forEach((pane) => {
    pane.classList.toggle("active", pane.dataset.pane === name);
  });
  if (name === "local" && localChart) {
    const el = document.getElementById("local_chart");
    localChart.applyOptions({ width: el.clientWidth, height: el.clientHeight });
  }
  if (name === "tradingview" && currentTvSymbol) {
    renderTradingView(currentTvSymbol);
  }
}

function renderTradingView(symbol) {
  const wrap = document.getElementById("tv_chart_wrap");
  const label = document.getElementById("tv_symbol_label");
  if (MI.mountTradingView) MI.mountTradingView(wrap, symbol, label);
}

function logLoadError(context, err) {
  console.warn(context, err);
}

function ensureLocalChart() {
  if (localChart || !window.LightweightCharts) return;
  const el = document.getElementById("local_chart");
  localChart = window.LightweightCharts.createChart(el, {
    layout: { background: { color: "#0b0e11" }, textColor: "#787b86" },
    grid: { vertLines: { color: "#1e222d" }, horLines: { color: "#1e222d" } },
    rightPriceScale: { borderColor: "#363a45" },
    timeScale: { borderColor: "#363a45", timeVisible: false },
  });
  localSeries = localChart.addCandlestickSeries({
    upColor: "#26a69a",
    downColor: "#ef5350",
    borderVisible: false,
  });
  localVolume = localChart.addHistogramSeries({ priceFormat: { type: "volume" }, priceScaleId: "" });
  localVolume.priceScale().applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
}

async function loadLocalPrices(stockId) {
  try {
    ensureLocalChart();
    if (!localSeries) return;
    const body = await apiGet(`/stocks/${encodeURIComponent(stockId)}/prices?limit=365`);
  const rows = (body.prices || []).slice().reverse();
  const candles = [];
  const volumes = [];
  rows.forEach((row) => {
    if (!row.trade_date) return;
    candles.push({
      time: row.trade_date,
      open: Number(row.open),
      high: Number(row.high),
      low: Number(row.low),
      close: Number(row.close),
    });
    volumes.push({
      time: row.trade_date,
      value: Number(row.volume || 0),
      color: Number(row.close) >= Number(row.open) ? "rgba(38,166,154,0.5)" : "rgba(239,83,80,0.5)",
    });
  });
  localSeries.setData(candles);
  localVolume.setData(volumes);
    localChart.timeScale().fitContent();
  } catch (err) {
    logLoadError("OHLCV", err);
  }
}

function renderMetrics(metrics) {
  document.getElementById("metrics_strip").innerHTML = `
    <div class="metric"><span>Stocks</span><strong>${metrics.active_stocks ?? 0}</strong></div>
    <div class="metric"><span>Prices</span><strong>${metrics.price_rows ?? 0}</strong></div>
    <div class="metric"><span>News</span><strong>${metrics.news_rows ?? 0}</strong></div>
    <div class="metric"><span>Filings</span><strong>${metrics.announcement_rows ?? 0}</strong></div>`;
}

function getScreenerFilters() {
  return {
    signal: document.getElementById("filter_signal")?.value || "all",
    sector: document.getElementById("filter_sector")?.value || "all",
    staleOnly: document.getElementById("filter_stale")?.checked || false,
    minAbsChange: document.getElementById("filter_min_change")?.value || "",
    query: document.getElementById("watch_search")?.value || "",
  };
}

function applyScreenerToDom() {
  if (!MI.applyWatchlistFilters) return;
  const visible = new Set(MI.applyWatchlistFilters(watchlistRows, getScreenerFilters()).map((r) => r.stock_id));
  document.querySelectorAll(".watch-row").forEach((el) => {
    el.style.display = visible.has(el.dataset.stockId) ? "" : "none";
  });
}

function populateSectorFilter() {
  const sel = document.getElementById("filter_sector");
  if (!sel || !MI.collectSectors) return;
  while (sel.options.length > 1) sel.remove(1);
  MI.collectSectors(watchlistRows).forEach((sector) => {
    const opt = document.createElement("option");
    opt.value = sector;
    opt.textContent = sector;
    sel.appendChild(opt);
  });
}

async function loadHealthPill() {
  try {
    const health = await fetch("/health").then((r) => r.json());
    if (MI.renderHealthPill) MI.renderHealthPill(health, document.getElementById("health_pill"));
    const opsHealth = document.getElementById("ops_health");
    if (opsHealth && health.latest_job) {
      const j = health.latest_job;
      opsHealth.textContent = `Last job: ${j.job_name} · ${j.status} · ${j.started_at || ""}`;
    }
  } catch {
    const pill = document.getElementById("health_pill");
    if (pill) {
      pill.textContent = "Health unavailable";
      pill.className = "health-pill warn";
    }
  }
}

function bindScreener() {
  ["filter_signal", "filter_sector", "filter_stale", "filter_min_change"].forEach((id) => {
    const node = document.getElementById(id);
    if (!node) return;
    node.addEventListener("change", applyScreenerToDom);
    if (node.type === "number") node.addEventListener("input", applyScreenerToDom);
  });
}

function renderWatchlist(rows, onSelect) {
  const root = document.getElementById("watchlist");
  root.innerHTML = "";
  rows.forEach((row, idx) => {
    const div = document.createElement("div");
    div.className = "watch-row" + (idx === 0 ? " active" : "");
    div.dataset.stockId = row.stock_id;
    div.dataset.search = `${row.stock_id} ${row.symbol || ""} ${row.company_name || ""} ${row.sector || ""}`;
    const fresh = row.freshness || {};
    const dotClass = MI.freshnessClass ? MI.freshnessClass(fresh.status) : "freshness-missing";
    div.innerHTML = `
      <span class="watch-symbol-line">
        <span class="freshness-dot ${dotClass}" title="${fresh.label || ""}"></span>
        <span class="watch-symbol">${row.symbol || row.stock_id}</span>
      </span>
      <span class="watch-price">${row.close ?? "—"}</span>
      <span class="watch-name">${row.company_name || row.tv_symbol || ""}</span>
      <span class="watch-change ${changeClass(row.day_change_pct)}">${fmtPct(row.day_change_pct)}</span>`;
    div.addEventListener("click", () => onSelect(row, div));
    root.appendChild(div);
  });
  applyScreenerToDom();
}

function setActiveRow(activeEl) {
  document.querySelectorAll(".watch-row").forEach((el) => el.classList.remove("active"));
  activeEl.classList.add("active");
}

function renderPrediction(prediction) {
  const signalEl = document.getElementById("intel_signal");
  const predEl = document.getElementById("intel_prediction");
  const explainEl = document.getElementById("intel_signal_explain");
  const signal = prediction?.signal || "—";
  signalEl.textContent = signal;
  signalEl.className = "signal-pill " + signalClass(signal);
  if (explainEl && MI.explainPrediction) explainEl.textContent = MI.explainPrediction(prediction);
  predEl.innerHTML = "";
  Object.entries(prediction || {}).forEach(([key, val]) => {
    if (key === "signal") return;
    const dt = document.createElement("dt");
    dt.textContent = key.replace(/_/g, " ");
    const dd = document.createElement("dd");
    dd.textContent = typeof val === "object" ? JSON.stringify(val) : String(val);
    predEl.appendChild(dt);
    predEl.appendChild(dd);
  });
}

function renderFeeds(news, announcements) {
  document.getElementById("intel_news").innerHTML =
    (news.news || [])
      .map(
        (n) =>
          `<li><a href="${n.source_url}" target="_blank" rel="noopener">${n.headline}</a><span class="feed-meta">${[n.sentiment, n.source].filter(Boolean).join(" · ")}</span></li>`
      )
      .join("") || '<li class="empty-feed">No news</li>';
  document.getElementById("intel_announcements").innerHTML =
    (announcements.announcements || [])
      .map((a) => `<li><a href="${a.source_url}" target="_blank" rel="noopener">${a.title}</a></li>`)
      .join("") || '<li class="empty-feed">No announcements</li>';
}

async function selectStock(row, rowEl) {
  setActiveRow(rowEl);
  document.getElementById("bar_symbol").textContent = row.symbol || row.stock_id;
  document.getElementById("bar_company").textContent = row.company_name || "";
  document.getElementById("bar_tv").textContent = tvSymbolFor(row);
  document.getElementById("bar_price").textContent = fmtNum(row.close);
  const ch = document.getElementById("bar_change");
  ch.textContent = fmtPct(row.day_change_pct);
  ch.className = changeClass(row.day_change_pct);
  const freshEl = document.getElementById("bar_freshness");
  if (freshEl && row.freshness) {
    freshEl.textContent = row.freshness.label || "";
    freshEl.className = "sub " + (MI.freshnessClass ? MI.freshnessClass(row.freshness.status) : "");
  }
  currentTvSymbol = tvSymbolFor(row);
  if (activeChartTab === "tradingview") {
    renderTradingView(currentTvSymbol);
  }
  void loadLocalPrices(row.stock_id);
  try {
    const [snapshot, news, announcements] = await Promise.all([
      apiGet(`/stocks/${encodeURIComponent(row.stock_id)}/snapshot`),
      apiGet(`/stocks/${encodeURIComponent(row.stock_id)}/news?limit=8`),
      apiGet(`/stocks/${encodeURIComponent(row.stock_id)}/announcements?limit=8`),
    ]);
    const prediction = snapshot.stock?.latest_prediction || row.prediction;
    renderPrediction(prediction);
    renderFeeds(news, announcements);
    if (MI.buildTimeline && MI.renderTimeline) {
      MI.renderTimeline(
        document.getElementById("intel_timeline"),
        MI.buildTimeline(row, news.news || [], announcements.announcements || [])
      );
    }
  } catch (err) {
    logLoadError("stock details", err);
  }
}

async function loadJobs() {
  const body = await apiGet("/jobs/recent?limit=10");
  document.getElementById("jobs_list").innerHTML = (body.jobs || [])
    .map(
      (j) =>
        `<li><strong>${j.job_name}</strong> · ${j.status} · ${j.duration_ms ?? "—"}ms<span class="feed-meta">${j.started_at || ""}</span></li>`
    )
    .join("") || '<li class="empty-feed">No jobs yet</li>';
}

async function refreshWatchlist() {
  const watchlist = document.getElementById("watchlist");
  if (watchlist) watchlist.innerHTML = '<div class="empty-feed" style="padding:1rem">Loading live quotes…</div>';
  const [metricsBody, overviewBody] = await Promise.all([
    apiGet("/metrics"),
    apiGet("/stocks/overview/market?price_limit=10"),
  ]);
  renderMetrics(metricsBody.metrics || {});
  watchlistRows = overviewBody.stocks || [];
  populateSectorFilter();
  renderWatchlist(watchlistRows, selectStock);
  if (watchlistRows.length) await selectStock(watchlistRows[0], document.querySelector(".watch-row"));
}

async function bootApp() {
  document.getElementById("login_view").classList.add("hidden");
  document.getElementById("app_view").classList.remove("hidden");
  const health = await fetch("/health").then((r) => r.json());
  document.getElementById("env_badge").textContent = health.environment || "app";
  if (health.market_data === "demo") {
    document.getElementById("env_badge").textContent = "demo";
    const localTab = document.querySelector('.chart-tab[data-tab="local"]');
    if (localTab) localTab.textContent = "Yahoo OHLCV";
  }
  await loadHealthPill();
  document.querySelectorAll(".chart-tab").forEach((btn) => {
    btn.addEventListener("click", () => setChartTab(btn.dataset.tab));
  });
  setChartTab("local");
  await refreshWatchlist();
  bindScreener();
  document.getElementById("watch_search").addEventListener("input", () => applyScreenerToDom());
  document.getElementById("ops_toggle").addEventListener("click", () => {
    document.getElementById("ops_panel").classList.toggle("hidden");
    loadJobs().catch(() => {});
    loadHealthPill().catch(() => {});
  });
  document.getElementById("run_update_btn").addEventListener("click", async () => {
    const status = document.getElementById("ops_status");
    status.textContent = "Running update…";
    try {
      const result = await apiPost("/update/stocks", {
        include_fundamentals: true,
        include_news: true,
        include_announcements: true,
      });
      status.textContent = `Done · updated ${result.updated ?? "—"} · failed ${result.failed ?? 0}`;
      await loadJobs();
      await refreshWatchlist();
    } catch (err) {
      status.textContent = String(err.message || err);
    }
  });
  document.getElementById("refresh_data_btn").addEventListener("click", () => refreshWatchlist());
  document.getElementById("add_stock_form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    await apiPost("/admin/stocks", {
      stock_id: fd.get("stock_id"),
      symbol: fd.get("symbol"),
      yfinance_symbol: fd.get("yfinance_symbol"),
      company_name: fd.get("company_name") || null,
    });
    e.target.reset();
    document.getElementById("ops_status").textContent = "Stock created.";
    await refreshWatchlist();
  });
}

document.getElementById("login_form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const key = document.getElementById("api_key").value.trim();
  try {
    await apiPost("/auth/login", { api_key: key });
    useCookieAuth = true;
    sessionStorage.removeItem(STORAGE_KEY);
    await bootApp();
  } catch {
    try {
      sessionStorage.setItem(STORAGE_KEY, key);
      useCookieAuth = false;
      await apiGet("/metrics");
      await bootApp();
    } catch {
      alert("Invalid API key or server unavailable.");
    }
  }
});

document.getElementById("logout_btn").addEventListener("click", async () => {
  await apiPost("/auth/logout").catch(() => {});
  sessionStorage.removeItem(STORAGE_KEY);
  location.reload();
});

fetch("/health")
  .then((r) => r.json())
  .then((health) => MI.renderLoginHealth?.(health, document.getElementById("login_health")))
  .catch(() => {
    const el = document.getElementById("login_health");
    if (el) el.textContent = "Server unreachable";
  });

(async () => {
  try {
    await apiGet("/auth/session");
    useCookieAuth = true;
    await bootApp();
  } catch {
    const savedKey = sessionStorage.getItem(STORAGE_KEY);
    if (savedKey) bootApp().catch(() => sessionStorage.removeItem(STORAGE_KEY));
  }
})();
