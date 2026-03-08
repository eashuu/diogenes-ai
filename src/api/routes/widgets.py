"""
Widget API Routes.

Provides endpoints for rich inline widgets: stock quotes, calculator, etc.
"""

import re
import httpx
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/widgets", tags=["widgets"])


# ─── Stock Quote ──────────────────────────────────────────────

class StockQuoteResponse(BaseModel):
    symbol: str
    name: str
    price: float
    change: float
    changePercent: float
    high: float
    low: float
    open: float
    previousClose: float
    volume: str


_TICKER_RE = re.compile(r"^[A-Z]{1,5}$")


@router.get("/stock", response_model=StockQuoteResponse)
async def get_stock_quote(
    symbol: str = Query(..., description="Ticker symbol (e.g. AAPL)", max_length=5),
):
    """
    Fetch a real‑time stock quote using the Yahoo Finance v8 public endpoint.

    No API key required. Returns current price, day change, high/low, volume.
    """
    ticker = symbol.strip().upper()
    if not _TICKER_RE.match(ticker):
        raise HTTPException(status_code=400, detail="Invalid ticker symbol")

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    params = {"range": "1d", "interval": "1d", "includePrePost": "false"}

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            resp = await client.get(url, params=params, headers={
                "User-Agent": "Mozilla/5.0 (compatible; Diogenes/1.0)",
            })
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        logger.warning(f"Yahoo Finance HTTP error for {ticker}: {exc.response.status_code}")
        raise HTTPException(status_code=502, detail=f"Upstream error fetching {ticker}")
    except httpx.RequestError as exc:
        logger.warning(f"Yahoo Finance request error for {ticker}: {exc}")
        raise HTTPException(status_code=502, detail="Could not reach stock data provider")

    try:
        result = data["chart"]["result"][0]
        meta = result["meta"]

        price = meta.get("regularMarketPrice", 0)
        prev_close = meta.get("chartPreviousClose", meta.get("previousClose", price))
        change = round(price - prev_close, 2)
        change_pct = round((change / prev_close) * 100, 2) if prev_close else 0

        raw_vol = meta.get("regularMarketVolume", 0)
        vol_str = _format_volume(raw_vol)

        return StockQuoteResponse(
            symbol=ticker,
            name=meta.get("shortName", meta.get("longName", ticker)),
            price=round(price, 2),
            change=change,
            changePercent=change_pct,
            high=round(meta.get("regularMarketDayHigh", meta.get("dayHigh", price)), 2),
            low=round(meta.get("regularMarketDayLow", meta.get("dayLow", price)), 2),
            open=round(meta.get("regularMarketOpen", meta.get("open", price)), 2),
            previousClose=round(prev_close, 2),
            volume=vol_str,
        )
    except (KeyError, IndexError, TypeError) as exc:
        logger.warning(f"Failed to parse Yahoo Finance response for {ticker}: {exc}")
        raise HTTPException(status_code=404, detail=f"No data found for symbol {ticker}")


def _format_volume(vol: int | float) -> str:
    """Human readable volume string."""
    vol = int(vol)
    if vol >= 1_000_000_000:
        return f"{vol / 1_000_000_000:.1f}B"
    if vol >= 1_000_000:
        return f"{vol / 1_000_000:.1f}M"
    if vol >= 1_000:
        return f"{vol / 1_000:.1f}K"
    return str(vol)
