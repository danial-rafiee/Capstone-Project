# Stores energy summary and scores

from decimal import Decimal


class EnergySummary:

    def __init__(self, totals=0, savings=0, reference=None, score=None,
                 penalties: str = ""):
        self.configure(totals, savings, reference, score, penalties)

    def configure(self, totals=0, savings=0, reference=None, score=None,
                  penalties: str = "") -> None:

        totals = self._number(totals, "Total energy", minimum=Decimal("0"))
        savings = self._number(savings, "Savings")
        reference = None if reference is None else self._number(
            reference, "Reference energy", minimum=Decimal("0"))
        score = None if score is None else self._number(
            score, "Score", minimum=Decimal("0"), maximum=Decimal("100"))
        if not isinstance(penalties, str):
            raise TypeError("Penalties must be text.")
        self._totals, self._savings, self._reference = totals, savings, reference
        self._score, self._penalties = score, penalties.strip()

    @staticmethod
    def _number(value, label: str, minimum: Decimal | None = None,
                maximum: Decimal | None = None) -> Decimal:
        if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
            raise TypeError(f"{label} must be a number.")
        value = Decimal(str(value))
        if not value.is_finite():
            raise ValueError(f"{label} must be finite.")
        if minimum is not None and value < minimum:
            raise ValueError(f"{label} must be at least {minimum}.")
        if maximum is not None and value > maximum:
            raise ValueError(f"{label} must be at most {maximum}.")
        return value

    def get_totals(self) -> Decimal:
        return self._totals

    def set_totals(self, value) -> None:
        self.configure(value, self._savings, self._reference, self._score, self._penalties)

    def get_savings(self) -> Decimal:
        return self._savings

    def set_savings(self, value) -> None:
        self.configure(self._totals, value, self._reference, self._score, self._penalties)

    def get_reference(self) -> Decimal | None:
        return self._reference

    def set_reference(self, value) -> None:
        self.configure(self._totals, self._savings, value, self._score, self._penalties)

    def get_score(self) -> Decimal | None:
        return self._score

    def set_score(self, value) -> None:
        self.configure(self._totals, self._savings, self._reference, value, self._penalties)

    def get_penalties(self) -> str:
        return self._penalties

    def set_penalties(self, value: str) -> None:
        self.configure(self._totals, self._savings, self._reference, self._score, value)

    totals = property(get_totals, set_totals)
    savings = property(get_savings, set_savings)
    reference = property(get_reference, set_reference)
    score = property(get_score, set_score)
    penalties = property(get_penalties, set_penalties)

    def to_dict(self) -> dict:

        return {"totals": self._totals, "savings": self._savings,
                "reference": self._reference, "score": self._score,
                "penalties": self._penalties}

    def __str__(self) -> str:
        return f"EnergySummary(totals={self._totals}, savings={self._savings}, score={self._score})"