export const weekdays = [
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
  "sunday",
] as const;

export type Weekday = (typeof weekdays)[number];

export interface FoodTruck {
  id: string;
  name: string;
  cuisine: string | null;
  website: string | null;
  phone: string | null;
  note: string | null;
  image: string;
}

export interface FoodTruckLocation {
  id: string;
  name: string;
  mapUrl: string | null;
  accent: string;
}

export interface FoodTruckStop {
  truckId: string;
  locationId: string;
  days: Weekday[];
}

export interface FoodTruckFeed {
  schemaVersion: 1;
  sourceUrl: string;
  updatedAt: string;
  locations: FoodTruckLocation[];
  foodTrucks: FoodTruck[];
  stops: FoodTruckStop[];
}

export interface ResolvedFoodTruckStop {
  truck: FoodTruck;
  location: FoodTruckLocation;
  days: Weekday[];
}

const weekdayLabels: Record<Weekday, string> = {
  monday: "Lundi",
  tuesday: "Mardi",
  wednesday: "Mercredi",
  thursday: "Jeudi",
  friday: "Vendredi",
  saturday: "Samedi",
  sunday: "Dimanche",
};

export function parisWeekday(now = new Date()): Weekday {
  return new Intl.DateTimeFormat("en-US", {
    weekday: "long",
    timeZone: "Europe/Paris",
  })
    .format(now)
    .toLowerCase() as Weekday;
}

export function resolveFoodTruckStops(
  feed: FoodTruckFeed,
  day?: Weekday,
): ResolvedFoodTruckStop[] {
  const trucks = new Map(feed.foodTrucks.map((truck) => [truck.id, truck]));
  const locations = new Map(feed.locations.map((location) => [location.id, location]));

  return feed.stops
    .filter((stop) => !day || stop.days.includes(day))
    .map((stop) => {
      const truck = trucks.get(stop.truckId);
      const location = locations.get(stop.locationId);
      if (!truck || !location) return null;
      return { truck, location, days: stop.days };
    })
    .filter((stop): stop is ResolvedFoodTruckStop => stop !== null)
    .sort((left, right) => {
      if (!day) {
        const dayDifference = firstDayIndex(left.days) - firstDayIndex(right.days);
        if (dayDifference !== 0) return dayDifference;
      }
      return (
        left.location.name.localeCompare(right.location.name, "fr") ||
        left.truck.name.localeCompare(right.truck.name, "fr")
      );
    });
}

export function formatStopDays(days: Weekday[]): string {
  if (days.length === weekdays.length) return "Tous les jours";
  if (
    days.length === 5 &&
    weekdays.slice(0, 5).every((day) => days.includes(day))
  ) {
    return "Du lundi au vendredi";
  }
  return days.map((day) => weekdayLabels[day]).join(" · ");
}

export function weekdayLabel(day: Weekday): string {
  return weekdayLabels[day];
}

function firstDayIndex(days: Weekday[]): number {
  return Math.min(...days.map((day) => weekdays.indexOf(day)));
}
