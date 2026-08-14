import json
import os
import jieba
from datetime import datetime
from pathlib import Path
import chromadb
from config import CHROMA_DIR, DATA_DIR, TOP_K, SCORE_THRESHOLD, HYBRID_WEIGHT_VECTOR, HYBRID_WEIGHT_KEYWORD
from app.core.embedding import EmbeddingService


class VectorStore:
    """向量存储：管理ChromaDB的增删查，实现三种检索"""

    def __init__(self, embedding_service: EmbeddingService):
        self.embedding_service = embedding_service
        # 初始化ChromaDB（持久化存储）
        self.client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self.collection = self.client.get_or_create_collection(
            name="rag_documents",
            metadata={"hnsw:space": "cosine"}
        )
        # 文档元数据文件路径
        self.meta_file = DATA_DIR / "documents_meta.json"
        self.documents_meta = self._load_meta()

    def _load_meta(self) -> dict:
        """加载文档元数据"""
        if self.meta_file.exists():
            with open(self.meta_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_meta(self):
        """保存文档元数据到磁盘"""
        with open(self.meta_file, "w", encoding="utf-8") as f:
            json.dump(self.documents_meta, f, ensure_ascii=False, indent=2)
    def add_document(self, doc_id: str, filename: str, chunks: list):
        """将文档的chunks批量写入向量库"""
        ids = []
        embeddings = []
        documents = []
        metadatas = []

        # 提取所有chunk的文本
        texts = [chunk["content"] for chunk in chunks]

        # 批量转向量
        embeddings = self.embedding_service.embed_texts(texts)

        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_chunk_{i}"
            ids.append(chunk_id)
            documents.append(chunk["content"])
            metadatas.append({
                "doc_id": doc_id,
                "filename": filename,
                "chunk_index": i,
                "char_count": chunk["char_count"],
            })

        # 批量写入ChromaDB
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

        # 记录文档元数据
        total_chars = sum(c["char_count"] for c in chunks)
        self.documents_meta[doc_id] = {
            "filename": filename,
            "chunk_count": len(chunks),
            "total_chars": total_chars,
            "upload_time": datetime.now().isoformat(),
        }
        self._save_meta()
    def search(self, query: str, top_k: int = TOP_K, doc_id: str = None) -> list:
        """向量语义检索：把query转向量，在ChromaDB里找最相似的K条"""
        # 1. query转向量
        query_embedding = self.embedding_service.embed_text(query)

        # 2. 构建查询参数
        query_params = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
        }

        # 3. 如果指定了doc_id，只在该文档里搜
        if doc_id:
            query_params["where"] = {"doc_id": doc_id}

        # 4. 执行查询
        results = self.collection.query(**query_params)

        # 5. 整理返回结果
        output = []
        if results and results["ids"] and results["ids"][0]:
            for i, chunk_id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i]
                # ChromaDB返回cosine distance（0=相同，2=相反）
                # 转成similarity：1 - distance/2，范围0~1
                similarity = 1 - distance / 2
                output.append({
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "score": round(similarity, 4),
                    "source": "vector",
                })

        return output
    def keyword_search(self, query: str, top_k: int = TOP_K) -> list:
        """关键词检索：用jieba分词，遍历所有chunk计算匹配分数"""
        # 1. 对query分词
        query_words = set(jieba.cut(query))
        # 去掉停用词（空格、标点）
        query_words = {w for w in query_words if w.strip()}

        if not query_words:
            return []

        # 2. 获取所有文档
        all_docs = self.collection.get()

        # 3. 遍历计算匹配分数
        scored = []
        for i, doc_text in enumerate(all_docs["documents"]):
            # 统计query中有多少词出现在这段文本里
            match_count = sum(1 for w in query_words if w in doc_text)
            if match_count > 0:
                # 分数 = 匹配词数 / 总词数
                score = match_count / len(query_words)
                scored.append({
                    "content": doc_text,
                    "metadata": all_docs["metadatas"][i],
                    "score": round(score, 4),
                    "source": "keyword",
                })

        # 4. 按分数排序，取Top-K
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]
    def hybrid_search(self, query: str, top_k: int = TOP_K,
                  vector_weight: float = HYBRID_WEIGHT_VECTOR,
                  keyword_weight: float = HYBRID_WEIGHT_KEYWORD) -> list:
        """混合检索：向量+关键词两路检索，加权合并"""
        # 1. 两路并行检索
        vector_results = self.search(query, top_k=top_k * 2)
        keyword_results = self.keyword_search(query, top_k=top_k * 2)

        # 2. 用内容前50字符做key去重
        merged = {}

        for item in vector_results:
            key = item["content"][:50]
            merged[key] = {
                "content": item["content"],
                "metadata": item["metadata"],
                "vector_score": item["score"],
                "keyword_score": 0,
            }

        for item in keyword_results:
            key = item["content"][:50]
            if key in merged:
                # 两路都命中，记录关键词分数
                merged[key]["keyword_score"] = item["score"]
            else:
                merged[key] = {
                    "content": item["content"],
                    "metadata": item["metadata"],
                    "vector_score": 0,
                    "keyword_score": item["score"],
                }

        # 3. 加权合并分数
        output = []
        for item in merged.values():
            final_score = (
                item["vector_score"] * vector_weight +
                item["keyword_score"] * keyword_weight
            )
            output.append({
                "content": item["content"],
                "metadata": item["metadata"],
                "score": round(final_score, 4),
                "source": "hybrid",
            })

        # 4. 按最终分数排序
        output.sort(key=lambda x: x["score"], reverse=True)
        return output[:top_k]
    def delete_document(self, doc_id: str):
        """删除指定文档的所有chunk"""
        # 1. 找出该文档所有chunk的id
        results = self.collection.get(where={"doc_id": doc_id})
        if results and results["ids"]:
            self.collection.delete(ids=results["ids"])

        # 2. 删除元数据记录
        if doc_id in self.documents_meta:
            del self.documents_meta[doc_id]
            self._save_meta()
    def list_documents(self) -> list:
        """列出所有已上传的文档"""
        return [
            {"doc_id": doc_id, **meta}
            for doc_id, meta in self.documents_meta.items()
            ]     
    def get_stats(self) -> dict:
        """返回向量库统计信息"""
        total_chunks = self.collection.count()
        return {
            "total_chunks": total_chunks,
            "total_documents": len(self.documents_meta),
            "documents": list(self.documents_meta.keys()),
        }   