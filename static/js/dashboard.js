(function () {
  const cfg = window.__DASHBOARD__ || {};
  const apiKey = cfg.accessToken || "";
  const MI = window.MITerminal || {};
  let tvWidget = null;
  let localChart = null;
  let localSeries = null;
  let localVolume = null;
  let selectedId = cfg.initialStockId || null;
  let activeChartTab = "local";
  let currentTvSymbol = cfg.initialTvSymbol || null;

  function apiFetch(path) {
    const headers = { Accept: "application/json" };
    if (apiKey) headers["x-api-key"] = apiKey;
    return fetch(path, { headers: headers, credentials: "include" });
  }

  function apiHeaders() {
    return { "x-api-key": apiKey, Accept: "application/json" };
  }

  function fmtNum(value, digits) {
    if (value === null || value === undefined || value === "") return "—";
    const n = Number(value);
    if (Number.isNaN(n)) return String(value);
    return n.toLocaleString(undefined, {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
  }

  function fmtPct(value) {
    if (value === null || value === undefined) return "—";
    const n = Number(value);
    if (Number.isNaN(n)) return "—";
    const sign = n > 0 ? "+" : "";
    return sign + n.toFixed(2) + "%";
  }

  function changeClass(value) {
    const n = Number(value);
    if (Number.isNaN(n) || n === 0) return "";
    return n > 0 ? "pos" : "neg";
  }

  function findRow(stockId) {
    return (cfg.watchlist || []).find(function (r) {
      return r.stock_id === stockId;
    });
  }

  function setChartTab(name) {
    activeChartTab = name;
    document.querySelectorAll(".chart-tab").forEach(function (btn) {
      btn.classList.toggle("active", btn.dataset.tab === name);
    });
    document.querySelectorAll(".chart-pane").forEach(function (pane) {
      pane.classList.toggle("active", pane.dataset.pane === name);
    });
    if (name === "local" && localChart) {
      localChart.applyOptions({ width: document.getElementById("local_chart").clientWidth });
    }
    if (name === "tradingview" && currentTvSymbol) {
      renderTradingView(currentTvSymbol);
    }
  }

  function renderTradingView(tvSymbol) {
    const wrap = document.getElementById("tv_chart_wrap");
    const label = document.getElementById("tv_symbol_label");
    if (MI.mountTradingView) {
      MI.mountTradingView(wrap, tvSymbol, label);
      return;
    }
    if (!wrap) return;
    const run = function () {
      if (!window.TradingView) return;
      wrap.innerHTML = '<div id="tv_chart_inner"></div>';
      tvWidget = new window.TradingView.widget({
      autosize: true,
      symbol: tvSymbol,
      interval: "D",
      timezone: "Asia/Kolkata",
      theme: "dark",
      style: "1",
      locale: "en",
      toolbar_bg: "#1e222d",
      enable_publishing: false,
      hide_side_toolbar: false,
      allow_symbol_change: true,
      container_id: "tv_chart_inner",
      studies: ["MASimple@tv-basicstudies", "RSI@tv-basicstudies"],
      withdateranges: true,
      range: "6M",
      details: true,
      hotlist: true,
      calendar: false,
      });
      const label = document.getElementById("tv_symbol_label");
      if (label) label.textContent = tvSymbol;
    };
    if (window.TradingView) {
      run();
      return;
    }
    let attempts = 0;
    const timer = setInterval(function () {
      attempts += 1;
      if (window.TradingView) {
        clearInterval(timer);
        run();
      } else if (attempts > 60) {
        clearInterval(timer);
      }
    }, 100);
  }

  function ensureLocalChart() {
    if (localChart || !window.LightweightCharts) return;
    const el = document.getElementById("local_chart");
    localChart = window.LightweightCharts.createChart(el, {
      layout: {
        background: { color: "#0b0e11" },
        textColor: "#787b86",
      },
      grid: {
        vertLines: { color: "#1e222d" },
        horzLines: { color: "#1e222d" },
      },
      crosshair: { mode: window.LightweightCharts.CrosshairMode.Normal },
      rightPriceScale: { borderColor: "#363a45" },
      timeScale: { borderColor: "#363a45", timeVisible: false },
    });
    localSeries = localChart.addCandlestickSeries({
      upColor: "#26a69a",
      downColor: "#ef5350",
      borderVisible: false,
      wickUpColor: "#26a69a",
      wickDownColor: "#ef5350",
    });
    localVolume = localChart.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "",
    });
    localVolume.priceScale().applyOptions({
      scaleMargins: { top: 0.82, bottom: 0 },
    });
    window.addEventListener("resize", function () {
      if (localChart) {
        localChart.applyOptions({ width: el.clientWidth, height: el.clientHeight });
      }
    });
  }

  async function loadLocalPrices(stockId) {
    ensureLocalChart();
    if (!localSeries) return;
    const res = await apiFetch("/stocks/" + encodeURIComponent(stockId) + "/prices?limit=365");
    if (!res.ok) {
      localSeries.setData([]);
      if (localVolume) localVolume.setData([]);
      return;
    }
    const body = await res.json();
    const rows = (body.prices || []).slice().reverse();
    const candles = [];
    const volumes = [];
    rows.forEach(function (row) {
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
    if (localVolume) localVolume.setData(volumes);
    localChart.timeScale().fitContent();
    const el = document.getElementById("local_chart");
    localChart.applyOptions({ width: el.clientWidth, height: el.clientHeight });
  }

  function signalClass(signal) {
    const s = (signal || "").toLowerCase();
    if (s.includes("buy") || s.includes("long") || s.includes("bull")) return "buy";
    if (s.includes("sell") || s.includes("short") || s.includes("bear")) return "sell";
    return "hold";
  }

  async function loadIntel(stockId) {
    const signalEl = document.getElementById("intel_signal");
    const predEl = document.getElementById("intel_prediction");
    const newsEl = document.getElementById("intel_news");
    const explainEl = document.getElementById("intel_signal_explain");
    const row = findRow(stockId);
    const prediction = (row && row.prediction) || {};
    const signal = prediction.signal || "—";
    signalEl.textContent = signal;
    signalEl.className = "signal-pill " + signalClass(signal);
    if (explainEl && MI.explainPrediction) {
      explainEl.textContent = MI.explainPrediction(prediction);
    }
    predEl.innerHTML = "";
    Object.keys(prediction).forEach(function (key) {
      if (key === "signal") return;
      const dt = document.createElement("dt");
      dt.textContent = key.replace(/_/g, " ");
      const dd = document.createElement("dd");
      dd.textContent = typeof prediction[key] === "object" ? JSON.stringify(prediction[key]) : String(prediction[key]);
      predEl.appendChild(dt);
      predEl.appendChild(dd);
    });

    newsEl.innerHTML = '<li class="empty-feed">Loading…</li>';
    const newsRes = await apiFetch("/stocks/" + encodeURIComponent(stockId) + "/news?limit=8");
    let newsItems = [];
    if (!newsRes.ok) {
      newsEl.innerHTML = '<li class="empty-feed">Could not load news.</li>';
    } else {
      const body = await newsRes.json();
      newsItems = body.news || [];
      if (!newsItems.length) {
        newsEl.innerHTML = '<li class="empty-feed">No recent headlines.</li>';
      } else {
        newsEl.innerHTML = "";
        newsItems.forEach(function (item) {
          const li = document.createElement("li");
          const a = document.createElement("a");
          a.href = item.source_url || "#";
          a.target = "_blank";
          a.rel = "noopener noreferrer";
          a.textContent = item.headline || "Untitled";
          li.appendChild(a);
          const meta = document.createElement("span");
          meta.className = "feed-meta";
          meta.textContent = [item.published_at, item.sentiment, item.source].filter(Boolean).join(" · ");
          li.appendChild(meta);
          newsEl.appendChild(li);
        });
      }
    }

    let annItems = [];
    const annRes = await apiFetch("/stocks/" + encodeURIComponent(stockId) + "/announcements?limit=8");
    const listEl = document.getElementById("intel_announcements");
    if (!annRes.ok) {
      if (listEl) listEl.innerHTML = '<li class="empty-feed">Could not load announcements.</li>';
    } else {
      annItems = (await annRes.json()).announcements || [];
      if (listEl) {
        if (!annItems.length) {
          listEl.innerHTML = '<li class="empty-feed">No recent filings.</li>';
        } else {
          listEl.innerHTML = "";
          annItems.forEach(function (item) {
            const li = document.createElement("li");
            const a = document.createElement("a");
            a.href = item.source_url || "#";
            a.target = "_blank";
            a.rel = "noopener noreferrer";
            a.textContent = item.title || "Untitled";
            li.appendChild(a);
            const meta = document.createElement("span");
            meta.className = "feed-meta";
            meta.textContent = [item.published_at, item.category].filter(Boolean).join(" · ");
            li.appendChild(meta);
            listEl.appendChild(li);
          });
        }
      }
    }
    if (MI.buildTimeline && MI.renderTimeline) {
      MI.renderTimeline(document.getElementById("intel_timeline"), MI.buildTimeline(row, newsItems, annItems));
    }
  }

  function updateSymbolBar(row) {
    if (!row) return;
    document.getElementById("bar_symbol").textContent = row.symbol || row.stock_id;
    document.getElementById("bar_company").textContent = row.company_name || "";
    document.getElementById("bar_tv").textContent = row.tv_symbol || "";
    document.getElementById("bar_price").textContent = fmtNum(row.close, 2);
    const ch = document.getElementById("bar_change");
    ch.textContent = fmtPct(row.day_change_pct);
    ch.className = changeClass(row.day_change_pct);
    const freshEl = document.getElementById("bar_freshness");
    if (freshEl && row.freshness) {
      freshEl.textContent = row.freshness.label || "";
      freshEl.className = "sub " + (MI.freshnessClass ? MI.freshnessClass(row.freshness.status) : "");
    }
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
    const visible = new Set(
      MI.applyWatchlistFilters(cfg.watchlist || [], getScreenerFilters()).map(function (r) {
        return r.stock_id;
      })
    );
    document.querySelectorAll(".watch-row").forEach(function (el) {
      el.style.display = visible.has(el.dataset.stockId) ? "" : "none";
    });
  }

  function populateSectorFilter() {
    const sel = document.getElementById("filter_sector");
    if (!sel || !MI.collectSectors) return;
    MI.collectSectors(cfg.watchlist || []).forEach(function (sector) {
      const opt = document.createElement("option");
      opt.value = sector;
      opt.textContent = sector;
      sel.appendChild(opt);
    });
  }

  async function loadHealthPill() {
    const el = document.getElementById("health_pill");
    if (!el) return;
    try {
      const health = await fetch("/health").then(function (r) {
        return r.json();
      });
      if (MI.renderHealthPill) MI.renderHealthPill(health, el);
    } catch {
      el.textContent = "Health unavailable";
      el.className = "health-pill warn";
    }
  }

  function bindScreener() {
    ["filter_signal", "filter_sector", "filter_stale", "filter_min_change"].forEach(function (id) {
      const node = document.getElementById(id);
      if (node) node.addEventListener("change", applyScreenerToDom);
      if (node && node.type === "number") node.addEventListener("input", applyScreenerToDom);
    });
    const search = document.getElementById("watch_search");
    if (search) {
      search.addEventListener("input", function () {
        applyScreenerToDom();
      });
    }
  }

  function selectStock(stockId) {
    const row = findRow(stockId);
    if (!row) return;
    selectedId = stockId;
    document.querySelectorAll(".watch-row").forEach(function (el) {
      el.classList.toggle("active", el.dataset.stockId === stockId);
    });
    updateSymbolBar(row);
    currentTvSymbol = row.tv_symbol || cfg.initialTvSymbol;
    if (activeChartTab === "tradingview") {
      renderTradingView(currentTvSymbol);
    }
    loadLocalPrices(stockId);
    loadIntel(stockId);
  }

  function bindWatchlist() {
    document.querySelectorAll(".watch-row").forEach(function (el) {
      el.addEventListener("click", function () {
        selectStock(el.dataset.stockId);
      });
    });
  }

  function bindSearch() {
    const input = document.getElementById("watch_search");
    if (!input) return;
    input.addEventListener("input", function () {
      applyScreenerToDom();
    });
  }

  function bindTabs() {
    document.querySelectorAll(".chart-tab").forEach(function (btn) {
      btn.addEventListener("click", function () {
        setChartTab(btn.dataset.tab);
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    bindWatchlist();
    bindSearch();
    bindTabs();
    populateSectorFilter();
    bindScreener();
    loadHealthPill();
    setChartTab("local");
    if (selectedId) {
      selectStock(selectedId);
    }
  });
})();
