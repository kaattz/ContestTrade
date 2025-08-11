<p align="center">
  <img src="assets/logo.jpg" style="width: 100%; height: auto;">
</p>
<div align="center" style="line-height: 1;">
  <a href="https://arxiv.org/abs/2508.00554" target="_blank"><img alt="arXiv" src="https://img.shields.io/badge/arXiv-2508.00554-B31B1B?logo=arxiv"/></a>
  <a href="https://opensource.org/licenses/Apache-2.0" target="_blank"><img alt="License" src="https://img.shields.io/badge/License-Apache_2.0-blue.svg"/></a>
  <a href="https://www.python.org/downloads/release/python-3100/" target="_blank"><img alt="Python Version" src="https://img.shields.io/badge/Python-3.10+-brightgreen.svg"/></a>
</div>
<div align="center">
  <a href="README.md">中文</a> | <a href="README_en.md">English</a>
</div>

---
# ContestTrade: A Multi-Agent Trading System Based on Internal Contest Mechanism

**ContestTrade** 是一个创新的多智能体（Multi-Agent）交易框架，我们通过引入独特的内部竞赛机制，模拟了现实投资公司的团队协作与内部竞争，从而在动态变化的市场环境中保持决策的鲁棒性并实现卓越的交易表现。

##  Introduction (项目简介)

*   **🏆 内部竞赛机制 (Internal Contest Mechanism):** 框架的核心创新。系统内所有智能体的表现都会被持续评分和排名，只有表现最优的智能体输出（无论是数据因子还是交易信号）才会被采纳，从而实现优胜劣汰和持续的自我优化。
*   **👥 双团队架构 (Two-Tiered Team Framework):** 结构设计清晰，模仿专业投资公司。
    *   **数据团队 (Data Team):** 负责处理海量的市场数据，并将其提炼为多样化的高密度文本因子组合。
    *   **研究团队 (Research Team):** 基于数据团队提供的有效因子，并行地进行多路径深度研究，并生成最终的交易决策。
*   **🛠️ 深度研究 (Deep Research):** 研究员智能体被赋予了一套强大的专业金融工具集（如股票筛选、财务数据分析、网页搜索等），使其能够自主规划并执行深度分析，显著提升交易信号的质量。
*   **🔌 内部竞争机制:** 通过基于真实市场反馈的竞赛机制，系统能够自适应地调整数据团队和研究团队的资源分配，有效提高整体决策质量，提升整体决策的稳定性和可靠性。

## Framework Overview (框架概览)

<p align="center">
  <img src="assets/architecture.jpg" style="width: 90%; height: auto;">
</p>

ContestTrade 的工作流程通过一个结构化的双阶段管道来运作，模拟了投资公司的动态决策过程。这个双重竞赛框架确保了最终的决策只被最稳健、最有效的洞察所驱动，从而在复杂的市场中保持了强大的适应性和抗干扰能力。

1.  **数据处理阶段:** 首先，来自多个来源的原始市场数据被输入到**数据团队**。团队中的多个数据分析智能体 (Data Analysis Agents) 并行工作，将这些原始数据提炼成结构化的“文本因子”。在这一阶段，内部竞赛机制会评估每个数据智能体生成的因子的潜在价值，并构建出一个最优的“因子投资组合”。

2.  **研究决策阶段:** 这个最优的因子组合随后被传递给**研究团队**。团队中的多个研究员智能体 (Research Agents) 会基于各自独特的“交易信念” (Trading Beliefs) 和强大的金融工具集，对这些因子进行并行的深度分析，并各自提交交易提案。随后，第二轮内部竞赛会评估这些交易提案，并最终合成一个统一、可靠的资产配置策略作为最终输出。

## Installation (安装)

```bash
# 1. 克隆项目仓库
git clone https://github.com/FinStep-AI/ContestTrade.git
cd ContestTrade

# 2. (推荐) 创建并激活虚拟环境
conda create -n contesttrade python=3.10
conda activate contesttrade

# 3. 安装项目依赖
pip install -r requirements.txt
```

## Configuration (配置)

在运行ContestTrade之前，您需要配置必要的API密钥和LLM参数。

编辑 `trade_agent\config\config.yaml` 文件，填入您的API密钥。下表列出了所有必需和可选的密钥：

| Key | Description | Required |
| :--- | :--- | :--- |
| `TUSHARE_KEY` | Tushare 数据接口密钥 | **Yes** |
| `BOCHA_KEY` | Bocha 搜索引擎密钥 | No |
| `SERP_KEY` | SerpAPI 搜索引擎密钥 | No |
| `LLM_API_KEY` | 用于通用任务的LLM API密钥 | **Yes** |
| `LLM_BASE_URL` | 用于通用任务的LLM API地址 | **Yes** |
| `LLM_THINKING_API_KEY` | 用于复杂推理的LLM API密钥 | No |
| `LLM_THINKING_BASE_URL`| 用于复杂推理的LLM API地址 | No |
| `VLM_API_KEY` | 用于视觉分析的VLM API密钥 | No |
| `VLM_BASE_URL` | 用于视觉分析的VLM API地址 | No |

## Usage (使用方法)

您可以通过命令行界面（CLI）轻松启动ContestTrade。

```bash
python -m cli.main run
```

程序启动后，您将进入终端交互式界面，可以根据提示进行后续操作。


## Contributing (贡献指南)

我们非常欢迎来自社区的贡献！无论您是想修复一个bug、增加一个新的金融工具，还是改进文档，您的帮助对我们都至关重要。

如果您有兴趣，可以从以下方面开始：

*   查看`Issues`页面，寻找可以解决的问题。
*   提出您的新功能建议。
*   帮助我们完善和翻译文档。

## Citation (引用)

如果您在您的研究中使用了ContestTrade，请引用我们的论文：

```bibtex
@misc{zhao2025contesttrade,
      title={ContestTrade: A Multi-Agent Trading System Based on Internal Contest Mechanism}, 
      author={Li Zhao and Rui Sun and Zuoyou Jiang and Bo Yang and Yuxiao Bai and Mengting Chen and Xinyang Wang and Jing Li and Zuo Bai},
      year={2025},
      eprint={2508.00554},
      archivePrefix={arXiv},
      primaryClass={q-fin.TR}
}
```

## License (许可证)

本项目采用 [Apache 2.0 License](LICENSE) 许可证。
