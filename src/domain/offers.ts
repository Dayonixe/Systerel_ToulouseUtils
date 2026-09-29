export type SyncState = "ok" | "error" | "pending";

export interface PromotionOffer {
  id: string;
  originalText: string;
  startDate: string | null;
  endDate: string | null;
  code: string;
  codeSource: "refectory" | "contributor" | null;
  confirmationCount: number;
  discountLabel: string | null;
  minimumOrderLabel: string | null;
  cities: string[];
  scope: "global" | "toulouse";
  isCurrentlyValid: boolean;
}

export interface PromotionFeed {
  schemaVersion: 1;
  sourceUrl: string;
  offers: PromotionOffer[];
}

export interface PromotionSync {
  schemaVersion: 1;
  sourceUrl: string;
  status: SyncState;
  lastAttemptAt: string | null;
  lastSuccessAt: string | null;
  offerCount: number;
  codeCount?: number;
  waitingForCodeCount?: number;
  message: string | null;
}

export interface PromotionData {
  feed: PromotionFeed;
  sync: PromotionSync;
}

export function activeOffers(feed: PromotionFeed, now = new Date()): PromotionOffer[] {
  const today = parisDateKey(now);
  return feed.offers.filter(
    (offer) =>
      offer.isCurrentlyValid &&
      (!offer.startDate || offer.startDate <= today) &&
      (!offer.endDate || today <= offer.endDate),
  );
}

export function buildContributionUrl(
  formUrl: string,
  offer: PromotionOffer,
): string | null {
  if (!formUrl.trim()) return null;

  try {
    const url = new URL(formUrl);
    if (!['https:', 'http:'].includes(url.protocol)) return null;
    url.searchParams.set("offer_id", offer.id);
    url.searchParams.set(
      "offer_label",
      `${offer.discountLabel ?? "Offre Refectory"} — ${formatOfferPeriod(offer)}`,
    );
    if (offer.endDate) url.searchParams.set("valid_until", offer.endDate);
    return url.toString();
  } catch {
    return null;
  }
}

export function formatOfferPeriod(offer: PromotionOffer): string {
  const formatter = new Intl.DateTimeFormat("fr-FR", {
    day: "numeric",
    month: "long",
    timeZone: "Europe/Paris",
  });

  if (!offer.startDate && !offer.endDate) return "Dates non précisées";
  if (!offer.startDate && offer.endDate) {
    return `Jusqu’au ${formatter.format(asLocalDate(offer.endDate))}`;
  }
  if (offer.startDate && !offer.endDate) {
    return `À partir du ${formatter.format(asLocalDate(offer.startDate))}`;
  }

  return `Du ${formatter.format(asLocalDate(offer.startDate!))} au ${formatter.format(asLocalDate(offer.endDate!))}`;
}

export function formatSyncLabel(sync: PromotionSync, now = new Date()): {
  label: string;
  stale: boolean;
} {
  if (!sync.lastSuccessAt) {
    return { label: sync.message ?? "Synchronisation en attente", stale: true };
  }

  const updatedAt = new Date(sync.lastSuccessAt);
  const ageHours = (now.getTime() - updatedAt.getTime()) / 3_600_000;
  const formatter = new Intl.DateTimeFormat("fr-FR", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Paris",
  });

  return {
    label: `Vérifié le ${formatter.format(updatedAt)}`,
    stale: sync.status !== "ok" || ageHours > 36,
  };
}

function asLocalDate(value: string): Date {
  return new Date(`${value}T12:00:00`);
}

function parisDateKey(value: Date): string {
  const parts = new Intl.DateTimeFormat("fr-FR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    timeZone: "Europe/Paris",
  }).formatToParts(value);
  const get = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((part) => part.type === type)?.value ?? "";
  return `${get("year")}-${get("month")}-${get("day")}`;
}
