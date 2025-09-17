"""
RAG管道和数据流管理
实现完整的RAG处理管道，包括检索、上下文构建、提示词生成和响应处理
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import time
from .retrieval import RetrievalManager, RetrievalConfig, RetrievedDocument
from .context import ContextManager, ContextConfig, ContextWindow
from .prompts import PromptSystem, RenderedPrompt
from ..services.llm.manager import LLMManager
from ..services.llm.base import LLMResponse
from ..core.vector_db import VectorDBManager
from ..services.vectorization.service import VectorizationService

logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    """管道阶段"""
    RETRIEVAL = "retrieval"
    CONTEXT_BUILDING = "context_building"
    PROMPT_GENERATION = "prompt_generation"
    LLM_INFERENCE = "llm_inference"
    RESPONSE_PROCESSING = "response_processing"
    POST_PROCESSING = "post_processing"


class PipelineStatus(Enum):
    """管道状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PipelineConfig:
    """管道配置"""
    retrieval_config: RetrievalConfig = None
    context_config: ContextConfig = None
    max_total_tokens: int = 8000
    enable_caching: bool = True
    enable_monitoring: bool = True
    timeout: int = 30
    max_retries: int = 3
    enable_fallback: bool = True
    enable_parallel_processing: bool = True


@dataclass
class PipelineMetrics:
    """管道指标"""
    total_time: float = 0.0
    retrieval_time: float = 0.0
    context_building_time: float = 0.0
    prompt_generation_time: float = 0.0
    llm_inference_time: float = 0.0
    response_processing_time: float = 0.0
    documents_retrieved: int = 0
    tokens_used: int = 0
    cache_hits: int = 0
    error_count: int = 0
    success_count: int = 0


@dataclass
class PipelineResult:
    """管道结果"""
    query: str
    response: str
    documents: List[RetrievedDocument]
    context_window: ContextWindow
    prompt: RenderedPrompt
    llm_response: LLMResponse
    metrics: PipelineMetrics
    metadata: Dict[str, Any]
    status: PipelineStatus = PipelineStatus.COMPLETED
    error_message: Optional[str] = None


class PipelineStageHandler:
    """管道阶段处理器"""

    def __init__(self, name: str):
        self.name = name
        self.metrics = {
            'executions': 0,
            'successes': 0,
            'failures': 0,
            'average_time': 0.0
        }

    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行阶段"""
        start_time = time.time()
        self.metrics['executions'] += 1

        try:
            result = await self._execute_impl(context)
            execution_time = time.time() - start_time

            self.metrics['successes'] += 1
            self._update_average_time(execution_time)

            return result

        except Exception as e:
            execution_time = time.time() - start_time
            self.metrics['failures'] += 1
            self._update_average_time(execution_time)

            logger.error(f"管道阶段 {self.name} 执行失败: {str(e)}")
            raise

    async def _execute_impl(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """子类实现具体的执行逻辑"""
        raise NotImplementedError

    def _update_average_time(self, execution_time: float):
        """更新平均执行时间"""
        total_executions = self.metrics['executions']
        current_avg = self.metrics['average_time']
        self.metrics['average_time'] = (current_avg * (total_executions - 1) + execution_time) / total_executions

    def get_metrics(self) -> Dict[str, Any]:
        """获取指标"""
        return {
            'name': self.name,
            **self.metrics,
            'success_rate': self.metrics['successes'] / max(self.metrics['executions'], 1)
        }


class RetrievalStageHandler(PipelineStageHandler):
    """检索阶段处理器"""

    def __init__(self, retrieval_manager: RetrievalManager):
        super().__init__("retrieval")
        self.retrieval_manager = retrieval_manager

    async def _execute_impl(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行检索"""
        query = context['query']
        config = context.get('retrieval_config', RetrievalConfig())

        documents = await self.retrieval_manager.retrieve(query, config)

        context['documents'] = documents
        context['retrieval_time'] = time.time() - context.get('start_time', time.time())

        return context


class ContextBuildingStageHandler(PipelineStageHandler):
    """上下文构建阶段处理器"""

    def __init__(self, context_manager: ContextManager):
        super().__init__("context_building")
        self.context_manager = context_manager

    async def _execute_impl(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """构建上下文"""
        query = context['query']
        documents = context['documents']

        context_window = await self.context_manager.build_context(query, documents)

        context['context_window'] = context_window
        context['context_building_time'] = time.time() - context.get('start_time', time.time())

        return context


class PromptGenerationStageHandler(PipelineStageHandler):
    """提示词生成阶段处理器"""

    def __init__(self, prompt_system: PromptSystem):
        super().__init__("prompt_generation")
        self.prompt_system = prompt_system

    async def _execute_impl(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """生成提示词"""
        context_window = context['context_window']
        query = context['query']

        prompt = self.prompt_system.generate_rag_prompt(context_window, query)

        context['prompt'] = prompt
        context['prompt_generation_time'] = time.time() - context.get('start_time', time.time())

        return context


class LLMInferenceStageHandler(PipelineStageHandler):
    """LLM推理阶段处理器"""

    def __init__(self, llm_manager: LLMManager):
        super().__init__("llm_inference")
        self.llm_manager = llm_manager

    async def _execute_impl(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行LLM推理"""
        prompt = context['prompt']
        model = context.get('model', 'gpt-3.5-turbo')

        # 构建消息
        messages = [
            {"role": "system", "content": "你是一个专业的助手，基于提供的上下文信息回答用户问题。"},
            {"role": "user", "content": prompt.content}
        ]

        response = await self.llm_manager.generate_response(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=2000
        )

        context['llm_response'] = response
        context['llm_inference_time'] = time.time() - context.get('start_time', time.time())

        return context


class ResponseProcessingStageHandler(PipelineStageHandler):
    """响应处理阶段处理器"""

    def __init__(self):
        super().__init__("response_processing")

    async def _execute_impl(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理响应"""
        llm_response = context['llm_response']
        documents = context['documents']

        # 后处理响应
        processed_response = self._process_response(llm_response.content, documents)

        context['response'] = processed_response
        context['response_processing_time'] = time.time() - context.get('start_time', time.time())

        return context

    def _process_response(self, response: str, documents: List[RetrievedDocument]) -> str:
        """处理响应"""
        # 简单的后处理逻辑
        processed = response.strip()

        # 添加引用信息
        if documents and len(documents) > 0:
            references = []
            for i, doc in enumerate(documents[:3]):  # 只显示前3个引用
                source = doc.metadata.get('source', f'文档{i+1}')
                references.append(f"[{i+1}] {source}")

            if references:
                processed += f"\n\n参考文献：{', '.join(references)}"

        return processed


class RAGPipeline:
    """RAG管道"""

    def __init__(self, vector_db: VectorDBManager, vectorization_service: VectorizationService,
                 llm_manager: LLMManager, config: PipelineConfig = None):
        self.config = config or PipelineConfig()
        self.vector_db = vector_db
        self.vectorization_service = vectorization_service
        self.llm_manager = llm_manager

        # 初始化组件
        self.retrieval_manager = RetrievalManager(vector_db, vectorization_service)
        self.context_manager = ContextManager(self.config.context_config)
        self.prompt_system = PromptSystem()

        # 初始化阶段处理器
        self._init_stage_handlers()

        # 管道指标
        self.metrics = PipelineMetrics()
        self._pipeline_cache = {}

    def _init_stage_handlers(self):
        """初始化阶段处理器"""
        self.stages = {
            PipelineStage.RETRIEVAL: RetrievalStageHandler(self.retrieval_manager),
            PipelineStage.CONTEXT_BUILDING: ContextBuildingStageHandler(self.context_manager),
            PipelineStage.PROMPT_GENERATION: PromptGenerationStageHandler(self.prompt_system),
            PipelineStage.LLM_INFERENCE: LLMInferenceStageHandler(self.llm_manager),
            PipelineStage.RESPONSE_PROCESSING: ResponseProcessingStageHandler()
        }

    async def execute(self, query: str, model: str = "gpt-3.5-turbo",
                     pipeline_config: PipelineConfig = None) -> PipelineResult:
        """执行管道"""
        start_time = time.time()
        config = pipeline_config or self.config

        try:
            # 检查缓存
            if config.enable_caching:
                cache_key = self._generate_cache_key(query, model)
                cached_result = self._get_cached_result(cache_key)
                if cached_result:
                    logger.info("使用缓存的管道结果")
                    return cached_result

            # 准备执行上下文
            context = {
                'query': query,
                'model': model,
                'config': config,
                'retrieval_config': config.retrieval_config or RetrievalConfig(),
                'start_time': start_time,
                'pipeline_metrics': PipelineMetrics()
            }

            # 执行管道阶段
            await self._execute_stages(context)

            # 构建结果
            result = self._build_result(context, start_time)

            # 缓存结果
            if config.enable_caching:
                self._cache_result(cache_key, result)

            # 更新指标
            self._update_pipeline_metrics(result)

            logger.info(f"RAG管道执行完成，耗时: {result.metrics.total_time:.2f}秒")
            return result

        except Exception as e:
            logger.error(f"RAG管道执行失败: {str(e)}")
            return PipelineResult(
                query=query,
                response="",
                documents=[],
                context_window=None,
                prompt=None,
                llm_response=None,
                metrics=PipelineMetrics(total_time=time.time() - start_time),
                metadata={},
                status=PipelineStatus.FAILED,
                error_message=str(e)
            )

    async def _execute_stages(self, context: Dict[str, Any]):
        """执行所有阶段"""
        stage_order = [
            PipelineStage.RETRIEVAL,
            PipelineStage.CONTEXT_BUILDING,
            PipelineStage.PROMPT_GENERATION,
            PipelineStage.LLM_INFERENCE,
            PipelineStage.RESPONSE_PROCESSING
        ]

        for stage in stage_order:
            if stage in self.stages:
                logger.debug(f"执行管道阶段: {stage.value}")
                context = await self.stages[stage].execute(context)

    def _build_result(self, context: Dict[str, Any], start_time: float) -> PipelineResult:
        """构建结果"""
        end_time = time.time()
        total_time = end_time - start_time

        return PipelineResult(
            query=context['query'],
            response=context['response'],
            documents=context['documents'],
            context_window=context['context_window'],
            prompt=context['prompt'],
            llm_response=context['llm_response'],
            metrics=PipelineMetrics(
                total_time=total_time,
                retrieval_time=context.get('retrieval_time', 0),
                context_building_time=context.get('context_building_time', 0),
                prompt_generation_time=context.get('prompt_generation_time', 0),
                llm_inference_time=context.get('llm_inference_time', 0),
                response_processing_time=context.get('response_processing_time', 0),
                documents_retrieved=len(context['documents']),
                tokens_used=context['llm_response'].total_tokens if context['llm_response'] else 0
            ),
            metadata={
                'model': context['model'],
                'pipeline_config': context['config'],
                'stage_metrics': {stage.value: handler.get_metrics() for stage, handler in self.stages.items()},
                'executed_at': datetime.now().isoformat()
            }
        )

    def _generate_cache_key(self, query: str, model: str) -> str:
        """生成缓存键"""
        return f"{query}_{model}_{hash(str(self.config))}"

    def _get_cached_result(self, cache_key: str) -> Optional[PipelineResult]:
        """获取缓存结果"""
        if cache_key in self._pipeline_cache:
            cached_data = self._pipeline_cache[cache_key]
            if time.time() - cached_data['timestamp'] < 3600:  # 1小时缓存
                return cached_data['result']
            else:
                # 缓存过期，删除
                del self._pipeline_cache[cache_key]

        return None

    def _cache_result(self, cache_key: str, result: PipelineResult):
        """缓存结果"""
        self._pipeline_cache[cache_key] = {
            'result': result,
            'timestamp': time.time()
        }

        # 清理过期缓存
        self._cleanup_cache()

    def _cleanup_cache(self):
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = []

        for key, cached_data in self._pipeline_cache.items():
            if current_time - cached_data['timestamp'] > 3600:
                expired_keys.append(key)

        for key in expired_keys:
            del self._pipeline_cache[key]

    def _update_pipeline_metrics(self, result: PipelineResult):
        """更新管道指标"""
        if result.status == PipelineStatus.COMPLETED:
            self.metrics.success_count += 1
        else:
            self.metrics.error_count += 1

        # 更新平均时间
        total_executions = self.metrics.success_count + self.metrics.error_count
        current_avg = self.metrics.total_time
        new_avg = (current_avg * (total_executions - 1) + result.metrics.total_time) / total_executions
        self.metrics.total_time = new_avg

    async def execute_batch(self, queries: List[str], model: str = "gpt-3.5-turbo") -> List[PipelineResult]:
        """批量执行"""
        if self.config.enable_parallel_processing:
            # 并行处理
            tasks = []
            for query in queries:
                task = self.execute(query, model)
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理异常结果
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    processed_results.append(PipelineResult(
                        query=queries[i],
                        response="",
                        documents=[],
                        context_window=None,
                        prompt=None,
                        llm_response=None,
                        metrics=PipelineMetrics(),
                        metadata={},
                        status=PipelineStatus.FAILED,
                        error_message=str(result)
                    ))
                else:
                    processed_results.append(result)

            return processed_results
        else:
            # 顺序处理
            results = []
            for query in queries:
                result = await self.execute(query, model)
                results.append(result)
            return results

    def get_pipeline_metrics(self) -> Dict[str, Any]:
        """获取管道指标"""
        stage_metrics = {}
        for stage, handler in self.stages.items():
            stage_metrics[stage.value] = handler.get_metrics()

        return {
            'overall_metrics': asdict(self.metrics),
            'stage_metrics': stage_metrics,
            'cache_stats': {
                'cache_size': len(self._pipeline_cache),
                'cache_enabled': self.config.enable_caching
            },
            'config': asdict(self.config),
            'timestamp': datetime.now().isoformat()
        }

    def get_stage_handler(self, stage: PipelineStage) -> Optional[PipelineStageHandler]:
        """获取阶段处理器"""
        return self.stages.get(stage)

    def add_custom_stage(self, stage: PipelineStage, handler: PipelineStageHandler):
        """添加自定义阶段"""
        self.stages[stage] = handler
        logger.info(f"添加自定义管道阶段: {stage.value}")

    def clear_cache(self):
        """清理缓存"""
        self._pipeline_cache.clear()
        logger.info("RAG管道缓存已清理")

    def reset_metrics(self):
        """重置指标"""
        self.metrics = PipelineMetrics()
        for handler in self.stages.values():
            handler.metrics = {
                'executions': 0,
                'successes': 0,
                'failures': 0,
                'average_time': 0.0
            }
        logger.info("RAG管道指标已重置")


class PipelineManager:
    """管道管理器"""

    def __init__(self, vector_db: VectorDBManager, vectorization_service: VectorizationService,
                 llm_manager: LLMManager):
        self.vector_db = vector_db
        self.vectorization_service = vectorization_service
        self.llm_manager = llm_manager
        self._pipelines = {}
        self._default_pipeline = None

    def create_pipeline(self, name: str, config: PipelineConfig = None) -> RAGPipeline:
        """创建管道"""
        pipeline = RAGPipeline(self.vector_db, self.vectorization_service, self.llm_manager, config)
        self._pipelines[name] = pipeline
        logger.info(f"创建RAG管道: {name}")
        return pipeline

    def get_pipeline(self, name: str) -> Optional[RAGPipeline]:
        """获取管道"""
        return self._pipelines.get(name)

    def set_default_pipeline(self, name: str):
        """设置默认管道"""
        if name in self._pipelines:
            self._default_pipeline = name
            logger.info(f"设置默认RAG管道: {name}")

    async def execute_default(self, query: str, model: str = "gpt-3.5-turbo") -> PipelineResult:
        """执行默认管道"""
        if not self._default_pipeline:
            raise ValueError("没有设置默认管道")

        pipeline = self._pipelines[self._default_pipeline]
        return await pipeline.execute(query, model)

    def list_pipelines(self) -> List[str]:
        """列出所有管道"""
        return list(self._pipelines.keys())

    def get_pipeline_metrics(self, name: str = None) -> Dict[str, Any]:
        """获取管道指标"""
        if name:
            pipeline = self._pipelines.get(name)
            if pipeline:
                return pipeline.get_pipeline_metrics()
            return {}

        # 获取所有管道的指标
        all_metrics = {}
        for pipeline_name, pipeline in self._pipelines.items():
            all_metrics[pipeline_name] = pipeline.get_pipeline_metrics()

        return all_metrics

    def remove_pipeline(self, name: str) -> bool:
        """删除管道"""
        if name in self._pipelines:
            del self._pipelines[name]
            if self._default_pipeline == name:
                self._default_pipeline = None
            logger.info(f"删除RAG管道: {name}")
            return True
        return False