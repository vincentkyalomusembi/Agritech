"""
services/advisory.py
Generates farmer advisory tips via Gemini 2.5 Flash.
Falls back to deterministic season/farm-type tips if Gemini is unavailable.
"""

import logging
from datetime import datetime

from core.config import settings

log = logging.getLogger(__name__)

# ── Kenya seasonal calendar ───────────────────────────────────────────────────
# Long rains: Mar–May | Short rains: Oct–Dec | Dry: Jan–Feb, Jun–Sep

def _current_season() -> str:
    month = datetime.now().month
    if month in (3, 4, 5):
        return "long_rains"
    if month in (10, 11, 12):
        return "short_rains"
    if month in (1, 2):
        return "dry_jan_feb"
    return "dry_jun_sep"


# ── Fallback tips (no Gemini) ─────────────────────────────────────────────────

_FALLBACK_TIPS: dict[str, dict[str, str]] = {
    "crop": {
        "long_rains": (
            "Crop Tips — Long Rains\n"
            "• Prepare seedbeds early\n"
            "• Use certified seeds\n"
            "• Apply basal fertiliser at planting\n"
            "• Space rows properly for air circulation\n"
            "• Scout for armyworm and aphids"
        ),
        "short_rains": (
            "Crop Tips — Short Rains\n"
            "• Plant fast-maturing varieties\n"
            "• Top-dress with CAN fertiliser\n"
            "• Monitor for grey leaf spot\n"
            "• Harvest before rains end\n"
            "• Store grain at <13% moisture"
        ),
        "dry_jan_feb": (
            "Crop Tips — Dry Season\n"
            "• Use drought-resistant varieties\n"
            "• Practice mulching to retain moisture\n"
            "• Plan irrigation schedule\n"
            "• Test soil and prepare for next season\n"
            "• Collect and store rainwater"
        ),
        "dry_jun_sep": (
            "Crop Tips — Cold Dry Season\n"
            "• Protect crops from frost (highlands)\n"
            "• Clear previous crop residue\n"
            "• Apply lime to acidic soils\n"
            "• Plan crop rotation\n"
            "• Repair tools and storage"
        ),
    },
    "livestock": {
        "long_rains": (
            "Livestock Tips — Long Rains\n"
            "• Prevent waterborne diseases\n"
            "• Improve shelter drainage\n"
            "• Vaccinate against seasonal diseases\n"
            "• Manage pasture rotation\n"
            "• Check for parasites weekly"
        ),
        "short_rains": (
            "Livestock Tips — Short Rains\n"
            "• Deworm before rains peak\n"
            "• Stock hay and dry fodder\n"
            "• Check water troughs for contamination\n"
            "• Mark animals for breeding season\n"
            "• Monitor foot-rot in wet conditions"
        ),
        "dry_jan_feb": (
            "Livestock Tips — Dry Season\n"
            "• Ensure enough water for all animals\n"
            "• Provide quality hay and fodder\n"
            "• Supplement with mineral licks\n"
            "• Monitor heat stress in midday\n"
            "• Reduce herd numbers if pasture low"
        ),
        "dry_jun_sep": (
            "Livestock Tips — Cold Dry Season\n"
            "• Provide warm shelter at night\n"
            "• Increase feed portions slightly\n"
            "• Plan breeding for spring calving\n"
            "• Repair fences and shelters\n"
            "• Check vaccination schedule"
        ),
    },
}


def get_advisory_tips(
    farm_type: str = "crop",
    county: str | None = None,
    recommendation: str | None = None,
) -> str:
    """
    Returns advisory tips for the farmer.
    Tries Gemini first (2s timeout), falls back to seasonal tips.

    Args:
        farm_type:      'crop' | 'livestock'
        county:         County name — used in Gemini prompt if available
        recommendation: Current ML recommendation — makes tips more specific
    """
    season = _current_season()
    farm_type = (farm_type or "crop").lower()

    # ── Try Gemini ────────────────────────────────────────────────────────────
    if settings.GEMINI_API_KEY:
        try:
            import google.generativeai as genai

            genai.configure(api_key=settings.GEMINI_API_KEY)

            season_label = season.replace("_", " ").title()
            county_part = f" in {county}," if county else ""
            rec_part = f" currently growing/raising {recommendation}," if recommendation else ""

            prompt = (
                f"You are an expert Kenyan agricultural extension officer. "
                f"A {farm_type} farmer{county_part}{rec_part} needs 5 concise "
                f"practical tips for the {season_label} season in Kenya. "
                f"Format as a short bulleted list. Max 180 characters total. "
                f"Be specific to Kenya's climate and local conditions."
            )

            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(
                prompt,
                request_options={"timeout": 2},
            )
            if getattr(response, "text", None):
                return response.text.strip()
        except Exception as exc:
            log.warning("[advisory] Gemini failed: %s — using fallback tips", exc)

    # ── Fallback ──────────────────────────────────────────────────────────────
    farm_tips = _FALLBACK_TIPS.get(farm_type, _FALLBACK_TIPS["crop"])
    return farm_tips.get(season, farm_tips["dry_jan_feb"])