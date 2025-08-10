import questionary
from typing import List, Optional, Tuple, Dict
from datetime import datetime
import re
from rich.console import Console

from .models import AgentType, AgentStatus

console = Console()

# 数据代理配置
DATA_AGENTS = [
    ("THX新闻摘要代理", "thx_summary_agent"),
    ("新浪新闻摘要代理", "sina_summary_agent"),
    ("价格市场代理", "price_market_agent"),
    ("热钱流向代理", "hot_money_agent"),
]

# 研究代理信念
RESEARCH_BELIEFS = [
    ("深度价值猎手", "Deep value hunter. Searches for neglected stocks trading below net current assets. Focuses on balance sheet strength and negative EV opportunities. Relies on SEC filings and value investing forums."),
    ("股息侦探", "Dividend detective. Identifies sustainable high-yield stocks through payout ratio analysis. Tracks dividend history and management commentary. Avoids companies with deteriorating cash flows."),
    ("转型专家", "Turnaround specialist. Seeks distressed companies with new management teams. Analyzes restructuring plans via press releases and earnings call transcripts. Focuses on debt reduction progress."),
]


def get_trigger_time() -> str:
    """提示用户输入触发时间"""
    def validate_datetime(datetime_str: str) -> bool:
        try:
            datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
            return True
        except ValueError:
            return False

    # 提供预设选项
    now = datetime.now()
    options = [
        f"现在 ({now.strftime('%Y-%m-%d %H:%M:%S')})",
        f"今天开盘 ({now.strftime('%Y-%m-%d')} 09:30:00)",
        f"昨天收盘 ({now.strftime('%Y-%m-%d')} 15:00:00)",
        "自定义时间",
    ]
    
    choice = questionary.select(
        "选择触发时间:",
        choices=options,
        style=questionary.Style([
            ("text", "fg:green"),
            ("highlighted", "noinherit"),
        ])
    ).ask()
    
    if choice == options[0]:  # 现在
        return now.strftime('%Y-%m-%d %H:%M:%S')
    elif choice == options[1]:  # 今天开盘
        return f"{now.strftime('%Y-%m-%d')} 09:30:00"
    elif choice == options[2]:  # 昨天收盘
        return f"{now.strftime('%Y-%m-%d')} 15:00:00"
    else:  # 自定义时间
        trigger_time = questionary.text(
            "请输入自定义触发时间 (YYYY-MM-DD HH:MM:SS):",
            default=now.strftime('%Y-%m-%d %H:%M:%S'),
            validate=lambda x: validate_datetime(x.strip()) or "请输入有效的时间格式 YYYY-MM-DD HH:MM:SS",
            style=questionary.Style([
                ("text", "fg:green"),
                ("highlighted", "noinherit"),
            ])
        ).ask()

        if not trigger_time:
            console.print("\n[red]未提供触发时间，退出...[/red]")
            exit(1)

        return trigger_time.strip()


def select_data_agents() -> List[str]:
    """选择数据代理"""
    choices = questionary.checkbox(
        "选择数据代理团队:",
        choices=[
            questionary.Choice(display, value=value) for display, value in DATA_AGENTS
        ],
        default=[value for _, value in DATA_AGENTS],  # 默认全选
        instruction="\n- 按空格键选择/取消选择代理\n- 按 'a' 全选/取消全选\n- 按回车确认",
        validate=lambda x: len(x) > 0 or "至少选择一个数据代理",
        style=questionary.Style([
            ("checkbox-selected", "fg:green"),
            ("selected", "fg:green noinherit"),
            ("highlighted", "noinherit"),
            ("pointer", "noinherit"),
        ])
    ).ask()

    if not choices:
        console.print("\n[red]未选择数据代理，退出...[/red]")
        exit(1)

    return choices


def select_research_agents() -> List[str]:
    """选择研究代理"""
    choices = questionary.checkbox(
        "选择研究代理团队:",
        choices=[
            questionary.Choice(display, value=belief) for display, belief in RESEARCH_BELIEFS
        ],
        default=[belief for _, belief in RESEARCH_BELIEFS],  # 默认全选
        instruction="\n- 按空格键选择/取消选择代理\n- 按 'a' 全选/取消全选\n- 按回车确认",
        validate=lambda x: len(x) > 0 or "至少选择一个研究代理",
        style=questionary.Style([
            ("checkbox-selected", "fg:blue"),
            ("selected", "fg:blue noinherit"),
            ("highlighted", "noinherit"),
            ("pointer", "noinherit"),
        ])
    ).ask()

    if not choices:
        console.print("\n[red]未选择研究代理，退出...[/red]")
        exit(1)

    return choices


def select_contest_mode() -> str:
    """选择竞赛模式"""
    mode = questionary.select(
        "选择竞赛模式:",
        choices=[
            ("标准模式 - 选择前3个最佳信号", "standard"),
            ("激进模式 - 选择前1个最佳信号", "aggressive"),
            ("保守模式 - 选择前5个最佳信号", "conservative"),
        ],
        default="standard",
        style=questionary.Style([
            ("text", "fg:yellow"),
            ("highlighted", "noinherit"),
        ])
    ).ask()

    return mode





def validate_config() -> bool:
    """验证配置"""
    try:
        import sys
        import os
        # 添加项目根目录到Python路径
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        from contest_trade.config.config import cfg
        return True
    except ImportError as e:
        console.print(f"[red]配置加载失败: {e}[/red]")
        return False
    except Exception as e:
        console.print(f"[red]配置验证失败: {e}[/red]")
        return False


def format_agent_name(agent_type: str, agent_id: int, agent_name: str) -> str:
    """格式化代理名称"""
    if agent_type == "data":
        return f"📊 Data Agent {agent_id} ({agent_name})"
    elif agent_type == "research":
        return f"🔍 Research Agent {agent_id} ({agent_name})"
    else:
        return f"🤖 Agent {agent_id} ({agent_name})"


def format_event_type(event_type: str) -> str:
    """格式化事件类型"""
    event_icons = {
        "on_chain_start": "🔄",
        "on_chain_end": "✅",
        "on_custom": "🎯",
        "on_chain_error": "❌",
    }
    return f"{event_icons.get(event_type, '📝')} {event_type}"


def extract_signal_info(signal: Dict) -> Dict:
    """提取信号信息"""
    return {
        "symbol_name": signal.get("symbol_name", "N/A"),
        "symbol_code": signal.get("symbol_code", "N/A"),
        "action": signal.get("action", "N/A"),
        "probability": signal.get("probability", "N/A"),
        "has_opportunity": signal.get("has_opportunity", "N/A"),
    } 