"""工具包初始化"""

from .tavily_search import tavily_search
from .function_schema import tools

# 工具函数映射
tool_functions = {
    "tavily_search": tavily_search
}

__all__ = ["tool_functions", "tools"]