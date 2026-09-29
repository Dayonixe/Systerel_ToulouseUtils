import { describe, expect, it } from "vitest";
import { activeOffers, buildContributionUrl, formatOfferPeriod, formatSyncLabel, type PromotionFeed, type PromotionOffer } from "./offers";

const offer: PromotionOffer = {
  id: "offer-1",
  originalText: "Une offre",
  startDate: "2026-09-21",
  endDate: "2026-09-25",
  code: "TOULOUSE",
  codeSource: "refectory",
  confirmationCount: 0,
  discountLabel: "2 € offerts",
  minimumOrderLabel: "7,90 €",
  cities: ["Toulouse"],
  scope: "toulouse",
  isCurrentlyValid: true,
};

describe("activeOffers", () => {
  it("conserve aussi les offres actives dont le code est encore recherché", () => {
    const feed: PromotionFeed = {
      schemaVersion: 1,
      sourceUrl: "https://example.test",
      offers: [offer, { ...offer, id: "expired", isCurrentlyValid: false }, { ...offer, id: "no-code", code: "" }],
    };

    expect(activeOffers(feed, new Date("2026-09-25T12:00:00+02:00"))).toEqual([
      offer,
      { ...offer, id: "no-code", code: "" },
    ]);
  });

  it("masque une offre expirée même si un ancien export la marquait active", () => {
    const feed: PromotionFeed = {
      schemaVersion: 1,
      sourceUrl: "https://example.test",
      offers: [offer],
    };

    expect(activeOffers(feed, new Date("2026-09-26T12:00:00+02:00"))).toEqual([]);
  });
});

describe("buildContributionUrl", () => {
  it("préremplit les champs cachés de l'offre", () => {
    const result = new URL(buildContributionUrl("https://tally.so/r/example", offer)!);

    expect(result.searchParams.get("offer_id")).toBe("offer-1");
    expect(result.searchParams.get("valid_until")).toBe("2026-09-25");
    expect(result.searchParams.get("offer_label")).toContain("2 € offerts");
  });

  it("refuse une URL qui n'est pas HTTP", () => {
    expect(buildContributionUrl("javascript:alert(1)", offer)).toBeNull();
  });
});

describe("formatOfferPeriod", () => {
  it("affiche une période française", () => {
    expect(formatOfferPeriod(offer)).toBe("Du 21 septembre au 25 septembre");
  });
});

describe("formatSyncLabel", () => {
  it("signale une donnée trop ancienne", () => {
    const result = formatSyncLabel(
      {
        schemaVersion: 1,
        sourceUrl: "https://example.test",
        status: "ok",
        lastAttemptAt: "2026-09-22T08:00:00+02:00",
        lastSuccessAt: "2026-09-22T08:00:00+02:00",
        offerCount: 1,
        message: null,
      },
      new Date("2026-09-25T12:00:00+02:00"),
    );

    expect(result.stale).toBe(true);
  });
});
