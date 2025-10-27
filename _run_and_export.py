import os, sys, json
from pathlib import Path
from datetime import datetime
import asyncio

# Ensure imports work
ROOT = Path(__file__).parent
PKG = ROOT / 'contest_trade'
if str(PKG) not in sys.path:
    sys.path.append(str(PKG))

from contest_trade.main import SimpleTradeCompany

async def run_and_export(trigger_time: str):
    os.environ['CONTEST_TRADE_MARKET'] = 'CN-Stock'
    company = SimpleTradeCompany()
    final_state = await company.run_company(trigger_time)

    # Prepare results dir
    results_dir = PKG / 'agents_workspace' / 'results'
    results_dir.mkdir(parents=True, exist_ok=True)
    ts_safe = trigger_time.replace(':','-').replace(' ','_')

    # Optionally persist a lightweight snapshot (skip non-serializable objects)
    try:
        raw_path = results_dir / f'state_{ts_safe}.json'
        def _simplify(obj):
            if isinstance(obj, dict):
                return {k: _simplify(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [_simplify(x) for x in obj]
            # keep only JSON-serializable primitives
            if isinstance(obj, (str, int, float, type(None), bool)):
                return obj
            # best-effort string fallback
            return str(obj)
        with open(raw_path, 'w', encoding='utf-8') as f:
            json.dump(_simplify(final_state), f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    # Build Markdown summary
    step = final_state.get('step_results', {})
    data_team = step.get('data_team', {})
    research_team = step.get('research_team', {})
    best = step.get('contest', {}).get('best_signals')
    if not best:
        best = final_state.get('research_signals', []) or []

    lines = []
    lines.append(f"# ContestTrade Summary ({trigger_time})\n")
    lines.append(f"- Market: CN-Stock")
    lines.append(f"- Data factors: {data_team.get('factors_count','-')}")
    lines.append(f"- Research signals: {research_team.get('signals_count','-')}")
    total_events = len(final_state.get('all_events', []))
    lines.append(f"- Total events: {total_events}\n")

    if best:
        lines.append("## Signals\n")
        lines.append("| # | Symbol | Name | Action | Prob | Notes |")
        lines.append("|---|--------|------|--------|------|-------|")
        for i, s in enumerate(best, 1):
            sym = s.get('symbol_code', '-')
            name = s.get('symbol_name', '-')
            act = s.get('action', '-')
            prob = s.get('probability', '-')
            ev = s.get('evidence_list')
            if isinstance(ev, list):
                note = (ev[0] if ev else '-')
            else:
                note = '-'
            # escape pipes
            note = str(note).replace('|','/')
            name = str(name).replace('|','/')
            lines.append(f"| {i} | {sym} | {name} | {act} | {prob} | {note} |")
    else:
        lines.append("_No signals produced._\n")

    md_path = results_dir / f'summary_{ts_safe}.md'
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(str(md_path))

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--time', required=True)
    args = ap.parse_args()
    asyncio.run(run_and_export(args.time))
