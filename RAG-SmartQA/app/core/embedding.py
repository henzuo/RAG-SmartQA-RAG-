import json
import hashlib
import os
from pathlib import Path
import dashscope
from config import DASHSCOPE_API_KEY, EMBEDDING_MODEL, EMBEDDING_DIMENSION, DATA_DIR


class EmbeddingService:
    """向量嵌入服务：调用DashScope API，带磁盘缓存"""

    def __init__(self):
        # 设置API Key
        dashscope.api_key = DASHSCOPE_API_KEY
        # 缓存文件路径
        self.cache_file = DATA_DIR / "embedding_cache.json"
        # 加载缓存到内存
        self.cache = self._load_cache()

    def _load_cache(self) -> dict:
        """从磁盘加载缓存到内存"""
        if self.cache_file.exists():
            with open(self.cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_cache(self):
        """把内存中的缓存写回磁盘"""
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, ensure_ascii=False)
    def embed_text(self, text: str) -> list:
        """单条文本转向量，先查缓存，没命中再调API"""
        # 1. 算md5作为缓存key
        text_hash = hashlib.md5(text.encode("utf-8")).hexdigest()

        # 2. 查缓存
        if text_hash in self.cache:
            return self.cache[text_hash]

        # 3. 没命中，调DashScope API
        response = dashscope.TextEmbedding.call(
            model=EMBEDDING_MODEL,
            input=text,
            dimension=EMBEDDING_DIMENSION,
        )

        # 4. 检查API是否成功
        if response.status_code != 200:
            raise Exception(f"Embedding API调用失败：{response.message}")

        # 5. 取出向量
        vector = response.output["embeddings"][0]["embedding"]

        # 6. 写入缓存（内存+磁盘）
        self.cache[text_hash] = vector
        self._save_cache()

        return vector
    def embed_texts(self, texts: list) -> list:
        """批量文本转向量，逐条调用（DashScope批量API不稳定）"""
        vectors = []
        for text in texts:
            vectors.append(self.embed_text(text))
        return vectors
    def get_cache_stats(self) -> dict:
        """返回缓存统计信息"""
        cache_size = os.path.getsize(self.cache_file) if self.cache_file.exists() else 0
        return {
            "cache_entries": len(self.cache),
            "cache_size_kb": round(cache_size / 1024, 1),
        }

    def clear_cache(self):
        """清空缓存"""
        self.cache = {}
        if self.cache_file.exists():
            os.remove(self.cache_file)