# Web搜索Agent API文档

## 认证
```http
Authorization: Bearer sk-your-deepseek-api-key
```

## 接口

### 1. 统一聊天接口
**POST** `/chat`

#### 请求头
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| Authorization | string | ✅ | Bearer token格式的DeepSeek API密钥 |
| Content-Type | string | ✅ | application/json |

#### 请求体参数
| 参数名 | 类型 | 必填 | 默认值 | 说明 |
|--------|------|------|--------|------|
| session_id | string | ✅ | - | 会话标识符，用于多轮对话 |
| message | string | ✅ | - | 用户问题 |
| tool_mode | string | ❌ | "auto" | 工具调用模式: never/auto/always |
| max_tool_calls | integer | ❌ | 3 | 最大工具调用次数 |
| stream | boolean | ❌ | true | 是否流式输出 |
| reset_session | boolean | ❌ | false | 是否重置会话历史 |
| include_history | boolean | ❌ | true | 是否返回完整历史 |
| include_tool_details | boolean | ❌ | true | 是否返回工具调用详情 |

#### 请求示例
```json
{
    "session_id": "user_123",
    "message": "今天北京天气怎么样？",
    "tool_mode": "auto",
    "max_tool_calls": 3,
    "stream": false,
    "reset_session": false,
    "include_history": true,
    "include_tool_details": true
}
```

#### 非流式响应（stream: false）
| 参数名 | 类型 | 说明 |
|--------|------|------|
| success | boolean | 请求是否成功 |
| final_answer | string | Agent的最终回答 |
| session_id | string | 会话ID |
| conversation_stats | object | 对话统计信息 |
| session_created | boolean | 是否创建了新会话 |
| conversation_history | array | 对话历史记录（可选） |
| tool_results | array | 工具调用结果（可选） |

#### conversation_stats 对象
| 参数名 | 类型 | 说明 |
|--------|------|------|
| total_turns | integer | 总对话轮数 |
| user_messages | integer | 用户消息数 |
| assistant_messages | integer | 助手消息数 |
| tool_calls_total | integer | 总工具调用次数 |
| tool_calls_current | integer | 当前对话工具调用次数 |

#### conversation_history 数组元素
| 参数名 | 类型 | 说明 |
|--------|------|------|
| role | string | 角色：user/assistant/system/tool |
| content | string | 消息内容 |
| timestamp | string | 时间戳（ISO格式） |
| message_id | string | 消息ID |
| tool_calls | array | 工具调用详情（可选） |

#### tool_calls 数组元素
| 参数名 | 类型 | 说明 |
|--------|------|------|
| tool_name | string | 工具名称 |
| query | string | 搜索查询 |
| result_count | integer | 结果数量 |
| execution_time | float | 执行时间（秒） |

#### 非流式响应示例
```json
{
    "success": true,
    "final_answer": "根据搜索结果，今天北京天气晴朗，温度15-25度，适合外出。",
    "session_id": "user_123",
    "conversation_stats": {
        "total_turns": 3,
        "user_messages": 3,
        "assistant_messages": 3,
        "tool_calls_total": 5,
        "tool_calls_current": 2
    },
    "session_created": false,
    "conversation_history": [
        {
            "role": "user",
            "content": "今天北京天气怎么样？",
            "timestamp": "2024-12-01T10:00:00Z",
            "message_id": "msg_001"
        },
        {
            "role": "assistant",
            "content": "根据搜索结果，今天北京天气晴朗...",
            "timestamp": "2024-12-01T10:00:05Z",
            "message_id": "msg_002",
            "tool_calls": [
                {
                    "tool_name": "tavily_search",
                    "query": "北京今天天气",
                    "result_count": 3,
                    "execution_time": 1.2
                }
            ]
        }
    ],
    "tool_results": [
        {
            "tool_name": "tavily_search",
            "query": "北京今天天气",
            "result_count": 3,
            "execution_time": 1.2
        }
    ]
}
```

#### 流式响应（stream: true）
响应格式为Server-Sent Events (SSE)：

```
data: {"type": "session", "id": "user_123", "created": false}

data: {"type": "text", "data": "根据搜索结果，今天北京天气晴朗，温度15-25度，适合外出。"}

data: {"type": "tool_start", "data": "执行搜索 (第1次)"}

data: {"type": "tool_executing", "data": {"name": "tavily_search", "query": "北京今天天气"}}

data: {"type": "tool_result", "data": {"name": "tavily_search", "result_preview": "北京今天天气晴朗..."}}

data: {"type": "final_start", "data": "基于搜索结果生成回答..."}

data: {"type": "done", "data": {"final_content": "根据搜索结果...", "tool_calls": 2}}
```

#### 流式消息类型
| 类型 | 说明 | 数据格式 |
|------|------|----------|
| session | 会话信息 | `{"id": "session_id", "created": boolean}` |
| text | 文本内容片段 | `{"data": "文本内容"}` |
| tool_start | 开始执行工具 | `{"data": "执行信息"}` |
| tool_executing | 工具执行中 | `{"data": {"name": "工具名", "query": "查询"}}` |
| tool_result | 工具执行结果 | `{"data": {"name": "工具名", "result_preview": "结果预览"}}` |
| tool_error | 工具执行错误 | `{"data": "错误信息"}` |
| tool_limit | 达到工具调用上限 | `{"data": "限制信息"}` |
| final_start | 开始生成最终回答 | `{"data": "提示信息"}` |
| system | 系统消息 | `{"data": "系统信息"}` |
| done | 处理完成 | `{"data": {"final_content": "最终内容", "tool_calls": 数量}}` |
| error | 错误信息 | `{"data": "错误详情"}` |

### 2. 获取会话历史
**GET** `/session/{session_id}/history`

#### 路径参数
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| session_id | string | ✅ | 会话标识符 |

#### 请求示例
```
GET /session/user_123/history
```

#### 响应参数
| 参数名 | 类型 | 说明 |
|--------|------|------|
| success | boolean | 请求是否成功 |
| session_id | string | 会话ID |
| conversation_stats | object | 对话统计信息 |
| conversation_history | array | 对话历史记录 |

#### 响应示例
```json
{
    "success": true,
    "session_id": "user_123",
    "conversation_stats": {
        "total_turns": 6,
        "user_messages": 3,
        "assistant_messages": 3,
        "tool_calls_total": 5,
        "tool_calls_current": 0
    },
    "conversation_history": [
        {
            "role": "user",
            "content": "今天北京天气怎么样？",
            "timestamp": "2024-12-01T10:00:00Z",
            "message_id": "msg_001"
        },
        {
            "role": "assistant",
            "content": "根据搜索结果，今天北京天气晴朗...",
            "timestamp": "2024-12-01T10:00:05Z",
            "message_id": "msg_002",
            "tool_calls": [
                {
                    "tool_name": "tavily_search",
                    "query": "北京今天天气",
                    "result_count": 3,
                    "execution_time": 1.2
                }
            ]
        }
    ]
}
```

### 3. 删除会话
**DELETE** `/session/{session_id}`

#### 路径参数
| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| session_id | string | ✅ | 会话标识符 |

#### 请求示例
```
DELETE /session/user_123
```

#### 响应参数
| 参数名 | 类型 | 说明 |
|--------|------|------|
| success | boolean | 操作是否成功 |
| message | string | 操作结果消息 |
| session_id | string | 会话ID |

#### 响应示例
```json
{
    "success": true,
    "message": "Session deleted",
    "session_id": "user_123"
}
```

## 工具模式说明
- `never`: 不调用搜索工具，仅基于模型训练数据回答
- `auto`: 自动决定是否调用搜索工具（推荐）
- `always`: 强制调用搜索工具，确保基于最新信息回答

## 使用示例

### Python - 非流式
```python
import requests

headers = {
    "Authorization": "Bearer sk-your-api-key",
    "Content-Type": "application/json"
}
data = {
    "session_id": "user_123",
    "message": "今天北京天气怎么样？",
    "tool_mode": "auto",
    "stream": False,
    "include_history": True,
    "include_tool_details": True
}

response = requests.post(
    "http://localhost:8000/chat",
    headers=headers,
    json=data
)

result = response.json()
print(result["final_answer"])
print(f"工具调用次数: {result['conversation_stats']['tool_calls_current']}")
```

### Python - 流式
```python
import requests
import json

headers = {
    "Authorization": "Bearer sk-your-api-key",
    "Content-Type": "application/json"
}
data = {
    "session_id": "user_123",
    "message": "今天北京天气怎么样？",
    "tool_mode": "auto",
    "stream": True
}

response = requests.post(
    "http://localhost:8000/chat",
    headers=headers,
    json=data,
    stream=True
)

for line in response.iter_lines():
    if line.startswith(b'data: '):
        try:
            data = json.loads(line[6:])
            if data['type'] == 'text':
                print(data['data'], end='', flush=True)
            elif data['type'] == 'tool_executing':
                print(f"\n[执行工具]: {data['data']['name']} - {data['data']['query']}")
            elif data['type'] == 'done':
                print(f"\n\n[完成] 工具调用次数: {data['data']['tool_calls']}")
        except json.JSONDecodeError:
            continue
```

### JavaScript - 非流式
```javascript
const response = await fetch('/chat', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer sk-your-api-key',
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        session_id: 'user_123',
        message: '今天北京天气怎么样？',
        tool_mode: 'auto',
        stream: false,
        include_history: true,
        include_tool_details: true
    })
});

const result = await response.json();
console.log(result.final_answer);
console.log('工具调用次数:', result.conversation_stats.tool_calls_current);
```

### JavaScript - 流式
```javascript
const response = await fetch('/chat', {
    method: 'POST',
    headers: {
        'Authorization': 'Bearer sk-your-api-key',
        'Content-Type': 'application/json'
    },
    body: JSON.stringify({
        session_id: 'user_123',
        message: '今天北京天气怎么样？',
        tool_mode: 'auto',
        stream: true
    })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');
    
    for (const line of lines) {
        if (line.startsWith('data: ')) {
            try {
                const data = JSON.parse(line.slice(6));
                if (data.type === 'text') {
                    console.log(data.data);
                } else if (data.type === 'tool_executing') {
                    console.log(`[执行工具]: ${data.data.name} - ${data.data.query}`);
                } else if (data.type === 'done') {
                    console.log(`[完成] 工具调用次数: ${data.data.tool_calls}`);
                }
            } catch (e) {
                continue;
            }
        }
    }
}
```

### cURL - 非流式
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Authorization: Bearer sk-your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "user_123",
    "message": "今天北京天气怎么样？",
    "tool_mode": "auto",
    "stream": false,
    "include_history": true,
    "include_tool_details": true
  }'
```

### cURL - 流式
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Authorization: Bearer sk-your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "user_123",
    "message": "今天北京天气怎么样？",
    "tool_mode": "auto",
    "stream": true
  }' \
  --no-buffer
```

## 错误码
- `200`: 成功
- `400`: 参数错误
- `401`: 认证失败
- `404`: 资源不存在
- `500`: 服务器错误

## 注意事项
1. **API密钥**: 请确保使用有效的DeepSeek API密钥
2. **会话管理**: 会话ID用于多轮对话，建议使用唯一标识符
3. **流式传输**: 流式响应使用Server-Sent Events格式
4. **工具调用**: 工具调用次数受max_tool_calls参数限制
5. **历史记录**: 可通过include_history参数控制是否返回完整历史
6. **工具详情**: 可通过include_tool_details参数控制是否返回工具调用详情