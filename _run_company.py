import asyncio, os, sys
from pathlib import Path
# Ensure package modules can import `config` etc.
PROJECT_ROOT = Path(__file__).parent / 'contest_trade'
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))
from contest_trade.main import SimpleTradeCompany
from datetime import datetime

async def main():
    company = SimpleTradeCompany()
    trigger_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    final_state = await company.run_company(trigger_time)
    print('\n=== SUMMARY ===')
    print('trigger_time:', final_state.get('trigger_time'))
    step_results = final_state.get('step_results', {})
    print('data_team:', step_results.get('data_team'))
    print('research_team:', step_results.get('research_team'))

asyncio.run(main())
