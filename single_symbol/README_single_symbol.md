# 单只股票买卖信号与证据生成指南

本指南介绍如何使用本仓库提供的单标脚本，针对“某一支股票”生成当下的买/卖/HOLD 信号及其支撑证据，并导出 JSON 与 Markdown 报告。

---

## 功能概述

- 输入市场、股票代码、触发时间，脚本会调用研究 Agent 与工具链（Akshare + 搜索等）收集行情、技术面、新闻与财务等信息。
- 输出一个或多个结构化信号（BUY/SELL/HOLD），并列出证据（描述/时间/来源）与概率。
- 若 Agent 产出的信号包含其他股票，脚本会自动过滤，仅保留你输入的标的；如果最终无有效信号，会给出 HOLD 建议（含原因）。

脚本位置：`scripts/single_symbol_signal.py`

别名工具（将通用名映射到 Akshare 实现）：`contest_trade/tools/aliases.py`

---

## 环境准备

- Python >= 3.10
- 依赖安装（在项目根目录）：
  - `pip install -r requirements.txt`
- LLM 与数据源配置
  - 推荐使用专用的单标配置：`config_single.yaml`
  - 通过环境变量指定：
    - Windows PowerShell 当前会话：
      - `$env:CONTEST_TRADE_CONFIG_FILE="C:\\Code\\ContestTrade\\config_single.yaml"`
      - `$env:CONTEST_TRADE_MARKET="CN-Stock"`
  - 或使用默认 `config.yaml`，但建议单标任务使用 `config_single.yaml`（已精简数据代理、优先注册别名工具）
- 必填/可选 Key（以 `config_single.yaml` 为准）
  - llm/base_url/api_key/model_name（必填）
  - tushare_key（可选；部分工具会使用，需注意频控）
  - bocha_key、serp_key（可选，用于搜索工具）

> 提示：Windows 建议开启 UTF-8 输出以避免表情符号导致编码报错：`$env:PYTHONUTF8='1'`

---

## 快速开始

- CN A股示例（603799.SH）：

```
# 在项目根目录下
$env:CONTEST_TRADE_CONFIG_FILE="C:\\Code\\ContestTrade\\config_single.yaml"
$env:CONTEST_TRADE_MARKET="CN-Stock"
$env:PYTHONUTF8='1'
python ContestTrade/scripts/single_symbol_signal.py --market CN-Stock --symbol 603799.SH --time "2025-10-28 09:30:00"
```

- US 美股示例（NVDA）：

```
# 请先在 config_us.yaml 配置 fmp_key（可选 finnhub_key）
$env:CONTEST_TRADE_CONFIG_FILE="C:\\Code\\ContestTrade\\config_single.yaml"
$env:CONTEST_TRADE_MARKET="US-Stock"
python ContestTrade/scripts/single_symbol_signal.py --market US-Stock --symbol NVDA --time "2025-10-28 09:30:00"
```

参数说明：
- `--market`：`CN-Stock` 或 `US-Stock`
- `--symbol`：股票代码，A 股请使用带交易所后缀，如 `600519.SH`
- `--time`：触发时间，`YYYY-MM-DD HH:MM:SS`

---

## 输出位置与格式

- JSON：`contest_trade/agents_workspace/results/single_<symbol>_<time>.json`
- Markdown：`contest_trade/agents_workspace/results/single_<symbol>_<time>.md`

JSON 示例（精简）：
```json
{
  "symbol": "603799.SH",
  "trigger_time": "2025-10-27 23:55:37",
  "signals": [
    {
      "has_opportunity": "yes",
      "action": "BUY",
      "symbol_code": "603799.SH",
      "symbol_name": "某公司",
      "probability": "70",
      "evidence_list": [
        { "description": "……", "time": "2025-10-24", "from_source": "price_info" },
        { "description": "……", "time": "2025-10-24", "from_source": "search_web" }
      ]
    }
  ]
}
```

Markdown 报告会将关键信息（行动、概率、证据列表）以可读形式展示，便于快速浏览与分享。

---

## 工具与别名映射

- 为与提示词中的“通用工具名”对齐，本项目新增了别名工具（位于 `tools/aliases.py`）：
  - `stock_quote` → `price_info_akshare.price_info`
  - `corp_info` → `corp_info_akshare.company_financial_info`
  - `stock_symbol_search` → `stock_symbol_search_akshare.stock_symbol_search`
  - `stock_selector` → `stock_selector_akshare.stock_selector`
  - `stock_summary` → `stock_summary_akshare.stock_summary`
- `config_single.yaml` 已优先注册上述别名，并保留 Akshare 原始工具作为后备。

---

## 常见问题（FAQ）

1) 看不到单标配置生效？
- 日志会打印 `Loading config from: <path> (Override via CONTEST_TRADE_CONFIG_FILE)`。
- 若仍显示加载 `config.yaml`，请确认已设置 `$env:CONTEST_TRADE_CONFIG_FILE` 并在同一终端中执行脚本。

2) 工具未注册/不可调用（is not callable / Tool not found）？
- 请使用 `config_single.yaml` 并确保依赖安装完成。
- 已放宽工具注册逻辑以支持 LangChain Tool 对象；如仍失败，尝试重启 Python 进程以清理模块缓存。

3) Tushare 接口频控或数据获取失败？
- 换时间错峰尝试，或减少频繁调用。
- 单标脚本会在必要时回退为 HOLD，并在证据中说明原因。

4) 输出与目标标的不一致？
- 脚本内已做“只保留目标标的”的过滤；若 Agent 误产出其他标的，会被丢弃。

5) 编码错误（Windows GBK）？
- 建议设置：`$env:PYTHONUTF8='1'`。

---

## 进阶配置

- 想修改工具/模型/搜索策略，可在 `config_single.yaml` 中调整 `research_agent_config.tools`、`llm` 等项。
- 若需要不同的单标配置，可复制 `config_single.yaml` 并通过 `CONTEST_TRADE_CONFIG_FILE` 指向新文件。

---

## 安全与免责声明

- 请妥善保管 API Key，不要提交到公共仓库。
- 本项目为研究用途，输出不构成任何投资建议，据此操作风险自负。

