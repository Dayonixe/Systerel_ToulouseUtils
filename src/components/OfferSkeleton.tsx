export function OfferSkeleton() {
  return (
    <div className="offers-grid" aria-label="Chargement des offres" aria-busy="true">
      {[0, 1, 2].map((item) => (
        <div className="promo-card promo-card--skeleton" key={item}>
          <span className="skeleton skeleton--short" />
          <span className="skeleton skeleton--title" />
          <span className="skeleton skeleton--line" />
          <span className="skeleton skeleton--button" />
        </div>
      ))}
    </div>
  );
}
