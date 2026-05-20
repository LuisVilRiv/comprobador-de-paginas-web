import {
  parseCron,
  splitCronRules,
  detectFrequency,
  parseCronRule,
  serializeCronRule,
  isWeeklyRule,
  expandWeeklyRule,
  normalizeWeeklyRules,
  createWeeklyRule,
} from "./scheduler.js";


describe("Scheduler Utility Tests (12 Test Cases)", () => {
  
  test("parseCron - parses standard cron successfully", () => {
    const res = parseCron("15 14 1 5 *");
    expect(res).toEqual({ min: "15", hour: "14", dom: "1", month: "5", dow: "*" });
  });

  test("parseCron - falls back gracefully on invalid or empty cron", () => {
    const res = parseCron("");
    expect(res).toEqual({ min: "0", hour: "0", dom: "*", month: "*", dow: "*" });
  });

  test("splitCronRules - splits multiple comma-separated cron schedules", () => {
    const rules = splitCronRules("0 0 * * * , 0 12 * * *");
    expect(rules).toEqual(["0 0 * * *", "0 12 * * *"]);
  });

  test("splitCronRules - handles empty or null values elegantly", () => {
    expect(splitCronRules("")).toEqual([]);
    expect(splitCronRules(null)).toEqual([]);
  });

  test("detectFrequency - detects weekly frequency correctly", () => {
    const res = detectFrequency({ min: "0", hour: "0", dom: "*", month: "*", dow: "1,5" });
    expect(res).toBe("weekly");
  });

  test("detectFrequency - detects monthly periodic frequency correctly", () => {
    const res = detectFrequency({ min: "0", hour: "0", dom: "*", month: "*/3", dow: "*" });
    expect(res).toBe("monthly_periodic");
  });

  test("detectFrequency - detects daily periodic frequency correctly", () => {
    const res = detectFrequency({ min: "0", hour: "0", dom: "*/5", month: "*", dow: "*" });
    expect(res).toBe("daily_periodic");
  });

  test("detectFrequency - detects monthly frequency correctly", () => {
    const res = detectFrequency({ min: "0", hour: "0", dom: "15", month: "*", dow: "*" });
    expect(res).toBe("monthly");
  });

  test("detectFrequency - detects yearly frequency correctly", () => {
    const res = detectFrequency({ min: "0", hour: "0", dom: "15", month: "12", dow: "*" });
    expect(res).toBe("yearly");
  });

  test("parseCronRule - extracts and structures cron values", () => {
    const rule = parseCronRule("30 18 10 * *");
    expect(rule).toEqual({ min: "30", hour: "18", dom: "10", month: "*", dow: "*" });
  });

  test("serializeCronRule - stringifies cron rule objects", () => {
    const rule = { min: "5", hour: "6", dom: "7", month: "8", dow: "1" };
    expect(serializeCronRule(rule)).toBe("5 6 7 8 1");
  });

  test("isWeeklyRule - checks if rules fit weekly criteria", () => {
    const r1 = { min: "0", hour: "0", dom: "*", month: "*", dow: "2" };
    const r2 = { min: "0", hour: "0", dom: "10", month: "*", dow: "2" };
    expect(isWeeklyRule(r1)).toBe(true);
    expect(isWeeklyRule(r2)).toBe(false);
  });

  test("expandWeeklyRule - expands comma-separated weekly days into individual rules", () => {
    const rule = { min: "0", hour: "0", dom: "*", month: "*", dow: "1,3" };
    const expanded = expandWeeklyRule(rule);
    expect(expanded).toHaveLength(2);
    expect(expanded[0].dow).toBe("1");
    expect(expanded[1].dow).toBe("3");
  });

  test("normalizeWeeklyRules - expands and sorts weekly rules based on day number", () => {
    const rules = [
      { min: "0", hour: "0", dom: "*", month: "*", dow: "4,2" }
    ];
    const normalized = normalizeWeeklyRules(rules);
    expect(normalized).toHaveLength(2);
    expect(normalized[0].dow).toBe("2");
    expect(normalized[1].dow).toBe("4");
  });

  test("createWeeklyRule - builds correct weekly rule structure", () => {
    expect(createWeeklyRule("5")).toEqual({ min: "0", hour: "0", dom: "*", month: "*", dow: "5" });
  });

});
