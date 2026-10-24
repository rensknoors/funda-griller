"""Buyer Profile (Koperprofiel): the household's finances and preferences, stored locally and versioned."""

import re
from datetime import date
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field, StringConstraints, ValidationInfo, field_validator

MAX_AMOUNT = 100_000_000
MAX_INCOME = 5_000_000
EARLIEST_BIRTH_YEAR = 1900

Amount = Annotated[int, Field(ge=0, le=MAX_AMOUNT)]
Income = Annotated[int, Field(ge=0, le=MAX_INCOME)]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

# Best-effort: a Dutch postcode ("3511 AB", "3511ab") or a street name followed by a house number.
_ADDRESS = re.compile(
    r"\b[1-9]\d{3}\s?[A-Z]{2}\b|\b[1-9]\d{3}[a-z]{2}\b"
    r"|\b\w*(straat|laan|weg|plein|gracht|kade|singel|dijk|steeg|hof|pad)\s+\d+"
)


def _no_address(text: str) -> str:
    if _ADDRESS.search(text):
        raise ValueError("Geen adres of postcode: deze tekst gaat mee naar het taalmodel")
    return text


# Free text that reaches the LLM verbatim through the reduced profile (see `reduce_profile`).
PreferenceText = Annotated[Text, AfterValidator(_no_address)]


class HouseholdMember(BaseModel):
    role: Literal["adult", "child"]
    birth_date: date

    @field_validator("birth_date")
    @classmethod
    def plausible_birth_date(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Geboortedatum ligt in de toekomst")
        if value.year < EARLIEST_BIRTH_YEAR:
            raise ValueError("Geboortedatum is niet geloofwaardig")
        return value


class Assets(BaseModel):
    savings: Amount
    investments: Amount


class CurrentHome(BaseModel):
    value: Amount
    outstanding_mortgage: Amount
    selling_costs: Amount
    address: str | None = None

    @field_validator("outstanding_mortgage")
    @classmethod
    def mortgage_within_value(cls, mortgage: int, info: ValidationInfo) -> int:
        value = info.data.get("value")
        if value is not None and mortgage > value:
            raise ValueError("Hypotheek is hoger dan de woningwaarde")
        return mortgage


class CommuteDestination(BaseModel):
    label: PreferenceText
    address: Text
    max_minutes: Annotated[int, Field(ge=1, le=300)] | None = None


class BuyerProfile(BaseModel):
    household: list[HouseholdMember]
    gross_annual_income: Income
    assets: Assets
    current_home: CurrentHome | None = None
    must_haves: list[PreferenceText] = []
    nice_to_haves: list[PreferenceText] = []
    deal_breakers: list[PreferenceText] = []
    commute_destinations: list[CommuteDestination] = []
    renovation_tolerance: int

    @field_validator("household")
    @classmethod
    def has_an_adult(cls, household: list[HouseholdMember]) -> list[HouseholdMember]:
        if not any(member.role == "adult" for member in household):
            raise ValueError("Voeg minstens één volwassene toe")
        return household

    @field_validator("renovation_tolerance")
    @classmethod
    def tolerance_in_range(cls, value: int) -> int:
        if not 1 <= value <= 5:
            raise ValueError("Kies een waarde van 1 tot en met 5")
        return value


class DraftAssets(BaseModel):
    savings: Amount = 0
    investments: Amount = 0


class FinanceDraft(BaseModel):
    """The finance vakken of a Buyer Profile being edited: enough for the Gevolgen panel.

    Blank balances count as zero and members without a birth date are left out by the form,
    so the figures appear as soon as income is filled in.
    """

    household: list[HouseholdMember] = []
    gross_annual_income: Income
    assets: DraftAssets = DraftAssets()
    current_home: CurrentHome | None = None


def home_equity(profile: BuyerProfile | FinanceDraft) -> int:
    home = profile.current_home
    return home.value - home.outstanding_mortgage - home.selling_costs if home else 0


def reduce_profile(version: int, profile: BuyerProfile) -> dict:
    """The only form of the Buyer Profile allowed to reach the LLM: derived figures and preferences.

    Exception: Must-have, Nice-to-have and Deal-breaker texts and commute labels pass verbatim,
    because the LLM must read the preference as the user wrote it. They are typed free text, so
    `PreferenceText` rejects postcodes and street-plus-number addresses at the boundary and the
    form warns that this text is shared. Commute addresses, income, balances and the home address
    never pass.
    """
    return {
        "profile_version": version,
        "household": {
            "adults": sum(member.role == "adult" for member in profile.household),
            "children": sum(member.role == "child" for member in profile.household),
        },
        "home_equity": home_equity(profile),
        "renovation_tolerance": profile.renovation_tolerance,
        "must_haves": profile.must_haves,
        "nice_to_haves": profile.nice_to_haves,
        "deal_breakers": profile.deal_breakers,
        "commute_destinations": [
            {"label": destination.label, "max_minutes": destination.max_minutes}
            for destination in profile.commute_destinations
        ],
    }


_MESSAGES = {
    "missing": "Verplicht veld",
    "string_too_short": "Verplicht veld",
    "greater_than_equal": "Bedrag buiten bereik",
    "less_than_equal": "Bedrag buiten bereik",
}


def describe_errors(errors: list[dict]) -> list[dict[str, str]]:
    """Field-keyed Dutch messages for the form: `{"field": "assets.savings", "message": ...}`."""
    described = []
    for error in errors:
        field = ".".join(str(part) for part in error["loc"] if part != "body")
        if error["type"] == "value_error":
            message = str(error["ctx"]["error"])
        elif error["type"].startswith("date"):
            message = "Ongeldige datum"
        else:
            message = _MESSAGES.get(error["type"], "Ongeldige waarde")
        described.append({"field": field, "message": message})
    return described
