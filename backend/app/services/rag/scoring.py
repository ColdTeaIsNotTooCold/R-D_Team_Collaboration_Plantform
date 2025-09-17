"""
RAG相关性和评分机制
实现文档相关性评分、质量评估和排序优化功能
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import time
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
from .retrieval import RetrievedDocument

logger = logging.getLogger(__name__)


class ScoringMethod(Enum):
    """评分方法"""
    COSINE_SIMILARITY = "cosine_similarity"
    BM25 = "bm25"
    JACCARD = "jaccard"
    EDIT_DISTANCE = "edit_distance"
    SEMANTIC_SIMILARITY = "semantic_similarity"
    HYBRID = "hybrid"


class QualityMetric(Enum):
    """质量指标"""
    RELEVANCE = "relevance"
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    CLARITY = "clarity"
    STRUCTURE = "structure"
    FRESHNESS = "freshness"


@dataclass
class ScoringConfig:
    """评分配置"""
    primary_method: ScoringMethod = ScoringMethod.HYBRID
    secondary_methods: List[ScoringMethod] = None
    weights: Dict[str, float] = None
    enable_quality_metrics: bool = True
    enable_temporal_decay: bool = True
    decay_factor: float = 0.95
    min_confidence: float = 0.3
    max_confidence: float = 1.0


@dataclass
class DocumentScore:
    """文档评分"""
    document_id: str
    overall_score: float
    component_scores: Dict[str, float]
    quality_metrics: Dict[str, float]
    confidence: float
    ranking_factors: Dict[str, Any]
    timestamp: datetime
    metadata: Dict[str, Any] = None


@dataclass
class ScoringResult:
    """评分结果"""
    query: str
    documents: List[RetrievedDocument]
    scores: List[DocumentScore]
    ranking: List[int]
    performance_metrics: Dict[str, Any]
    timestamp: datetime


class CosineSimilarityScorer:
    """余弦相似度评分器"""

    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words='english',
            ngram_range=(1, 2)
        )

    async def score(self, query: str, documents: List[RetrievedDocument]) -> List[float]:
        """计算余弦相似度分数"""
        if not documents:
            return []

        try:
            # 准备文本
            texts = [query] + [doc.content for doc in documents]

            # 向量化
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            query_vector = tfidf_matrix[0:1]
            doc_vectors = tfidf_matrix[1:]

            # 计算相似度
            similarities = cosine_similarity(query_vector, doc_vectors)[0]

            return similarities.tolist()

        except Exception as e:
            logger.error(f"余弦相似度计算失败: {str(e)}")
            return [0.0] * len(documents)


class BM25Scorer:
    """BM25评分器"""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.avg_doc_length = 0
        self.doc_freqs = {}
        self.corpus_size = 0

    def fit(self, documents: List[str]):
        """训练BM25模型"""
        self.corpus_size = len(documents)
        self.doc_freqs = {}
        doc_lengths = []

        for doc in documents:
            words = self._tokenize(doc)
            doc_lengths.append(len(words))

            # 计算词频
            word_freqs = {}
            for word in words:
                word_freqs[word] = word_freqs.get(word, 0) + 1

            # 更新文档频率
            for word in word_freqs:
                self.doc_freqs[word] = self.doc_freqs.get(word, 0) + 1

        self.avg_doc_length = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 0

    async def score(self, query: str, documents: List[RetrievedDocument]) -> List[float]:
        """计算BM25分数"""
        if not documents:
            return []

        try:
            # 训练模型
            doc_texts = [doc.content for doc in documents]
            self.fit(doc_texts)

            # 计算查询分数
            query_words = self._tokenize(query)
            scores = []

            for doc in documents:
                doc_words = self._tokenize(doc.content)
                score = self._calculate_bm25(query_words, doc_words, len(doc_words))
                scores.append(score)

            return scores

        except Exception as e:
            logger.error(f"BM25计算失败: {str(e)}")
            return [0.0] * len(documents)

    def _tokenize(self, text: str) -> List[str]:
        """分词"""
        return re.findall(r'\b\w+\b', text.lower())

    def _calculate_bm25(self, query_words: List[str], doc_words: List[str], doc_length: int) -> float:
        """计算BM25分数"""
        if not query_words or doc_length == 0:
            return 0.0

        score = 0.0
        doc_word_freqs = {}
        for word in doc_words:
            doc_word_freqs[word] = doc_word_freqs.get(word, 0) + 1

        for word in query_words:
            if word in doc_word_freqs:
                # IDF
                idf = self._calculate_idf(word)

                # TF
                tf = doc_word_freqs[word]

                # BM25公式
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * doc_length / self.avg_doc_length)

                score += idf * (numerator / denominator)

        return score

    def _calculate_idf(self, word: str) -> float:
        """计算IDF"""
        doc_freq = self.doc_freqs.get(word, 0)
        if doc_freq == 0:
            return 0.0

        return np.log((self.corpus_size - doc_freq + 0.5) / (doc_freq + 0.5))


class JaccardScorer:
    """Jaccard相似度评分器"""

    async def score(self, query: str, documents: List[RetrievedDocument]) -> List[float]:
        """计算Jaccard相似度"""
        if not documents:
            return []

        try:
            query_words = set(self._tokenize(query))
            scores = []

            for doc in documents:
                doc_words = set(self._tokenize(doc.content))

                if not query_words or not doc_words:
                    scores.append(0.0)
                    continue

                intersection = len(query_words.intersection(doc_words))
                union = len(query_words.union(doc_words))

                jaccard_score = intersection / union if union > 0 else 0.0
                scores.append(jaccard_score)

            return scores

        except Exception as e:
            logger.error(f"Jaccard相似度计算失败: {str(e)}")
            return [0.0] * len(documents)

    def _tokenize(self, text: str) -> List[str]:
        """分词"""
        return re.findall(r'\b\w+\b', text.lower())


class EditDistanceScorer:
    """编辑距离评分器"""

    async def score(self, query: str, documents: List[RetrievedDocument]) -> List[float]:
        """计算编辑距离分数"""
        if not documents:
            return []

        try:
            scores = []
            for doc in documents:
                # 使用简化的编辑距离计算
                distance = self._calculate_edit_distance(query, doc.content)
                max_length = max(len(query), len(doc.content))

                # 转换为相似度分数
                similarity = 1.0 - (distance / max_length) if max_length > 0 else 0.0
                scores.append(max(0.0, similarity))

            return scores

        except Exception as e:
            logger.error(f"编辑距离计算失败: {str(e)}")
            return [0.0] * len(documents)

    def _calculate_edit_distance(self, s1: str, s2: str) -> int:
        """计算编辑距离"""
        if len(s1) < len(s2):
            return self._calculate_edit_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]


class QualityAssessment:
    """质量评估器"""

    def __init__(self):
        self.quality_weights = {
            QualityMetric.RELEVANCE: 0.3,
            QualityMetric.COMPLETENESS: 0.2,
            QualityMetric.ACCURACY: 0.2,
            QualityMetric.CLARITY: 0.15,
            QualityMetric.STRUCTURE: 0.1,
            QualityMetric.FRESHNESS: 0.05
        }

    async def assess_quality(self, query: str, document: RetrievedDocument) -> Dict[str, float]:
        """评估文档质量"""
        try:
            quality_scores = {}

            # 相关性
            quality_scores[QualityMetric.RELEVANCE.value] = self._assess_relevance(query, document)

            # 完整性
            quality_scores[QualityMetric.COMPLETENESS.value] = self._assess_completeness(document)

            # 准确性
            quality_scores[QualityMetric.ACCURACY.value] = self._assess_accuracy(document)

            # 清晰度
            quality_scores[QualityMetric.CLARITY.value] = self._assess_clarity(document)

            # 结构性
            quality_scores[QualityMetric.STRUCTURE.value] = self._assess_structure(document)

            # 新鲜度
            quality_scores[QualityMetric.FRESHNESS.value] = self._assess_freshness(document)

            return quality_scores

        except Exception as e:
            logger.error(f"质量评估失败: {str(e)}")
            return {metric.value: 0.0 for metric in QualityMetric}

    def _assess_relevance(self, query: str, document: RetrievedDocument) -> float:
        """评估相关性"""
        # 基于词重叠和相关性的简单评估
        query_words = set(query.lower().split())
        doc_words = set(document.content.lower().split())

        if not query_words:
            return 0.0

        overlap = len(query_words.intersection(doc_words))
        relevance_score = overlap / len(query_words)

        return min(1.0, relevance_score)

    def _assess_completeness(self, document: RetrievedDocument) -> float:
        """评估完整性"""
        content_length = len(document.content)

        # 基于长度的完整性评估
        if content_length < 50:
            return 0.3
        elif content_length < 200:
            return 0.6
        elif content_length < 500:
            return 0.8
        else:
            return 1.0

    def _assess_accuracy(self, document: RetrievedDocument) -> float:
        """评估准确性"""
        # 简化的准确性评估（可以后续扩展）
        # 检查是否有明显的不准确特征
        content = document.content.lower()

        # 检查是否包含不确定的表述
        uncertain_phrases = ["可能", "也许", "大概", "似乎", "大概"]
        uncertainty_count = sum(1 for phrase in uncertain_phrases if phrase in content)

        # 基于不确定性的准确性评估
        uncertainty_penalty = min(0.3, uncertainty_count * 0.1)
        accuracy_score = 1.0 - uncertainty_penalty

        return max(0.0, accuracy_score)

    def _assess_clarity(self, document: RetrievedDocument) -> float:
        """评估清晰度"""
        content = document.content

        # 基于句子长度和结构的清晰度评估
        sentences = content.split('.')
        if not sentences:
            return 0.0

        avg_sentence_length = sum(len(s.split()) for s in sentences) / len(sentences)

        # 理想的句子长度在10-20个词之间
        if 10 <= avg_sentence_length <= 20:
            clarity_score = 1.0
        elif 5 <= avg_sentence_length < 10:
            clarity_score = 0.8
        elif 20 < avg_sentence_length <= 30:
            clarity_score = 0.7
        else:
            clarity_score = 0.5

        return clarity_score

    def _assess_structure(self, document: RetrievedDocument) -> float:
        """评估结构性"""
        content = document.content

        # 检查结构特征
        has_paragraphs = '\n\n' in content
        has_lists = any(marker in content for marker in ['•', '-', '*', '1.', '2.'])
        has_headings = any(content.startswith(marker) for marker in ['#', '##', '###'])

        structure_score = 0.0
        if has_paragraphs:
            structure_score += 0.3
        if has_lists:
            structure_score += 0.3
        if has_headings:
            structure_score += 0.4

        return structure_score

    def _assess_freshness(self, document: RetrievedDocument) -> float:
        """评估新鲜度"""
        # 基于时间戳的新鲜度评估
        if hasattr(document, 'timestamp') and document.timestamp:
            # 计算时间差（简化版本）
            now = datetime.now()
            age = (now - document.timestamp).days

            if age < 1:
                return 1.0
            elif age < 7:
                return 0.8
            elif age < 30:
                return 0.6
            elif age < 365:
                return 0.4
            else:
                return 0.2
        else:
            return 0.5  # 默认中等新鲜度

    def calculate_overall_quality(self, quality_scores: Dict[str, float]) -> float:
        """计算总体质量分数"""
        total_score = 0.0
        total_weight = 0.0

        for metric, score in quality_scores.items():
            weight = self.quality_weights.get(QualityMetric(metric), 0.1)
            total_score += score * weight
            total_weight += weight

        return total_score / total_weight if total_weight > 0 else 0.0


class DocumentScorer:
    """文档评分器"""

    def __init__(self, config: ScoringConfig = None):
        self.config = config or ScoringConfig()
        self.scorers = {
            ScoringMethod.COSINE_SIMILARITY: CosineSimilarityScorer(),
            ScoringMethod.BM25: BM25Scorer(),
            ScoringMethod.JACCARD: JaccardScorer(),
            ScoringMethod.EDIT_DISTANCE: EditDistanceScorer()
        }
        self.quality_assessor = QualityAssessment()
        self._performance_metrics = {
            'total_scorings': 0,
            'average_scoring_time': 0.0,
            'method_usage': {}
        }

    async def score_documents(self, query: str, documents: List[RetrievedDocument]) -> ScoringResult:
        """对文档进行评分"""
        if not documents:
            return ScoringResult(
                query=query,
                documents=[],
                scores=[],
                ranking=[],
                performance_metrics={},
                timestamp=datetime.now()
            )

        start_time = time.time()

        try:
            # 执行评分
            component_scores = await self._calculate_component_scores(query, documents)

            # 计算总体分数
            overall_scores = self._calculate_overall_scores(component_scores)

            # 质量评估
            quality_metrics = await self._assess_quality(query, documents)

            # 创建评分对象
            scores = self._create_document_scores(documents, overall_scores, component_scores, quality_metrics)

            # 排序
            ranking = self._rank_documents(scores)

            # 更新性能指标
            self._update_performance_metrics(time.time() - start_time)

            return ScoringResult(
                query=query,
                documents=documents,
                scores=scores,
                ranking=ranking,
                performance_metrics=self.get_performance_metrics(),
                timestamp=datetime.now()
            )

        except Exception as e:
            logger.error(f"文档评分失败: {str(e)}")
            raise

    async def _calculate_component_scores(self, query: str, documents: List[RetrievedDocument]) -> Dict[ScoringMethod, List[float]]:
        """计算组件分数"""
        component_scores = {}

        # 主要方法
        if self.config.primary_method in self.scorers:
            scorer = self.scorers[self.config.primary_method]
            scores = await scorer.score(query, documents)
            component_scores[self.config.primary_method] = scores

        # 次要方法
        secondary_methods = self.config.secondary_methods or [ScoringMethod.COSINE_SIMILARITY]
        for method in secondary_methods:
            if method in self.scorers and method != self.config.primary_method:
                scorer = self.scorers[method]
                scores = await scorer.score(query, documents)
                component_scores[method] = scores

        return component_scores

    def _calculate_overall_scores(self, component_scores: Dict[ScoringMethod, List[float]]) -> List[float]:
        """计算总体分数"""
        if not component_scores:
            return []

        num_documents = len(list(component_scores.values())[0])
        overall_scores = [0.0] * num_documents

        # 使用权重计算总体分数
        weights = self.config.weights or {
            ScoringMethod.COSINE_SIMILARITY.value: 0.4,
            ScoringMethod.BM25.value: 0.3,
            ScoringMethod.JACCARD.value: 0.2,
            ScoringMethod.EDIT_DISTANCE.value: 0.1
        }

        for method, scores in component_scores.items():
            weight = weights.get(method.value, 0.25)
            for i, score in enumerate(scores):
                overall_scores[i] += score * weight

        return overall_scores

    async def _assess_quality(self, query: str, documents: List[RetrievedDocument]) -> List[Dict[str, float]]:
        """评估质量"""
        quality_metrics = []
        for doc in documents:
            metrics = await self.quality_assessor.assess_quality(query, doc)
            quality_metrics.append(metrics)
        return quality_metrics

    def _create_document_scores(self, documents: List[RetrievedDocument], overall_scores: List[float],
                              component_scores: Dict[ScoringMethod, List[float]],
                              quality_metrics: List[Dict[str, float]]) -> List[DocumentScore]:
        """创建文档评分对象"""
        scores = []
        for i, doc in enumerate(documents):
            # 组件分数
            comp_scores = {}
            for method, scores_list in component_scores.items():
                comp_scores[method.value] = scores_list[i]

            # 计算置信度
            confidence = self._calculate_confidence(overall_scores[i], quality_metrics[i])

            # 排序因子
            ranking_factors = self._calculate_ranking_factors(doc, overall_scores[i], quality_metrics[i])

            score = DocumentScore(
                document_id=doc.id,
                overall_score=overall_scores[i],
                component_scores=comp_scores,
                quality_metrics=quality_metrics[i],
                confidence=confidence,
                ranking_factors=ranking_factors,
                timestamp=datetime.now(),
                metadata={
                    'original_score': doc.score,
                    'original_rank': doc.rank,
                    'retrieval_method': doc.retrieval_method
                }
            )
            scores.append(score)

        return scores

    def _calculate_confidence(self, overall_score: float, quality_metrics: Dict[str, float]) -> float:
        """计算置信度"""
        if not self.config.enable_quality_metrics:
            return min(max(overall_score, self.config.min_confidence), self.config.max_confidence)

        # 基于质量指标调整置信度
        quality_score = self.quality_assessor.calculate_overall_quality(quality_metrics)

        # 综合考虑总体分数和质量分数
        confidence = (overall_score * 0.7 + quality_score * 0.3)

        # 应用置信度范围限制
        confidence = max(self.config.min_confidence, min(self.config.max_confidence, confidence))

        return confidence

    def _calculate_ranking_factors(self, document: RetrievedDocument, overall_score: float,
                                 quality_metrics: Dict[str, float]) -> Dict[str, Any]:
        """计算排序因子"""
        factors = {
            'content_length': len(document.content),
            'original_score': document.score,
            'original_rank': document.rank,
            'metadata_quality': len(document.metadata),
            'retrieval_method': document.retrieval_method
        }

        if self.config.enable_temporal_decay:
            # 时间衰减因子
            if hasattr(document, 'timestamp'):
                age = (datetime.now() - document.timestamp).days
                decay_factor = self.config.decay_factor ** age
                factors['temporal_decay'] = decay_factor
            else:
                factors['temporal_decay'] = 1.0

        return factors

    def _rank_documents(self, scores: List[DocumentScore]) -> List[int]:
        """排序文档"""
        # 按总体分数排序
        sorted_scores = sorted(scores, key=lambda x: x.overall_score, reverse=True)

        # 返回排序后的索引
        ranking = []
        for score in sorted_scores:
            # 找到原始索引
            original_index = next(i for i, s in enumerate(scores) if s.document_id == score.document_id)
            ranking.append(original_index)

        return ranking

    def _update_performance_metrics(self, scoring_time: float):
        """更新性能指标"""
        self._performance_metrics['total_scorings'] += 1

        # 更新平均评分时间
        total_scorings = self._performance_metrics['total_scorings']
        current_avg = self._performance_metrics['average_scoring_time']
        self._performance_metrics['average_scoring_time'] = (current_avg * (total_scorings - 1) + scoring_time) / total_scorings

        # 更新方法使用统计
        if self.config.primary_method:
            method_name = self.config.primary_method.value
            if method_name not in self._performance_metrics['method_usage']:
                self._performance_metrics['method_usage'][method_name] = 0
            self._performance_metrics['method_usage'][method_name] += 1

    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return {
            'metrics': self._performance_metrics,
            'config': self.config.__dict__,
            'timestamp': datetime.now().isoformat()
        }

    def get_scorer_info(self) -> Dict[str, Any]:
        """获取评分器信息"""
        return {
            'available_methods': [method.value for method in ScoringMethod],
            'primary_method': self.config.primary_method.value,
            'secondary_methods': [method.value for method in self.config.secondary_methods or []],
            'quality_metrics_enabled': self.config.enable_quality_metrics,
            'quality_weights': {metric.value: weight for metric, weight in self.quality_assessor.quality_weights.items()}
        }

    async def rerank_documents(self, query: str, documents: List[RetrievedDocument],
                             top_k: int = None) -> List[RetrievedDocument]:
        """重排序文档"""
        if not documents:
            return []

        # 评分
        scoring_result = await self.score_documents(query, documents)

        # 按评分结果排序文档
        ranked_documents = []
        for rank_index in scoring_result.ranking:
            ranked_documents.append(documents[rank_index])

        # 限制返回数量
        if top_k:
            ranked_documents = ranked_documents[:top_k]

        return ranked_documents

    def set_config(self, config: ScoringConfig):
        """设置配置"""
        self.config = config
        logger.info("文档评分配置已更新")

    def add_custom_scorer(self, method: ScoringMethod, scorer):
        """添加自定义评分器"""
        self.scorers[method] = scorer
        logger.info(f"添加自定义评分器: {method.value}")