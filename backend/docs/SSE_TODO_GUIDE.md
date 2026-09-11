# SSE 事件接收指南 - 如何获取 todo JSON 数据

## 问题说明

如果你在 SSE 流中找不到 todo 的 JSON 数据，这是因为：
1. SSE 流包含两种事件类型：`answer` 和 `structured`
2. `answer` 事件：流式文本（用于显示对话框）
3. `structured` 事件：完整的 JSON 数据（包含 todos、user_info、intermediaries 等）

## SSE 事件格式

### 1. Answer 事件（流式文本）
```
data: {"type": "answer", "content": {"answer": "你好，我是 RootLink 寻根向导"}}
```

### 2. Structured 事件（包含 todos）
```
data: {
  "type": "structured",
  "content": {
    "message": "您好！我是 RootLink 寻根向导，很高兴能帮助您...",
    "user_info": {
      "surname": "王",
      "location": "河南焦作",
      "dialect": "未提供",
      "migration_info": "未提供"
    },
    "analysis": "根据字辈和移民信息判断...",
    "intermediaries": [...],
    "todos": [
      { "id": "collect_surname", "text": "收集家族姓氏", "done": true },
      { "id": "collect_origin", "text": "收集祖籍具体地址", "done": false }
    ]
  }
}
```

## 前端集成代码

### 方法 1：使用原生 EventSource（推荐）

```javascript
// 创建 SSE 连接
const eventSource = new EventSource('http://localhost:8000/api/chat/sse?user_id=123&message=你好');

// 全局状态
const todosMap = new Map();

// 监听消息事件
eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    // 判断事件类型
    if (data.type === 'answer') {
        // 处理流式文本
        const answerText = data.content.answer;
        console.log('收到文本:', answerText);
        // 更新对话框...
        
    } else if (data.type === 'structured') {
        // 🎯 这里是你关心的核心逻辑！
        // 处理结构化数据（包含 todos）
        const structuredData = data.content;
        
        // 获取 todos 数组
        const todos = structuredData.todos || [];
        console.log('收到 todos:', todos);
        
        // 更新 todos 状态
        updateTodos(todos);
    }
};

// 监听错误
eventSource.onerror = (error) => {
    console.error('SSE 错误:', error);
    eventSource.close();
};

// 监听打开
eventSource.onopen = () => {
    console.log('SSE 连接已建立');
};

// 更新 todos 的函数
function updateTodos(todos) {
    todos.forEach(todo => {
        // 检查是否已存在
        if (!todosMap.has(todo.id)) {
            // 新增 todo
            createTodoElement(todo);
        } else {
            // 更新现有 todo
            const existingElement = document.getElementById(`todo-${todo.id}`);
            if (existingElement) {
                const checkbox = existingElement.querySelector('.todo-checkbox');
                const text = existingElement.querySelector('.todo-text');
                
                // 更新 done 状态
                checkbox.checked = todo.done;
                if (todo.done) {
                    existingElement.classList.add('completed');
                } else {
                    existingElement.classList.remove('completed');
                }
                
                // 更新文本（如果有变化）
                if (text.textContent !== todo.text) {
                    text.textContent = todo.text;
                }
            }
        }
        
        // 更新状态 Map
        todosMap.set(todo.id, todo);
    });
}

// 创建 todo 元素
function createTodoElement(todo) {
    const div = document.createElement('div');
    div.className = 'todo-item';
    div.id = `todo-${todo.id}`;
    
    if (todo.done) {
        div.classList.add('completed');
    }
    
    div.innerHTML = `
        <input type="checkbox" ${todo.done ? 'checked' : ''}>
        <span>${todo.text}</span>
    `;
    
    document.getElementById('todos-container').appendChild(div);
}
```

### 方法 2：使用 Fetch + ReadableStream（更灵活）

```javascript
async function fetchWithSSE(message) {
    const response = await fetch(`http://localhost:8000/api/chat/sse?user_id=123&message=${encodeURIComponent(message)}`);
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    const todosMap = new Map();
    
    while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;
        
        // 解码数据
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n\n');
        
        for (const line of lines) {
            if (line.startsWith('data: ')) {
                const data = JSON.parse(line.substring(6));
                
                if (data.type === 'answer') {
                    // 处理流式文本
                    console.log('收到文本:', data.content.answer);
                    
                } else if (data.type === 'structured') {
                    // 🎯 这里是 todos！
                    const todos = data.content.todos || [];
                    console.log('收到 todos:', todos);
                    
                    // 更新 todos
                    updateTodos(todos);
                }
            }
        }
    }
}

// 调用
fetchWithSSE('你好，我想寻根');
```

## 调试技巧

### 1. 在浏览器控制台查看 SSE 事件

打开浏览器开发者工具（F12），切换到 Network 标签，找到 SSE 请求（类型为 `eventsource`），点击查看消息。

### 2. 添加调试日志

```javascript
eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    console.log('=== SSE 事件 ===');
    console.log('类型:', data.type);
    console.log('内容:', data.content);
    console.log('================');
    
    if (data.type === 'structured' && data.content.todos) {
        console.log('🎯 找到 todos:', data.content.todos);
    }
};
```

### 3. 使用 curl 测试

```bash
curl -N "http://localhost:8000/api/chat/sse?user_id=123&message=你好"
```

你会看到类似这样的输出：
```
data: {"type":"answer","content":{"answer":"你好"}}
data: {"type":"answer","content":{"answer":"，我是"}}
data: {"type":"answer","content":{"answer":" RootLink"}}
data: {"type":"structured","content":{"message":"你好，我是 RootLink 寻根向导...","todos":[{"id":"collect_surname","text":"收集家族姓氏","done":true}]}}
```

## 常见问题

### Q1: 为什么我只看到 answer 事件，看不到 structured 事件？

**A**: `structured` 事件会在流式文本发送完毕后才会发送。请确保：
1. 等待 SSE 连接完全关闭
2. 监听 `eventSource.onerror` 或 `eventSource.onclose` 事件

### Q2: todos 数组是空的怎么办？

**A**: 检查以下几点：
1. 确认后端正确配置了 System Prompt
2. 确认 Agent 返回的 JSON 包含 `todos` 字段
3. 在浏览器控制台查看完整的 structured 事件内容

### Q3: 如何处理重复的 todos？

**A**: 使用 Map 数据结构，以 todo 的 `id` 为 key：
```javascript
const todosMap = new Map();

todos.forEach(todo => {
    if (!todosMap.has(todo.id)) {
        // 新增
        createTodoElement(todo);
    } else {
        // 更新
        updateTodoElement(todo);
    }
    todosMap.set(todo.id, todo);
});
```

### Q4: 如何实现 todos 的跨轮对话累计？

**A**: 保持 `todosMap` 在全局作用域，不要每次发送消息时清空：
```javascript
// ❌ 错误：每次发送消息时清空
function sendMessage() {
    todosMap.clear();  // 不要这样做！
    // ...
}

// ✅ 正确：保持全局状态
const todosMap = new Map();  // 全局变量

function sendMessage() {
    // 发送消息，但不清空 todosMap
    // ...
}
```

## 完整示例

查看 `docs/frontend_integration_example.html` 获取完整的前端集成示例，包括：
- SSE 连接管理
- 流式文本渲染
- Todos 状态管理
- 用户信息展示
- 中间人推荐展示
- 调试信息面板

## 后端修复内容

为了确保 `structured` 事件正确发送，我们修复了以下代码：

### src/utils/sse_handler.py
1. 在 `stream_agent_response_sync` 函数末尾添加了 `structured` 事件发送逻辑
2. 修复了 `format_sse_event` 函数，确保事件数据包含 `type` 字段

### 修复前的代码
```python
# ❌ 缺少 structured 事件发送
for chunk in agent.stream({"messages": messages}, config=config):
    # ... 处理 answer 事件
    # 缺少 structured 事件！
```

### 修复后的代码
```python
# ✅ 正确发送 structured 事件
for chunk in agent.stream({"messages": messages}, config=config):
    # ... 处理 answer 事件

# 发送结构化事件
structured_data = handler.parse_structured_data(full_response)
sanitized_data = handler.sanitize_structured_data(structured_data)
yield handler.format_sse_event("structured", sanitized_data)
```

## 总结

1. **todo 的 JSON 数据在 `structured` 事件中**
2. **`structured` 事件会在流式文本发送完毕后发送**
3. **使用 `data.type` 判断事件类型**
4. **使用 Map 管理 todos 状态，实现跨轮对话累计**
5. **确保前端监听 SSE 的所有事件，包括错误和关闭事件**

如果你还有问题，请查看 `docs/frontend_integration_example.html` 中的完整示例代码！
# 当前接口说明

当前生产接口仅使用 `POST /api/chat/sse`，JSON 请求体为
`{"user_id":"...","message":"...","lang":"zh"}`。本文后面的
`EventSource + GET` 内容是历史说明，请以 `frontend_sse_example.html`
和实际前端 `public/agent.html` 的 `fetch + POST` 实现为准。
