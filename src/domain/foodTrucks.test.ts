import { describe, expect, it } from "vitest";
import {
  formatStopDays,
  parisWeekday,
  resolveFoodTruckStops,
  type FoodTruckFeed,
} from "./foodTrucks";

const feed: FoodTruckFeed = {
  schemaVersion: 1,
  sourceUrl: "https://example.test/planning",
  updatedAt: "2026-10-01",
  locations: [
    {
      id: "parking",
      name: "Parking",
      mapUrl: "https://maps.example.test",
      accent: "#49a9ff",
    },
  ],
  foodTrucks: [
    {
      id: "daily",
      name: "Tous les jours",
      cuisine: "Test",
      website: null,
      phone: null,
      note: null,
      image: "world-bowl.jpg",
    },
    {
      id: "thursday",
      name: "Le jeudi",
      cuisine: null,
      website: null,
      phone: null,
      note: null,
      image: "burger-grill.jpg",
    },
  ],
  stops: [
    {
      truckId: "daily",
      locationId: "parking",
      days: [
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
      ],
    },
    { truckId: "thursday", locationId: "parking", days: ["thursday"] },
  ],
};

describe("planning des food trucks", () => {
  it("utilise le jour civil à Toulouse", () => {
    expect(parisWeekday(new Date("2026-09-30T22:30:00Z"))).toBe("thursday");
  });

  it("affiche en priorité uniquement les passages du jour", () => {
    expect(resolveFoodTruckStops(feed, "thursday").map(({ truck }) => truck.id)).toEqual([
      "thursday",
      "daily",
    ]);
  });

  it("identifie les stands présents tous les jours", () => {
    expect(formatStopDays(feed.stops[0].days)).toBe("Tous les jours");
  });
});
