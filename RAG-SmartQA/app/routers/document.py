import os
import shutil
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from app import main as app_main
from config import DOCS_DIR

router = APIRouter(prefix="/api/docs", tags=["documents"])


@router.post("/upload")
async def upload_document(file: UploadFile = File(...), strategy: str = Form("sentence")):
    """上传文档：验证→保存→解析→分段→写入向量库"""
    # 1. 验证文件
    try:
        app_main.doc_processor.validate_file(file.filename, file.size)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 2. 保存到data/docs/
    filepath = DOCS_DIR / file.filename
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # 3. 解析为纯文本
    text = app_main.doc_processor.parse_file(str(filepath))

    # 4. 分段
    chunks = app_main.doc_processor.chunk_text(text, strategy)

    # 5. 生成doc_id并写入向量库
    doc_id = app_main.doc_processor.generate_doc_id(file.filename, text)
    app_main.store.add_document(doc_id, file.filename, chunks)

    return {
        "doc_id": doc_id,
        "filename": file.filename,
        "chunk_count": len(chunks),
        "total_chars": len(text),
        "strategy": strategy,
    }


@router.get("/list")
async def list_documents():
    """列出所有已上传的文档"""
    return app_main.store.list_documents()


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """删除文档"""
    app_main.store.delete_document(doc_id)
    return {"message": f"文档 {doc_id} 已删除"}


@router.post("/preview-chunks")
async def preview_chunks(file: UploadFile = File(...), strategy: str = Form("sentence")):
    """预览分段结果（不入库）"""
    try:
        app_main.doc_processor.validate_file(file.filename, file.size)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 读取文件内容
    content = await file.read()
    # 写入临时文件再解析
    filepath = DOCS_DIR / f"_preview_{file.filename}"
    with open(filepath, "wb") as f:
        f.write(content)

    try:
        text = app_main.doc_processor.parse_file(str(filepath))
        chunks = app_main.doc_processor.chunk_text(text, strategy)
    finally:
        # 清理临时文件
        os.remove(filepath)

    return {
        "filename": file.filename,
        "chunk_count": len(chunks),
        "chunks": chunks,
    }


@router.get("/strategies")
async def get_strategies():
    """获取可用的分段策略列表"""
    return app_main.doc_processor.get_available_strategies()


@router.get("/stats")
async def get_stats():
    """获取向量库统计信息"""
    return app_main.store.get_stats()