import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent / 'contest_trade'
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))
from config.config import cfg
print('Market Type:', getattr(cfg, 'market_type', None))
print('Has tushare_key:', hasattr(cfg, 'tushare_key'))
print('Has data_agents_config:', hasattr(cfg, 'data_agents_config'))
print('Has research_agent_config:', hasattr(cfg, 'research_agent_config'))
print('Has market_config_file:', hasattr(cfg, 'market_config_file'))
print('Keys example:', [k for k in dir(cfg) if not k.startswith('_')][:30])
