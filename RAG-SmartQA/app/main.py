from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.core.document import DocumentProcessor
from app.core.embedding import EmbeddingService
from app.core.vector_store import VectorStore
from app.core.llm_service import LLMService


# 直接初始化全局实例（不用lifespan）
doc_processor = DocumentProcessor()
embedding_service = EmbeddingService()
store = VectorStore(embedding_service)
llm_service = LLMService()


app = FastAPI(title="RAG-SmartQA")

# 注册路由
from app.routers import document, chat
app.include_router(document.router)
app.include_router(chat.router)

# 静态文件 + HTML模板
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/")
async def index(request: Request):
    """首页"""
    return templates.TemplateResponse(request, "index.html")