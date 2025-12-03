# Loguru 日志配置系统

本项目集成了基于 Loguru 的日志配置系统，支持灵活的日志级别控制、文件轮转和每次运行生成新日志文件的功能。

## 文件结构

```
ContestTrade/
├── log_config.yaml              # 日志配置文件
├── contest_trade/utils/
│   └── logger_config.py         # 日志配置加载模块
├── logger_example.py            # 使用示例
└── logs/                        # 日志文件目录（自动创建）
    ├── app_2025-12-03_11-22-35.log
    └── error_2025-12-03_11-22-35.log
```

## 配置说明

### log_config.yaml 配置项

- **level**: 全局日志级别 (TRACE, DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **format**: 日志输出格式
- **console**: 控制台输出配置
- **file**: 普通日志文件配置
- **error_file**: 错误日志文件配置

### 主要特性

1. **每次运行生成新日志文件**
   - 普通日志：`logs/app_{time:YYYY-MM-DD_HH-mm-ss}.log`
   - 错误日志：`logs/error_{time:YYYY-MM-DD_HH-mm-ss}.log`

2. **日志文件轮转**
   - 普通日志文件大小达到 10MB 时自动轮转
   - 错误日志文件大小达到 5MB 时自动轮转

3. **日志保留策略**
   - 普通日志保留 7 天
   - 错误日志保留 30 天
   - 轮转后的日志文件自动压缩为 zip 格式

## 使用方法

### 1. 基本使用

```python
from contest_trade.utils.logger_config import get_logger

# 获取logger实例
logger = get_logger()

# 记录不同级别的日志
logger.debug("调试信息")
logger.info("普通信息")
logger.warning("警告信息")
logger.error("错误信息")
logger.critical("严重错误")
```

### 2. 自定义配置文件路径

```python
from contest_trade.utils.logger_config import setup_logger

# 使用自定义配置文件
logger = setup_logger("path/to/your/config.yaml")
```

### 3. 通过环境变量指定配置文件

```bash
export LOG_CONFIG_FILE=path/to/your/config.yaml
python your_app.py
```

## 配置修改

### 修改日志级别

编辑 `log_config.yaml` 文件：

```yaml
# 修改全局日志级别为DEBUG
level: "DEBUG"

# 或者只修改控制台输出级别
console:
  enabled: true
  level: "WARNING"  # 只在控制台显示WARNING及以上级别的日志
```

### 修改日志文件路径

```yaml
file:
  path: "custom_logs/my_app_{time:YYYY-MM-DD_HH-mm-ss}.log"
```

### 禁用控制台输出

```yaml
console:
  enabled: false
```

## 示例运行

运行提供的示例文件：

```bash
python logger_example.py
```

运行后会在 `logs/` 目录下生成带时间戳的日志文件，并在控制台显示彩色日志输出。

## 集成到现有代码

在现有模块中使用日志系统：

```python
# 在文件顶部导入
from contest_trade.utils.logger_config import get_logger

logger = get_logger()

class YourClass:
    def __init__(self):
        logger.info("初始化 YourClass")
    
    def your_method(self):
        logger.debug("执行 your_method")
        try:
            # 你的代码逻辑
            result = some_operation()
            logger.info(f"操作结果: {result}")
            return result
        except Exception as e:
            logger.exception(f"操作失败: {e}")
            raise
```

## 注意事项

1. 日志目录会自动创建，无需手动创建
2. 每次运行都会生成新的日志文件，便于区分不同运行时段的日志
3. 错误日志会单独记录到专门的错误文件中
4. 日志文件会根据配置自动轮转和清理旧文件
5. 使用 `logger.exception()` 可以自动记录异常堆栈信息

## 高级配置

如需更复杂的日志配置，可以参考 [Loguru 官方文档](https://loguru.readthedocs.io/) 修改 `contest_trade/utils/logger_config.py` 文件中的配置逻辑。