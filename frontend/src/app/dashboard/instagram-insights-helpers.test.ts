import { describe, expect, it } from "vitest";
import type { InstagramPostInsights } from "@/modules/editorial-operations";
import { formatMetric, sumMetric } from "./instagram-insights-helpers";

function post(
  overrides: Partial<InstagramPostInsights> = {},
): InstagramPostInsights {
  return {
    media_id: "1",
    carousel_project_id: null,
    permalink: null,
    topic: null,
    views: null,
    reach: null,
    saved: null,
    shares: null,
    follows: null,
    profile_visits: null,
    total_interactions: null,
    shares_per_100_views: null,
    fetched_at: null,
    stale: false,
    ...overrides,
  };
}

describe("instagram insights helpers", () => {
  it("sums only the posts that report the metric", () => {
    const items = [
      post({ follows: 3 }),
      post({ follows: null }),
      post({ follows: 2 }),
    ];
    expect(sumMetric(items, "follows")).toBe(5);
  });

  // Scenario: Missing metric
  it("is null (n/d) when no post reports the metric", () => {
    expect(sumMetric([post(), post()], "follows")).toBeNull();
    expect(sumMetric([], "views")).toBeNull();
    expect(formatMetric(null, "n/d", "pt-BR")).toBe("n/d");
  });

  it("formats counts and ratios for the locale", () => {
    expect(formatMetric(1234, "n/d", "pt-BR")).toBe("1.234");
    expect(formatMetric(0, "n/d", "en")).toBe("0");
    expect(formatMetric(1.256, "n/d", "en")).toBe("1.26");
  });
});
