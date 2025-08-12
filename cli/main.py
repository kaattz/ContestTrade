"""
ContestTrade: 基于内部竞赛机制的Multi-Agent交易系统
"""
import asyncio
import sys
import re
import json
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime
from collections import deque

import typer
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich.align import Align
from rich import box

from .utils import get_trigger_time, validate_config
from .static.report_template import display_final_report_interactive
from contest_trade.config.config import cfg, PROJECT_ROOT
sys.path.append(str(PROJECT_ROOT))
from contest_trade.main import SimpleTradeCompany

console = Console()

app = typer.Typer(
    name="contesttrade",
    help="ContestTrade: 基于内部竞赛机制的Multi-Agent交易系统",
    add_completion=True,
)


def _get_agent_config():
    """从配置文件动态获取代理配置"""
    agent_status = {}
    
    # 从配置文件获取数据代理
    data_agents_config = cfg.data_agents_config
    for agent_config in data_agents_config:
        agent_name = agent_config.get('agent_name', '')
        if agent_name:
            agent_status[agent_name] = "pending"
    
    # 从belief_list.json获取研究代理数量
    belief_list_path = PROJECT_ROOT / "config" / "belief_list.json"

    with open(belief_list_path, 'r', encoding='utf-8') as f:
        belief_list = json.load(f)
    # 根据belief数量创建研究代理
    for i in range(len(belief_list)):
        agent_status[f"agent_{i}"] = "pending"
    
    return agent_status
class ContestTradeDisplay:
    """ContestTrade显示管理器"""
    
    def __init__(self):
        self.messages = deque(maxlen=100)
        self.agent_status = _get_agent_config()
        self.current_task = "初始化系统..."
        self.progress_info = ""
        self.final_state = None
        self.analysis_completed = False
        self.step_counts = {"data": 0, "research": 0, "contest": 0, "finalize": 0}
        
    def add_message(self, message_type: str, content: str):
        """添加消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.messages.append(f"[{timestamp}] {message_type}: {content}")
        
    def update_agent_status(self, agent_name: str, status: str):
        """更新Agent状态"""
        if agent_name not in self.agent_status:
            self.agent_status[agent_name] = "pending"
            
        self.agent_status[agent_name] = status
        
    def set_current_task(self, task: str):
        """设置当前任务"""
        self.current_task = task
        
    def set_progress_info(self, info: str):
        """设置进度信息"""
        self.progress_info = info
        
    def set_analysis_completed(self, completed: bool = True):
        """设置分析完成状态"""
        self.analysis_completed = completed
        
    def create_layout(self, trigger_time: str) -> Layout:
        """创建自适应布局"""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=8),
            Layout(name="main_content")
        )
        layout["main_content"].split_row(
            Layout(name="left_panel", ratio=3),
            Layout(name="right_panel", ratio=4)
        )
        layout["left_panel"].split_column(
            Layout(name="status", ratio=3),
            Layout(name="progress", ratio=2)
        )
        layout["right_panel"].split_column(
            Layout(name="content", ratio=7),
            Layout(name="footer", ratio=4)
        )
        
        return layout
        
    def update_display(self, layout: Layout, trigger_time: str):
        """更新显示"""
        welcome_text = Path(__file__).parent / "static" / "welcome.txt"
        if welcome_text.exists():
            with open(welcome_text, "r", encoding="utf-8") as f:
                welcome = f.read()
        else:
            welcome = "ContestTrade: 基于内部竞赛机制的Multi-Agent交易系统"
        
        header_panel = Panel(
            Align.center(welcome),
            title="🎯 ContestTrade - 基于内部竞赛机制的Multi-Agent交易系统",
            border_style="blue",
            padding=(0, 1),
            expand=True  # 自适应宽度
        )
        layout["header"].update(header_panel)
        
        # 更新Agent状态面板
        status_text = Text()
        
        # 数据Agent状态
        data_agents = {k: v for k, v in self.agent_status.items() if not k.startswith("agent_")}
        if data_agents:
            status_text.append("📊 Data Analysis Agent\n", style="bold cyan")
            for agent_name, status in data_agents.items():
                status_icon = {
                    "pending": "⏳等待中...",
                    "running": "🔄分析中...", 
                    "completed": "✅分析完成"
                }.get(status, "❓")
                
                agent_display = agent_name[:20].ljust(20)
                status_text.append(f"{agent_display} {status_icon}\n")
        
        # Research Agent状态
        research_agents = {k: v for k, v in self.agent_status.items() if k.startswith("agent_")}
        if research_agents:
            status_text.append("\n🔍 Research Agent\n", style="bold green")
            for agent_name, status in research_agents.items():
                status_icon = {
                    "pending": "⏳等待中...",
                    "running": "🔄分析中...", 
                    "completed": "✅分析完成"
                }.get(status, "❓")
                
                agent_display = agent_name[:20].ljust(20)
                status_text.append(f"{agent_display} {status_icon}\n")
        
        status_panel = Panel(
            status_text,
            title="🤖 Agent状态",
            border_style="yellow",
            padding=(0, 1),
            expand=True  # 自适应宽度
        )
        layout["status"].update(status_panel)
        
        # 更新进度面板
        progress_text = Text()
        progress_text.append(f"📅 触发时间: {trigger_time}\n", style="cyan")
        progress_text.append(f"🎯 当前任务: {self.current_task}\n", style="yellow")
        if self.progress_info:
            progress_text.append(f"📈 进度: {self.progress_info}\n", style="green")
        
        # 显示步骤计数
        progress_text.append(f"\n📊 步骤统计:\n", style="bold blue")
        progress_text.append(f"  Data Analysis Agent事件: {self.step_counts['data']}\n")
        progress_text.append(f"  Research Agent事件: {self.step_counts['research']}\n")
        progress_text.append(f"  竞赛事件: {self.step_counts['contest']}\n")
        progress_text.append(f"  完成事件: {self.step_counts['finalize']}\n")
        
        progress_panel = Panel(
            progress_text,
            title="📊 进度信息",
            border_style="blue",
            padding=(0, 1),
            expand=True  # 自适应宽度
        )
        layout["progress"].update(progress_panel)
        
        # 更新主内容区域
        content_text = Text()
        content_text.append("🔄 实时事件日志\n", style="bold blue")
        
        if self.messages:
            for msg in list(self.messages)[-10:]:
                content_text.append(f"{msg}\n")
        else:
            content_text.append("  ⏳ 等待事件...\n")
        
        content_panel = Panel(
            content_text,
            title="📄 事件流",
            border_style="blue",
            padding=(1, 2),
            expand=True  # 自适应宽度
        )
        layout["content"].update(content_panel)
        
        # 更新底部
        if self.analysis_completed and self.final_state:
            footer_text = self._create_result_summary()
            footer_title = "🏆 结果摘要"
        else:
            footer_text = Text()
            footer_text.append("🔄 分析进行中...", style="bold yellow")
            if self.analysis_completed:
                footer_text.append("\n✅ 分析完成！请按回车键(↵)退出运行界面...", style="bold green")
            footer_title = "📊 状态信息"
        
        footer_panel = Panel(
            footer_text,
            title=footer_title,
            border_style="green",
            padding=(0, 1),
            expand=True  # 自适应宽度
        )
        layout["footer"].update(footer_panel)
    
    def _create_result_summary(self) -> Text:
        """创建结果摘要"""
        summary_text = Text()
        
        if self.final_state:
            # 从step_results中获取统计信息
            step_results = self.final_state.get('step_results', {})
            data_team_results = step_results.get('data_team', {})
            research_team_results = step_results.get('research_team', {})
            
            data_factors_count = data_team_results.get('factors_count', 0)
            research_signals_count = research_team_results.get('signals_count', 0)
            
            summary_text.append(f"📊 数据源: {data_factors_count} | ", style="green")
            summary_text.append(f"🔍 研究信号: {research_signals_count} | ", style="blue")
            
            # 获取所有信号并筛选有机会的信号
            best_signals = step_results.get('contest', {}).get('best_signals', [])
            
            # 筛选 has_opportunity 为 yes 的信号
            valid_signals = []
            for signal in best_signals:
                # 检查 has_opportunity 字段
                has_opportunity = signal.get('has_opportunity', 'no')
                if has_opportunity == 'yes':
                    valid_signals.append(signal)
            
            if valid_signals:
                summary_text.append(f"🎯 有效信号: {len(valid_signals)}", style="bold red")
                
                # 显示有效信号及其对应的Agent
                for i, signal in enumerate(valid_signals):
                    symbol_name = signal.get('symbol_name', 'N/A')
                    action = signal.get('action', 'N/A')
                    agent_id = signal.get('agent_id', 'N/A')
                    
                    summary_text.append(f"\n  {i+1}. Research Agent{agent_id}：", style="yellow")
                    summary_text.append(f"{symbol_name}({action}) ", style="cyan")
                    
            else:
                summary_text.append("🎯 有效信号: 0", style="bold red")     
                summary_text.append(" 无有效信号")

            summary_text.append("\n💡分析完成，按回车退出运行界面...")
        else:
            summary_text.append("❌ 分析失败", style="red")
        
        return summary_text


def _process_stdout_message(stdout_content: str, display: ContestTradeDisplay):
    """处理stdout消息来识别Agent状态变化"""
    
    lines = stdout_content.strip().split('\n')
    for line in lines:
        if not line.strip():
            continue
            
        # 识别Data Analysis Agent开始运行
        data_agent_start_match = re.search(r'🔍 开始运行Data Agent \d+ \((.+?)\)\.\.\.', line)
        if data_agent_start_match:
            agent_name = data_agent_start_match.group(1)
            
            # 映射到显示名称
            display_agent = _map_agent_name_to_display(agent_name)
            display.update_agent_status(display_agent, "running")
            display.add_message("Data Analysis Agent", f"🔍 {agent_name} 开始运行")
            continue
            
        # 识别Research Agent开始运行
        research_agent_start_match = re.search(r'🔍 开始运行Research Agent \d+ \((.+?)\)\.\.\.', line)
        if research_agent_start_match:
            agent_name = research_agent_start_match.group(1)
            display.update_agent_status(agent_name, "running")
            display.add_message("Research Agent", f"🔍 {agent_name} 开始运行")
            continue
            
        # 识别Data Analysis Agent完成
        if "Data analysis result saved to" in line:
            # 从路径中提取Agent名称
            path_match = re.search(r'/factors/(.+?)/\d{4}-\d{2}-\d{2}_\d{2}:\d{2}:\d{2}\.json', line)
            if path_match:
                agent_name = path_match.group(1)
                display_agent = _map_agent_name_to_display(agent_name)
                display.update_agent_status(display_agent, "completed")
                display.add_message("Data Analysis Agent", f"✅ {agent_name} 完成数据分析")
            continue
            
        # 识别Research Agent完成
        if "Research result saved to" in line:
            # 从路径中提取Agent名称
            path_match = re.search(r'/reports/(.+?)/\d{4}-\d{2}-\d{2}_\d{2}:\d{2}:\d{2}\.json', line)
            if path_match:
                agent_name = path_match.group(1)
                display.update_agent_status(agent_name, "completed")
                display.add_message("Research Agent", f"✅ {agent_name} 完成研究分析")
            continue


def _map_agent_name_to_display(agent_name: str) -> str:
    """将真实的agent_name映射到显示名称"""
    # 从配置中获取数据代理名称列表
    data_agents_config = cfg.data_agents_config
    data_agent_names = [agent_config.get('agent_name', '') for agent_config in data_agents_config]
    
    # 检查是否匹配配置中的数据代理名称
    for config_agent_name in data_agent_names:
        if config_agent_name and config_agent_name.lower() in agent_name.lower():
            return config_agent_name
    
    # 如果没有匹配到配置中的名称，使用原名
    return agent_name


def run_contest_analysis_interactive(trigger_time: str):
    """在交互界面中运行竞赛分析"""
    try:
        # 创建显示管理器
        display = ContestTradeDisplay()
        
        # 创建布局
        layout = display.create_layout(trigger_time)
        
        # 使用Live界面运行
        with Live(layout, refresh_per_second=3, screen=True, auto_refresh=True, console=console) as live:
            # 初始显示
            display.update_display(layout, trigger_time)
            
            # 添加初始消息
            display.add_message("系统", f"开始分析时间: {trigger_time}")
            display.set_current_task("初始化ContestTrade系统...")
            display.set_progress_info("系统启动中...")
            display.update_display(layout, trigger_time)
            
            # 检查模块导入
            try:
                if SimpleTradeCompany is None:
                    raise ImportError("SimpleTradeCompany模块导入失败")
                    
                display.add_message("系统", "✅ 成功导入SimpleTradeCompany模块")
                display.update_display(layout, trigger_time)
                
                # 创建公司实例
                company = SimpleTradeCompany()
                display.add_message("系统", "✅ 成功创建SimpleTradeCompany实例")
                display.update_display(layout, trigger_time)
                
            except Exception as e:
                display.add_message("错误", f"❌ 模块导入失败: {str(e)}")
                display.update_display(layout, trigger_time)
                return None, display
            
            # 运行工作流并捕获输出
            final_state = asyncio.run(run_with_events_capture(company, trigger_time, display, layout))
            
            # 运行结束后
            if final_state:
                display.add_message("完成", "✅ 分析完成！")
                display.set_current_task("分析完成，等待用户选择...")
                display.set_analysis_completed(True)
                display.final_state = final_state
                display.update_display(layout, trigger_time)
                
                # 等待用户手动退出
                console.print("\n[green]✅ 分析完成！[/green]")
                console.print("[dim]按任意键退出运行界面...[/dim]")
                input()
                
            else:
                display.add_message("错误", "❌ 分析失败")
                display.set_current_task("分析失败")
                display.update_display(layout, trigger_time)
                console.print("\n[red]❌ 分析失败！[/red]")
                console.print("[dim]按任意键退出运行界面...[/dim]")
                input()
                return None, display
                
    except Exception as e:
        console.print(f"[red]运行失败: {e}[/red]")
        return None, None
    
    # Live界面结束后，处理用户输入
    if final_state:
        return ask_user_for_next_action(final_state)
    
    return final_state, display


async def run_with_events_capture(company, trigger_time: str, display: ContestTradeDisplay, layout):
    """运行公司工作流并捕获事件流"""
    try:
        display.add_message("开始", "🚀 开始运行工作流...")
        display.set_current_task("🔄 启动工作流...")
        display.update_display(layout, trigger_time)
        
        # 运行公司工作流并处理事件
        final_state = None
        async for event in company.run_company_with_events(trigger_time):
            event_name = event.get("name", "")
            event_type = event.get("event", "")
            event_data = event.get("data", {})
            
            # 捕获stdout消息来识别Agent状态变化
            if event_type == "on_stdout":
                stdout_content = event_data.get("chunk", "")
                _process_stdout_message(stdout_content, display)
                continue
            
            # 处理公司级别事件
            if event_name in ["run_data_agents", "run_research_agents", "run_contest", "finalize"]:
                if event_type == "on_chain_start":
                    display.set_current_task(f"🔄 开始 {event_name}")
                    if event_name == "run_data_agents":
                        display.set_progress_info("数据收集阶段 1/4")
                    elif event_name == "run_research_agents":
                        display.set_progress_info("研究分析阶段 2/4")
                    elif event_name == "run_contest":
                        display.set_progress_info("竞赛评选阶段 3/4")
                    elif event_name == "finalize":
                        display.set_progress_info("结果生成阶段 4/4")
                        
                elif event_type == "on_chain_end":
                    display.set_current_task(f"✅ 完成 {event_name}")
                    if event_name == "finalize":
                        final_state = event_data.get("output", {})
                        # 确保trigger_time被包含在final_state中
                        if 'trigger_time' not in final_state:
                            final_state['trigger_time'] = trigger_time
                        display.set_analysis_completed(True)
                        
            # 处理LangGraph子图事件（Agent事件）
            elif event_name == "LangGraph":
                if event_type == "on_chain_start":
                    # 检查是否是Agent相关的事件
                    tags = event.get("tags", [])
                    if any("agent" in str(tag).lower() for tag in tags):
                        display.add_message("Agent", f"🔄 启动Agent子图")
                        if "data" in str(tags).lower():
                            display.step_counts["data"] += 1
                        elif "research" in str(tags).lower():
                            display.step_counts["research"] += 1
                            
                elif event_type == "on_chain_end":
                    tags = event.get("tags", [])
                    if any("agent" in str(tag).lower() for tag in tags):
                        display.add_message("Agent", f"✅ 完成Agent子图")
            
            # 处理具体的节点事件
            elif event_type in ["on_chain_start", "on_chain_end"]:
                # 过滤掉不需要显示的事件
                if event_name not in ["__start__", "__end__"]:
                    emoji = "🔄" if event_type == "on_chain_start" else "✅"
                    
                    # 识别Agent类型
                    if any(keyword in event_name.lower() for keyword in ["init_factor", "recompute_factor", "submit_result"]):
                        # Data Analysis Agent相关事件
                        agent_type = "Data Analysis Agent"
                        display.step_counts["data"] += 1
                    elif any(keyword in event_name.lower() for keyword in ["init_signal", "recompute_signal"]):
                        # Research Agent相关事件
                        agent_type = "Research Agent"  
                        display.step_counts["research"] += 1
                    else:
                        agent_type = "系统"
                    
                    display.add_message(agent_type, f"{emoji} {event_name}")
            
            # 更新显示
            display.update_display(layout, trigger_time)
        
        # 设置所有Agent为完成状态
        for agent_name in display.agent_status:
            display.update_agent_status(agent_name, "completed")
        
        # 确保final_state包含trigger_time
        if final_state is not None and 'trigger_time' not in final_state:
            final_state['trigger_time'] = trigger_time
        
        return final_state
        
    except Exception as e:
        display.add_message("错误", f"❌ 运行失败: {str(e)}")
        console.print(f"[red]详细错误: {e}[/red]")
        return None


def ask_user_for_next_action(final_state):
    """询问用户下一步操作"""
    console.print("\n[green]✅ 分析完成！[/green]")
    console.print("[dim]输入 'd' 查看详细结果 | 'n' 运行新分析 | 'q' 退出[/dim]")
    
    while True:
        try:
            user_input = input("请选择操作 (d/n/q): ").strip().lower()
            if user_input == 'd':
                display_detailed_report(final_state)
                console.print("[dim]输入 'n' 运行新分析 | 'q' 退出[/dim]")
            elif user_input == 'n':
                return final_state, "new_analysis"
            elif user_input == 'q':
                return final_state, "quit"
            else:
                console.print("[yellow]无效输入，请输入 'd', 'n' 或 'q'[/yellow]")
        except KeyboardInterrupt:
            console.print("\n[yellow]用户中断，退出...[/yellow]")
            return final_state, "quit"

def display_detailed_report(final_state: Dict):
    """显示详细报告"""
    if not final_state:
        console.print("[red]无结果可显示[/red]")
        return
    
    # 确定results目录路径 - 修正路径为ContestTrade/contest_trade/agents_workspace/results
    results_dir = Path(PROJECT_ROOT) / "agents_workspace" / "results"
    
    try:
        # 使用新的报告模板生成和显示报告
        report_path = display_final_report_interactive(final_state, results_dir)
        console.print(f"\n[green]✨ 报告生成完成！[/green]")
        console.print(f"[blue]📄 报告路径: {report_path}[/blue]")
        
    except Exception as e:
        console.print(f"[red]报告生成失败: {e}[/red]")
        console.print("[yellow]正在显示简化版报告...[/yellow]")
        
        # 显示简化版报告
        step_results = final_state.get('step_results', {})
        best_signals = step_results.get('contest', {}).get('best_signals', [])
        valid_signals = [s for s in best_signals if s.get('has_opportunity', 'no') == 'yes']
        
        console.print(f"\n[bold]分析摘要:[/bold]")
        console.print(f"总信号: {len(best_signals)}, 有效信号: {len(valid_signals)}")
        
        for i, signal in enumerate(valid_signals, 1):
            console.print(f"{i}. {signal.get('symbol_name', 'N/A')} - {signal.get('action', 'N/A')}")


def display_simple_report(final_state: Dict):
    """显示简单报告（备用方案）"""
    console.print("\n" + "="*50)
    console.print("[bold blue]ContestTrade 简化报告[/bold blue]")
    console.print("="*50)
    
    step_results = final_state.get('step_results', {})
    best_signals = step_results.get('contest', {}).get('best_signals', [])
    valid_signals = [s for s in best_signals if s.get('has_opportunity', 'no') == 'yes']
    
    console.print(f"总信号数: {len(best_signals)}")
    console.print(f"有效信号: {len(valid_signals)}")
    
    if valid_signals:
        console.print("\n有效投资信号:")
        for i, signal in enumerate(valid_signals, 1):
            console.print(f"  {i}. {signal.get('symbol_name', 'N/A')} - {signal.get('action', 'N/A')}")
    
    console.print("\n" + "="*50)

@app.command()
def run(
    trigger_time: Optional[str] = typer.Option(None, "--time", "-t", help="触发时间 (YYYY-MM-DD HH:MM:SS)"),
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", "-i", help="交互模式"),
):
    """运行ContestTrade分析"""
    
    # 验证配置
    if not validate_config():
        console.print("[red]配置验证失败，请检查配置文件[/red]")
        raise typer.Exit(1)
    
    # 交互模式获取参数
    if interactive:
        if not trigger_time:
            trigger_time = get_trigger_time()
    
    # 验证触发时间
    if not trigger_time:
        console.print("[red]未提供触发时间[/red]")
        raise typer.Exit(1)
    
    try:
        datetime.strptime(trigger_time, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        console.print("[red]触发时间格式错误，请使用 YYYY-MM-DD HH:MM:SS 格式[/red]")
        raise typer.Exit(1)
    
    # 主循环
    while True:
        try:
            result = run_contest_analysis_interactive(trigger_time)
        except Exception as e:
            console.print(f"[red]运行分析时发生错误: {e}[/red]")
            break
        
        if result is None or (isinstance(result, tuple) and result[0] is None):
            console.print("[red]❌ 分析失败[/red]")
            break
            
        if isinstance(result, tuple):
            final_state, action = result
            if action == "new_analysis":
                trigger_time = get_trigger_time()
                continue
            elif action == "quit":
                break
        else:
            final_state = result
            display = None

        break
    
    console.print("[green]感谢使用ContestTrade![/green]")

@app.command()
def config():
    """显示当前配置"""
    try:
        if cfg is None:
            console.print("[red]配置模块导入失败[/red]")
            raise typer.Exit(1)
            
        console.print("[bold blue]ContestTrade 配置信息[/bold blue]")
        console.print("="*50)
        
        console.print(f"\n[bold]LLM配置:[/bold]")
        console.print(f"  模型: {cfg.llm.get('model_name', 'N/A')}")
        console.print(f"  基础URL: {cfg.llm.get('base_url', 'N/A')}")
        
        # Data Analysis Agent配置
        console.print(f"\n[bold]Data Analysis Agent配置:[/bold]")
        for i, agent_config in enumerate(cfg.data_agents_config, 1):
            console.print(f"  {i}. {agent_config.get('agent_name', 'N/A')}")
            console.print(f"     数据源: {', '.join(agent_config.get('data_source_list', []))}")
        
        # Research Agent配置
        console.print(f"\n[bold]Research Agent配置:[/bold]")
        console.print(f"  最大反应步骤: {cfg.research_agent_config.get('max_react_step', 'N/A')}")
        console.print(f"  输出语言: {cfg.research_agent_config.get('output_language', 'N/A')}")
        console.print(f"  工具数量: {len(cfg.research_agent_config.get('tools', []))}")
        
    except Exception as e:
        console.print(f"[red]配置加载失败: {e}[/red]")
        raise typer.Exit(1)

@app.command()
def version():
    """显示版本信息"""
    console.print("[bold blue]ContestTrade[/bold blue]")
    console.print("基于内部竞赛机制的Multi-Agent交易系统")
    console.print("Multi-Agent Trading System Based on Internal Contest Mechanism")
    console.print(f"版本: 1.0.0")

if __name__ == "__main__":
    app()