from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date


@dataclass(frozen=True, slots=True)
class Offer:
    """A promotion normalised for the public portal."""

    identifier: str
    original_text: str
    start_date: date | None
    end_date: date | None
    code: str | None
    discount_label: str | None
    minimum_order_label: str | None
    cities: tuple[str, ...]
    scope: str
    is_currently_valid: bool
    code_source: str | None = None
    confirmation_count: int = 0

    def applies_to_toulouse(self) -> bool:
        return self.scope == "global" or "Toulouse" in self.cities

    def with_contributor_code(self, code: str, confirmation_count: int) -> "Offer":
        if self.code:
            return self
        return replace(
            self,
            code=code,
            code_source="contributor",
            confirmation_count=max(1, confirmation_count),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.identifier,
            "originalText": self.original_text,
            "startDate": self.start_date.isoformat() if self.start_date else None,
            "endDate": self.end_date.isoformat() if self.end_date else None,
            "code": self.code or "",
            "codeSource": self.code_source,
            "confirmationCount": self.confirmation_count,
            "discountLabel": self.discount_label,
            "minimumOrderLabel": self.minimum_order_label,
            "cities": list(self.cities),
            "scope": self.scope,
            "isCurrentlyValid": self.is_currently_valid,
        }
