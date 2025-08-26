"""
Contest预测模块

负责：
- 基于历史reward数据进行预测
- 计算因子排序分数
- 实现简单的历史均值预测策略
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime

from data_contest_types import FactorData

logger = logging.getLogger(__name__)


class ContestPredictor:
    """因子预测器"""
    
    def __init__(self, history_window_days: int = 5):
        # 当前使用简单的历史均值策略，未来可以扩展
        self.prediction_window_days = history_window_days
    
    def predict_factor_values(self, current_date: str, agent_factors: Dict[str, List[Optional[FactorData]]]) -> Dict[str, float]:
        """
        预测因子价值分数
        
        Args:
            current_date: 当前日期 YYYY-MM-DD
            agent_factors: 结构化的历史因子数据 Dict[agent_name, List[Optional[FactorData]]]
            
        Returns:
            Dict[agent_name, predicted_value]: 预测价值分数
        """
        logger.info(f"开始预测因子排序 - 当前日期: {current_date}")
        
        try:
            # 直接从结构化数据计算历史表现
            agent_rewards = self._collect_agent_rewards(agent_factors)
            
            # 计算预测得分（简单均值策略）
            predicted_scores = self._calculate_predicted_scores(agent_rewards)
            
            logger.info(f"预测完成，{len(predicted_scores)} 个agent有预测得分")
            self._log_prediction_summary(predicted_scores)
            
            return predicted_scores
            
        except Exception as e:
            logger.error(f"预测因子排序失败: {e}")
            raise RuntimeError(f"预测失败: {e}")
    
    def _collect_agent_rewards(self, agent_factors: Dict[str, List[Optional[FactorData]]]) -> Dict[str, List[Optional[float]]]:
        """
        从结构化因子数据中提取reward数据
        
        Args:
            agent_factors: 结构化的历史因子数据 Dict[agent_name, List[Optional[FactorData]]]
            
        Returns:
            Dict[agent_name, List[Optional[reward]]]: 每个agent对应固定5天的reward列表，按时间顺序[最远->最近]，缺位为None
        """
        agent_rewards = {}
        
        for agent_name, factors_list in agent_factors.items():
            rewards_list = []
            for factor in factors_list:
                if factor is None:
                    rewards_list.append(None)  # 缺位对应None
                elif factor.has_contest_data():
                    rewards_list.append(factor.contest_data["reward"])  # 有评估数据
                else:
                    rewards_list.append(None)  # 没有评估数据，暂时为None
                    
            agent_rewards[agent_name] = rewards_list
        
        return agent_rewards
    
    def _calculate_predicted_scores(self, agent_rewards: Dict[str, List[Optional[float]]]) -> Dict[str, float]:
        """计算预测得分 - 当前使用简单均值"""
        predicted_scores = {}
        
        for agent_name, rewards in agent_rewards.items():
            # 过滤掉None值
            valid_rewards = [r for r in rewards if r is not None]
            if valid_rewards:
                # 简单的历史均值策略
                predicted_scores[agent_name] = sum(valid_rewards) / len(valid_rewards)
            else:
                predicted_scores[agent_name] = 0.0
        
        return predicted_scores
    
    def _log_prediction_summary(self, predicted_scores: Dict[str, float]):
        """打印预测结果摘要"""
        if not predicted_scores:
            return
        
        # 按分数排序
        sorted_scores = sorted(predicted_scores.items(), key=lambda x: x[1], reverse=True)
        
        logger.info("预测结果摘要 (Top 5):")
        for i, (agent_name, score) in enumerate(sorted_scores[:5]):
            logger.info(f"  {i+1}. {agent_name}: {score:.3f}")
    
    
