from fastapi import APIRouter
from pydantic import BaseModel
from app import main as app_main
from config import TOP_K, SCORE_THRESHOLD, HYBRID_WEIGHT_VECTOR, HYBRID_WEIGHT_KEYWORD

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """聊天请求体"""
    message: str
    mode: str = "cot"
    top_k: int = TOP_K
    threshold: float = SCORE_THRESHOLD
    use_hybrid: bool = False


@router.post("/send")
async def send_message(req: ChatRequest):
    """发送消息：检索→生成回答"""
    # 1. 检索
    if req.use_hybrid:
        results = app_main.store.hybrid_search(req.message, top_k=req.top_k)
    else:
        results = app_main.store.search(req.message, top_k=req.top_k)

    # 2. 按阈值过滤
    filtered = [r for r in results if r["score"] >= req.threshold]

    # 3. 拼接参考资料
    context = "\n\n".join([r["content"] for r in filtered])

    # 4. 调用LLM生成回答
    llm_result = app_main.llm_service.generate(
        query=req.message,
        context=context,
        mode=req.mode,
    )

    return {
        "answer": llm_result["answer"],
        "thinking": llm_result["thinking"],
        "references": [
            {
                "content": r["content"][:100],
                "score": r["score"],
                "source": r["source"],
                "filename": r["metadata"].get("filename", ""),
                "chunk_index": r["metadata"].get("chunk_index", 0),
            }
            for r in filtered
        ],
    }


@router.post("/clear")
async def clear_history():
    """清空对话历史"""
    app_main.llm_service.clear_history()
    return {"message": "对话历史已清空"}


@router.get("/history")
async def get_history():
    """获取对话历史"""
    return app_main.llm_service.get_history()