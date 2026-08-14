import os
from pathlib import Path
from api import api_key
#——路径配置——
#Path(__file__)是当前文件的路径,.parent是它所在的文件夹
#这样写的好处：不管项目放在哪里，路径都能自动适配
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DOCS_DIR = DATA_DIR / "docs"
CHROMA_DIR = DATA_DIR / "chroma"

#创建DATA_DIR,DOCS_DIR,CHROMA_DIR，d.mkdir创建文件，
# parents=True为自动创建多级父文件夹，默认为False。exist_ok=True，若存在不抛出异常，默认False
for d in [DATA_DIR,DOCS_DIR,CHROMA_DIR]:
    d.mkdir(parents=True,exist_ok=True)

# —— API key ——
#环境变量管理key
# DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY","key")
DASHSCOPE_API_KEY = api_key
# —— 模型选择 ——
EMBEDDING_MODEL  = "text-embedding-v3"
LLM_MODEL= "qwen-turbo"
EMBEDDING_DIMENSION = 1024

# —— 文档限制 ——
MAX_FILE_SIZE_MB = 20
ALLOWED_EXTENSIONS = {".txt",".pdf",".docx"}

# ── 分段策略 ──
#1.固定长度分段,2.语义分段,3.Q&A问答对分段
CHUNK_STRATEGIES = {
    "fixed":{
        "name":"固定长度分段",
        "chunk_size":500,
        "chunk_overlap":50,
    },
    "sentence":{
            "name":"语义分段",
            "separators":["\n\n", "\n", "。", "！", "？"],
            "chunk_size":500,
            "chunk_overlap":50,
    },
    "qa":{
            "name":"Q&A问答对分段",
            "separators": ["\n\n"],
            "chunk_size":500,
            "chunk_overlap":50,
    },
}
#默认策略
DEFAULT_STRATEGY = "sentence"

# ── 检索参数 ──
TOP_K = 3
SCORE_THRESHOLD = 0.0
HYBRID_WEIGHT_VECTOR = 0.7
HYBRID_WEIGHT_KEYWORD = 0.3

# ── 对话参数 ──
MAX_HISTORY_TURNS = 10

# ── 系统提示词 ──
# CoT：让模型先分析问题再回答（思维链）
SYSTEM_PROMPT_COT = """你是一个专业的知识库问答助手。请根据以下参考资料回答用户问题。

思考过程要求：
1. 先分析用户问题，明确问题类型和关键信息
2. 检查参考资料中与问题相关的信息
3. 如果资料充足，组织答案并回答
4. 如果资料不足，明确告知用户哪些信息缺失
5. 回答要简洁准确，不要编造内容

参考资料：
{context}


注意：如果参考资料为空或与问题无关，请礼貌告知用户"当前知识库中没有相关信息"。"""
# ReAct智能体提示词：支持模型自主多次检索知识库
#ReAct：让模型循环执行"思考→搜索→观察→再思考"
SYSTEM_PROMPT_REACT = """你是一个专业的知识库问答助手，可以使用工具来获取信息。

你可以使用以下工具：
- search(query): 在知识库中搜索相关信息
- answer(text): 给出最终答案

思考过程格式：
Thought: 分析用户问题
Action: search("搜索关键词")
Observation: 搜索结果
Thought: 分析搜索结果是否充分
Action: answer("最终答案")

可用参考资料：
{context}

注意：搜索结果为空时，礼貌告知用户没有相关信息。最终答案要简洁准确。"""
