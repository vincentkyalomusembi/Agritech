"""
Get agricultural market prices from FAO with local caching and GEE adjustments.
"""

from services.fao_prices import get_fao_prices, adjust_price_by_gee_risk
from services.gee import get_gee_insights


def get_market_prices(item: str = "maize", county: str = None, gee_adjust: bool = True):
    """
    Get market prices for a commodity.
    
    Args:
        item: commodity name (maize, beans, goat, dairy, etc.)
        county: Kenya county name (for GEE risk adjustment)
        gee_adjust: whether to adjust prices based on GEE drought/stress
    
    Returns:
        dict: {min, max, unit, source, risk_adjusted, risk_level}
    """
    item = (item or "maize").strip().lower()
    
    # Get FAO prices (cached or fresh)
    fao_prices = get_fao_prices()
    prices = fao_prices.get(item, {"min": 0, "max": 0, "unit": "Ksh"})
    
    # Add source info
    prices["source"] = f"FAO ({fao_prices.get('source', 'unknown')})"
    
    # Optionally adjust by GEE risk if county provided
    if gee_adjust and county:
        try:
            gee_data = get_gee_insights(county)
            if gee_data.get("status") == "ok":
                risk_level = gee_data.get("alert_level", "low")
                adjusted = adjust_price_by_gee_risk(prices, risk_level)
                prices.update(adjusted)
        except Exception:
            # If GEE fails, just return raw FAO prices
            pass
    
    return prices
