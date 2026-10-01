import type { FoodTruckFeed } from "../domain/foodTrucks";

const foodTrucksUrl = `${import.meta.env.BASE_URL}data/food-trucks.json`;

export async function loadFoodTruckData(signal?: AbortSignal): Promise<FoodTruckFeed> {
  const response = await fetch(foodTrucksUrl, { cache: "no-store", signal });
  if (!response.ok) {
    throw new Error("Le planning des food trucks n’est pas disponible.");
  }

  const feed = (await response.json()) as FoodTruckFeed;
  if (
    feed.schemaVersion !== 1 ||
    !Array.isArray(feed.locations) ||
    !Array.isArray(feed.foodTrucks) ||
    !Array.isArray(feed.stops)
  ) {
    throw new Error("Le format du planning des food trucks n’est pas compatible.");
  }

  return feed;
}
