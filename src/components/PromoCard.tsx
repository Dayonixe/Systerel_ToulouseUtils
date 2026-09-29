import { useState } from "react";
import type { PromotionOffer } from "../domain/offers";
import { buildContributionUrl, formatOfferPeriod } from "../domain/offers";
import { CheckIcon, CopyIcon, ExternalIcon } from "./Icons";

interface PromoCardProps {
  offer: PromotionOffer;
  index: number;
  contributionFormUrl: string;
}

export function PromoCard({ offer, index, contributionFormUrl }: PromoCardProps) {
  const [copied, setCopied] = useState(false);
  const [copyFailed, setCopyFailed] = useState(false);
  const hasCode = Boolean(offer.code);
  const contributionUrl = buildContributionUrl(contributionFormUrl, offer);

  async function copyCode() {
    try {
      await navigator.clipboard.writeText(offer.code);
      setCopyFailed(false);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopyFailed(true);
    }
  }

  return (
    <article className="promo-card" style={{ "--card-index": index } as React.CSSProperties}>
      <div className="promo-card__topline">
        <span className={`promo-card__status${hasCode ? "" : " promo-card__status--waiting"}`}>
          <span aria-hidden="true" /> {hasCode ? "Code disponible" : "Code recherché"}
        </span>
        <span className="promo-card__scope">
          {offer.scope === "global" ? "Tous les secteurs" : "Toulouse"}
        </span>
      </div>

      <div className="promo-card__body">
        <p className="promo-card__eyebrow">Offre Refectory</p>
        <h2>{offer.discountLabel ?? "Avantage en cours"}</h2>
        <p className="promo-card__period">{formatOfferPeriod(offer)}</p>

        {hasCode ? (
          <>
            <button className={`code-button${copied ? " code-button--copied" : ""}`} onClick={copyCode} type="button">
              <span>
                <small>{copied ? "Code copié" : "Code promotionnel"}</small>
                <strong>{offer.code}</strong>
              </span>
              {copied ? <CheckIcon /> : <CopyIcon />}
            </button>
            {copyFailed && <p className="promo-card__feedback" role="alert">Copie impossible. Sélectionnez le code manuellement.</p>}
            {offer.codeSource === "contributor" && (
              <p className="promo-card__feedback">
                Partagé par les collaborateurs
                {offer.confirmationCount > 1 ? ` · ${offer.confirmationCount} confirmations` : ""}
              </p>
            )}
          </>
        ) : (
          <div className="contribution-callout">
            <div>
              <strong>Vous avez reçu le code ?</strong>
              <span>Une seule contribution suffit pour toute la durée de l’offre.</span>
            </div>
            {contributionUrl ? (
              <a href={contributionUrl} target="_blank" rel="noreferrer">
                Partager le code <ExternalIcon />
              </a>
            ) : (
              <small>Formulaire de contribution bientôt disponible.</small>
            )}
          </div>
        )}

        {offer.minimumOrderLabel && (
          <p className="promo-card__condition">
            Minimum de commande : <strong>{offer.minimumOrderLabel}</strong>
          </p>
        )}

        <details>
          <summary>Voir les conditions complètes</summary>
          <p>{offer.originalText}</p>
        </details>
      </div>
    </article>
  );
}
