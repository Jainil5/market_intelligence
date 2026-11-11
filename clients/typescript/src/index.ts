export type StockOverview = {
  stock_id: string;
  symbol?: string;
  company_name?: string;
  tv_symbol?: string;
  close?: number;
  day_change_pct?: number;
  prediction?: Record<string, unknown>;
};

export type MarketIntelClientOptions = {
  baseUrl: string;
  apiKey: string;
  fetchImpl?: typeof fetch;
};

export class MarketIntelClient {
  private readonly baseUrl: string;
  private readonly apiKey: string;
  private readonly fetchImpl: typeof fetch;

  constructor(options: MarketIntelClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/$/, "");
    this.apiKey = options.apiKey;
    this.fetchImpl = options.fetchImpl ?? fetch;
  }

  private headers(): HeadersInit {
    return { "x-api-key": this.apiKey, Accept: "application/json" };
  }

  async health(): Promise<Record<string, unknown>> {
    return this.get("/health", false);
  }

  async metrics(): Promise<{ metrics: Record<string, number> }> {
    return this.get("/metrics");
  }

  async listStocks(params?: { search?: string; sector?: string; includeInactive?: boolean }) {
    const q = new URLSearchParams();
    if (params?.search) q.set("search", params.search);
    if (params?.sector) q.set("sector", params.sector);
    if (params?.includeInactive) q.set("include_inactive", "true");
    const suffix = q.toString() ? `?${q}` : "";
    return this.get<{ stocks: Record<string, unknown>[] }>(`/stocks${suffix}`);
  }

  async marketOverview() {
    return this.get<{ stocks: StockOverview[] }>("/stocks/overview/market");
  }

  async stockSnapshot(stockId: string) {
    return this.get(`/stocks/${encodeURIComponent(stockId)}/snapshot`);
  }

  async stockPrices(stockId: string, limit = 90) {
    return this.get(`/stocks/${encodeURIComponent(stockId)}/prices?limit=${limit}`);
  }

  async stockNews(stockId: string, limit = 20) {
    return this.get(`/stocks/${encodeURIComponent(stockId)}/news?limit=${limit}`);
  }

  async stockAnnouncements(stockId: string, limit = 20) {
    return this.get(`/stocks/${encodeURIComponent(stockId)}/announcements?limit=${limit}`);
  }

  async updateStocks(body: Record<string, unknown> = {}) {
    return this.post("/update/stocks", body);
  }

  async login(payload: { api_key: string }) {
    return this.post("/auth/login", payload, false);
  }

  async logout() {
    return this.post("/auth/logout", {});
  }

  async recentJobs(limit = 20) {
    return this.get(`/jobs/recent?limit=${limit}`);
  }

  async createStock(body: Record<string, unknown>) {
    return this.post("/admin/stocks", body);
  }

  private async get<T>(path: string, auth = true): Promise<T> {
    const res = await this.fetchImpl(`${this.baseUrl}${path}`, {
      headers: auth ? this.headers() : { Accept: "application/json" },
    });
    if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
    return res.json() as Promise<T>;
  }

  private async post<T>(path: string, body: unknown, auth = true): Promise<T> {
    const headers: HeadersInit = { "Content-Type": "application/json", Accept: "application/json" };
    if (auth) Object.assign(headers, this.headers());
    const res = await this.fetchImpl(`${this.baseUrl}${path}`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
    return res.json() as Promise<T>;
  }
}

export default MarketIntelClient;
