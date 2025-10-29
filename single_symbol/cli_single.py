"""
Simple CLI to generate a single-stock trading signal and evidence for CN A-share.

Usage examples:
  python ContestTrade/scripts/cli_single.py run
  python ContestTrade/scripts/cli_single.py run --symbol 603799 --time "2025-10-28 09:30:00"

It uses the single-symbol pipeline implemented in `single_symbol_signal.py`.
Make sure your LLM/data config is set, ideally via `config_single.yaml` by:

  $env:CONTEST_TRADE_CONFIG_FILE="C:\\Code\\ContestTrade\\config_single.yaml"
  $env:CONTEST_TRADE_MARKET="CN-Stock"
"""
from __future__ import annotations

import os
import sys
import json
from pathlib import Path
from datetime import datetime

import typer

# Ensure imports for local package
REPO_ROOT = Path(__file__).resolve().parents[1]
PKG_ROOT = REPO_ROOT / "contest_trade"
if str(PKG_ROOT) not in sys.path:
    sys.path.append(str(PKG_ROOT))

import asyncio

app = typer.Typer(name="single-signal", help="Single stock signal CLI (CN-Stock)")


def normalize_cn_symbol(code: str) -> str:
    code = code.strip().upper()
    if "." in code:
        return code
    # Heuristics for A-share exchange suffix
    # 60/68 -> SH; 000/002/003/300/301 -> SZ
    if code.startswith("60") or code.startswith("68"):
        return f"{code}.SH"
    if code.startswith(("000", "002", "003", "300", "301")) or code.startswith("00") or code.startswith("30"):
        return f"{code}.SZ"
    # Fallback: assume SH for 6xxxx, SZ otherwise
    if code.startswith("6"):
        return f"{code}.SH"
    return f"{code}.SZ"


@app.command()
def run(
    symbol: str = typer.Option(None, "--symbol", "-s", help="CN A-share code, e.g. 600519 or 600519.SH"),
    time: str = typer.Option(None, "--time", "-t", help="Trigger time YYYY-MM-DD HH:MM:SS; default=now"),
):
    """Prompt for code/time and generate a trading signal with evidence."""
    market = "CN-Stock"

    if not symbol:
        symbol = typer.prompt("请输入股票代码(如 600519 或 600519.SH)")
    symbol_norm = normalize_cn_symbol(symbol)

    if not time:
        time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Ensure env for market
    os.environ["CONTEST_TRADE_MARKET"] = market
    # Default to config_single.yaml when not explicitly set
    if not os.environ.get("CONTEST_TRADE_CONFIG_FILE"):
        default_cfg = (REPO_ROOT / "config_single.yaml").resolve()
        if default_cfg.exists():
            os.environ["CONTEST_TRADE_CONFIG_FILE"] = str(default_cfg)

    # Run pipeline
    typer.echo(f"[运行] 市场={market} 代码={symbol_norm} 时间={time}")
    # Import after env prepared to ensure correct config is loaded
    from single_symbol_signal import run_single_symbol  # type: ignore
    asyncio.run(run_single_symbol(market, symbol_norm, time))

    # Compute output paths
    results_root = PKG_ROOT / "agents_workspace" / "results"
    markdown_dir = results_root / "markdown"
    safe_symbol = symbol_norm.replace(".", "_")
    ts_safe = time.replace(":", "-").replace(" ", "_")
    json_path = results_root / f"single_{safe_symbol}_{ts_safe}.json"
    md_path = markdown_dir / f"single_{safe_symbol}_{ts_safe}.md"

    if json_path.exists():
        data = json.loads(json_path.read_text(encoding="utf-8"))
        signals = data.get("signals", [])
        if signals:
            s = signals[0]
            typer.echo("\n=== 信号结果 ===")
            typer.echo(f"标的: {s.get('symbol_code','-')} {s.get('symbol_name','-')}")
            typer.echo(f"动作: {s.get('action','-')}  概率: {s.get('probability','-')}")
            ev = s.get("evidence_list", [])
            if ev:
                typer.echo("证据(前3条):")
                for i, e in enumerate(ev[:3], 1):
                    typer.echo(f"  {i}. {e.get('description','-')} ({e.get('time','N/A')} / {e.get('from_source','N/A')})")
        else:
            typer.echo("\n未生成有效信号（已输出兜底 HOLD 建议或请稍后重试）")
    else:
        typer.echo("\n未找到结果文件，请检查日志或重试。")

    typer.echo(f"\n报告: {md_path}")


if __name__ == "__main__":
    # Accept both styles:
    #   python cli_single.py --symbol 600519
    #   python cli_single.py run --symbol 600519
    if len(sys.argv) > 1 and sys.argv[1].lower() == "run":
        sys.argv.pop(1)
    app()
