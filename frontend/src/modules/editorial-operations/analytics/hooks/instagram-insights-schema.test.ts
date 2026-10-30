import { describe, expect, it } from "vitest";
import {
  instagramConnectorSchema,
  instagramInsightsSchema,
  instagramPostInsightsSchema,
} from "./instagram-insights-schema";

const ROW = {
  media_id: "1789",
  carousel_project_id: null,
  permalink: null,
  topic: null,
  views: 1000,
  reach: 800,
  saved: 40,
  shares: 10,
  follows: null,
  profile_visits: 25,
  total_interactions: 90,
  shares_per_100_views: 1,
  fetched_at: "2026-10-30T10:00:00Z",
  stale: false,
};

const CONNECTOR = {
  channel: "instagram",
  configured: true,
  last_sync_at: "2026-10-30T10:00:00Z",
  stale: false,
  error: null,
};

describe("instagramInsightsSchema", () => {
  it("parses the response with the connector block", () => {
    const parsed = instagramInsightsSchema.parse({
      items: [ROW],
      follows_total: 5,
      follows_per_post: 5,
      shares_per_100_views: 1,
      configured: true,
      connector: CONNECTOR,
    });

    expect(parsed.connector.channel).toBe("instagram");
    expect(parsed.items[0]?.views).toBe(1000);
  });

  it("rejects a response without the connector block", () => {
    expect(() =>
      instagramInsightsSchema.parse({
        items: [],
        follows_total: null,
        follows_per_post: null,
        shares_per_100_views: null,
        configured: true,
      }),
    ).toThrow();
  });

  it("keeps a missing metric null in a post row", () => {
    const parsed = instagramPostInsightsSchema.parse(ROW);
    expect(parsed.follows).toBeNull();
  });

  it("parses a connector with an error and no last sync", () => {
    const parsed = instagramConnectorSchema.parse({
      channel: "instagram",
      configured: true,
      last_sync_at: null,
      stale: true,
      error: "graph_down",
    });

    expect(parsed.error).toBe("graph_down");
    expect(parsed.stale).toBe(true);
  });
});
