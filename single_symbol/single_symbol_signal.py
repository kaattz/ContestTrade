"""
Run a single-symbol research to get investment action and supporting evidence.

Usage:
  python scripts/single_symbol_signal.py --market CN-Stock --symbol 600519.SH --time "2025-10-27 21:00:00"

Notes:
  - Ensure config.yaml/config_us.yaml and API keys are set.
  - Results will be printed to console and saved under agents_workspace/results.
"""
from __future__ import annotations

import os
import re
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
import asyncio


REPO_ROOT = Path(__file__).resolve().parents[1]
PKG_ROOT = REPO_ROOT / "contest_trade"
if str(PKG_ROOT) not in sys.path:
    sys.path.append(str(PKG_ROOT))

from agents.research_agent import ResearchAgent, ResearchAgentConfig, ResearchAgentInput  # type: ignore
from config.config import PROJECT_ROOT  # type: ignore


def parse_signals_from_output(thinking_result: str, output_result: str):
    """Parse <signal> blocks from agent outputs.

    The ResearchAgent outputs usually contain a "<Output>..." section with one
    or multiple <signal>...</signal> blocks.
    """
    thinking = thinking_result.split("<Output>")[0].strip("\n").strip()
    output = output_result.split("<Output>")[-1].strip("\n").strip()

    signals = []
    try:
        blocks = re.findall(r"<signal>(.*?)</signal>", output, flags=re.DOTALL)
        for blk in blocks:
            def _get(tag: str, default: str = ""):
                m = re.search(fr"<{tag}>(.*?)</{tag}>", blk, flags=re.DOTALL)
                return m.group(1).strip() if m else default

            has_opportunity = _get("has_opportunity", "")
            action = _get("action", "")
            symbol_code = _get("symbol_code", "")
            symbol_name = _get("symbol_name", "")

            ev_list_raw = _get("evidence_list", "")
            ev_items = re.findall(r"<evidence>(.*?)</evidence>", ev_list_raw, flags=re.DOTALL)
            evidence_list = []
            for item in ev_items:
                desc_m = re.search(r"<description>(.*?)</description>", item, flags=re.DOTALL)
                description = (desc_m.group(1).strip() if desc_m else item.strip())
                time_m = re.search(r"<time>(.*?)</time>", item, flags=re.DOTALL)
                from_m = re.search(r"<from_source>(.*?)</from_source>", item, flags=re.DOTALL)
                evidence_list.append({
                    "description": description,
                    "time": time_m.group(1).strip() if time_m else "N/A",
                    "from_source": from_m.group(1).strip() if from_m else "N/A",
                })

            prob = _get("probability", "")

            signals.append({
                "thinking": thinking,
                "has_opportunity": has_opportunity,
                "action": action,
                "symbol_code": symbol_code,
                "symbol_name": symbol_name,
                "evidence_list": evidence_list,
                "probability": prob,
            })
    except Exception:
        pass
    return signals


async def run_single_symbol(market: str, symbol: str, trigger_time: str):
    os.environ["CONTEST_TRADE_MARKET"] = market

    # Configure a lightweight ResearchAgent that focuses on the given symbol
    belief = (
        f"仅针对股票 {symbol} 在指定时间点进行研究与信号判定；"
        f"若无清晰机会请输出 HOLD；输出结构化 <signal> 格式。"
    )
    cfg = ResearchAgentConfig(agent_name="agent_single", belief=belief)
    agent = ResearchAgent(cfg)

    inp = ResearchAgentInput(
        background_information=(
            f"目标标的: {symbol}\n触发时间: {trigger_time}\n"
            f"请基于可用工具（选股/行情/财务/搜索/摘要）严格输出 <signal> 结构。"
        ),
        trigger_time=trigger_time,
    )

    final_output = None
    async for event in agent.run_with_monitoring_events(inp):
        if event.get("event") == "on_chain_end" and event.get("name") == "submit_result":
            final_output = event.get("data", {}).get("output", {})

    if not final_output:
        raise RuntimeError("No output returned from ResearchAgent")

    thinking = getattr(final_output, "final_result_thinking", "") or final_output.get("final_result_thinking", "")
    output = getattr(final_output, "final_result", "") or final_output.get("final_result", "")
    signals = parse_signals_from_output(thinking, output)

    # Keep only signals for the requested symbol (case-insensitive)
    in_sym_norm = symbol.strip().upper()
    filtered = []
    for s in signals:
        sym = (s.get('symbol_code') or '').strip().upper()
        if sym == in_sym_norm:
            filtered.append(s)
    signals = filtered or signals

    # Fallback: if still no signal, output a HOLD recommendation for the symbol
    if not signals:
        signals = [{
            "thinking": "",
            "has_opportunity": "no",
            "action": "HOLD",
            "symbol_code": symbol,
            "symbol_name": "-",
            "evidence_list": [{
                "description": "未检索到针对该标的的有效研究信号，建议观望。",
                "time": trigger_time,
                "from_source": "agent"
            }],
            "probability": "N/A",
        }]

    # Persist results (markdown/pdf split directories)
    results_root = PROJECT_ROOT / "agents_workspace" / "results"
    markdown_dir = results_root / "markdown"
    pdf_dir = results_root / "pdf"
    json_dir = results_root / "json"
    markdown_dir.mkdir(parents=True, exist_ok=True)
    pdf_dir.mkdir(parents=True, exist_ok=True)
    json_dir.mkdir(parents=True, exist_ok=True)
    safe_symbol = symbol.replace(".", "_")
    ts_safe = trigger_time.replace(":", "-").replace(" ", "_")
    out_json = json_dir / f"single_{safe_symbol}_{ts_safe}.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump({"symbol": symbol, "trigger_time": trigger_time, "signals": signals}, f, ensure_ascii=False, indent=2)

    # Simple markdown
    md_lines = [f"# Single Symbol Signal ({market})", ""]
    if signals:
        s = signals[0]
        md_lines += [
            f"- Symbol: {s.get('symbol_code','-')} ({s.get('symbol_name','-')})",
            f"- Action: {s.get('action','-')}",
            f"- Probability: {s.get('probability','-')}",
            "",
            "## Evidence",
        ]
        for i, ev in enumerate(s.get("evidence_list", []), 1):
            md_lines.append(f"{i}. {ev.get('description','-')} ({ev.get('time','N/A')} / {ev.get('from_source','N/A')})")
    else:
        md_lines.append("_No signal produced._")

    out_md = markdown_dir / f"single_{safe_symbol}_{ts_safe}.md"
    with open(out_md, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    # Export PDF alongside Markdown (best-effort)
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import mm
        import textwrap
        pdf_path = pdf_dir / f"single_{safe_symbol}_{ts_safe}.pdf"
        c = canvas.Canvas(str(pdf_path), pagesize=A4)
        width, height = A4
        x_margin, y_start = 20 * mm, height - 20 * mm
        textobject = c.beginText()
        textobject.setTextOrigin(x_margin, y_start)
        textobject.setFont("Helvetica", 10)
        for line in md_lines:
            for wrapped in textwrap.wrap(line, width=100):
                textobject.textLine(wrapped)
        c.drawText(textobject)
        c.showPage()
        c.save()
    except Exception:
        pass

    # Console print
    print(json.dumps({"symbol": symbol, "trigger_time": trigger_time, "signals": signals}, ensure_ascii=False, indent=2))
    print(str(out_md))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--market", choices=["CN-Stock", "US-Stock"], required=True)
    ap.add_argument("--symbol", required=True, help="e.g., 600519.SH or NVDA")
    ap.add_argument("--time", required=True, help="YYYY-MM-DD HH:MM:SS")
    args = ap.parse_args()

    asyncio.run(run_single_symbol(args.market, args.symbol, args.time))


if __name__ == "__main__":
    main()
