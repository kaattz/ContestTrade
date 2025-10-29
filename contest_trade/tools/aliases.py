"""
Tool aliases to bridge generic tool names used by agents to concrete
Akshare-based implementations present in this repository.

This helps when prompts call tools like `stock_quote` or `corp_info`, while
the project provides `price_info_akshare.price_info` and
`corp_info_akshare.company_financial_info`.
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional, List

from tools.tool_utils import smart_tool

# Import concrete Akshare-backed tools
from .price_info_akshare import price_info as _ak_price_info
from .corp_info_akshare import company_financial_info as _ak_corp_info
from .stock_symbol_search_akshare import stock_symbol_search as _ak_symbol_search
from .stock_selector_akshare import stock_selector as _ak_stock_selector
from .stock_summary_akshare import stock_summary as _ak_stock_summary


class StockQuoteInput(BaseModel):
    market: str = Field(default="CN-Stock", description="Market name, e.g. CN-Stock")
    symbol: str = Field(description="Stock symbol, e.g. 600519.SH")
    trigger_time: Optional[str] = Field(default=None, description="YYYY-MM-DD HH:MM:SS")


@smart_tool(
    description="Get latest price/quote information for a stock symbol.",
    args_schema=StockQuoteInput,
    max_output_len=4000,
    timeout_seconds=30.0,
)
async def stock_quote(market: str, symbol: str, trigger_time: Optional[str] = None) -> str:
    return await _ak_price_info(market=market, symbol=symbol, trigger_time=trigger_time)


class CorpInfoInput(BaseModel):
    market: str = Field(default="CN-Stock", description="Market name, e.g. CN-Stock")
    symbol: Optional[str] = Field(default=None, description="Stock symbol, e.g. 600519.SH")
    stock_code: Optional[str] = Field(default=None, description="Alias for symbol")
    task: str = Field(default="overview", description="Info type, e.g. recent_announcements/overview/financials")
    trigger_time: Optional[str] = Field(default=None, description="YYYY-MM-DD HH:MM:SS")


@smart_tool(
    description="Get company information/financial data for a stock.",
    args_schema=CorpInfoInput,
    max_output_len=6000,
    timeout_seconds=45.0,
)
async def corp_info(
    market: str,
    symbol: Optional[str] = None,
    stock_code: Optional[str] = None,
    task: str = "overview",
    trigger_time: Optional[str] = None,
) -> str:
    sym = symbol or stock_code
    if not sym:
        raise ValueError("symbol or stock_code is required")
    return await _ak_corp_info(market=market, symbol=sym, task=task, trigger_time=trigger_time)


class SymbolSearchInput(BaseModel):
    market: str = Field(default="CN-Stock", description="Market name")
    query: str = Field(description="Company name or partial symbol")
    limit: int = Field(default=5, description="Max results")
    match_mode: str = Field(default="best", description="best|all|exact")
    trigger_time: Optional[str] = Field(default=None, description="YYYY-MM-DD HH:MM:SS")


@smart_tool(
    description="Search stock symbols by a single query (Akshare-backed).",
    args_schema=SymbolSearchInput,
    max_output_len=4000,
    timeout_seconds=30.0,
)
async def stock_symbol_search(
    market: str,
    query: str,
    limit: int = 5,
    match_mode: str = "best",
    trigger_time: Optional[str] = None,
) -> str:
    return await _ak_symbol_search(
        market=market,
        queries=[query],
        trigger_time=trigger_time or "",
        limit_per_query=limit,
        match_mode=match_mode,
    )


class StockSelectorInput(BaseModel):
    market: str = Field(default="CN-Stock")
    query: str = Field(description="Selection query or rule text")
    trigger_time: Optional[str] = Field(default=None)
    limit: int = Field(default=10)


@smart_tool(
    description="Run stock selector (Akshare-backed).",
    args_schema=StockSelectorInput,
    max_output_len=6000,
    timeout_seconds=45.0,
)
async def stock_selector(
    market: str,
    query: str,
    trigger_time: Optional[str] = None,
    limit: int = 10,
) -> str:
    return await _ak_stock_selector(market=market, query=query, trigger_time=trigger_time or "", limit=limit)


class StockSummaryInput(BaseModel):
    market: str = Field(default="CN-Stock")
    symbol: str = Field(description="Stock symbol, e.g. 600519.SH")
    trigger_time: str = Field(description="YYYY-MM-DD HH:MM:SS")


@smart_tool(
    description="Generate a comprehensive stock summary (Akshare-backed).",
    args_schema=StockSummaryInput,
    max_output_len=8000,
    timeout_seconds=60.0,
)
async def stock_summary(market: str, symbol: str, trigger_time: str) -> str:
    return await _ak_stock_summary(market=market, symbol=symbol, trigger_time=trigger_time)

