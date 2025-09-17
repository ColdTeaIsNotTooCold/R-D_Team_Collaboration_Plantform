"""
RAG上下文构建和优化模块
实现智能上下文构建、压缩和优化策略
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
import time
from datetime import datetime
import re
import tiktoken
from .retrieval import RetrievedDocument

logger = logging.getLogger(__name__)


class ContextCompressionStrategy(Enum):
    """上下文压缩策略"""
    NONE = "none"
    TRUNCATE = "truncate"
    SUMMARIZE = "summarize"
    KEY_EXTRACTION = "key_extraction"
    HIERARCHICAL = "hierarchical"


class ContextOptimization(Enum):
    """上下文优化策略"""
    RELEVANCE_BASED = "relevance_based"
    DIVERSITY_BASED = "diversity_based"
    COVERAGE_BASED = "coverage_based"
    QUALITY_BASED = "quality_based"


@dataclass
class ContextConfig:
    """上下文配置"""
    max_context_length: int = 4000
    compression_strategy: ContextCompressionStrategy = ContextCompressionStrategy.TRUNCATE
    optimization_strategy: ContextOptimization = ContextOptimization.RELEVANCE_BASED
    enable_deduplication: bool = True
    enable_context_windowing: bool = True
    enable_semantic_clustering: bool = True
    min_document_score: float = 0.5
    max_documents: int = 10
    context_buffer_ratio: float = 0.1  # 保留10%的缓冲空间


@dataclass
class ContextWindow:
    """上下文窗口"""
    content: str
    documents: List[RetrievedDocument]
    total_tokens: int
    window_size: int
    metadata: Dict[str, Any]
    compression_ratio: float = 1.0
    optimization_score: float = 0.0


class ContextBuilder:
    """上下文构建器"""

    def __init__(self, config: ContextConfig = None):
        self.config = config or ContextConfig()
        self._token_encoder = tiktoken.get_encoding("cl100k_base")
        self._performance_metrics = {
            'total_contexts_built': 0,
            'average_build_time': 0.0,
            'average_compression_ratio': 0.0,
            'optimization_improvements': 0
        }

    async def build_context(self, query: str, documents: List[RetrievedDocument]) -> ContextWindow:
        """构建上下文"""
        try:
            start_time = time.time()

            # 过滤和排序文档
            filtered_docs = self._filter_documents(documents)
            sorted_docs = self._sort_documents(filtered_docs, query)

            # 上下文优化
            optimized_docs = await self._optimize_context(sorted_docs, query)

            # 上下文压缩
            compressed_docs = await self._compress_context(optimized_docs)

            # 构建最终上下文
            context_content = self._build_context_content(query, compressed_docs)

            # 计算token数量
            total_tokens = self._count_tokens(context_content)

            # 创建上下文窗口
            context_window = ContextWindow(
                content=context_content,
                documents=compressed_docs,
                total_tokens=total_tokens,
                window_size=len(context_content),
                metadata={
                    'query': query,
                    'build_time': time.time() - start_time,
                    'compression_strategy': self.config.compression_strategy.value,
                    'optimization_strategy': self.config.optimization_strategy.value
                }
            )

            # 更新性能指标
            self._update_performance_metrics(context_window)

            logger.info(f"上下文构建完成，包含 {len(compressed_docs)} 个文档，{total_tokens} 个token，压缩比: {context_window.compression_ratio:.2f}")
            return context_window

        except Exception as e:
            logger.error(f"上下文构建失败: {str(e)}")
            raise

    def _filter_documents(self, documents: List[RetrievedDocument]) -> List[RetrievedDocument]:
        """过滤文档"""
        filtered = []

        for doc in documents:
            # 分数过滤
            if doc.score >= self.config.min_document_score:
                # 内容长度过滤
                if len(doc.content) > 10:  # 最小内容长度
                    filtered.append(doc)

        return filtered

    def _sort_documents(self, documents: List[RetrievedDocument], query: str) -> List[RetrievedDocument]:
        """排序文档"""
        if self.config.optimization_strategy == ContextOptimization.RELEVANCE_BASED:
            return self._sort_by_relevance(documents, query)
        elif self.config.optimization_strategy == ContextOptimization.DIVERSITY_BASED:
            return self._sort_by_diversity(documents, query)
        elif self.config.optimization_strategy == ContextOptimization.COVERAGE_BASED:
            return self._sort_by_coverage(documents, query)
        elif self.config.optimization_strategy == ContextOptimization.QUALITY_BASED:
            return self._sort_by_quality(documents, query)
        else:
            return sorted(documents, key=lambda x: x.score, reverse=True)

    def _sort_by_relevance(self, documents: List[RetrievedDocument], query: str) -> List[RetrievedDocument]:
        """按相关性排序"""
        return sorted(documents, key=lambda x: x.score, reverse=True)

    def _sort_by_diversity(self, documents: List[RetrievedDocument], query: str) -> List[RetrievedDocument]:
        """按多样性排序"""
        sorted_docs = []
        remaining_docs = documents.copy()

        while remaining_docs:
            # 选择与已选文档最不相似的文档
            next_doc = self._select_most_diverse_document(remaining_docs, sorted_docs)
            sorted_docs.append(next_doc)
            remaining_docs.remove(next_doc)

        return sorted_docs

    def _sort_by_coverage(self, documents: List[RetrievedDocument], query: str) -> List[RetrievedDocument]:
        """按覆盖度排序"""
        # 简化的覆盖度排序，确保不同主题的文档都有机会被包含
        return self._sort_by_diversity(documents, query)

    def _sort_by_quality(self, documents: List[RetrievedDocument], query: str) -> List[RetrievedDocument]:
        """按质量排序"""
        # 综合考虑分数、内容质量和其他因素
        return sorted(documents, key=lambda x: self._calculate_quality_score(x, query), reverse=True)

    def _calculate_quality_score(self, doc: RetrievedDocument, query: str) -> float:
        """计算质量分数"""
        # 基础分数
        quality_score = doc.score

        # 内容长度奖励（适中的长度）
        content_length = len(doc.content)
        if 100 <= content_length <= 1000:
            quality_score += 0.1
        elif content_length > 1000:
            quality_score -= 0.05

        # 结构化内容奖励
        if self._is_structured_content(doc.content):
            quality_score += 0.05

        # 元数据质量奖励
        if doc.metadata and len(doc.metadata) > 0:
            quality_score += 0.02

        return quality_score

    def _is_structured_content(self, content: str) -> bool:
        """检查是否为结构化内容"""
        # 检查是否有标题、列表、代码块等结构
        patterns = [
            r'^#+\s+',  # 标题
            r'^\s*[-*+]\s+',  # 列表
            r'^\s*\d+\.\s+',  # 数字列表
            r'```',  # 代码块
            r'^\s*\w+:\s+\w+',  # 键值对
        ]

        for pattern in patterns:
            if re.search(pattern, content, re.MULTILINE):
                return True

        return False

    def _select_most_diverse_document(self, candidates: List[RetrievedDocument],
                                    selected: List[RetrievedDocument]) -> RetrievedDocument:
        """选择最多样化的文档"""
        if not selected:
            # 如果还没有选择的文档，选择分数最高的
            return max(candidates, key=lambda x: x.score)

        # 计算每个候选文档与已选文档的平均相似度
        best_doc = candidates[0]
        min_similarity = float('inf')

        for candidate in candidates:
            total_similarity = 0
            for selected_doc in selected:
                similarity = self._calculate_document_similarity(candidate, selected_doc)
                total_similarity += similarity

            avg_similarity = total_similarity / len(selected)

            if avg_similarity < min_similarity:
                min_similarity = avg_similarity
                best_doc = candidate
            elif avg_similarity == min_similarity and candidate.score > best_doc.score:
                best_doc = candidate

        return best_doc

    def _calculate_document_similarity(self, doc1: RetrievedDocument, doc2: RetrievedDocument) -> float:
        """计算文档相似度"""
        # 使用词重叠率作为相似度指标
        words1 = set(doc1.content.lower().split())
        words2 = set(doc2.content.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union)

    async def _optimize_context(self, documents: List[RetrievedDocument], query: str) -> List[RetrievedDocument]:
        """优化上下文"""
        optimized_docs = documents.copy()

        # 语义聚类
        if self.config.enable_semantic_clustering:
            optimized_docs = await self._semantic_clustering(optimized_docs, query)

        # 去重
        if self.config.enable_deduplication:
            optimized_docs = self._deduplicate_documents(optimized_docs)

        return optimized_docs

    async def _semantic_clustering(self, documents: List[RetrievedDocument], query: str) -> List[RetrievedDocument]:
        """语义聚类"""
        try:
            # 简化的语义聚类实现
            # 在实际应用中，可以使用更复杂的聚类算法

            clusters = []
            unclustered = documents.copy()

            while unclustered:
                # 选择第一个文档作为聚类中心
                center_doc = unclustered.pop(0)
                cluster = [center_doc]

                # 寻找相似的文档加入聚类
                i = 0
                while i < len(unclustered):
                    doc = unclustered[i]
                    similarity = self._calculate_document_similarity(center_doc, doc)

                    if similarity > 0.6:  # 相似度阈值
                        cluster.append(doc)
                        unclustered.pop(i)
                    else:
                        i += 1

                clusters.append(cluster)

            # 从每个聚类中选择最佳文档
            optimized_docs = []
            for cluster in clusters:
                best_doc = max(cluster, key=lambda x: x.score)
                optimized_docs.append(best_doc)

            return optimized_docs

        except Exception as e:
            logger.error(f"语义聚类失败: {str(e)}")
            return documents

    def _deduplicate_documents(self, documents: List[RetrievedDocument]) -> List[RetrievedDocument]:
        """去重文档"""
        unique_docs = []
        seen_contents = set()

        for doc in documents:
            # 内容哈希去重
            content_hash = hash(doc.content.strip().lower())
            if content_hash not in seen_contents:
                seen_contents.add(content_hash)
                unique_docs.append(doc)

        return unique_docs

    async def _compress_context(self, documents: List[RetrievedDocument]) -> List[RetrievedDocument]:
        """压缩上下文"""
        if self.config.compression_strategy == ContextCompressionStrategy.NONE:
            return documents

        try:
            if self.config.compression_strategy == ContextCompressionStrategy.TRUNCATE:
                return await self._truncate_documents(documents)
            elif self.config.compression_strategy == ContextCompressionStrategy.SUMMARIZE:
                return await self._summarize_documents(documents)
            elif self.config.compression_strategy == ContextCompressionStrategy.KEY_EXTRACTION:
                return await self._extract_key_documents(documents)
            elif self.config.compression_strategy == ContextCompressionStrategy.HIERARCHICAL:
                return await self._hierarchical_compress(documents)
            else:
                return documents

        except Exception as e:
            logger.error(f"上下文压缩失败: {str(e)}")
            return documents

    async def _truncate_documents(self, documents: List[RetrievedDocument]) -> List[RetrievedDocument]:
        """截断文档"""
        max_length = self.config.max_context_length
        total_length = 0
        truncated_docs = []

        for doc in documents:
            doc_length = len(doc.content)
            if total_length + doc_length <= max_length:
                truncated_docs.append(doc)
                total_length += doc_length
            else:
                # 截断最后一个文档
                remaining_length = max_length - total_length
                if remaining_length > 50:  # 至少保留50个字符
                    truncated_content = doc.content[:remaining_length]
                    truncated_doc = RetrievedDocument(
                        id=doc.id,
                        content=truncated_content,
                        metadata=doc.metadata,
                        score=doc.score,
                        rank=doc.rank,
                        retrieval_method=doc.retrieval_method,
                        timestamp=doc.timestamp
                    )
                    truncated_docs.append(truncated_doc)
                break

        return truncated_docs

    async def _summarize_documents(self, documents: List[RetrievedDocument]) -> List[RetrievedDocument]:
        """摘要文档"""
        # 简化的摘要实现
        # 在实际应用中，可以调用LLM进行摘要
        summarized_docs = []

        for doc in documents:
            if len(doc.content) > 500:  # 对长文档进行摘要
                # 简单摘要：取前200个字符和后200个字符
                summary = doc.content[:200] + "..." + doc.content[-200:]
                summarized_doc = RetrievedDocument(
                    id=doc.id,
                    content=summary,
                    metadata=doc.metadata,
                    score=doc.score,
                    rank=doc.rank,
                    retrieval_method=doc.retrieval_method,
                    timestamp=doc.timestamp
                )
                summarized_docs.append(summarized_doc)
            else:
                summarized_docs.append(doc)

        return summarized_docs

    async def _extract_key_documents(self, documents: List[RetrievedDocument]) -> List[RetrievedDocument]:
        """提取关键文档"""
        # 提取分数最高的文档
        return sorted(documents, key=lambda x: x.score, reverse=True)[:self.config.max_documents]

    async def _hierarchical_compress(self, documents: List[RetrievedDocument]) -> List[RetrievedDocument]:
        """层次压缩"""
        # 先按分数排序，然后应用多种压缩策略
        sorted_docs = sorted(documents, key=lambda x: x.score, reverse=True)

        # 第一层：按分数选择
        top_docs = sorted_docs[:self.config.max_documents * 2]

        # 第二层：按长度和多样性优化
        final_docs = []
        total_length = 0
        max_length = self.config.max_context_length

        for doc in top_docs:
            if total_length + len(doc.content) <= max_length:
                final_docs.append(doc)
                total_length += len(doc.content)
            else:
                break

        return final_docs

    def _build_context_content(self, query: str, documents: List[RetrievedDocument]) -> str:
        """构建上下文内容"""
        context_parts = []

        # 添加查询信息
        context_parts.append(f"查询: {query}")
        context_parts.append("=" * 50)

        # 添加文档内容
        for i, doc in enumerate(documents):
            context_parts.append(f"文档 {i+1} (分数: {doc.score:.2f}):")
            context_parts.append(doc.content)
            context_parts.append("-" * 30)

        # 添加元数据信息
        if documents:
            context_parts.append("=" * 50)
            context_parts.append(f"共 {len(documents)} 个相关文档")

        return "\n".join(context_parts)

    def _count_tokens(self, text: str) -> int:
        """计算token数量"""
        return len(self._token_encoder.encode(text))

    def _update_performance_metrics(self, context_window: ContextWindow):
        """更新性能指标"""
        self._performance_metrics['total_contexts_built'] += 1

        # 更新平均构建时间
        total_contexts = self._performance_metrics['total_contexts_built']
        build_time = context_window.metadata['build_time']
        current_avg = self._performance_metrics['average_build_time']
        self._performance_metrics['average_build_time'] = (current_avg * (total_contexts - 1) + build_time) / total_contexts

        # 更新平均压缩比
        current_compression_avg = self._performance_metrics['average_compression_ratio']
        self._performance_metrics['average_compression_ratio'] = (current_compression_avg * (total_contexts - 1) + context_window.compression_ratio) / total_contexts

    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return {
            'metrics': self._performance_metrics,
            'timestamp': datetime.now().isoformat()
        }

    def estimate_context_size(self, documents: List[RetrievedDocument]) -> int:
        """估算上下文大小"""
        total_chars = sum(len(doc.content) for doc in documents)
        # 粗略估算：1个字符约等于0.25个token
        estimated_tokens = int(total_chars * 0.25)
        return estimated_tokens

    def optimize_for_model(self, context_window: ContextWindow, model_max_tokens: int) -> ContextWindow:
        """为特定模型优化上下文"""
        if context_window.total_tokens > model_max_tokens:
            # 需要进一步压缩
            compression_ratio = model_max_tokens / context_window.total_tokens
            logger.info(f"上下文超过模型限制，压缩比例为: {compression_ratio:.2f}")

            # 简单的截断策略
            new_content = context_window.content[:int(len(context_window.content) * compression_ratio)]
            context_window.content = new_content
            context_window.total_tokens = self._count_tokens(new_content)
            context_window.compression_ratio *= compression_ratio

        return context_window


class ContextManager:
    """上下文管理器"""

    def __init__(self, config: ContextConfig = None):
        self.config = config or ContextConfig()
        self.builder = ContextBuilder(config)
        self._context_cache = {}
        self._cache_ttl = 3600  # 1小时缓存

    async def build_context(self, query: str, documents: List[RetrievedDocument]) -> ContextWindow:
        """构建上下文"""
        # 检查缓存
        cache_key = self._generate_cache_key(query, documents)
        cached_context = self._get_cached_context(cache_key)
        if cached_context:
            logger.info("使用缓存的上下文")
            return cached_context

        # 构建新上下文
        context = await self.builder.build_context(query, documents)

        # 缓存上下文
        self._cache_context(cache_key, context)

        return context

    def _generate_cache_key(self, query: str, documents: List[RetrievedDocument]) -> str:
        """生成缓存键"""
        # 简化的缓存键生成
        doc_ids = [doc.id for doc in documents]
        return f"{query}_{hash(str(doc_ids))}"

    def _get_cached_context(self, cache_key: str) -> Optional[ContextWindow]:
        """获取缓存的上下文"""
        if cache_key in self._context_cache:
            cached_data = self._context_cache[cache_key]
            if time.time() - cached_data['timestamp'] < self._cache_ttl:
                return cached_data['context']
            else:
                # 缓存过期，删除
                del self._context_cache[cache_key]

        return None

    def _cache_context(self, cache_key: str, context: ContextWindow):
        """缓存上下文"""
        self._context_cache[cache_key] = {
            'context': context,
            'timestamp': time.time()
        }

        # 清理过期的缓存
        self._cleanup_expired_cache()

    def _cleanup_expired_cache(self):
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = []

        for key, cached_data in self._context_cache.items():
            if current_time - cached_data['timestamp'] > self._cache_ttl:
                expired_keys.append(key)

        for key in expired_keys:
            del self._context_cache[key]

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            'cache_size': len(self._context_cache),
            'cache_ttl': self._cache_ttl,
            'timestamp': datetime.now().isoformat()
        }

    def clear_cache(self):
        """清理缓存"""
        self._context_cache.clear()
        logger.info("上下文缓存已清理")