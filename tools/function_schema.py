"""工具Function Schema定义"""

tools = [{
    "type": "function",
    "function": {
        "name": "tavily_search",
        "description": "搜索互联网最新信息，获取实时数据、新闻或当前事件",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词或问题"
                },
                "max_results": {
                    "type": "integer",
                    "description": "返回结果数量(1-10)",
                    "default": 3
                },
                "time_range": {
                    "type": "string",
                    "enum": ["day", "week", "month", "year"],
                    "description": "时间范围过滤"
                },
                "include_answer": {
                    "type": "string",
                    "enum": ["basic", "advanced"],
                    "description": "AI答案详细程度",
                    "default": "advanced"
                },
                "include_favicon": {
                    "type": "boolean",
                    "description": "是否包含网站图标",
                    "default": False
                }
            },
            "required": ["query"]
        }
    }
}]