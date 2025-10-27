from datetime import datetime
from utils.market_manager import GLOBAL_MARKET_MANAGER

def get_current_datetime(trigger_time: str) -> str:
    """Get current time"""
    if trigger_time:
        return trigger_time
    else:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_previous_trading_date(trigger_time: str, output_format: str = "%Y%m%d") -> str:
    """获取触发日对应的最近一个交易日（不晚于触发日）。

    行为调整：
    - 若触发日本身为交易日，则返回“触发日”本身。
    - 若触发日为非交易日（周末/节假日），返回其之前最近的一个交易日。

    Args:
        trigger_time (str): 触发时间，格式：YYYY-MM-DD HH:MM:SS

    Returns:
        str: 最近交易日，格式：YYYYMMDD
    """
    # 解析 trigger_time
    trigger_datetime = datetime.strptime(trigger_time, "%Y-%m-%d %H:%M:%S")
    trigger_date = trigger_datetime.strftime("%Y%m%d")

    # 获取交易日列表
    trade_dates = GLOBAL_MARKET_MANAGER.get_trade_date(market_name="CN-Stock")
    if not trade_dates:
        # 兜底：无交易日信息时，退回触发日
        return trigger_date

    # 选择不晚于触发日的最近交易日（<= trigger_date）
    candidates = [dt for dt in trade_dates if dt <= trigger_date]
    if not candidates:
        # 如果触发日早于最早交易日，则取最早可用交易日
        nearest = trade_dates[0]
    else:
        nearest = candidates[-1]

    # 组装回与触发时间同一时间点，便于保持时间粒度一致
    nearest_dt_str = f"{nearest[:4]}-{nearest[4:6]}-{nearest[6:]} {trigger_time.split(' ')[1]}"
    nearest_formatted = datetime.strptime(nearest_dt_str, "%Y-%m-%d %H:%M:%S").strftime(output_format)
    return nearest_formatted


if __name__ == "__main__":
    print(get_current_datetime("2025-01-01 10:00:00"))
    print(get_previous_trading_date("2025-01-01 10:00:00"))
