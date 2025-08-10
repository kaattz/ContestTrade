"""
信号评估和权重优化系统 - 基于LLM评分的信号筛选和权重调整
"""
import json
import os
import asyncio
import textwrap
import time
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import requests
import concurrent.futures
import warnings
import re
from collections import defaultdict


from config.config import cfg, PROJECT_ROOT
from contest.judger_weight_optimizer import WeightOptimizer
from agents.research_agent import ResearchAgentInput
from config.config import cfg
from models.llm_model import GLOBAL_LLM

warnings.filterwarnings('ignore')

class DataFormatConverter:
    """数据格式转换器，将新格式数据转换为评分系统所需格式"""
    
    def __init__(self, workspace_dir: str):
        self.workspace_dir = Path(workspace_dir)
        self.reports_dir = self.workspace_dir / "reports"
        self.factors_dir = self.workspace_dir / "factors"
    
    def load_research_signals(self, trigger_time: str) -> Dict[str, Dict]:
        """
        加载研究信号数据
        
        Args:
            trigger_time: 触发时间，格式为 "2025-08-07 09:00:00"
            
        Returns:
            Dict[agent_name, signal_data]: 信号数据字典
        """
        signals = {}
        
        # 生成文件名 (保留冒号，只替换空格为下划线)
        filename = f"{trigger_time.replace(' ', '_')}.json"
        
        # 遍历所有agent目录
        if self.reports_dir.exists():
            for agent_dir in self.reports_dir.iterdir():
                if agent_dir.is_dir() and agent_dir.name.startswith('agent_'):
                    signal_file = agent_dir / filename
                    if signal_file.exists():
                        try:
                            with open(signal_file, 'r', encoding='utf-8') as f:
                                signal_data = json.load(f)
                            signals[agent_dir.name] = signal_data
                        except Exception as e:
                            print(f"加载信号文件失败 {signal_file}: {e}")
        
        return signals
    
    def load_factor_data(self, trigger_time: str) -> Dict[str, Dict]:
        """
        加载因子数据
        
        Args:
            trigger_time: 触发时间
            
        Returns:
            Dict[agent_name, factor_data]: 因子数据字典
        """
        factors = {}
        
        # 生成文件名 (保留冒号，只替换空格为下划线)
        filename = f"{trigger_time.replace(' ', '_')}.json"
        
        # 遍历所有factor目录
        if self.factors_dir.exists():
            for factor_dir in self.factors_dir.iterdir():
                if factor_dir.is_dir():
                    factor_file = factor_dir / filename
                    if factor_file.exists():
                        try:
                            with open(factor_file, 'r', encoding='utf-8') as f:
                                factor_data = json.load(f)
                            factors[factor_dir.name] = factor_data
                        except Exception as e:
                            print(f"加载因子文件失败 {factor_file}: {e}")
        
        return factors
    
    def convert_signals_for_judging(self, signals: Dict[str, Dict], factors: Dict[str, Dict]) -> Dict[str, Dict]:
        """
        将信号数据转换为评分系统所需格式
        
        Args:
            signals: 研究信号数据
            factors: 因子数据
            
        Returns:
            Dict[signal_name, signal_data]: 转换后的信号数据
        """
        converted_signals = {}
        
        for agent_name, signal_data in signals.items():
            # 解析final_result获取结构化数据
            parsed_signal = self._parse_final_result(signal_data.get('final_result', ''))
            
            if parsed_signal:
                # 构建标准化的信号数据
                signal_name = agent_name
                converted_signal = {
                    'signal_name': signal_name,
                    'date': signal_data.get('trigger_time', ''),
                    'thinking': signal_data.get('final_result_thinking', ''),
                    'has_opportunity': parsed_signal.get('has_opportunity', 'no'),
                    'action': parsed_signal.get('action', 'none'),
                    'symbol_code': parsed_signal.get('symbol_code', ''),
                    'symbol_name': parsed_signal.get('symbol_name', ''),
                    'evidence_list': parsed_signal.get('evidence_list', []),
                    'limitations': parsed_signal.get('limitations', []),
                    'probability': parsed_signal.get('probability', '0'),
                    'belief': signal_data.get('belief', ''),
                    'background_information': signal_data.get('background_information', '')
                }
                converted_signals[signal_name] = converted_signal
        
        return converted_signals
    
    def _parse_final_result(self, final_result: str) -> Optional[Dict]:
        """解析final_result字符串，提取结构化数据"""
        try:
            # 移除<Output>标签
            if '<Output>' in final_result:
                final_result = final_result.split('<Output>')[-1].strip()
            
            # 提取各个字段
            has_opportunity = self._extract_field(final_result, 'has_opportunity')
            action = self._extract_field(final_result, 'action')
            symbol_code = self._extract_field(final_result, 'symbol_code')
            symbol_name = self._extract_field(final_result, 'symbol_name')
            probability = self._extract_field(final_result, 'probability')
            
            # 提取evidence_list
            evidence_list = self._extract_evidence_list(final_result)
            
            # 提取limitations
            limitations = self._extract_limitations(final_result)
            
            return {
                'has_opportunity': has_opportunity,
                'action': action,
                'symbol_code': symbol_code,
                'symbol_name': symbol_name,
                'evidence_list': evidence_list,
                'limitations': limitations,
                'probability': probability
            }
        except Exception as e:
            print(f"解析final_result失败: {e}")
            return None
    
    def _extract_field(self, text: str, field_name: str) -> str:
        """提取单个字段"""
        pattern = f"<{field_name}>(.*?)</{field_name}>"
        match = re.search(pattern, text, flags=re.DOTALL)
        return match.group(1).strip() if match else ''
    
    def _extract_evidence_list(self, text: str) -> List[Dict]:
        """提取evidence_list"""
        evidence_list = []
        
        # 提取整个evidence_list内容
        evidence_list_match = re.search(r"<evidence_list>(.*?)</evidence_list>", text, flags=re.DOTALL)
        if not evidence_list_match:
            return evidence_list
        
        evidence_list_content = evidence_list_match.group(1)
        
        # 分割每个evidence块
        evidence_blocks = re.split(r"<evidence>", evidence_list_content)
        
        for block in evidence_blocks:
            if '</evidence>' in block:
                evidence_parts = block.split('</evidence>')
                if len(evidence_parts) >= 1:
                    evidence_content = evidence_parts[0].strip()
                    
                    # 提取time和from_source
                    time_match = re.search(r"<time>(.*?)</time>", evidence_parts[0] if len(evidence_parts) > 1 else block, flags=re.DOTALL)
                    source_match = re.search(r"<from_source>(.*?)</from_source>", evidence_parts[0] if len(evidence_parts) > 1 else block, flags=re.DOTALL)
                    
                    evidence_list.append({
                        'description': evidence_content,
                        'time': time_match.group(1).strip() if time_match else '',
                        'from_source': source_match.group(1).strip() if source_match else ''
                    })
        
        return evidence_list
    
    def _extract_limitations(self, text: str) -> List[str]:
        """提取limitations"""
        limitations = []
        
        # 提取整个limitations内容
        limitations_match = re.search(r"<limitations>(.*?)</limitations>", text, flags=re.DOTALL)
        if not limitations_match:
            return limitations
        
        limitations_content = limitations_match.group(1)
        
        # 提取每个limitation
        limitation_matches = re.findall(r"<limitation>(.*?)</limitation>", limitations_content, flags=re.DOTALL)
        for limitation in limitation_matches:
            limitations.append(limitation.strip())
        
        return limitations


class SignalJudger:
    """信号评分器 - 使用多个LLM对信号进行评分"""
    
    def __init__(self, workspace_dir: str):
        self.workspace_dir = Path(workspace_dir)
        self.judger_scores_dir = self.workspace_dir / "judger_scores"
        self.window_m = cfg.researcher_contest_config.get('window_m', 5)
        
        # 从配置中获取judger设置
        self.contest_config = cfg.researcher_contest_config
        self.num_judgers = self.contest_config.get('num_judgers', 5)
        self.judger_config_name = self.contest_config.get('judger_config', 'llm')
        
        # 获取LLM配置
        self.llm_config = getattr(cfg, self.judger_config_name)
        
        # 创建输出目录
        self.judger_scores_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据转换器
        self.data_converter = DataFormatConverter(workspace_dir)
    
    def build_scoring_prompt(self, signals: Dict[str, Dict], historical_returns: Optional[Dict[str, float]] = None) -> str:
        """
        构建LLM批量批评提示词 - 完全对齐原脚本逻辑
        
        Args:
            signals: 所有信号数据字典 {signal_name: signal_data}
            historical_returns: 历史收益率数据
        Returns:
            str: 提示词
        """
        date = list(signals.values())[0].get('date', 'unknown')
        
        # 构建所有信号的信息
        signals_info = []
        for signal_name, signal_data in signals.items():
            # 获取历史收益率信息
            historical_info = ""
            if historical_returns and signal_name in historical_returns:
                returns = historical_returns[signal_name]
                if returns is not None:
                    historical_info = f"Average daily return over past {self.window_m} days: {returns:.2f}%"
                else:
                    historical_info = f"Average daily return over past {self.window_m} days: Insufficient data"
            else:
                historical_info = f"Average daily return over past {self.window_m} days: Insufficient data"
            
            # 获取信号详细信息
            thinking = signal_data.get('thinking', 'None')
            has_opportunity = signal_data.get('has_opportunity', 'None')
            evidence_list = signal_data.get('evidence_list', [])
            limitations = signal_data.get('limitations', 'None')
            probability = signal_data.get('probability', 'None')
            action = signal_data.get('action', 'None')
            
            # 格式化evidence_list
            evidence_text = ""
            if isinstance(evidence_list, list) and evidence_list:
                evidence_items = []
                for item in evidence_list:
                    if isinstance(item, dict):
                        # 如果是字典格式，提取description
                        description = item.get('description', '')
                        if description:
                            evidence_items.append(description)
                    elif isinstance(item, str):
                        # 如果是字符串格式，直接使用
                        if item:
                            evidence_items.append(item)
                
                if evidence_items:
                    evidence_text = "\n".join([f"- {item}" for item in evidence_items])
                else:
                    evidence_text = "None"
            else:
                evidence_text = "None"
            
            signal_info = f"""
Researcher ID: {signal_name}
Historical Performance: {historical_info}
Recommended Action: {action}
Thinking Process: {thinking}
Opportunity Assessment: {has_opportunity}
Evidence List: {evidence_text}
Limitations: {limitations}
Probability Assessment: {probability}
"""
            signals_info.append(signal_info)
        
        all_signals_text = "\n".join(signals_info)
        
        prompt = f"""
You are a strict stock investment analyst who needs to critically evaluate trading signals.

Evaluation Date: {date}

Below is the signal information from all researchers:

{all_signals_text}

Please evaluate all signals according to the following criticism criteria:

Criticism Criteria (Start from 100 points, only deduct points, no bonus points):
1. Historical Performance Issues: Poor performance over the past {self.window_m} days
2. Analysis Quality Issues: Confused thinking process, lack of depth, unclear logic
3. Insufficient Evidence Issues: Few evidence, poor quality, lack of persuasiveness, insufficient evidence
4. Risk Assessment Issues: Insufficient awareness of limitations, unreasonable probability assessment, weak risk awareness
5. Opportunity Judgment Issues: Inaccurate has_opportunity judgment, poor opportunity identification ability
6. Logical Flaws: Logical contradictions in analysis, imprecise reasoning
7. Data Issues: Improper data usage, data interpretation errors

Please output strictly according to the following format, one researcher per line:
researcher_0: 75|Average historical performance(-15), insufficient analysis depth(-10), moderate evidence(-5)
...
researcher_19: 45|Poor historical performance(-25), confused analysis logic(-15), insufficient evidence(-10), missing risk assessment(-5)
researcher_v2_0: 60|Average historical performance(-20), shallow analysis logic(-10), poor evidence quality(-10)
...
researcher_v2_19: 25|Very poor historical performance(-30), confused analysis logic(-20), severely insufficient evidence(-15), missing risk assessment(-10)

Format Instructions:
- Each line format: Researcher ID: Final Score|Criticism Reasons (only deduction items)
- Final score range: 0 to 100 (deduct from 100 points)
- Only question signals and logic and deduct points, no bonus points
- Criticism reasons should detail the reasons for deduction and specific problems
- Must use "|" to separate score and reasons, do not use other separators
"""
        return prompt
    
    def call_llm_for_scoring(self, prompt: str, judger_id: int, max_retries: int = 3) -> str:
        """调用LLM进行评分"""
        messages = [
            {'role': 'user', 'content': prompt}
        ]
        
        try:
            print(f"调用judger_{judger_id} (GLOBAL_LLM)...")
            
            result = GLOBAL_LLM.run(messages, max_tokens=10000, temperature=0.1)
            
            if result and hasattr(result, 'content'):
                return result.content
            else:
                print(f"警告: judger_{judger_id} 响应格式异常")
                return f"错误: 无法解析响应内容"
                
        except Exception as e:
            print(f"错误: judger_{judger_id} 调用失败: {e}")
            return f"错误: {e}"
    
    def parse_llm_scores(self, content: str) -> Dict[str, Dict]:
        """解析LLM返回的评分结果"""
        scores = {}
        try:
            lines = content.strip().split('\n')
            for line in lines:
                line = line.strip()
                if ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        signal_name = parts[0].strip()
                        score_reason_text = parts[1].strip()
                        
                        # 分离分数和理由
                        if '|' in score_reason_text:
                            score_text, reason = score_reason_text.split('|', 1)
                            reason = reason.strip()
                        elif ' - ' in score_reason_text:
                            score_text, reason = score_reason_text.split(' - ', 1)
                            reason = reason.strip()
                        else:
                            score_text = score_reason_text
                            reason = "无评分理由"
                        
                        # 提取数字
                        numbers = re.findall(r'\d+', score_text)
                        if numbers:
                            score = float(numbers[0])
                            scores[signal_name] = {
                                'score': min(max(score, 0), 100),
                                'reason': reason
                            }
        except Exception as e:
            print(f"解析评分结果出错: {e}")
        
        return scores
    
    def check_missing_signals(self, trigger_time: str, window_m: int = 5) -> List[str]:
        """
        检查过去window_m天是否有缺失的信号
        
        Args:
            trigger_time: 当前触发时间
            window_m: 历史窗口天数
            
        Returns:
            List[str]: 缺失信号的日期列表
        """
        missing_dates = []
        
        # 解析当前时间
        current_date = datetime.strptime(trigger_time, "%Y-%m-%d %H:%M:%S")
        
        # 检查过去window_m天
        for i in range(1, window_m + 1):
            check_date = current_date - timedelta(days=i)
            check_time = check_date.strftime("%Y-%m-%d %H:%M:%S")
            
            # 检查是否有信号文件
            signals = self.data_converter.load_research_signals(check_time)
            if not signals:
                missing_dates.append(check_time)
        
        return missing_dates
    
    async def run_missing_signals(self, missing_dates: List[str], research_agents) -> bool:
        """
        运行缺失的信号（不进行contest）
        
        Args:
            missing_dates: 缺失信号的日期列表
            research_agents: research agents实例
            
        Returns:
            bool: 是否成功运行
        """
        if not missing_dates:
            return True
        
        print(f"发现 {len(missing_dates)} 个缺失信号，开始补全...")
        
        for missing_time in missing_dates:
            print(f"补全时间: {missing_time}")
            try:
                # 运行research agents生成信号，但不进行contest
                # 这里需要调用research agents的run方法，但跳过contest步骤
                success = await self._run_research_agents_for_missing_signal(missing_time, research_agents)
                if success:
                    print(f"  ✅ 补全完成: {missing_time}")
                else:
                    print(f"  ❌ 补全失败: {missing_time}")
                    return False
            except Exception as e:
                print(f"  ❌ 补全失败: {missing_time} - {e}")
                return False
        
        return True
    
    async def _run_research_agents_for_missing_signal(self, trigger_time: str, research_agents) -> bool:
        """
        为缺失信号运行research agents（不进行contest）
        
        Args:
            trigger_time: 触发时间
            research_agents: research agents实例
            
        Returns:
            bool: 是否成功运行
        """
        try:
            # 这里需要实现具体的research agents运行逻辑
            # 由于research agents的运行逻辑比较复杂，这里提供一个框架
            
            # 1. 加载因子数据
            factors = self.data_converter.load_factor_data(trigger_time)
            
            # 2. 运行每个research agent
            for agent_id, agent in research_agents.items():
                try:
                    print(f"    运行agent_{agent_id}...")
                    
                    # 构建背景信息
                    background_information = agent.build_background_information(trigger_time, agent.config.belief, factors)
                    
                    # 创建agent输入
                    agent_input = ResearchAgentInput(
                        trigger_time=trigger_time,
                        background_information=background_information
                    )
                    
                    # 运行agent（不进行contest）
                    agent_events = []
                    async for event in agent.run_with_monitoring_events(agent_input, config=None):
                        agent_events.append(event)
                    
                    print(f"    agent_{agent_id} 运行完成")
                    
                except Exception as e:
                    print(f"    agent_{agent_id} 运行失败: {e}")
                    return False
            
            return True
            
        except Exception as e:
            print(f"运行research agents失败: {e}")
            return False

    def calculate_historical_returns(self, trigger_time: str) -> Optional[Dict[str, Optional[float]]]:
        """
        计算历史收益率
        
        Args:
            trigger_time: 当前触发时间
            
        Returns:
            Dict[signal_name, avg_return]: 历史平均收益率字典，None表示数据不足
        """
        try:
            from utils.market_manager import MarketManager, MarketManagerConfig
            
            # 初始化市场管理器
            market_config = MarketManagerConfig.from_config_file()
            market_manager = MarketManager(market_config)
            
            # 解析当前时间
            current_date = datetime.strptime(trigger_time, "%Y-%m-%d %H:%M:%S")
            
            # 获取所有agent的历史收益
            historical_returns = {}
            
            # 遍历所有agent目录
            reports_dir = self.workspace_dir / "reports"
            if reports_dir.exists():
                for agent_dir in reports_dir.iterdir():
                    if agent_dir.is_dir() and agent_dir.name.startswith('agent_'):
                        agent_name = agent_dir.name
                        returns = []
                        
                        # 获取过去window_m天的信号
                        for i in range(1, self.window_m + 1):
                            check_date = current_date - timedelta(days=i)
                            check_time = check_date.strftime("%Y-%m-%d %H:%M:%S")
                            
                            # 加载信号数据
                            signal_file = agent_dir / f"{check_time.replace(' ', '_')}.json"
                            if signal_file.exists():
                                try:
                                    with open(signal_file, 'r', encoding='utf-8') as f:
                                        signal_data = json.load(f)
                                    
                                    # 解析信号
                                    parsed_signal = self.data_converter._parse_final_result(signal_data.get('final_result', ''))
                                    if parsed_signal and parsed_signal.get('action') in ['buy', 'sell']:
                                        # 计算收益率
                                        return_value = self._calculate_signal_return(
                                            parsed_signal, check_time, market_manager
                                        )
                                        if return_value is not None:
                                            returns.append(return_value)
                                except Exception as e:
                                    print(f"计算历史收益失败 {agent_name} {check_time}: {e}")
                        
                        # 计算平均收益率
                        if returns:
                            historical_returns[agent_name] = np.mean(returns)
                        else:
                            historical_returns[agent_name] = None
            
            return historical_returns if historical_returns else None
            
        except Exception as e:
            print(f"历史收益计算失败: {e}")
            return None
    
    def _calculate_signal_return(self, signal_data: Dict, signal_time: str, market_manager) -> Optional[float]:
        """
        计算信号的过去五个交易日收益率（基于开盘价）
        
        对于buy信号：计算过去5个交易日的正向收益率
        对于sell信号：计算过去5个交易日的反向收益率（股价下跌对应正收益）
        
        Args:
            signal_data: 信号数据
            signal_time: 信号时间  
            market_manager: 市场管理器
            
        Returns:
            float: 过去五个交易日的累计收益率，None表示无法计算
        """
        try:
            action = signal_data.get('action', '')
            symbol_code = signal_data.get('symbol_code', '')
            
            if not action or not symbol_code:
                print(f"信号数据不完整: action={action}, symbol_code={symbol_code}")
                return None
            
            print(f"计算{symbol_code}的5日收益率，信号时间: {signal_time}, 操作: {action}")
            
            # 获取过去5个交易日的价格数据（需要6个点：T-5到T0）
            open_prices = []
            for i in range(6):  # 需要6个数据点来计算5个交易日的收益率
                try:
                    price_data = market_manager.get_symbol_price("CN-Stock", symbol_code, signal_time, -i)
                    if not price_data:
                        print(f"  T-{i}: 无法获取价格数据")
                        break
                    
                    open_price = price_data.get('open')
                    trade_date = price_data.get('trade_date', f'Day-{i}')
                    if open_price is not None and open_price > 0:
                        open_prices.append(open_price)
                        print(f"  T-{i}: {trade_date} 开盘价 {open_price:.2f}")
                    else:
                        print(f"  T-{i}: 开盘价无效 {open_price}")
                        break
                except Exception as e:
                    print(f"  T-{i}: 获取价格异常 {e}")
                    break
            
            # 需要至少6个价格点来计算5个交易日收益率
            if len(open_prices) < 6:
                print(f"数据不足，仅获取到{len(open_prices)}个价格点，需要6个")
                # 如果数据不足，尝试计算可用天数的收益率
                if len(open_prices) >= 2:
                    print(f"使用{len(open_prices)-1}个交易日计算收益率")
                    start_price = open_prices[-1]  # 最早的开盘价
                    end_price = open_prices[0]     # 当前日的开盘价
                    
                    # 计算基础收益率
                    base_return = (end_price - start_price) / start_price
                    print(f"  基础收益率: ({end_price:.2f} - {start_price:.2f}) / {start_price:.2f} = {base_return:.4f}")
                    
                    # 根据action调整收益率
                    if action.lower() == 'buy':
                        # buy信号：股价上涨为正收益
                        final_return = base_return
                        print(f"  买入信号，保持收益率: {final_return:.4f}")
                    elif action.lower() == 'sell':
                        # sell信号：股价下跌为正收益，所以取负值
                        final_return = -base_return
                        print(f"  卖出信号，收益率取反: {final_return:.4f}")
                    else:
                        print(f"  未知操作类型: {action}")
                        return None
                    
                    # 限制收益率在合理范围内
                    return max(-1.0, min(1.0, final_return))
                else:
                    return None
            
            # 计算完整5个交易日的累计收益率
            start_price = open_prices[5]  # 5个交易日前的开盘价
            end_price = open_prices[0]    # 当前日的开盘价
            
            # 计算基础收益率
            base_return = (end_price - start_price) / start_price
            print(f"  完整5日收益率: ({end_price:.2f} - {start_price:.2f}) / {start_price:.2f} = {base_return:.4f}")
            
            # 根据action调整收益率
            if action.lower() == 'buy':
                # buy信号：股价上涨为正收益
                final_return = base_return
                print(f"  买入信号，保持收益率: {final_return:.4f}")
            elif action.lower() == 'sell':
                # sell信号：股价下跌为正收益，所以取负值
                final_return = -base_return
                print(f"  卖出信号，收益率取反: {final_return:.4f}")
            else:
                print(f"  未知操作类型: {action}")
                return None
            
            # 限制收益率在合理范围内（5日累计收益率限制在±100%）
            final_return = max(-1.0, min(1.0, final_return))
            
            return final_return
            
        except Exception as e:
            print(f"计算信号过去5个交易日收益率失败: {e}")
            return None
    
    def calculate_expected_sharpe_ratios(self, trigger_time: str, window_n: int = 3) -> Optional[Dict[str, float]]:
        """
        计算预期夏普比率
        
        Args:
            trigger_time: 当前触发时间
            window_n: 未来窗口天数
            
        Returns:
            Dict[signal_name, sharpe_ratio]: 预期夏普比率字典，None表示数据不足
        """
        try:
            from utils.market_manager import MarketManager, MarketManagerConfig
            
            # 初始化市场管理器
            market_config = MarketManagerConfig.from_config_file()
            market_manager = MarketManager(market_config)
            
            # 解析当前时间
            current_date = datetime.strptime(trigger_time, "%Y-%m-%d %H:%M:%S")
            
            # 获取所有agent的预期夏普比率
            expected_sharpe_ratios = {}
            
            # 遍历所有agent目录
            reports_dir = self.workspace_dir / "reports"
            if reports_dir.exists():
                for agent_dir in reports_dir.iterdir():
                    if agent_dir.is_dir() and agent_dir.name.startswith('agent_'):
                        agent_name = agent_dir.name
                        daily_returns = []
                        
                        # 获取未来window_n天的信号（只考虑buy信号）
                        for i in range(window_n):
                            future_date = current_date + timedelta(days=i)
                            future_time = future_date.strftime("%Y-%m-%d %H:%M:%S")
                            
                            # 加载信号数据
                            signal_file = agent_dir / f"{future_time.replace(' ', '_')}.json"
                            if signal_file.exists():
                                try:
                                    with open(signal_file, 'r', encoding='utf-8') as f:
                                        signal_data = json.load(f)
                                    
                                    # 解析信号
                                    parsed_signal = self.data_converter._parse_final_result(signal_data.get('final_result', ''))
                                    if parsed_signal and parsed_signal.get('action') == 'buy':
                                        # 计算收益率
                                        return_value = self._calculate_signal_return(
                                            parsed_signal, future_time, market_manager
                                        )
                                        if return_value is not None:
                                            daily_returns.append(return_value)
                                except Exception as e:
                                    print(f"计算预期夏普失败 {agent_name} {future_time}: {e}")
                        
                        # 计算夏普比率
                        if len(daily_returns) > 1:
                            mean_return = np.mean(daily_returns)
                            std_return = np.std(daily_returns)
                            if std_return > 0:
                                # 年化夏普比率（假设252个交易日）
                                sharpe_ratio = (mean_return / std_return) * np.sqrt(252)
                                expected_sharpe_ratios[agent_name] = sharpe_ratio
                            else:
                                expected_sharpe_ratios[agent_name] = 0.0
                        elif len(daily_returns) == 1:
                            expected_sharpe_ratios[agent_name] = 0.0
                        else:
                            expected_sharpe_ratios[agent_name] = 0.0  # 改为0.0而不是None
            
            return expected_sharpe_ratios if expected_sharpe_ratios else None
            
        except Exception as e:
            print(f"预期夏普比率计算失败: {e}")
            return None
    
    async def judge_signals(self, trigger_time: str) -> Tuple[Dict, Dict]:
        """
        对信号进行评分
        
        Args:
            trigger_time: 触发时间
            
        Returns:
            tuple: (评分结果, 原始响应)
        """
        print(f"开始对时间 {trigger_time} 的信号进行评分...")
        
        # 加载数据
        signals = self.data_converter.load_research_signals(trigger_time)
        factors = self.data_converter.load_factor_data(trigger_time)
        
        if not signals:
            print("没有找到信号数据")
            return {}, {}
        
        print(f"加载了 {len(signals)} 个信号")
        
        # 转换数据格式
        converted_signals = self.data_converter.convert_signals_for_judging(signals, factors)
        
        if not converted_signals:
            print("信号数据转换失败")
            return {}, {}
        
        # 不再计算当天信号标的的历史表现，改为在权重优化阶段计算agent历史信号执行结果
        historical_returns = None
        
        # 构建prompt
        prompt = self.build_scoring_prompt(converted_signals, historical_returns)
        
        # 并发调用多个judger
        all_scores = {}
        all_responses = {}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_judgers) as executor:
            # 提交所有judger任务
            future_to_judger = {}
            for judger_id in range(self.num_judgers):
                future = executor.submit(self._score_with_single_judger, judger_id, prompt)
                future_to_judger[future] = judger_id
            
            # 收集结果
            for future in concurrent.futures.as_completed(future_to_judger):
                judger_id = future_to_judger[future]
                try:
                    response, scores = future.result()
                    judger_name = f"judger_{judger_id}"
                    all_scores[judger_name] = scores
                    all_responses[judger_name] = response
                    print(f"  judger_{judger_id} 完成评分，解析了 {len(scores)} 个信号")
                except Exception as exc:
                    print(f"  judger_{judger_id} 评分失败: {exc}")
                    judger_name = f"judger_{judger_id}"
                    all_scores[judger_name] = {}
                    all_responses[judger_name] = f"评分失败: {exc}"
        
        # 保存结果
        self._save_judge_results(trigger_time, all_scores, all_responses)
        
        return all_scores, all_responses
    
    def _score_with_single_judger(self, judger_id: int, prompt: str) -> Tuple[str, Dict]:
        """单个judger评分的辅助方法"""
        response = self.call_llm_for_scoring(prompt, judger_id)
        scores = self.parse_llm_scores(response)
        return response, scores
    
    def _save_judge_results(self, trigger_time: str, all_scores: Dict, all_responses: Dict):
        """保存评分结果"""
        timestamp = trigger_time.replace(' ', '_').replace(':', '')
        
        # 保存详细评分结果
        scores_file = self.judger_scores_dir / f"judge_scores_{timestamp}.json"
        with open(scores_file, 'w', encoding='utf-8') as f:
            json.dump({
                'trigger_time': trigger_time,
                'scores': all_scores,
                'responses': all_responses
            }, f, ensure_ascii=False, indent=2)
        
        print(f"评分结果已保存到: {scores_file}")


class JudgerCritic:
    """信号评分和权重优化的主控制器"""
    
    def __init__(self, workspace_dir: str = None):
        if workspace_dir is None:
            workspace_dir = PROJECT_ROOT / "agents_workspace"
        
        self.workspace_dir = Path(workspace_dir)
        self.signal_judger = SignalJudger(str(self.workspace_dir))
        self.weight_optimizer = WeightOptimizer(str(self.workspace_dir))
    
    async def run_judger_critic(self, trigger_time: str, research_agents=None) -> Dict[str, Any]:
        """
        运行完整的评分和权重优化流程
        
        Args:
            trigger_time: 触发时间
            research_agents: research agents实例，用于补全缺失信号
            
        Returns:
            Dict: 包含评分结果和权重的完整结果
        """
        print(f"🤖 开始运行JudgerCritic流程，时间: {trigger_time}")
        
        try:
            # 0. 检查并补全缺失信号
            print("🔍 步骤0: 检查历史信号完整性...")
            missing_dates = self.signal_judger.check_missing_signals(trigger_time, self.signal_judger.window_m)
            
            if missing_dates:
                print(f"发现 {len(missing_dates)} 个缺失信号，开始补全...")
                if research_agents:
                    success = await self.signal_judger.run_missing_signals(missing_dates, research_agents)
                    if not success:
                        print("❌ 缺失信号补全失败")
                        return {
                            'status': 'failed',
                            'reason': '缺失信号补全失败',
                            'trigger_time': trigger_time
                        }
                else:
                    print("⚠️ 未提供research_agents，跳过缺失信号补全")
            else:
                print("✅ 历史信号完整，无需补全")
            
            # 1. 信号评分
            print("📊 步骤1: 信号评分...")
            all_scores, all_responses = await self.signal_judger.judge_signals(trigger_time)
            
            if not all_scores:
                print("⚠️ 没有获得评分结果，退出")
                return {
                    'status': 'failed',
                    'reason': '没有获得评分结果',
                    'trigger_time': trigger_time
                }
            
            # 2. 计算共识评分
            print("🔄 步骤2: 计算共识评分...")
            consensus_scores = self.weight_optimizer.calculate_consensus_scores(all_scores)
            
            # 2.5. 过滤无效信号 (has_opportunity=no)
            print("🔍 步骤2.5: 过滤无效信号...")
            signals = self.signal_judger.data_converter.load_research_signals(trigger_time)
            factors = self.signal_judger.data_converter.load_factor_data(trigger_time)
            converted_signals = self.signal_judger.data_converter.convert_signals_for_judging(signals, factors)
            
            # 过滤掉has_opportunity=no的信号
            valid_signals = {}
            filtered_consensus_scores = {}
            for signal_name, signal_data in converted_signals.items():
                has_opportunity = signal_data.get('has_opportunity', 'no')
                if has_opportunity.lower() == 'yes':
                    valid_signals[signal_name] = signal_data
                    if signal_name in consensus_scores:
                        filtered_consensus_scores[signal_name] = consensus_scores[signal_name]
                    print(f"   ✅ 保留有效信号: {signal_name} (has_opportunity={has_opportunity})")
                else:
                    print(f"   ❌ 过滤无效信号: {signal_name} (has_opportunity={has_opportunity})")
            
            print(f"   过滤前信号数量: {len(consensus_scores)}, 过滤后有效信号数量: {len(filtered_consensus_scores)}")
            consensus_scores = filtered_consensus_scores
            
            # 3. 权重优化（基于共识评分和历史收益率）
            print("⚖️ 步骤3: 权重优化...")
            optimized_weights = self.weight_optimizer.optimize_weights(consensus_scores, trigger_time)
            
            # 4. 保存最终结果
            print("💾 步骤4: 保存最终结果...")
            final_result = self.weight_optimizer.save_final_results(
                trigger_time, consensus_scores, optimized_weights
            )
            
            print("✅ JudgerCritic流程完成")
            print(f"   共识评分数量: {len(consensus_scores)}")
            print(f"   平均评分: {final_result['summary']['avg_score']:.2f}")
            print(f"   最高评分信号: {final_result['summary']['top_signals'][0] if final_result['summary']['top_signals'] else 'None'}")
            
            return {
                'status': 'success',
                'trigger_time': trigger_time,
                'all_scores': all_scores,
                'consensus_scores': consensus_scores,
                'optimized_weights': optimized_weights,
                'final_result': final_result
            }
            
        except Exception as e:
            print(f"❌ JudgerCritic流程失败: {e}")
            return {
                'status': 'failed',
                'reason': str(e),
                'trigger_time': trigger_time
            }


# 主函数用于测试
async def main():
    """测试函数"""
    judger_critic = JudgerCritic()
    
    # 使用示例时间进行测试
    test_time = "2025-08-07 09:00:00"
    result = await judger_critic.run_judger_critic(test_time)
    
    print("\n" + "="*60)
    print("测试结果:")
    print(f"状态: {result['status']}")
    if result['status'] == 'success':
        print(f"共识评分: {result['consensus_scores']}")
        print(f"优化权重: {result['optimized_weights']}")
    else:
        print(f"失败原因: {result['reason']}")


if __name__ == "__main__":
    asyncio.run(main())
