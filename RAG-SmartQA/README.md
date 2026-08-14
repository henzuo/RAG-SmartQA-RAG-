# RAG-SmartQA 全链路 RAG 智能问答系统

一个不依赖 Dify 等平台，用 Python 从零实现的完整 RAG（检索增强生成）智能问答系统。

## 技术栈

- **后端框架：** FastAPI
- **向量数据库：** ChromaDB
- **LLM：** 通义千问（DashScope API）
- **Embedding：** DashScope text-embedding-v3（1024维）
- **文本处理：** LangChain Text Splitters
- **中文分词：** jieba
- **部署：** Docker

## 核心功能

- **文档上传：** 支持 txt / pdf / docx 三种格式，自动检测编码
- **三种分段策略：** 固定长度、语义分段、Q&A 问答对
- **三种检索方式：** 向量语义检索、关键词检索（jieba分词）、混合检索（加权合并）
- **两种 Agent 模式：** CoT 思维链、ReAct 推理-行动
- **多轮对话记忆：** 自动维护上下文
- **检索调试面板：** 可视化命中段落和相似度分数

## 快速启动

### 本地运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置API Key
# 在项目根目录创建 api.py，写入：
# api_key = "your-dashscope-api-key"

# 3. 启动服务
python run.py
# 访问 http://localhost:8000
```

### Docker 部署

```bash
docker build -t rag-smartqa .
docker run -p 8000:8000 rag-smartqa
```

## 项目结构

```
RAG-SmartQA/
├── config.py                ← 配置中心
├── run.py                   ← 启动入口
├── Dockerfile               ← Docker 配置
├── api.py                   ← API Key（不提交到Git）
├── app/
│   ├── main.py              ← FastAPI 初始化 + 路由
│   ├── core/                ← 核心模块
│   │   ├── document.py      ← 文档解析 + 智能分段
│   │   ├── embedding.py     ← 向量嵌入 + 磁盘缓存
│   │   ├── vector_store.py  ← ChromaDB + 三种检索
│   │   └── llm_service.py   ← CoT + ReAct Agent
│   ├── routers/             ← API 接口
│   │   ├── document.py      ← 文档管理
│   │   └── chat.py          ← 聊天问答
│   ├── static/              ← 前端资源
│   └── templates/           ← HTML 模板
└── data/                    ← 数据目录
    ├── docs/                ← 上传的文档
    └── chroma/              ← ChromaDB 持久化
```

## API 接口

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | /api/docs/upload | 上传文档 |
| GET | /api/docs/list | 文档列表 |
| DELETE | /api/docs/{doc_id} | 删除文档 |
| GET | /api/docs/strategies | 分段策略列表 |
| GET | /api/docs/stats | 向量库统计 |
| POST | /api/chat/send | 发送消息 |
| POST | /api/chat/clear | 清空对话 |
| GET | /api/chat/history | 对话历史 |

## 分段策略说明

- **固定长度（fixed）：** 按换行符切分，每段最多 500 字符，重叠 50 字符
- **语义分段（sentence）：** 按标点符号自然断句（段落→行→句号→感叹号→问号），保持语义完整
- **Q&A 问答对（qa）：** 按双换行切分，保证每对问答完整不被切断

## CoT vs ReAct

- **CoT（思维链）：** 一次性让模型先分析问题、检查资料、再回答，适合简单问答
- **ReAct（推理-行动）：** 循环执行 Thought → Action → Observation，最多 3 步，适合复杂多步推理

## License

MIT
