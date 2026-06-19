"""Canonical test fixtures from docs/edgecases.md."""

from __future__ import annotations

FIX_JP = (
    "Plan a 5-day trip to Japan. Tokyo + Kyoto. $3,000 budget. "
    "Love food and temples, hate crowds."
)
FIX_IN = (
    "Plan a 4-day trip to Rajasthan. Jaipur + Udaipur. ₹60,000 budget. "
    "Love forts and street food, hate crowds."
)
FIX_NB = "Weekend in Barcelona. Love architecture."
FIX_LOW = "3 days Tokyo only. $400 total. Food focused."
FIX_MANY = "10 days: Tokyo, Kyoto, Osaka, Hiroshima, Nara. $2,000."
FIX_EMPTY = ""
FIX_SINGLE = "5 days in Kyoto. $1,500. Temples."

FIXTURES = {
    "FIX-JP": FIX_JP,
    "FIX-IN": FIX_IN,
    "FIX-NB": FIX_NB,
    "FIX-LOW": FIX_LOW,
    "FIX-MANY": FIX_MANY,
    "FIX-EMPTY": FIX_EMPTY,
    "FIX-SINGLE": FIX_SINGLE,
}
