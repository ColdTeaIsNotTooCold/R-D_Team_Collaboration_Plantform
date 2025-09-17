"""
嵌入生成模块
提供文本嵌入生成和预处理功能
"""
import logging
from typing import List, Dict, Any, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
import re
from ..core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """文本嵌入生成器"""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.model = None
        self._initialized = False

    async def initialize(self) -> bool:
        """初始化嵌入模型"""
        try:
            logger.info(f"加载嵌入模型: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            self._initialized = True
            logger.info("嵌入模型初始化成功")
            return True

        except Exception as e:
            logger.error(f"嵌入模型初始化失败: {str(e)}")
            return False

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized and self.model is not None

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """生成文本嵌入向量"""
        if not self.is_initialized():
            logger.error("嵌入模型未初始化")
            return []

        try:
            # 预处理文本
            processed_texts = [self._preprocess_text(text) for text in texts]

            # 生成嵌入
            embeddings = self.model.encode(processed_texts, convert_to_numpy=True)

            # 转换为列表格式
            embedding_list = embeddings.tolist()

            logger.info(f"成功生成 {len(embedding_list)} 个嵌入向量")
            return embedding_list

        except Exception as e:
            logger.error(f"生成嵌入失败: {str(e)}")
            return []

    async def generate_embedding(self, text: str) -> List[float]:
        """生成单个文本的嵌入向量"""
        embeddings = await self.generate_embeddings([text])
        return embeddings[0] if embeddings else []

    def _preprocess_text(self, text: str) -> str:
        """预处理文本"""
        if not text:
            return ""

        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text.strip())

        # 移除特殊字符（保留基本标点）
        text = re.sub(r'[^\w\s\.\,\!\?\;\:\-\(\)\[\]\{\}\"\'\/\@\#\$\%\^\&\*\+\=\~\`]', '', text)

        return text

    async def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """计算两个嵌入向量的余弦相似度"""
        try:
            if not embedding1 or not embedding2:
                return 0.0

            # 转换为numpy数组
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)

            # 计算余弦相似度
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)
            return float(similarity)

        except Exception as e:
            logger.error(f"计算相似度失败: {str(e)}")
            return 0.0

    async def find_most_similar(
        self,
        query_embedding: List[float],
        candidate_embeddings: List[List[float]],
        top_k: int = 5
    ) -> List[Tuple[int, float]]:
        """找到最相似的候选嵌入"""
        try:
            if not query_embedding or not candidate_embeddings:
                return []

            similarities = []
            for i, candidate_embedding in enumerate(candidate_embeddings):
                similarity = await self.calculate_similarity(query_embedding, candidate_embedding)
                similarities.append((i, similarity))

            # 按相似度排序
            similarities.sort(key=lambda x: x[1], reverse=True)

            # 返回前top_k个结果
            return similarities[:top_k]

        except Exception as e:
            logger.error(f"查找相似嵌入失败: {str(e)}")
            return []

    async def batch_generate_embeddings(
        self,
        texts: List[str],
        batch_size: int = 32
    ) -> List[List[float]]:
        """批量生成嵌入向量"""
        if not self.is_initialized():
            logger.error("嵌入模型未初始化")
            return []

        try:
            all_embeddings = []

            # 分批处理
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_embeddings = await self.generate_embeddings(batch_texts)
                all_embeddings.extend(batch_embeddings)

            logger.info(f"批量生成 {len(all_embeddings)} 个嵌入向量")
            return all_embeddings

        except Exception as e:
            logger.error(f"批量生成嵌入失败: {str(e)}")
            return []

    async def get_embedding_dimension(self) -> int:
        """获取嵌入向量的维度"""
        if not self.is_initialized():
            return 0

        try:
            # 生成一个测试嵌入来获取维度
            test_embedding = await self.generate_embedding("test")
            return len(test_embedding) if test_embedding else 0

        except Exception as e:
            logger.error(f"获取嵌入维度失败: {str(e)}")
            return 0


class TextChunker:
    """文本分块器"""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str) -> List[str]:
        """将文本分块"""
        try:
            # 按句子分割
            sentences = re.split(r'(?<=[.!?])\s+', text)

            chunks = []
            current_chunk = ""

            for sentence in sentences:
                # 如果添加这个句子会超过chunk_size，则创建新块
                if len(current_chunk) + len(sentence) > self.chunk_size:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                        current_chunk = sentence
                    else:
                        # 如果单个句子就超过chunk_size，强制分割
                        chunks.append(sentence[:self.chunk_size])
                        current_chunk = sentence[self.chunk_size:]
                else:
                    current_chunk += " " + sentence if current_chunk else sentence

            # 添加最后一个块
            if current_chunk:
                chunks.append(current_chunk.strip())

            # 处理重叠
            if self.chunk_overlap > 0 and len(chunks) > 1:
                chunks = self._add_overlap(chunks)

            return chunks

        except Exception as e:
            logger.error(f"文本分块失败: {str(e)}")
            return [text]

    def _add_overlap(self, chunks: List[str]) -> List[str]:
        """为块添加重叠"""
        overlapped_chunks = []

        for i, chunk in enumerate(chunks):
            if i == 0:
                overlapped_chunks.append(chunk)
            else:
                # 从前一个块的末尾获取重叠部分
                prev_chunk = chunks[i-1]
                overlap_text = prev_chunk[-self.chunk_overlap:] if len(prev_chunk) > self.chunk_overlap else prev_chunk
                overlapped_chunk = overlap_text + " " + chunk
                overlapped_chunks.append(overlapped_chunk)

        return overlapped_chunks


# 全局嵌入生成器实例
embedding_generator = EmbeddingGenerator()
text_chunker = TextChunker()


async def get_embedding_generator() -> EmbeddingGenerator:
    """获取嵌入生成器实例"""
    return embedding_generator


async def get_text_chunker() -> TextChunker:
    """获取文本分块器实例"""
    return text_chunker