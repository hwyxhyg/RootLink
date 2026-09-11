# SSE 流式输出集成指南

## 概述

寻根问祖助手 Agent 现已支持 SSE（Server-Sent Events）流式输出，可以将响应分为两种事件类型：

1. **answer 事件**：流式文本展示（支持打字机效果）
2. **structured 事件**：结构化数据（便于前端渲染）

## SSE 事件格式

### Answer 事件（流式文本）

```
data: {"type":"answer","content":{"answer":"部分文本..."}}

```

### Structured 事件（结构化数据）

```
data: {"type":"structured","content":{...}}

```

每个事件以 `\n\n` 结尾。

## Structured 事件内容格式

```json
{
  "user_info": {
    "surname": "王",
    "location": "河南焦作",
    "dialect": null,
    "migration_info": "山西洪洞大槐树移民"
  },
  "analysis": "根据您提供的字辈和移民信息分析，您的家族最可能来自河南焦作地区，置信度为中等...",
  "intermediaries": [
    {
      "id": "INT001",
      "name": "王建国",
      "location": "河南省洛阳市",
      "match_score": 100,
      "notes": "姓氏匹配（王）。熟悉河南地区王氏分布。深入研究山西洪洞移民历史。",
      "contact_info": "wangjianguo@example.com",
      "success_cases": [
        {
          "description": "帮助王先生找到失散的洛阳支系",
          "year": 2023
        }
      ]
    }
  ],
  "todos": ["联系王建国先生", "准备家族信息便于沟通", "关注后续进展"],
  "message": "为您推荐一位非常合适的寻根向导——王建国先生..."
}
```

## 字段说明

| 字段 | 类型 | 说明 |
|-----|------|------|
| user_info.surname | string \| null | 用户姓氏 |
| user_info.location | string \| null | 祖籍地 |
| user_info.dialect | string \| null | 方言类型 |
| user_info.migration_info | string \| null | 迁移时间和背景 |
| analysis | string | 亲缘地分析（纯文本） |
| intermediaries | Array | 中间人推荐列表 |
| intermediaries[].id | string | 中间人ID |
| intermediaries[].name | string | 姓名 |
| intermediaries[].location | string | 所在地 |
| intermediaries[].match_score | number | 匹配度（0-100） |
| intermediaries[].notes | string | 备注（包含匹配理由） |
| intermediaries[].contact_info | string | 联系方式 |
| intermediaries[].success_cases | Array | 成功案例 |
| intermediaries[].success_cases[].description | string | 案例描述 |
| intermediaries[].success_cases[].year | number | 年份 |
| todos | Array | 行动建议列表 |
| message | string | 给用户的对话内容 |

## 后端集成

### FastAPI 示例

```python
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from agents.agent import build_agent
from utils.sse_handler import stream_agent_response_sync
from langchain_core.messages import HumanMessage

app = FastAPI()
agent = build_agent()

class ChatRequest(BaseModel):
    user_id: str
    message: str

@app.post("/api/chat/sse")
async def chat_with_sse(req: ChatRequest):
    def generate_sse_events():
        config = {"configurable": {"thread_id": req.user_id}}
        
        for sse_event in stream_agent_response_sync(
            agent=agent,
            messages=[HumanMessage(content=req.message)],
            config=config
        ):
            yield sse_event
    
    return StreamingResponse(
        generate_sse_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
```

### Flask 示例

```python
from flask import Flask, Response, request, jsonify
from agents.agent import build_agent
from utils.sse_handler import stream_agent_response_sync
from langchain_core.messages import HumanMessage
import json

app = Flask(__name__)
agent = build_agent()

@app.route('/api/chat/sse', methods=['POST'])
def chat_with_sse():
    data = request.json
    user_id = data['user_id']
    message = data['message']
    
    def generate():
        config = {"configurable": {"thread_id": user_id}}
        
        for sse_event in stream_agent_response_sync(
            agent=agent,
            messages=[HumanMessage(content=message)],
            config=config
        ):
            yield sse_event
    
    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        }
    )
```

## 前端集成

### JavaScript 示例

```javascript
async function sendMessage(userId, message) {
  const response = await fetch('/api/chat/sse', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      user_id: userId,
      message: message
    })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let fullText = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    while (true) {
      const eventEndIndex = buffer.indexOf('\n\n');
      if (eventEndIndex === -1) break;

      const eventData = buffer.slice(0, eventEndIndex);
      buffer = buffer.slice(eventEndIndex + 2);

      if (eventData.startsWith('data: ')) {
        const jsonStr = eventData.slice(6);
        const event = JSON.parse(jsonStr);

        if (event.type === 'answer') {
          // 处理流式文本
          fullText += event.content.answer;
          console.log('流式文本:', fullText);
        } else if (event.type === 'structured') {
          // 处理结构化数据
          console.log('结构化数据:', event.content);
          // 渲染 UI
          renderStructuredData(event.content);
        }
      }
    }
  }
}

function renderStructuredData(data) {
  // 渲染用户信息
  if (data.user_info.surname) {
    document.getElementById('surname').textContent = data.user_info.surname;
  }

  // 渲染分析
  if (data.analysis) {
    document.getElementById('analysis').textContent = data.analysis;
  }

  // 渲染中间人推荐
  data.intermediaries.forEach(inter => {
    const card = createIntermediaryCard(inter);
    document.getElementById('intermediaries').appendChild(card);
  });

  // 渲染行动建议
  data.todos.forEach(todo => {
    const li = document.createElement('li');
    li.textContent = todo;
    document.getElementById('todos').appendChild(li);
  });
}
```

### Vue 示例

```vue
<template>
  <div>
    <textarea v-model="message" placeholder="请输入问题..."></textarea>
    <button @click="sendMessage" :disabled="loading">发送</button>

    <div class="chat">
      <div v-if="currentText" class="message">{{ currentText }}</div>

      <div v-if="structuredData" class="structured-data">
        <div v-if="structuredData.user_info.surname" class="user-info">
          <h4>📋 您的寻根信息</h4>
          <p>姓氏: {{ structuredData.user_info.surname }}</p>
          <p>祖籍地: {{ structuredData.user_info.location }}</p>
        </div>

        <div v-if="structuredData.analysis" class="analysis">
          <h4>🎯 亲缘地分析</h4>
          <p>{{ structuredData.analysis }}</p>
        </div>

        <div v-if="structuredData.intermediaries.length" class="intermediaries">
          <h4>👥 推荐的寻根向导</h4>
          <div v-for="inter in structuredData.intermediaries" :key="inter.id" class="card">
            <h5>{{ inter.name }} (匹配度: {{ inter.match_score }}/100)</h5>
            <p>所在地: {{ inter.location }}</p>
            <p>联系方式: {{ inter.contact_info }}</p>
          </div>
        </div>

        <div v-if="structuredData.todos.length" class="todos">
          <h4>📝 下一步建议</h4>
          <ul>
            <li v-for="todo in structuredData.todos" :key="todo">{{ todo }}</li>
          </ul>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const message = ref('');
const currentText = ref('');
const structuredData = ref(null);
const loading = ref(false);

async function sendMessage() {
  if (!message.value) return;

  loading.value = true;
  currentText.value = '';
  structuredData.value = null;

  try {
    const response = await fetch('/api/chat/sse', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: 'user_123',
        message: message.value
      })
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      while (true) {
        const eventEndIndex = buffer.indexOf('\n\n');
        if (eventEndIndex === -1) break;

        const eventData = buffer.slice(0, eventEndIndex);
        buffer = buffer.slice(eventEndIndex + 2);

        if (eventData.startsWith('data: ')) {
          const event = JSON.parse(eventData.slice(6));

          if (event.type === 'answer') {
            currentText.value += event.content.answer;
          } else if (event.type === 'structured') {
            structuredData.value = event.content;
          }
        }
      }
    }
  } finally {
    loading.value = false;
    message.value = '';
  }
}
</script>
```

## 完整示例

查看 `docs/frontend_sse_example.html` 获取完整的前端示例代码。

## 注意事项

1. **SSE 连接保活**：确保服务器端正确处理连接保活
2. **错误处理**：添加适当的错误处理和重连机制
3. **XSS 防护**：后端已经对文本进行了净化，但前端仍需谨慎处理
4. **编码**：确保使用 UTF-8 编码
5. **缓冲**：某些服务器（如 Nginx）可能会缓冲 SSE 事件，需要配置 `X-Accel-Buffering: no`

## 备用方案

如果无法使用 SSE，可以使用普通 JSON 接口：

```python
@app.post("/api/chat/json")
async def chat_with_json(req: ChatRequest):
    config = {"configurable": {"thread_id": req.user_id}}
    response = agent.invoke(
        {"messages": [HumanMessage(content=req.message)]},
        config=config
    )
    # 返回结构化 JSON
    return parse_structured_data(response)
```
