from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel


class AgentType(str, Enum):
    """代理类型枚举"""
    DATA = "data"
    RESEARCH = "research"


class AgentStatus(str, Enum):
    """代理状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ContestResult(BaseModel):
    """竞赛结果模型"""
    trigger_time: str
    data_factors_count: int
    research_signals_count: int
    total_events_count: int
    best_signals: List[Dict]
    step_results: Dict 