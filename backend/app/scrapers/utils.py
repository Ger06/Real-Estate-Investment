"""
Shared utilities for scrapers.
"""
import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def clean_price(price_text: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Parse price text and extract amount and currency.

    Handles Argentine real estate price formats:
    - "USD 239.000"       -> (239000.0, "USD")
    - "USD 239.000,50"    -> (239000.50, "USD")
    - "$ 1.500.000"       -> (1500000.0, "ARS")
    - "U$S 150000"        -> (150000.0, "USD")
    - "US$ 119.000"       -> (119000.0, "USD")
    - "ARS 25.000"        -> (25000.0, "ARS")
    - "1,000,000"         -> (1000000.0, None)
    - "1.000,50"          -> (1000.50, None)

    Args:
        price_text: Price string from page

    Returns:
        Tuple of (price_amount, currency) or (None, None) if parsing fails
    """
    if not price_text:
        return None, None

    text = price_text.strip().upper()

    # Detect currency
    currency = None
    if "USD" in text or "U$S" in text or "US$" in text:
        currency = "USD"
    elif "ARS" in text or "AR$" in text:
        currency = "ARS"
    elif "$" in text:
        # Bare "$" -> ARS in Argentina context
        currency = "ARS"

    # Extract numeric portions (digits, dots, commas)
    numbers = re.findall(r'[\d.,]+', text)
    if not numbers:
        return None, currency

    # Take the first number and clean it
    price_str = numbers[0]

    # Handle different number formats:
    if price_str.count('.') > 1:
        # Format: 1.000.000 (periods as thousands separator)
        price_str = price_str.replace('.', '')
    elif price_str.count(',') > 1:
        # Format: 1,000,000 (commas as thousands separator)
        price_str = price_str.replace(',', '')
    elif ',' in price_str and '.' in price_str:
        # Format: 1,000.00 or 1.000,00
        if price_str.index(',') < price_str.index('.'):
            # 1,000.00 format (comma = thousands, dot = decimal)
            price_str = price_str.replace(',', '')
        else:
            # 1.000,00 format (dot = thousands, comma = decimal)
            price_str = price_str.replace('.', '').replace(',', '.')
    elif ',' in price_str:
        # Could be 1,000 (thousands) or 1,50 (decimal)
        # In Argentine real estate context, prices > 100 are always thousands
        parts = price_str.split(',')
        if len(parts[-1]) == 2 and len(parts) == 2:
            # Likely decimal: "150000,50" or "1500,00"
            price_str = price_str.replace(',', '.')
        else:
            # Likely thousands separator: "1,000" or "150,000"
            price_str = price_str.replace(',', '')
    elif '.' in price_str:
        # Could be 1.000 (thousands) or 1.50 (decimal)
        parts = price_str.split('.')
        if len(parts[-1]) == 2 and len(parts) == 2:
            # Could be decimal (1.50) — but in real estate, 239.00 is unlikely
            # If the integer part is small, keep as decimal; otherwise treat as thousands
            int_part = int(parts[0]) if parts[0] else 0
            if int_part < 100:
                # Decimal: 1.50, 99.00
                pass
            else:
                # Thousands: 239.00 -> 23900? No — "239.00" is ambiguous but rare.
                # In practice, real estate uses "239.000" (3 decimal digits = thousands)
                pass
        elif len(parts[-1]) == 3:
            # Thousands: 1.000, 239.000
            price_str = price_str.replace('.', '')
        # else: keep as-is (could be decimal)

    try:
        return float(price_str), currency
    except ValueError:
        return None, currency
