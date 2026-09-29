import type { PromotionData, PromotionFeed, PromotionSync } from "../domain/offers";

const dataBase = `${import.meta.env.BASE_URL}data`;

export async function loadPromotionData(signal?: AbortSignal): Promise<PromotionData> {
  const [feedResponse, syncResponse] = await Promise.all([
    fetch(`${dataBase}/refectory-offers.json`, { cache: "no-store", signal }),
    fetch(`${dataBase}/refectory-sync.json`, { cache: "no-store", signal }),
  ]);

  if (!feedResponse.ok || !syncResponse.ok) {
    throw new Error("Les données Refectory ne sont pas disponibles.");
  }

  const feed = (await feedResponse.json()) as PromotionFeed;
  const sync = (await syncResponse.json()) as PromotionSync;

  if (feed.schemaVersion !== 1 || sync.schemaVersion !== 1) {
    throw new Error("Le format des données Refectory n’est pas compatible.");
  }

  return { feed, sync };
}
