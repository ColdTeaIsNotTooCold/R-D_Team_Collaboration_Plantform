"""
向量化服务模块
提供文本嵌入生成、缓存和批量处理功能
"""

from .service import VectorizationService, get_vectorization_service

__all__ = ['VectorizationService', 'get_vectorization_service']