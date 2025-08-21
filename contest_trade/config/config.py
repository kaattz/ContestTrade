"""
config module for trade agent
"""
from pathlib import Path
import yaml
import os

PROJECT_ROOT = Path(__file__).parent.parent.resolve()


class ProjectConfig:

    def __init__(self, config_path: str = None) -> None:
        if config_path:
            yaml_path = Path(config_path)
        else:
            # 检查环境变量是否指定了配置文件
            env_config = os.environ.get('CONTEST_TRADE_CONFIG')
            if env_config:
                yaml_path = Path(env_config)
            else:
                yaml_path = PROJECT_ROOT.parent / "config.yaml"

        with open(yaml_path, "r", encoding="utf-8") as fr:
            config = yaml.load(fr, Loader=yaml.FullLoader)
        for k in config:
            setattr(self, k, config[k])

    def reload_config(self, config_path: str = None):
        """重新加载配置"""
        self.__init__(config_path)

cfg = ProjectConfig()

if __name__ == "__main__":
    print(cfg.data_agents_config)
    print(cfg.research_agent_config)
    print(cfg.llm)
    print(cfg.llm_thinking)
    print(cfg.vlm)