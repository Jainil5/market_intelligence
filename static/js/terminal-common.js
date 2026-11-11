/**
 * Shared terminal UI helpers (dashboard + /app). No build step — load before app bundle.
 */
(function (global) {
  function signalBucket(signal) {
    const s = (signal || "").toLowerCase();
    if (s.includes("buy") || s.includes("long") || s.includes("bull")) return "bullish";
    if (s.includes("sell") || s.includes("short") || s.includes("bear")) return "bearish";
    if (s.includes("neutral") || s.includes("hold")) return "neutral";
    return "other";
  }

  function explainPrediction(prediction) {
    if (!prediction || typeof prediction !== "object") {
      return "No model output stored for this symbol yet.";
    }
    const signal = prediction.signal || "unknown";
    const model = prediction.model || "model";
    if (signal === "insufficient_data") {
      return `The ${model} needs more price history (only ${prediction.bars ?? "?"} bars available). Run a price backfill from Ops or cron.`;
    }
    if (prediction.sma5 != null && prediction.sma20 != null) {
      const rel =
        Number(prediction.sma5) > Number(prediction.sma20)
          ? "above"
          : Number(prediction.sma5) < Number(prediction.sma20)
            ? "below"
            : "equal to";
      return `${model}: short SMA (${prediction.sma5}) is ${rel} long SMA (${prediction.sma20}) as of ${prediction.as_of || "latest bar"} → ${signal}.`;
    }
    const extras = Object.entries(prediction)
      .filter(([k]) => !["signal", "model", "stock_id"].includes(k))
      .map(([k, v]) => `${k.replace(/_/g, " ")}: ${typeof v === "object" ? JSON.stringify(v) : v}`)
      .slice(0, 4);
    return `${model} → ${signal}${extras.length ? ". " + extras.join("; ") : ""}.`;
  }

  function parseDay(value) {
    if (!value) return null;
    const d = new Date(String(value).slice(0, 10));
    return Number.isNaN(d.getTime()) ? null : d;
  }

  function buildTimeline(row, newsItems, announcementItems) {
    const items = [];
    const move = row?.day_change_pct;
    if (row?.latest_trade_date && move != null && Math.abs(Number(move)) >= 1) {
      items.push({
        kind: "move",
        at: row.latest_trade_date,
        title: `Price moved ${move > 0 ? "+" : ""}${Number(move).toFixed(2)}% on last session`,
        meta: row.symbol || row.stock_id,
      });
    }
    (newsItems || []).forEach(function (n) {
      items.push({
        kind: "news",
        at: n.published_at || n.created_at,
        title: n.headline || "News",
        url: n.source_url,
        meta: [n.sentiment, n.source].filter(Boolean).join(" · "),
      });
    });
    (announcementItems || []).forEach(function (a) {
      items.push({
        kind: "announcement",
        at: a.published_at || a.created_at,
        title: a.title || "Announcement",
        url: a.source_url,
        meta: a.category || "",
      });
    });
    items.sort(function (a, b) {
      const da = parseDay(a.at);
      const db = parseDay(b.at);
      if (!da && !db) return 0;
      if (!da) return 1;
      if (!db) return -1;
      return db - da;
    });
    return items.slice(0, 12);
  }

  function renderTimeline(el, items) {
    if (!el) return;
    if (!items.length) {
      el.innerHTML = '<li class="empty-feed">No recent events for this symbol.</li>';
      return;
    }
    el.innerHTML = items
      .map(function (item) {
        const label = item.kind === "move" ? "Move" : item.kind === "news" ? "News" : "Filing";
        const body = item.url
          ? `<a href="${item.url}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.title)}</a>`
          : escapeHtml(item.title);
        return `<li><span class="timeline-tag">${label}</span>${body}<span class="feed-meta">${escapeHtml(
          [item.at, item.meta].filter(Boolean).join(" · ")
        )}</span></li>`;
      })
      .join("");
  }

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function freshnessClass(status) {
    if (status === "fresh") return "freshness-fresh";
    if (status === "aging") return "freshness-aging";
    if (status === "stale") return "freshness-stale";
    return "freshness-missing";
  }

  function freshnessBadge(freshness) {
    const f = freshness || {};
    const cls = freshnessClass(f.status);
    return `<span class="freshness-dot ${cls}" title="${escapeHtml(f.label || "")}"></span>`;
  }

  function applyWatchlistFilters(rows, filters) {
    const signal = filters.signal || "all";
    const sector = filters.sector || "all";
    const staleOnly = !!filters.staleOnly;
    const minAbs = Number(filters.minAbsChange);
    const query = (filters.query || "").trim().toLowerCase();
    return rows.filter(function (row) {
      if (query) {
        const hay = `${row.stock_id} ${row.symbol || ""} ${row.company_name || ""} ${row.sector || ""}`.toLowerCase();
        if (!hay.includes(query)) return false;
      }
      if (sector !== "all" && (row.sector || "—") !== sector) return false;
      if (staleOnly && (row.freshness || {}).status !== "stale") return false;
      if (signal !== "all") {
        const bucket = signalBucket((row.prediction || {}).signal);
        if (bucket !== signal) return false;
      }
      if (!Number.isNaN(minAbs) && minAbs > 0) {
        const ch = Number(row.day_change_pct);
        if (Number.isNaN(ch) || Math.abs(ch) < minAbs) return false;
      }
      return true;
    });
  }

  function collectSectors(rows) {
    const set = new Set();
    rows.forEach(function (r) {
      if (r.sector) set.add(r.sector);
    });
    return Array.from(set).sort();
  }

  function renderHealthPill(health, el) {
    if (!el || !health) return;
    const demo = health.market_data === "demo";
    const ok = health.status === "ok" || demo;
    const supa = health.checks?.supabase?.ok;
    el.className = "health-pill " + (demo || (ok && supa) ? "ok" : "warn");
    const job = health.latest_job;
    const jobBit = job ? ` · last job ${job.job_name} (${job.status})` : "";
    const modeBit = demo ? " · Demo charts (Yahoo)" : "";
    const catalog = health.demo_catalog;
    const catBit = catalog ? ` · ${catalog.symbols} symbols (${catalog.name})` : "";
    el.textContent = `${demo ? "Demo mode" : ok ? "API ok" : "Degraded"} · Supabase ${supa ? "up" : "off"}${modeBit}${catBit}${jobBit}`;
    el.title = health.timestamp || "";
  }

  function renderLoginHealth(health, el) {
    if (!el) return;
    if (!health) {
      el.textContent = "Checking server…";
      return;
    }
    renderHealthPill(health, el);
  }

  global.MITerminal = {
    signalBucket,
    explainPrediction,
    buildTimeline,
    renderTimeline,
    freshnessBadge,
    freshnessClass,
    applyWatchlistFilters,
    collectSectors,
    renderHealthPill,
    renderLoginHealth,
    escapeHtml,
    tradingViewWidgetOptions,
    mountTradingView,
  };

  function tradingViewWidgetOptions(symbol, containerId) {
    return {
      autosize: true,
      symbol,
      interval: "D",
      timezone: "Asia/Kolkata",
      theme: "dark",
      style: "1",
      locale: "en",
      toolbar_bg: "#1e222d",
      enable_publishing: false,
      allow_symbol_change: false,
      container_id: containerId,
      withdateranges: true,
      range: "6M",
      studies: ["MASimple@tv-basicstudies"],
      disabled_features: [
        "header_saveload",
        "header_compare",
        "header_undo_redo",
        "use_localstorage_for_settings",
        "create_volume_indicator_by_default",
        "show_logo_on_all_charts",
        "caption_buttons_text_if_possible",
      ],
    };
  }

  function mountTradingView(wrap, symbol, labelEl) {
    if (!wrap || !symbol) return;
    const run = function () {
      if (!global.TradingView) return;
      wrap.innerHTML = '<div id="tv_chart_inner"></div>';
      new global.TradingView.widget(tradingViewWidgetOptions(symbol, "tv_chart_inner"));
      if (labelEl) labelEl.textContent = symbol;
    };
    if (global.TradingView) run();
    else {
      var n = 0;
      var t = setInterval(function () {
        n += 1;
        if (global.TradingView) {
          clearInterval(t);
          run();
        } else if (n > 60) clearInterval(t);
      }, 100);
    }
  }
})(window);
