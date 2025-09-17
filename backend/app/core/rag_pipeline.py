"""
RAG管道核心集成模块
整合RAG系统所有组件，提供统一的接口和配置管理
"""
import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import asyncio
from ..services.rag.pipeline import RAGPipeline, PipelineConfig, PipelineManager, PipelineResult
from ..services.rag.retrieval import RetrievalManager, RetrievalConfig, RetrievalStrategy
from ..services.rag.context import ContextManager, ContextConfig, ContextCompressionStrategy, ContextOptimization
from ..services.rag.prompts import PromptSystem
from ..services.rag.scoring import DocumentScorer, ScoringConfig, ScoringMethod
from ..services.llm.manager import LLMManager
from ..core.vector_db import VectorDBManager
from ..services.vectorization.service import VectorizationService
from ..core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class RAGSystemConfig:
    """RAG系统配置"""
    # 检索配置
    retrieval_strategy: str = "semantic_search"
    retrieval_max_results: int = 10
    retrieval_score_threshold: float = 0.7
    retrieval_enable_fallback: bool = True

    # 上下文配置
    context_max_length: int = 4000
    context_compression_strategy: str = "truncate"
    context_optimization_strategy: str = "relevance_based"
    context_enable_deduplication: bool = True
    context_enable_semantic_clustering: bool = True

    # 管道配置
    pipeline_max_tokens: int = 8000
    pipeline_enable_caching: bool = True
    pipeline_enable_monitoring: bool = True
    pipeline_timeout: int = 30
    pipeline_max_retries: int = 3

    # 评分配置
    scoring_primary_method: str = "hybrid"
    scoring_enable_quality_metrics: bool = True
    scoring_enable_temporal_decay: bool = True
    scoring_min_confidence: float = 0.3

    # 模型配置
    default_model: str = "gpt-3.5-turbo"
    fallback_model: str = "claude-3-haiku-20240307"

    class Config:
        extra = "allow"


class RAGSystem:
    """RAG系统主类"""

    def __init__(self, config: RAGSystemConfig = None):
        self.config = config or RAGSystemConfig()
        self._initialized = False
        self._init_start_time = None

        # 核心组件
        self.vector_db: Optional[VectorDBManager] = None
        self.vectorization_service: Optional[VectorizationService] = None
        self.llm_manager: Optional[LLMManager] = None
        self.pipeline_manager: Optional[PipelineManager] = None
        self.retrieval_manager: Optional[RetrievalManager] = None
        self.context_manager: Optional[ContextManager] = None
        self.prompt_system: Optional[PromptSystem] = None
        self.document_scorer: Optional[DocumentScorer] = None

        # 性能指标
        self._performance_metrics = {
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'average_response_time': 0.0,
            'cache_hits': 0,
            'cache_misses': 0,
            'system_uptime': 0.0
        }

    async def initialize(self) -> bool:
        """初始化RAG系统"""
        try:
            self._init_start_time = datetime.now()
            logger.info("开始初始化RAG系统...")

            # 初始化向量数据库
            self.vector_db = VectorDBManager()
            if not await self.vector_db.initialize():
                raise RuntimeError("向量数据库初始化失败")

            # 初始化向量化服务
            self.vectorization_service = VectorizationService(self.vector_db)

            # 初始化LLM管理器
            self.llm_manager = LLMManager()
            if not await self.llm_manager.initialize():
                raise RuntimeError("LLM管理器初始化失败")

            # 初始化RAG组件
            await self._initialize_rag_components()

            # 创建默认管道
            self.pipeline_manager = PipelineManager(
                self.vector_db,
                self.vectorization_service,
                self.llm_manager
            )
            default_pipeline = self.pipeline_manager.create_pipeline("default", self._create_pipeline_config())
            self.pipeline_manager.set_default_pipeline("default")

            self._initialized = True
            init_time = (datetime.now() - self._init_start_time).total_seconds()
            logger.info(f"RAG系统初始化完成，耗时: {init_time:.2f}秒")

            return True

        except Exception as e:
            logger.error(f"RAG系统初始化失败: {str(e)}")
            return False

    async def _initialize_rag_components(self):
        """初始化RAG组件"""
        # 初始化检索管理器
        self.retrieval_manager = RetrievalManager(self.vector_db, self.vectorization_service)

        # 初始化上下文管理器
        self.context_manager = ContextManager(self._create_context_config())

        # 初始化提示词系统
        self.prompt_system = PromptSystem()

        # 初始化文档评分器
        self.document_scorer = DocumentScorer(self._create_scoring_config())

    def _create_retrieval_config(self) -> RetrievalConfig:
        """创建检索配置"""
        strategy_map = {
            "semantic_search": RetrievalStrategy.SEMANTIC_SEARCH,
            "hybrid_search": RetrievalStrategy.HYBRID_SEARCH,
            "multi_query": RetrievalStrategy.MULTI_QUERY,
            "query_reformulation": RetrievalStrategy.QUERY_REFORMULATION,
            "reranking": RetrievalStrategy.RERANKING
        }

        return RetrievalConfig(
            strategy=strategy_map.get(self.config.retrieval_strategy, RetrievalStrategy.SEMANTIC_SEARCH),
            max_results=self.config.retrieval_max_results,
            score_threshold=self.config.retrieval_score_threshold,
            enable_fallback=self.config.retrieval_enable_fallback
        )

    def _create_context_config(self) -> ContextConfig:
        """创建上下文配置"""
        compression_map = {
            "none": ContextCompressionStrategy.NONE,
            "truncate": ContextCompressionStrategy.TRUNCATE,
            "summarize": ContextCompressionStrategy.SUMMARIZE,
            "key_extraction": ContextCompressionStrategy.KEY_EXTRACTION,
            "hierarchical": ContextCompressionStrategy.HIERARCHICAL
        }

        optimization_map = {
            "relevance_based": ContextOptimization.RELEVANCE_BASED,
            "diversity_based": ContextOptimization.DIVERSITY_BASED,
            "coverage_based": ContextOptimization.COVERAGE_BASED,
            "quality_based": ContextOptimization.QUALITY_BASED
        }

        return ContextConfig(
            max_context_length=self.config.context_max_length,
            compression_strategy=compression_map.get(self.config.context_compression_strategy, ContextCompressionStrategy.TRUNCATE),
            optimization_strategy=optimization_map.get(self.config.context_optimization_strategy, ContextOptimization.RELEVANCE_BASED),
            enable_deduplication=self.config.context_enable_deduplication,
            enable_semantic_clustering=self.config.context_enable_semantic_clustering
        )

    def _create_pipeline_config(self) -> PipelineConfig:
        """创建管道配置"""
        return PipelineConfig(
            retrieval_config=self._create_retrieval_config(),
            context_config=self._create_context_config(),
            max_total_tokens=self.config.pipeline_max_tokens,
            enable_caching=self.config.pipeline_enable_caching,
            enable_monitoring=self.config.pipeline_enable_monitoring,
            timeout=self.config.pipeline_timeout,
            max_retries=self.config.pipeline_max_retries
        )

    def _create_scoring_config(self) -> ScoringConfig:
        """创建评分配置"""
        method_map = {
            "cosine_similarity": ScoringMethod.COSINE_SIMILARITY,
            "bm25": ScoringMethod.BM25,
            "jaccard": ScoringMethod.JACCARD,
            "edit_distance": ScoringMethod.EDIT_DISTANCE,
            "semantic_similarity": ScoringMethod.SEMANTIC_SIMILARITY,
            "hybrid": ScoringMethod.HYBRID
        }

        return ScoringConfig(
            primary_method=method_map.get(self.config.scoring_primary_method, ScoringMethod.HYBRID),
            enable_quality_metrics=self.config.scoring_enable_quality_metrics,
            enable_temporal_decay=self.config.scoring_enable_temporal_decay,
            min_confidence=self.config.scoring_min_confidence
        )

    async def query(self, query: str, model: str = None, pipeline_name: str = None) -> PipelineResult:
        """执行RAG查询"""
        if not self._initialized:
            await self.initialize()

        if not self._initialized:
            raise RuntimeError("RAG系统未初始化")

        start_time = datetime.now()
        model = model or self.config.default_model

        try:
            # 更新查询计数
            self._performance_metrics['total_queries'] += 1

            # 执行查询
            if pipeline_name:
                pipeline = self.pipeline_manager.get_pipeline(pipeline_name)
                if not pipeline:
                    raise ValueError(f"管道不存在: {pipeline_name}")
                result = await pipeline.execute(query, model)
            else:
                result = await self.pipeline_manager.execute_default(query, model)

            # 更新成功计数
            if result.status.value == "completed":
                self._performance_metrics['successful_queries'] += 1
            else:
                self._performance_metrics['failed_queries'] += 1

            # 更新响应时间
            response_time = (datetime.now() - start_time).total_seconds()
            self._update_average_response_time(response_time)

            # 更新缓存统计
            if hasattr(result, 'metadata') and 'cached' in result.metadata:
                if result.metadata['cached']:
                    self._performance_metrics['cache_hits'] += 1
                else:
                    self._performance_metrics['cache_misses'] += 1

            logger.info(f"RAG查询完成，响应时间: {response_time:.2f}秒")
            return result

        except Exception as e:
            logger.error(f"RAG查询失败: {str(e)}")
            self._performance_metrics['failed_queries'] += 1
            raise

    async def query_batch(self, queries: List[str], model: str = None, pipeline_name: str = None) -> List[PipelineResult]:
        """批量执行RAG查询"""
        if not self._initialized:
            await self.initialize()

        if not self._initialized:
            raise RuntimeError("RAG系统未初始化")

        model = model or self.config.default_model

        try:
            if pipeline_name:
                pipeline = self.pipeline_manager.get_pipeline(pipeline_name)
                if not pipeline:
                    raise ValueError(f"管道不存在: {pipeline_name}")
                results = await pipeline.execute_batch(queries, model)
            else:
                # 使用默认管道批量查询
                pipeline = self.pipeline_manager.get_pipeline(self.pipeline_manager._default_pipeline)
                results = await pipeline.execute_batch(queries, model)

            logger.info(f"批量RAG查询完成，处理了 {len(queries)} 个查询")
            return results

        except Exception as e:
            logger.error(f"批量RAG查询失败: {str(e)}")
            raise

    async def add_documents(self, documents: List[str], metadatas: List[Dict[str, Any]] = None) -> bool:
        """添加文档到向量数据库"""
        if not self._initialized:
            await self.initialize()

        if not self._initialized:
            raise RuntimeError("RAG系统未初始化")

        try:
            success = await self.vector_db.add_documents(documents, metadatas)
            if success:
                logger.info(f"成功添加 {len(documents)} 个文档到向量数据库")
            return success

        except Exception as e:
            logger.error(f"添加文档失败: {str(e)}")
            return False

    async def search_documents(self, query: str, n_results: int = 10) -> List[Dict[str, Any]]:
        """搜索文档"""
        if not self._initialized:
            await self.initialize()

        if not self._initialized:
            raise RuntimeError("RAG系统未初始化")

        try:
            results = await self.vector_db.search(query, n_results=n_results)
            logger.info(f"文档搜索完成，返回 {len(results)} 个结果")
            return results

        except Exception as e:
            logger.error(f"文档搜索失败: {str(e)}")
            return []

    async def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        try:
            info = {
                'initialized': self._initialized,
                'config': asdict(self.config),
                'performance_metrics': self._performance_metrics.copy(),
                'component_status': {},
                'timestamp': datetime.now().isoformat()
            }

            if self._initialized:
                # 向量数据库信息
                if self.vector_db:
                    info['component_status']['vector_db'] = {
                        'initialized': self.vector_db.is_initialized(),
                        'collection_info': await self.vector_db.get_collection_info()
                    }

                # 向量化服务信息
                if self.vectorization_service:
                    info['component_status']['vectorization'] = {
                        'performance_metrics': self.vectorization_service.get_performance_metrics()
                    }

                # LLM管理器信息
                if self.llm_manager:
                    info['component_status']['llm'] = {
                        'health_status': await self.llm_manager.get_health_status(),
                        'cost_monitor': self.llm_manager.get_cost_monitor_status()
                    }

                # 管道管理器信息
                if self.pipeline_manager:
                    info['component_status']['pipeline'] = {
                        'pipelines': self.pipeline_manager.list_pipelines(),
                        'metrics': self.pipeline_manager.get_pipeline_metrics()
                    }

                # 检索管理器信息
                if self.retrieval_manager:
                    info['component_status']['retrieval'] = {
                        'performance_metrics': self.retrieval_manager.get_performance_metrics(),
                        'strategies': await self.retrieval_manager.get_retrieval_strategies()
                    }

                # 上下文管理器信息
                if self.context_manager:
                    info['component_status']['context'] = {
                        'cache_stats': self.context_manager.get_cache_stats()
                    }

                # 提示词系统信息
                if self.prompt_system:
                    info['component_status']['prompts'] = {
                        'template_count': len(self.prompt_system.get_template_manager().list_templates()),
                        'scorer_info': self.document_scorer.get_scorer_info() if self.document_scorer else {}
                    }

            return info

        except Exception as e:
            logger.error(f"获取系统信息失败: {str(e)}")
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}

    async def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        try:
            metrics = {
                'system_metrics': self._performance_metrics.copy(),
                'component_metrics': {},
                'timestamp': datetime.now().isoformat()
            }

            if self._initialized:
                # 系统运行时间
                if self._init_start_time:
                    uptime = (datetime.now() - self._init_start_time).total_seconds()
                    metrics['system_metrics']['system_uptime'] = uptime

                # 组件指标
                if self.vector_db:
                    metrics['component_metrics']['vector_db'] = await self.vector_db.get_performance_metrics()

                if self.vectorization_service:
                    metrics['component_metrics']['vectorization'] = self.vectorization_service.get_performance_metrics()

                if self.llm_manager:
                    metrics['component_metrics']['llm'] = {
                        'health_status': await self.llm_manager.get_health_status(),
                        'cost_monitor': self.llm_manager.get_cost_monitor_status()
                    }

                if self.pipeline_manager:
                    metrics['component_metrics']['pipeline'] = self.pipeline_manager.get_pipeline_metrics()

                if self.retrieval_manager:
                    metrics['component_metrics']['retrieval'] = self.retrieval_manager.get_performance_metrics()

                if self.document_scorer:
                    metrics['component_metrics']['scoring'] = self.document_scorer.get_performance_metrics()

            return metrics

        except Exception as e:
            logger.error(f"获取性能指标失败: {str(e)}")
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}

    def _update_average_response_time(self, response_time: float):
        """更新平均响应时间"""
        total_queries = self._performance_metrics['total_queries']
        current_avg = self._performance_metrics['average_response_time']
        self._performance_metrics['average_response_time'] = (current_avg * (total_queries - 1) + response_time) / total_queries

    async def reset_metrics(self):
        """重置性能指标"""
        try:
            # 重置系统指标
            self._performance_metrics = {
                'total_queries': 0,
                'successful_queries': 0,
                'failed_queries': 0,
                'average_response_time': 0.0,
                'cache_hits': 0,
                'cache_misses': 0,
                'system_uptime': 0.0
            }

            # 重置组件指标
            if self.vector_db:
                await self.vector_db.reset_performance_metrics()

            if self.vectorization_service:
                self.vectorization_service.reset_performance_metrics()

            if self.pipeline_manager:
                self.pipeline_manager.reset_metrics()

            if self.retrieval_manager:
                # 重置检索管理器指标
                self.retrieval_manager._performance_metrics = {
                    'total_retrievals': 0,
                    'successful_retrievals': 0,
                    'failed_retrievals': 0,
                    'average_retrieval_time': 0.0,
                    'strategy_usage': {}
                }

            logger.info("RAG系统性能指标已重置")

        except Exception as e:
            logger.error(f"重置性能指标失败: {str(e)}")

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            health_status = {
                'status': 'healthy',
                'components': {},
                'timestamp': datetime.now().isoformat()
            }

            if not self._initialized:
                health_status['status'] = 'not_initialized'
                return health_status

            # 检查向量数据库
            if self.vector_db:
                health_status['components']['vector_db'] = {
                    'status': 'healthy' if self.vector_db.is_initialized() else 'unhealthy'
                }
            else:
                health_status['components']['vector_db'] = {'status': 'missing'}

            # 检查向量化服务
            if self.vectorization_service:
                health_status['components']['vectorization'] = {'status': 'healthy'}
            else:
                health_status['components']['vectorization'] = {'status': 'missing'}

            # 检查LLM管理器
            if self.llm_manager:
                try:
                    llm_health = await self.llm_manager.get_health_status()
                    health_status['components']['llm'] = {
                        'status': 'healthy' if llm_health.get('overall_healthy', False) else 'unhealthy'
                    }
                except Exception:
                    health_status['components']['llm'] = {'status': 'unhealthy'}
            else:
                health_status['components']['llm'] = {'status': 'missing'}

            # 检查管道管理器
            if self.pipeline_manager:
                health_status['components']['pipeline'] = {'status': 'healthy'}
            else:
                health_status['components']['pipeline'] = {'status': 'missing'}

            # 确定整体状态
            unhealthy_components = [
                name for name, info in health_status['components'].items()
                if info['status'] == 'unhealthy'
            ]

            if unhealthy_components:
                health_status['status'] = 'degraded'
                health_status['unhealthy_components'] = unhealthy_components

            return health_status

        except Exception as e:
            logger.error(f"健康检查失败: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    async def shutdown(self):
        """关闭RAG系统"""
        try:
            logger.info("开始关闭RAG系统...")

            # 清理缓存
            if self.pipeline_manager:
                self.pipeline_manager.clear_cache()

            if self.context_manager:
                self.context_manager.clear_cache()

            if self.prompt_system:
                self.prompt_system.renderer.clear_cache()

            logger.info("RAG系统已关闭")

        except Exception as e:
            logger.error(f"关闭RAG系统失败: {str(e)}")

    def update_config(self, new_config: RAGSystemConfig):
        """更新配置"""
        try:
            self.config = new_config
            logger.info("RAG系统配置已更新")

            # 重新创建配置对象
            if self._initialized:
                # 更新现有配置
                pass

        except Exception as e:
            logger.error(f"更新配置失败: {str(e)}")

    def get_config(self) -> Dict[str, Any]:
        """获取当前配置"""
        return asdict(self.config)


# 全局RAG系统实例
rag_system = RAGSystem()


async def get_rag_system() -> RAGSystem:
    """获取RAG系统实例"""
    return rag_system


async def initialize_rag_system(config: RAGSystemConfig = None) -> RAGSystem:
    """初始化RAG系统"""
    global rag_system
    rag_system = RAGSystem(config)
    if await rag_system.initialize():
        return rag_system
    else:
        raise RuntimeError("RAG系统初始化失败")