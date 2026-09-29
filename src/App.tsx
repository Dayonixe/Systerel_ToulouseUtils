import { useMemo } from "react";
import { OfferSkeleton } from "./components/OfferSkeleton";
import { ExternalIcon, RefreshIcon, TagIcon } from "./components/Icons";
import { PromoCard } from "./components/PromoCard";
import { activeOffers, formatSyncLabel } from "./domain/offers";
import { usePromotionData } from "./hooks/usePromotionData";

const REFECTORY_OFFERS_URL = "https://www.refectory.fr/conditions-des-offres-en-cours";
const CONTRIBUTION_FORM_URL = import.meta.env.VITE_REFECTORY_FORM_URL?.trim() ?? "";

function App() {
  const { status, data, error, reload } = usePromotionData();
  const offers = useMemo(() => (data ? activeOffers(data.feed) : []), [data]);
  const codeCount = offers.filter((offer) => Boolean(offer.code)).length;
  const waitingCount = offers.length - codeCount;
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
        <a className="source-link source-link--desktop" href={REFECTORY_OFFERS_URL} target="_blank" rel="noreferrer">
          Source officielle <ExternalIcon />
        </a>
      </header>

      <main id="main">
        <section className="intro" aria-labelledby="page-title">
          <div className="intro__copy">
            <p className="intro__date">{today}</p>
            <h1 id="page-title">Les bons plans du jour, sans détour.</h1>
            <p className="intro__lead">
              Les offres Refectory valables à Toulouse, leurs codes partagés et prêts à copier.
            </p>
          </div>

          <div className="intro__ticket" aria-hidden="true">
            <div className="intro__ticket-icon"><TagIcon /></div>
            <span>Pause déjeuner</span>
            <strong>{status === "ready" ? `${codeCount} code${codeCount === 1 ? "" : "s"}` : "—"}</strong>
            <small>{waitingCount > 0 ? `${waitingCount} offre${waitingCount === 1 ? "" : "s"} à compléter` : `actif${codeCount === 1 ? "" : "s"} aujourd’hui`}</small>
          </div>
        </section>

        <section className="offers-section" aria-labelledby="offers-title">
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
