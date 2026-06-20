"""配置管理模块 — Config 类。

配置来源优先级：环境变量 > config.json > 代码默认值。
敏感信息（API Key）优先从环境变量 DEEPSEEK_API_KEY 读取。
首次运行时自动生成 config.json。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional


# ============================================================
# 代码内默认配置（最低优先级）
# ============================================================
DEFAULT_CONFIG: dict[str, Any] = {
    "deepseek_api_key": "",
    "deepseek_model": "deepseek-chat",
    "deepseek_base_url": "https://api.deepseek.com/v1",
    "db_path": "./data/articles.db",
    "cookies_path": "./data/cookies.json",
    "browser_data_dir": "./data/browser_data",
    "crawl_interval_min": 2,
    "crawl_interval_max": 3,
    "login_timeout": 300,
    "log_level": "INFO",
    "log_file": "./logs/app.log",
    "output_dir": "./output",
    "theory_pillars": ["刘原理", "三视界法", "太乙预言机", "全息拓扑动力学"],  # 保持兼容，实际以 theory_systems 表为准
    "theory_systems": [
        {
            "name": "复合体理学",
            "description": "基于复合体理学的四重理论基石",
            "pillars": ["刘原理", "三视界法", "太乙预言机", "全息拓扑动力学"],
            "color_code": "#FF6B6B",
        }
    ],
    "active_theory_system": "复合体理学",  # 当前活跃的理论体系
    "tomas_agi_keywords": ["TOMAS-AGI", "TOMAS", "AGI", "通用人工智能"],
    "taiji_os_keywords": ["太极OS", "太极操作系统", "TaijiOS"],
    "multi_models": [],  # [{"name": "deepseek-chat", "api_key": "sk-...", "base_url": "https://api.deepseek.com/v1", "model": "deepseek-chat"}, ...]
}

# 环境变量映射表：config_key -> env_var_name
_ENV_MAPPING: dict[str, str] = {
    "deepseek_api_key": "DEEPSEEK_API_KEY",
    "deepseek_model": "DEEPSEEK_MODEL",
    "deepseek_base_url": "DEEPSEEK_BASE_URL",
    "db_path": "DB_PATH",
    "log_level": "LOG_LEVEL",
    "output_dir": "OUTPUT_DIR",
    "multi_models": "MULTI_MODELS",
}


class Config:
    """配置管理类，支持环境变量覆盖、config.json 持久化。

    使用方式::

        config = Config.load()
        print(config.deepseek_api_key)
        config.set("log_level", "DEBUG")
        config.save()
    """

    def __init__(self, config_path: str = "config.json") -> None:
        """初始化配置，加载默认值。

        Args:
            config_path: config.json 文件路径，默认为项目根目录。
        """
        self._config_path: str = config_path
        # 将默认配置写入实例属性
        for key, value in DEFAULT_CONFIG.items():
            setattr(self, key, value)

    # ----------------------------------------------------------
    # 类方法：加载配置
    # ----------------------------------------------------------
    @classmethod
    def load(cls, config_path: str = "config.json") -> "Config":
        """加载配置，按优先级合并：环境变量 > config.json > 默认值。

        Args:
            config_path: config.json 文件路径。

        Returns:
            Config 实例。
        """
        instance = cls(config_path)

        # 1. 从 config.json 加载（如果存在）
        file_config = cls._load_from_file(config_path)
        if file_config:
            for key, value in file_config.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)

        # 2. 环境变量覆盖（最高优先级）
        for config_key, env_var in _ENV_MAPPING.items():
            env_value = os.environ.get(env_var)
            if env_value is not None:
                # 尝试类型转换
                default_val = getattr(instance, config_key, None)
                converted = cls._convert_type(env_value, default_val)
                setattr(instance, config_key, converted)

        # 3. 如果 config.json 不存在，则生成默认配置文件
        if not Path(config_path).exists():
            instance.save()

        return instance

    # ----------------------------------------------------------
    # 实例方法：保存与访问
    # ----------------------------------------------------------
    def save(self) -> None:
        """将当前配置保存到 config.json。"""
        config_dir = Path(self._config_path).parent
        config_dir.mkdir(parents=True, exist_ok=True)

        data: dict[str, Any] = {}
        for key in DEFAULT_CONFIG:
            data[key] = getattr(self, key, DEFAULT_CONFIG[key])

        with open(self._config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def get(self, key: str) -> Any:
        """获取配置项。

        Args:
            key: 配置键名。

        Returns:
            配置值，不存在时返回 None。
        """
        return getattr(self, key, None)

    def set(self, key: str, value: Any) -> None:
        """设置配置项。

        Args:
            key: 配置键名。
            value: 配置值。
        """
        setattr(self, key, value)
        self.save()

    def to_dict(self) -> dict[str, Any]:
        """将所有配置项转为字典。

        Returns:
            配置字典。
        """
        result: dict[str, Any] = {}
        for key in DEFAULT_CONFIG:
            result[key] = getattr(self, key, DEFAULT_CONFIG[key])
        return result

    # ----------------------------------------------------------
    # 私有方法
    # ----------------------------------------------------------
    @staticmethod
    def _load_from_file(config_path: str) -> Optional[dict[str, Any]]:
        """从 JSON 文件加载配置。

        Args:
            config_path: 配置文件路径。

        Returns:
            配置字典，文件不存在或解析失败时返回 None。
        """
        path = Path(config_path)
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    @staticmethod
    def _convert_type(env_value: str, default_val: Any) -> Any:
        """根据默认值类型转换环境变量字符串。

        Args:
            env_value: 环境变量字符串值。
            default_val: 对应配置项的默认值（用于推断类型）。

        Returns:
            类型转换后的值。
        """
        if isinstance(default_val, bool):
            return env_value.lower() in ("true", "1", "yes")
        if isinstance(default_val, int):
            try:
                return int(env_value)
            except ValueError:
                return default_val
        if isinstance(default_val, float):
            try:
                return float(env_value)
            except ValueError:
                return default_val
        if isinstance(default_val, list):
            try:
                parsed = json.loads(env_value)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                # 尝试逗号分隔的简单字符串列表
                return [v.strip() for v in env_value.split(",") if v.strip()]
            return default_val
        return env_value
