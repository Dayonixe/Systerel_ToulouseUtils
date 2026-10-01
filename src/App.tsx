import { useMemo } from "react";
import { FoodTruckSection } from "./components/FoodTruckSection";
import { OfferSkeleton } from "./components/OfferSkeleton";
import { ExternalIcon, RefreshIcon, TagIcon, TruckIcon } from "./components/Icons";
import { PromoCard } from "./components/PromoCard";
import { parisWeekday, resolveFoodTruckStops } from "./domain/foodTrucks";
import { activeOffers, formatSyncLabel } from "./domain/offers";
import { useFoodTruckData } from "./hooks/useFoodTruckData";
import { usePromotionData } from "./hooks/usePromotionData";

const REFECTORY_OFFERS_URL = "https://www.refectory.fr/conditions-des-offres-en-cours";
const CONTRIBUTION_FORM_URL = import.meta.env.VITE_REFECTORY_FORM_URL?.trim() ?? "";

function App() {
  const foodTrucks = useFoodTruckData();
  const { status, data, error, reload } = usePromotionData();
  const offers = useMemo(() => (data ? activeOffers(data.feed) : []), [data]);
  const codeCount = offers.filter((offer) => Boolean(offer.code)).length;
  const currentDay = parisWeekday();
  const todayFoodTrucks = useMemo(
    () => foodTrucks.data ? resolveFoodTruckStops(foodTrucks.data, currentDay) : [],
    [currentDay, foodTrucks.data],
  );
  const today = new Intl.DateTimeFormat("fr-FR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    timeZone: "Europe/Paris",
  }).format(new Date());
  const syncInfo = data ? formatSyncLabel(data.sync) : null;

  return (
    <div className="app-shell">
      <header className="site-header">
        <a className="brand" href="#main" aria-label="Le Hub Toulouse — accueil">
          <span className="brand__mark" aria-hidden="true">H</span>
          <span>
            <strong>Le Hub</strong>
            <small>Toulouse · Collaborateurs</small>
          </span>
        </a>
        <nav className="site-nav" aria-label="Navigation principale">
          <a href="#food-trucks">Food trucks</a>
          <a href="#offers">Offres</a>
        </nav>
        <a className="source-link source-link--desktop" href={REFECTORY_OFFERS_URL} target="_blank" rel="noreferrer">
          Source officielle <ExternalIcon />
        </a>
      </header>

      <main id="main">
        <section className="intro" aria-labelledby="page-title">
          <div className="intro__copy">
            <p className="intro__date">{today}</p>
            <h1 id="page-title">Votre pause déjeuner, sans détour.</h1>
            <p className="intro__lead">
              Les food trucks autour du bureau et les offres Refectory du jour, réunis au même endroit.
            </p>
          </div>

          <div className="intro__ticket">
            <div className="intro__metrics">
              <div>
                <span className="intro__ticket-icon"><TruckIcon /></span>
                <span>Food trucks</span>
                <strong>{foodTrucks.status === "ready" ? todayFoodTrucks.length : "—"}</strong>
              </div>
              <div>
                <span className="intro__ticket-icon"><TagIcon /></span>
                <span>Codes promo</span>
                <strong>{status === "ready" ? codeCount : "—"}</strong>
              </div>
            </div>
            <small>
              {foodTrucks.status === "ready" && todayFoodTrucks.length > 0
                ? todayFoodTrucks.map(({ truck }) => truck.name).join(" · ")
                : "Planning en cours de chargement"}
            </small>
          </div>
        </section>

        <FoodTruckSection state={foodTrucks} today={currentDay} />

        <section id="offers" className="offers-section" aria-labelledby="offers-title">
          <div className="section-heading">
            <div>
              <p className="section-heading__kicker">Refectory</p>
              <h2 id="offers-title">Offres promotionnelles</h2>
            </div>

            {syncInfo && (
              <div className={`sync-status${syncInfo.stale ? " sync-status--stale" : ""}`} title={data?.sync.message ?? undefined}>
                <span aria-hidden="true" />
                {syncInfo.label}
              </div>
            )}
          </div>

          {status === "loading" && <OfferSkeleton />}

          {status === "error" && (
            <div className="state-panel" role="alert">
              <div className="state-panel__icon"><RefreshIcon /></div>
              <h3>Impossible de charger les offres</h3>
              <p>{error}</p>
              <button type="button" onClick={reload}><RefreshIcon /> Réessayer</button>
            </div>
          )}

          {status === "ready" && offers.length === 0 && (
            <div className="state-panel state-panel--empty">
              <div className="state-panel__icon"><TagIcon /></div>
              <h3>Aucune offre active aujourd’hui</h3>
              <p>
                La page Refectory a bien été vérifiée. Les prochaines offres apparaîtront ici dès leur publication.
              </p>
              <a href={REFECTORY_OFFERS_URL} target="_blank" rel="noreferrer">
                Consulter la source <ExternalIcon />
              </a>
            </div>
          )}

          {status === "ready" && offers.length > 0 && (
            <div className="offers-grid">
              {offers.map((offer, index) => (
                <PromoCard
                  contributionFormUrl={CONTRIBUTION_FORM_URL}
                  offer={offer}
                  index={index}
                  key={offer.id}
                />
              ))}
            </div>
          )}
        </section>

        <aside className="trust-note">
          <span aria-hidden="true">i</span>
          <p>
            Les offres sont extraites de la page publique Refectory. En cas de doute, les conditions publiées par Refectory font foi.
          </p>
        </aside>
      </main>

      <footer>
        <p>13 rue Michel Labrousse · Toulouse</p>
        <a className="source-link source-link--mobile" href={REFECTORY_OFFERS_URL} target="_blank" rel="noreferrer">
          Source officielle <ExternalIcon />
        </a>
      </footer>
    </div>
  );
}

export default App;
