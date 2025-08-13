<p align="center">
  <img src="assets/logo.jpg" style="width: 100%; height: auto;">
</p>
<div align="center" style="line-height: 1;">
  <a href="https://arxiv.org/abs/2508.00554" target="_blank"><img alt="arXiv" src="https://img.shields.io/badge/arXiv-2508.00554-B31B1B?logo=arxiv"/></a>
  <a href="https://opensource.org/licenses/Apache-2.0" target="_blank"><img alt="License" src="https://img.shields.io/badge/License-Apache_2.0-blue.svg"/></a>
  <a href="https://www.python.org/downloads/release/python-3100/" target="_blank"><img alt="Python Version" src="https://img.shields.io/badge/Python-3.10+-brightgreen.svg"/></a>
  <a href="./assets/wechat.png" target="_blank"><img alt="WeChat" src="https://img.shields.io/badge/WeChat-ContestTrade-brightgreen?logo=wechat&logoColor=white"/></a>
</div>
</div>
<div align="center">
  <a href="README.md">中文</a> | <a href="README_en.md">English</a>
</div>

---
# ContestTrade: A Multi-Agent Trading System Based on Internal Contest Mechanism

**ContestTrade** 是一个创新的多智能体（Multi-Agent）交易框架，通过**ContestTrade** 您可以轻松的打造一支专属的AI交易团队。只需设定分析时刻，它能自主扫描全市场，从海量数据中挖掘潜在的投资机会，并通过内部优选机制，为您构建最值得信赖的投资组合。


> **注意:** 目前框架仅支持 **中国A股** 市场。

##  Introduction (项目简介)
该项目致力于构建一个鲁棒的、基于大型语言模型（LLM）的量化交易系统。为了解决LLM对市场噪音敏感的挑战，我们引入了一种独特的内部竞争机制：系统中的多个智能体被分为数据团队和研究团队。

数据团队负责处理海量市场数据，并将其提炼成高密度的文本因子组合。随后，研究团队的智能体们会利用一套强大的专业金融工具集（如股票筛选、财务数据分析、网页搜索等），对这些因子进行多路径的深度研究，并生成交易决策。

在所有Agent分析结束后，系统会根据真实的市场反馈对所有智能体的表现进行实时评估和排名。最终，只有表现最佳的智能体所产生的决策才会被采纳。这种竞争和优胜劣汰的机制，使得系统能够自适应地调整资源分配，显著增强决策的稳健性和可靠性，从而实现更优异的交易结果。

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

编辑 `config.yaml` 文件，填入您的API密钥。下表列出了所有必需和可选的密钥：

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

程序启动后，您将进入终端交互式界面，可以根据提示输入分析时间。
<p align="center">
  <img src="assets/contest_trade_cli_start.jpg" style="width: 100%; height: auto;">
</p>

所有Agent运行完成后可在结果摘要中查看Agent给出的信号。
<p align="center">
  <img src="assets/contest_trade_cli_main.jpg" style="width: 100%; height: auto;">
</p>

同时可以进一步选择查看详细的报告。
<p align="center">
  <img src="assets/contest_trade_cli_report.jpg" style="width: 100%; height: auto;">
</p>

<p align="center">
  <img src="assets/contest_trade_cli_report_detail.jpg" style="width: 100%; height: auto;">
</p>


## 风险声明

**重要声明:** 本项目 `ContestTrade` 是一个开源的量化交易研究框架，仅供学术研究和教育目的使用。项目中包含的示例、数据和分析结果不构成任何形式的投资建议。

**风险提示:**
*   **市场风险:** 本项目不构成任何形式的投资、财务、法律或税务建议。所有输出，包括交易信号和分析，均为基于历史数据的AI模型推演结果，不应被视为任何买卖操作的依据。
*   **数据准确性:** 框架使用的数据源可能存在延迟、不准确或不完整的情况。我们不对数据的可靠性做任何保证。
*   **模型幻觉:** AI模型（包括大型语言模型）存在固有的局限性和“幻觉”风险。我们不保证框架生成信息的准确性、完整性或及时性。
*   **责任自负:**  开发者不对任何因使用或无法使用本框架而导致的直接或间接损失承担任何责任。投资有风险，入市需谨慎。

**在将本框架用于任何实际交易决策之前，请务必充分了解相关风险。**

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
