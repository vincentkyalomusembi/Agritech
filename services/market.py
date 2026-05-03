def get_market_prices(item: str = "maize"):
    item = (item or "maize").strip().lower()
    mock_prices = {
        "maize": {"min": 2800, "max": 3400, "unit": "Ksh/bag"},
        "beans": {"min": 6500, "max": 7800, "unit": "Ksh/bag"},
        "goat": {"min": 4500, "max": 8000, "unit": "Ksh/head"},
    }
    return mock_prices.get(item, {"min": 0, "max": 0, "unit": "Ksh"})