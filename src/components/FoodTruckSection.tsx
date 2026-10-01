import { useMemo, useState } from "react";
import {
  formatStopDays,
  resolveFoodTruckStops,
  weekdayLabel,
  type Weekday,
} from "../domain/foodTrucks";
import type { useFoodTruckData } from "../hooks/useFoodTruckData";
import {
  ExternalIcon,
  MapPinIcon,
  PhoneIcon,
  RefreshIcon,
  TruckIcon,
} from "./Icons";

type FoodTruckView = "today" | "all" | Weekday;

interface FoodTruckSectionProps {
  state: ReturnType<typeof useFoodTruckData>;
  today: Weekday;
}

const filters: { value: FoodTruckView; label: string }[] = [
  { value: "today", label: "Aujourd’hui" },
  { value: "monday", label: "Lun" },
  { value: "tuesday", label: "Mar" },
  { value: "wednesday", label: "Mer" },
  { value: "thursday", label: "Jeu" },
  { value: "friday", label: "Ven" },
  { value: "all", label: "Tous" },
];
const foodImageBase = `${import.meta.env.BASE_URL}images/food`;

export function FoodTruckSection({ state, today }: FoodTruckSectionProps) {
  const [view, setView] = useState<FoodTruckView>("today");
  const selectedDay = view === "all" ? undefined : view === "today" ? today : view;
  const stops = useMemo(
    () => (state.data ? resolveFoodTruckStops(state.data, selectedDay) : []),
    [selectedDay, state.data],
  );
  const selectionLabel =
    view === "all"
      ? "Tous les passages de la semaine"
      : view === "today"
        ? `Aujourd’hui · ${weekdayLabel(today)}`
        : weekdayLabel(view);

  return (
    <section id="food-trucks" className="food-trucks-section" aria-labelledby="food-trucks-title">
      <div className="section-heading section-heading--food-trucks">
        <div>
          <p className="section-heading__kicker">Autour du bureau</p>
          <h2 id="food-trucks-title">Food trucks</h2>
        </div>
        {state.data && (
          <a
            className="source-link"
            href={state.data.sourceUrl}
            target="_blank"
            rel="noreferrer"
          >
            Planning source <ExternalIcon />
          </a>
        )}
      </div>

      <div className="food-truck-toolbar">
        <div>
          <strong>{selectionLabel}</strong>
          {state.status === "ready" && (
            <span>{stops.length} passage{stops.length === 1 ? "" : "s"}</span>
          )}
        </div>
        <div className="day-filter" role="group" aria-label="Filtrer les food trucks par jour">
          {filters.map((filter) => (
            <button
              aria-pressed={view === filter.value}
              className={view === filter.value ? "is-active" : undefined}
              key={filter.value}
              onClick={() => setView(filter.value)}
              type="button"
            >
              {filter.label}
            </button>
          ))}
        </div>
      </div>

      {state.status === "loading" && (
        <div className="food-truck-grid" aria-busy="true" aria-label="Chargement du planning">
          {[0, 1, 2].map((index) => (
            <div className="food-truck-card food-truck-card--skeleton" key={index}>
              <span className="skeleton skeleton--short" />
              <span className="skeleton skeleton--food-truck-title" />
              <span className="skeleton skeleton--line" />
            </div>
          ))}
        </div>
      )}

      {state.status === "error" && (
        <div className="state-panel state-panel--compact" role="alert">
          <div className="state-panel__icon"><RefreshIcon /></div>
          <h3>Impossible de charger le planning</h3>
          <p>{state.error}</p>
          <button type="button" onClick={state.reload}><RefreshIcon /> Réessayer</button>
        </div>
      )}

      {state.status === "ready" && stops.length === 0 && (
        <div className="state-panel state-panel--compact">
          <div className="state-panel__icon"><TruckIcon /></div>
          <h3>Aucun passage renseigné</h3>
          <p>Le planning ne mentionne aucun food truck pour cette journée.</p>
        </div>
      )}

      {state.status === "ready" && stops.length > 0 && (
        <div className="food-truck-grid">
          {stops.map(({ truck, location, days }, index) => (
            <article
              className="food-truck-card"
              key={`${truck.id}-${location.id}`}
              style={{
                "--card-index": index,
                "--location-accent": location.accent,
              } as React.CSSProperties}
            >
              <div className="food-truck-card__topline">
                <span>{formatStopDays(days)}</span>
                <TruckIcon />
              </div>
              <div className="food-truck-card__media">
                <img
                  alt=""
                  decoding="async"
                  height="720"
                  loading="lazy"
                  src={`${foodImageBase}/${truck.image}`}
                  width="720"
                />
              </div>
              <div className="food-truck-card__body">
                {truck.cuisine && <p>{truck.cuisine}</p>}
                <h3>{truck.name}</h3>
                {truck.note && <small>{truck.note}</small>}
              </div>
              <div className="food-truck-card__footer">
                {location.mapUrl ? (
                  <a href={location.mapUrl} target="_blank" rel="noreferrer">
                    <MapPinIcon /> {location.name}
                  </a>
                ) : (
                  <span><MapPinIcon /> {location.name}</span>
                )}
                <div>
                  {truck.phone && (
                    <a href={`tel:${truck.phone.replaceAll(" ", "")}`} aria-label={`Appeler ${truck.name}`}>
                      <PhoneIcon /> <span>{truck.phone}</span>
                    </a>
                  )}
                  {truck.website && (
                    <a href={truck.website} target="_blank" rel="noreferrer" aria-label={`Site de ${truck.name}`}>
                      <ExternalIcon /> <span>Site</span>
                    </a>
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
