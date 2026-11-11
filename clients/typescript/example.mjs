#!/usr/bin/env node
/** Example: node example.mjs (set MI_BASE_URL and MI_API_KEY) */
import MarketIntelClient from "./dist/index.js";

const client = new MarketIntelClient({
  baseUrl: process.env.MI_BASE_URL || "http://127.0.0.1:8000",
  apiKey: process.env.MI_API_KEY || "",
});

const health = await client.health();
console.log("health", health.status);
const overview = await client.marketOverview();
console.log("watchlist", overview.stocks.map((s) => s.symbol).join(", "));
