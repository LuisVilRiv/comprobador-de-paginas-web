import {
  apiFetch,
  fetchClients,
  createClient,
  updateClient,
  deleteClient,
  fetchWebsites,
  createWebsite,
  updateWebsite,
  deleteWebsite,
  triggerAudit,
  fetchWebsiteRuns,
  fetchRunDetail,
  fetchRunSections,
  fetchRunIssues,
  fetchSummary,
  fetchSettings,
  saveSettings,
  exportClientReport,
} from "./api.js";


describe("API fetch layer (10 Test Cases)", () => {
  
  beforeEach(() => {
    global.fetch = jest.fn();
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  test("apiFetch - success GET returns JSON response", async () => {
    const mockData = { id: 1, name: "Test" };
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: jest.fn().mockResolvedValueOnce(mockData),
    });

    const res = await apiFetch("/test");
    expect(res).toEqual(mockData);
    expect(global.fetch).toHaveBeenCalledWith("/api/test", {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });
  });

  test("apiFetch - sends JSON body with POST method", async () => {
    const bodyData = { name: "New entity" };
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: jest.fn().mockResolvedValueOnce({ success: true }),
    });

    await apiFetch("/test", "POST", bodyData);
    expect(global.fetch).toHaveBeenCalledWith("/api/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(bodyData),
    });
  });

  test("apiFetch - throws error on response failure (!ok)", async () => {
    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      text: jest.fn().mockResolvedValueOnce("Internal Server Error"),
    });

    await expect(apiFetch("/test")).rejects.toThrow("API 500: Internal Server Error");
  });

  test("fetchClients - calls GET on /clients", async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: jest.fn().mockResolvedValueOnce([]),
    });

    await fetchClients();
    expect(global.fetch).toHaveBeenCalledWith("/api/clients", expect.any(Object));
  });

  test("createClient - calls POST on /clients with data", async () => {
    const data = { name: "Client A" };
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: jest.fn().mockResolvedValueOnce({ id: 1 }),
    });

    await createClient(data);
    expect(global.fetch).toHaveBeenCalledWith(
      "/api/clients",
      expect.objectContaining({ method: "POST", body: JSON.stringify(data) })
    );
  });

  test("fetchWebsites - appends client_id query param when provided", async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: jest.fn().mockResolvedValueOnce([]),
    });

    await fetchWebsites("123");
    expect(global.fetch).toHaveBeenCalledWith("/api/websites?client_id=123", expect.any(Object));
  });

  test("triggerAudit - posts to website audit endpoint", async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: jest.fn().mockResolvedValueOnce({ success: true }),
    });

    await triggerAudit("w-99");
    expect(global.fetch).toHaveBeenCalledWith("/api/websites/w-99/audit", expect.objectContaining({ method: "POST" }));
  });

  test("fetchRunIssues - structures query parameters for category and severity filters", async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: jest.fn().mockResolvedValueOnce([]),
    });

    await fetchRunIssues("run-1", "seo", "high");
    expect(global.fetch).toHaveBeenCalledWith(
      "/api/runs/run-1/issues?category=seo&severity=high",
      expect.any(Object)
    );
  });

  test("saveSettings - puts updated configs to /settings endpoint", async () => {
    const payload = { cron_active: "0 0 * * *" };
    global.fetch.mockResolvedValueOnce({
      ok: true,
      json: jest.fn().mockResolvedValueOnce({ success: true }),
    });

    await saveSettings(payload);
    expect(global.fetch).toHaveBeenCalledWith(
      "/api/settings",
      expect.objectContaining({ method: "PUT", body: JSON.stringify(payload) })
    );
  });

  test("exportClientReport - returns a binary blob on success response", async () => {
    const mockBlob = new Blob(["pdf content"], { type: "application/pdf" });
    global.fetch.mockResolvedValueOnce({
      ok: true,
      blob: jest.fn().mockResolvedValueOnce(mockBlob),
    });

    const res = await exportClientReport("client-1");
    expect(res).toBe(mockBlob);
    expect(global.fetch).toHaveBeenCalledWith("/api/clients/client-1/export");
  });

});
