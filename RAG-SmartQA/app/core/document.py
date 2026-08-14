import os
import hashlib
from langchain_text_splitters import CharacterTextSplitter, RecursiveCharacterTextSplitter
from config import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB, CHUNK_STRATEGIES


class DocumentProcessor:
    """文档处理器：负责文件解析和文本分段"""

    def validate_file(self,file_name:str,file_size:int) -> bool:
        """验证文件格式和大小是否合法"""
        # 1. 检查后缀
        ext = os.path.splitext(file_name)[1]
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"不支持{ext}格式，仅支持{ALLOWED_EXTENSIONS}")

        #2. 检查大小（config里是MB，file_size是字节，要换算）
        max_bytes = MAX_FILE_SIZE_MB * 1024 *1024
        if max_bytes < file_size:
            raise ValueError(f"文件过大：{file_size / 1024 / 1024:.1f}MB，上限 {MAX_FILE_SIZE_MB}MB")
        return True
    def parse_file(self,filepath:str) -> str:
        """根据文件后缀分发到不同解析器，返回纯文本"""
        ext = os.path.splitext(filepath)[1].lower()

        if ext == ".txt":
            return self._parse_txt(filepath)
        elif ext == ".pdf":
            return self._parse_pdf(filepath)
        elif ext == ".docx":
            return self._parse_docx(filepath)
        else:
            raise ValueError(f"不支持的文件格式：{ext}")
        
    def _parse_txt(self, filepath: str) -> str:
        """解析txt文件，自动检测编码"""
        for encoding in ["utf-8", "gbk", "latin-1"]:
            try:
                with open(filepath, "r", encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        raise ValueError(f"无法识别文件编码：{filepath}")
    def _parse_pdf(self,filepath:str) -> str:
         """用pypdf逐页提取文本"""
         from pypdf import PdfReader
         reader = PdfReader(filepath)
         text=""
         for page in reader.pages:
             text+= page.extract_text() or ""
         return text.strip()
    def _parse_docx(self, filepath: str) -> str:
        """用python-docx逐段提取文本"""
        from docx import Document
        doc = Document(filepath)
        text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
        return text
    def chunk_text(self, text: str, strategy: str = "sentence") -> list:
        """根据策略切分文本，返回chunk列表"""
        config = CHUNK_STRATEGIES.get(strategy)
        if not config:
            raise ValueError(f"不支持的分段策略：{strategy}")

        chunk_size = config["chunk_size"]
        chunk_overlap = config["chunk_overlap"]

        if strategy == "fixed":
            splitter = CharacterTextSplitter(
                separator="\n",
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
        elif strategy == "sentence":
            splitter = RecursiveCharacterTextSplitter(
                separators=config["separators"],
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
        elif strategy == "qa":
            splitter = CharacterTextSplitter(
                separator="\n\n",
                chunk_size=chunk_size,
                chunk_overlap=0,  # QA模式不需要重叠，问答对之间是独立的
            )

        chunks = splitter.split_text(text)

        # 包装成带元信息的列表返回
        return [
            {"content": chunk, "index": i, "char_count": len(chunk)}
            for i, chunk in enumerate(chunks)
        ]
    def generate_doc_id(self, filename: str, content: str) -> str:
        """用md5哈希生成文档唯一ID"""
        raw = filename + content
        return hashlib.md5(raw.encode("utf-8")).hexdigest()
    def get_available_strategies(self) -> list:
        """返回所有可用的分段策略"""
        return [
            {"key": key, "name": config["name"]}
            for key, config in CHUNK_STRATEGIES.items()
        ]