"""
向量化缓存管理模块
提供智能缓存策略、缓存优化和缓存清理功能
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
import asyncio
import time
import hashlib
import json
from datetime import datetime, timedelta
from collections import defaultdict, OrderedDict
import numpy as np
from ..core.config import settings
from ..core.redis import get_redis
from .service import VectorizationService

logger = logging.getLogger(__name__)


class VectorizationCacheManager:
    """向量化缓存管理器"""

    def __init__(self, max_memory_size: int = 100 * 1024 * 1024):  # 100MB
        self.vectorization_service = VectorizationService()
        self.max_memory_size = max_memory_size
        self._initialized = False

        # 内存缓存
        self._memory_cache = OrderedDict()
        self._cache_stats = defaultdict(int)
        self._cache_metadata = {}

        # Redis缓存
        self._redis_enabled = False
        self._redis_client = None

        # 缓存策略配置
        self._cache_config = {
            'ttl': settings.embedding_cache_ttl,
            'max_size': 10000,
            'cleanup_interval': 300,  # 5分钟
            'memory_threshold': 0.8,  # 80%内存使用率时清理
            'hit_rate_threshold': 0.5,  # 命中率低于50%时调整策略
        }

        # 性能监控
        self._performance_metrics = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'memory_hits': 0,
            'redis_hits': 0,
            'average_cache_time': 0.0,
            'cleanup_count': 0,
            'last_cleanup': None,
            'eviction_count': 0,
            'current_size': 0,
            'hit_rate': 0.0
        }

    async def initialize(self) -> bool:
        """初始化缓存管理器"""
        try:
            if not await self.vectorization_service.initialize():
                logger.error("向量化服务初始化失败")
                return False

            # 初始化Redis缓存
            try:
                self._redis_client = get_redis()
                await self._redis_client.ping()
                self._redis_enabled = True
                logger.info("Redis缓存已启用")
            except Exception as e:
                logger.warning(f"Redis缓存不可用，仅使用内存缓存: {str(e)}")
                self._redis_enabled = False

            self._initialized = True
            logger.info("向量化缓存管理器初始化成功")
            return True

        except Exception as e:
            logger.error(f"向量化缓存管理器初始化失败: {str(e)}")
            return False

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized

    def _generate_cache_key(self, content: str, cache_type: str, metadata: Dict[str, Any] = None) -> str:
        """生成缓存键"""
        meta_str = json.dumps(metadata, sort_keys=True) if metadata else "none"
        full_content = f"{cache_type}:{content}:{meta_str}"
        return hashlib.md5(full_content.encode('utf-8')).hexdigest()

    def _estimate_memory_usage(self, data: Any) -> int:
        """估算内存使用量"""
        try:
            if isinstance(data, (list, np.ndarray)):
                return len(data) * 8  # 假设每个float64占8字节
            elif isinstance(data, str):
                return len(data.encode('utf-8'))
            elif isinstance(data, dict):
                return len(json.dumps(data).encode('utf-8'))
            else:
                return len(str(data).encode('utf-8'))
        except:
            return 1024  # 默认估算

    async def get_cached_embedding(self, text: str, metadata: Dict[str, Any] = None) -> Optional[List[float]]:
        """获取缓存的嵌入向量"""
        if not self.is_initialized():
            return None

        start_time = time.time()
        self._performance_metrics['total_requests'] += 1

        cache_key = self._generate_cache_key(text, "embedding", metadata)

        # 1. 检查内存缓存
        if cache_key in self._memory_cache:
            cache_entry = self._memory_cache[cache_key]
            if self._is_cache_entry_valid(cache_entry):
                # 移到最近使用（LRU）
                self._memory_cache.move_to_end(cache_key)
                self._performance_metrics['cache_hits'] += 1
                self._performance_metrics['memory_hits'] += 1
                self._cache_stats['memory_hits'] += 1
                self._update_access_time(cache_key)
                logger.debug(f"内存缓存命中: {cache_key}")
                return cache_entry['data']
            else:
                # 清理过期缓存
                self._remove_cache_entry(cache_key)

        # 2. 检查Redis缓存
        if self._redis_enabled:
            redis_result = await self._get_from_redis(cache_key)
            if redis_result:
                self._performance_metrics['cache_hits'] += 1
                self._performance_metrics['redis_hits'] += 1
                self._cache_stats['redis_hits'] += 1
                # 回填到内存缓存
                await self._add_to_memory_cache(cache_key, redis_result, "embedding")
                logger.debug(f"Redis缓存命中: {cache_key}")
                return redis_result

        # 缓存未命中
        self._performance_metrics['cache_misses'] += 1
        self._cache_stats['misses'] += 1

        # 更新性能指标
        operation_time = time.time() - start_time
        self._update_performance_metrics(operation_time)

        return None

    async def cache_embedding(self, text: str, embedding: List[float], metadata: Dict[str, Any] = None) -> bool:
        """缓存嵌入向量"""
        if not self.is_initialized():
            return False

        try:
            cache_key = self._generate_cache_key(text, "embedding", metadata)

            # 添加到内存缓存
            success = await self._add_to_memory_cache(cache_key, embedding, "embedding")

            # 添加到Redis缓存
            if self._redis_enabled:
                redis_success = await self._add_to_redis(cache_key, embedding, "embedding")
                success = success and redis_success

            return success

        except Exception as e:
            logger.error(f"缓存嵌入向量失败: {str(e)}")
            return False

    async def _add_to_memory_cache(self, key: str, data: Any, cache_type: str) -> bool:
        """添加到内存缓存"""
        try:
            # 检查内存使用量
            data_size = self._estimate_memory_usage(data)
            if self._get_current_memory_usage() + data_size > self.max_memory_size:
                # 执行清理
                await self._cleanup_memory_cache()

            cache_entry = {
                'data': data,
                'type': cache_type,
                'created_at': datetime.now(),
                'last_accessed': datetime.now(),
                'access_count': 1,
                'size': data_size,
                'ttl': self._cache_config['ttl']
            }

            # 如果缓存已满，移除最旧的条目
            if len(self._memory_cache) >= self._cache_config['max_size']:
                oldest_key = next(iter(self._memory_cache))
                self._remove_cache_entry(oldest_key)

            self._memory_cache[key] = cache_entry
            self._performance_metrics['current_size'] += data_size

            return True

        except Exception as e:
            logger.error(f"添加到内存缓存失败: {str(e)}")
            return False

    async def _add_to_redis(self, key: str, data: Any, cache_type: str) -> bool:
        """添加到Redis缓存"""
        if not self._redis_enabled:
            return False

        try:
            cache_data = {
                'data': data,
                'type': cache_type,
                'created_at': datetime.now().isoformat(),
                'size': self._estimate_memory_usage(data)
            }

            # 序列化数据
            serialized_data = json.dumps(cache_data, ensure_ascii=False)

            # 存储到Redis，设置TTL
            await self._redis_client.setex(
                f"vector_cache:{key}",
                self._cache_config['ttl'],
                serialized_data
            )

            return True

        except Exception as e:
            logger.error(f"添加到Redis缓存失败: {str(e)}")
            return False

    async def _get_from_redis(self, key: str) -> Optional[Any]:
        """从Redis获取缓存"""
        if not self._redis_enabled:
            return None

        try:
            serialized_data = await self._redis_client.get(f"vector_cache:{key}")
            if serialized_data:
                cache_data = json.loads(serialized_data)
                return cache_data['data']
            return None

        except Exception as e:
            logger.error(f"从Redis获取缓存失败: {str(e)}")
            return None

    def _is_cache_entry_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """检查缓存条目是否有效"""
        try:
            # 检查TTL
            if 'ttl' in cache_entry and cache_entry['ttl'] > 0:
                expiry_time = cache_entry['created_at'] + timedelta(seconds=cache_entry['ttl'])
                if datetime.now() > expiry_time:
                    return False

            return True

        except Exception:
            return False

    def _remove_cache_entry(self, key: str) -> None:
        """移除缓存条目"""
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            self._performance_metrics['current_size'] -= entry['size']
            del self._memory_cache[key]
            self._performance_metrics['eviction_count'] += 1

    def _get_current_memory_usage(self) -> int:
        """获取当前内存使用量"""
        return sum(entry['size'] for entry in self._memory_cache.values())

    def _update_access_time(self, key: str) -> None:
        """更新访问时间"""
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            entry['last_accessed'] = datetime.now()
            entry['access_count'] += 1

    def _update_performance_metrics(self, operation_time: float) -> None:
        """更新性能指标"""
        self._performance_metrics['average_cache_time'] = (
            self._performance_metrics['average_cache_time'] * (self._performance_metrics['total_requests'] - 1) + operation_time
        ) / self._performance_metrics['total_requests']

        self._performance_metrics['hit_rate'] = (
            self._performance_metrics['cache_hits'] / self._performance_metrics['total_requests']
            if self._performance_metrics['total_requests'] > 0 else 0.0
        )

    async def _cleanup_memory_cache(self) -> None:
        """清理内存缓存"""
        try:
            if len(self._memory_cache) == 0:
                return

            # 1. 清理过期条目
            expired_keys = []
            for key, entry in self._memory_cache.items():
                if not self._is_cache_entry_valid(entry):
                    expired_keys.append(key)

            for key in expired_keys:
                self._remove_cache_entry(key)

            # 2. 如果仍然超过内存限制，使用LRU策略
            while (self._get_current_memory_usage() > self.max_memory_size * self._cache_config['memory_threshold'] and
                   len(self._memory_cache) > 0):
                oldest_key = next(iter(self._memory_cache))
                self._remove_cache_entry(oldest_key)

            self._performance_metrics['cleanup_count'] += 1
            self._performance_metrics['last_cleanup'] = datetime.now()

            logger.info(f"内存缓存清理完成，移除 {len(expired_keys)} 个过期条目")

        except Exception as e:
            logger.error(f"清理内存缓存失败: {str(e)}")

    async def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            memory_usage_percent = self._get_current_memory_usage() / self.max_memory_size if self.max_memory_size > 0 else 0

            stats = {
                'memory_cache': {
                    'size': len(self._memory_cache),
                    'memory_usage': self._get_current_memory_usage(),
                    'memory_usage_percent': memory_usage_percent,
                    'max_memory_size': self.max_memory_size,
                    'max_size': self._cache_config['max_size']
                },
                'redis_cache': {
                    'enabled': self._redis_enabled,
                    'status': 'connected' if self._redis_enabled else 'disabled'
                },
                'performance': self._performance_metrics,
                'config': self._cache_config,
                'cache_stats': dict(self._cache_stats),
                'timestamp': datetime.now().isoformat()
            }

            return stats

        except Exception as e:
            logger.error(f"获取缓存统计失败: {str(e)}")
            return {}

    async def clear_cache(self, cache_type: str = "all") -> bool:
        """清空缓存"""
        try:
            if cache_type in ["all", "memory"]:
                self._memory_cache.clear()
                self._performance_metrics['current_size'] = 0
                logger.info("内存缓存已清空")

            if cache_type in ["all", "redis"] and self._redis_enabled:
                # 清空Redis缓存
                keys = await self._redis_client.keys("vector_cache:*")
                if keys:
                    await self._redis_client.delete(*keys)
                logger.info(f"Redis缓存已清空，删除 {len(keys)} 个键")

            # 重置统计信息
            if cache_type == "all":
                self._performance_metrics.update({
                    'total_requests': 0,
                    'cache_hits': 0,
                    'cache_misses': 0,
                    'memory_hits': 0,
                    'redis_hits': 0,
                    'eviction_count': 0,
                    'hit_rate': 0.0
                })
                self._cache_stats.clear()

            return True

        except Exception as e:
            logger.error(f"清空缓存失败: {str(e)}")
            return False

    async def optimize_cache(self) -> bool:
        """优化缓存策略"""
        try:
            # 1. 分析缓存命中率
            hit_rate = self._performance_metrics['hit_rate']

            # 2. 根据命中率调整TTL
            if hit_rate < self._cache_config['hit_rate_threshold']:
                # 降低TTL以清理不常用的缓存
                self._cache_config['ttl'] = max(300, int(self._cache_config['ttl'] * 0.8))
                logger.info(f"缓存命中率低 ({hit_rate:.2f})，降低TTL至 {self._cache_config['ttl']} 秒")
            else:
                # 提高TTL以更好地利用缓存
                self._cache_config['ttl'] = min(3600 * 24, int(self._cache_config['ttl'] * 1.2))
                logger.info(f"缓存命中率高 ({hit_rate:.2f})，提高TTL至 {self._cache_config['ttl']} 秒")

            # 3. 执行缓存清理
            await self._cleanup_memory_cache()

            # 4. 如果使用Redis，清理Redis中的过期键
            if self._redis_enabled:
                try:
                    # 这里可以添加Redis特定的清理逻辑
                    pass
                except Exception as e:
                    logger.error(f"清理Redis缓存失败: {str(e)}")

            logger.info("缓存策略优化完成")
            return True

        except Exception as e:
            logger.error(f"优化缓存策略失败: {str(e)}")
            return False

    async def preload_cache(self, texts: List[str], metadata_list: List[Dict[str, Any]] = None) -> bool:
        """预加载缓存"""
        if not self.is_initialized():
            return False

        try:
            logger.info(f"开始预加载 {len(texts)} 个文本到缓存")

            # 批量生成嵌入
            embeddings = await self.vectorization_service.batch_generate_embeddings(
                texts=texts,
                use_cache=False  # 预加载时不使用缓存
            )

            # 批量缓存
            success_count = 0
            for i, (text, embedding) in enumerate(zip(texts, embeddings)):
                metadata = metadata_list[i] if metadata_list and i < len(metadata_list) else None
                if await self.cache_embedding(text, embedding, metadata):
                    success_count += 1

            logger.info(f"缓存预加载完成，成功缓存 {success_count}/{len(texts)} 个文本")
            return True

        except Exception as e:
            logger.error(f"预加载缓存失败: {str(e)}")
            return False


# 全局向量化缓存管理器实例
cache_manager = VectorizationCacheManager()


async def get_cache_manager() -> VectorizationCacheManager:
    """获取向量化缓存管理器实例"""
    return cache_manager