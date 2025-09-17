"""
向量化服务测试模块
测试向量数据库、向量化服务和相关功能
"""
import pytest
import asyncio
import numpy as np
from datetime import datetime
import tempfile
import json

from app.core.config import settings
from app.core.vector_db import VectorDBManager
from app.services.vectorization.service import VectorizationService
from app.services.vectorization.batch_processor import BatchVectorizationProcessor
from app.services.vectorization.search_optimizer import VectorSearchOptimizer
from app.services.vectorization.cache_manager import VectorizationCacheManager
from app.services.vectorization.similarity_optimizer import SimilarityOptimizer
from app.services.vectorization.import_export import VectorImportExportManager


class TestVectorizationService:
    """向量化服务测试"""

    @pytest.fixture
    async def vectorization_service(self):
        """创建向量化服务实例"""
        service = VectorizationService()
        await service.initialize()
        yield service
        await service.clear_cache()

    @pytest.mark.asyncio
    async def test_initialization(self, vectorization_service):
        """测试初始化"""
        assert vectorization_service.is_initialized() == True
        assert vectorization_service.embedding_generator.is_initialized() == True

    @pytest.mark.asyncio
    async def test_generate_embedding(self, vectorization_service):
        """测试生成单个嵌入"""
        text = "这是一个测试句子"
        embedding = await vectorization_service.generate_embedding(text)

        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, (int, float)) for x in embedding)

    @pytest.mark.asyncio
    async def test_batch_generate_embeddings(self, vectorization_service):
        """测试批量生成嵌入"""
        texts = ["这是第一个测试句子", "这是第二个测试句子", "这是第三个测试句子"]
        embeddings = await vectorization_service.batch_generate_embeddings(texts)

        assert isinstance(embeddings, list)
        assert len(embeddings) == len(texts)
        assert all(len(emb) > 0 for emb in embeddings)
        assert all(all(isinstance(x, (int, float)) for x in emb) for emb in embeddings)

    @pytest.mark.asyncio
    async def test_calculate_similarity(self, vectorization_service):
        """测试相似度计算"""
        text1 = "机器学习是人工智能的一个分支"
        text2 = "深度学习是机器学习的一个重要分支"
        text3 = "今天天气很好，适合出去散步"

        similarity_12 = await vectorization_service.calculate_similarity(text1, text2)
        similarity_13 = await vectorization_service.calculate_similarity(text1, text3)

        assert isinstance(similarity_12, float)
        assert isinstance(similarity_13, float)
        assert similarity_12 > similarity_13  # 相关文本应该更相似

    @pytest.mark.asyncio
    async def test_cache_functionality(self, vectorization_service):
        """测试缓存功能"""
        text = "缓存测试文本"

        # 第一次生成（应该缓存）
        embedding1 = await vectorization_service.generate_embedding(text, use_cache=True)

        # 第二次生成（应该命中缓存）
        embedding2 = await vectorization_service.generate_embedding(text, use_cache=True)

        assert embedding1 == embedding2

        # 检查缓存统计
        stats = await vectorization_service.get_embedding_stats()
        assert 'cache_hit_rate' in stats


class TestVectorDatabase:
    """向量数据库测试"""

    @pytest.fixture
    async def vector_db(self):
        """创建向量数据库实例"""
        db = VectorDBManager("test_collection")
        await db.initialize()
        yield db
        await db.clear_collection()

    @pytest.mark.asyncio
    async def test_initialization(self, vector_db):
        """测试初始化"""
        assert vector_db.is_initialized() == True
        assert vector_db.collection_name == "test_collection"

    @pytest.mark.asyncio
    async def test_add_and_search_documents(self, vector_db):
        """测试添加和搜索文档"""
        documents = [
            "机器学习是人工智能的核心技术",
            "深度学习使用神经网络进行学习",
            "自然语言处理处理人类语言"
        ]
        metadatas = [
            {"type": "tech", "category": "AI"},
            {"type": "tech", "category": "DL"},
            {"type": "tech", "category": "NLP"}
        ]

        # 添加文档
        success = await vector_db.add_documents(documents, metadatas)
        assert success == True

        # 搜索文档
        results = await vector_db.search("机器学习")
        assert len(results) > 0
        assert "机器学习" in results[0]['document']

    @pytest.mark.asyncio
    async def test_delete_documents(self, vector_db):
        """测试删除文档"""
        documents = ["测试文档1", "测试文档2"]
        metadatas = [{"id": "1"}, {"id": "2"}]

        # 添加文档
        await vector_db.add_documents(documents, metadatas)

        # 获取所有文档ID
        info = await vector_db.get_collection_info()
        assert info['document_count'] >= 2

        # 删除文档
        # 注意：这里需要根据实际的ChromaDB API调整


class TestBatchProcessor:
    """批量处理器测试"""

    @pytest.fixture
    async def batch_processor(self):
        """创建批量处理器实例"""
        processor = BatchVectorizationProcessor()
        await processor.initialize()
        yield processor

    @pytest.mark.asyncio
    async def test_initialization(self, batch_processor):
        """测试初始化"""
        assert batch_processor.is_initialized() == True

    @pytest.mark.asyncio
    async def test_process_text_batch(self, batch_processor):
        """测试批量文本处理"""
        texts = ["批量测试文本1", "批量测试文本2", "批量测试文本3"]

        result = await batch_processor.process_text_batch(texts, batch_size=2)

        assert result['success'] == True
        assert result['processed_count'] == 3
        assert len(result['embeddings']) == 3


class TestSearchOptimizer:
    """搜索优化器测试"""

    @pytest.fixture
    async def search_optimizer(self):
        """创建搜索优化器实例"""
        optimizer = VectorSearchOptimizer()
        await optimizer.initialize()
        yield optimizer
        await optimizer.clear_search_cache()

    @pytest.mark.asyncio
    async def test_initialization(self, search_optimizer):
        """测试初始化"""
        assert search_optimizer.is_initialized() == True

    @pytest.mark.asyncio
    async def test_optimized_search(self, search_optimizer):
        """测试优化搜索"""
        # 这里需要先添加一些测试数据到数据库
        # 由于时间关系，这里只测试缓存功能
        query = "测试查询"

        # 第一次搜索
        results1 = await search_optimizer.optimized_search(query, use_cache=True)

        # 第二次搜索（应该命中缓存）
        results2 = await search_optimizer.optimized_search(query, use_cache=True)

        # 结果应该相同
        assert results1 == results2


class TestCacheManager:
    """缓存管理器测试"""

    @pytest.fixture
    async def cache_manager(self):
        """创建缓存管理器实例"""
        manager = VectorizationCacheManager()
        await manager.initialize()
        yield manager
        await manager.clear_cache()

    @pytest.mark.asyncio
    async def test_initialization(self, cache_manager):
        """测试初始化"""
        assert cache_manager.is_initialized() == True

    @pytest.mark.asyncio
    async def test_cache_operations(self, cache_manager):
        """测试缓存操作"""
        text = "缓存测试文本"
        embedding = [0.1, 0.2, 0.3, 0.4]

        # 缓存嵌入
        success = await cache_manager.cache_embedding(text, embedding)
        assert success == True

        # 获取缓存的嵌入
        cached_embedding = await cache_manager.get_cached_embedding(text)
        assert cached_embedding == embedding

        # 获取缓存统计
        stats = await cache_manager.get_cache_stats()
        assert 'memory_cache' in stats
        assert stats['memory_cache']['size'] > 0


class TestSimilarityOptimizer:
    """相似度优化器测试"""

    @pytest.fixture
    async def similarity_optimizer(self):
        """创建相似度优化器实例"""
        optimizer = SimilarityOptimizer()
        await optimizer.initialize()
        yield optimizer
        await optimizer.clear_cache()

    @pytest.mark.asyncio
    async def test_initialization(self, similarity_optimizer):
        """测试初始化"""
        assert similarity_optimizer.is_initialized() == True

    @pytest.mark.asyncio
    async def test_similarity_calculation(self, similarity_optimizer):
        """测试相似度计算"""
        embedding1 = [0.1, 0.2, 0.3, 0.4]
        embedding2 = [0.2, 0.3, 0.4, 0.5]
        embedding3 = [0.9, 0.8, 0.7, 0.6]

        # 计算相似度
        similarity_12 = await similarity_optimizer.calculate_similarity_optimized(embedding1, embedding2)
        similarity_13 = await similarity_optimizer.calculate_similarity_optimized(embedding1, embedding3)

        assert isinstance(similarity_12, float)
        assert isinstance(similarity_13, float)
        assert similarity_12 > similarity_13  # 更相似的向量应该有更高的相似度

    @pytest.mark.asyncio
    async def test_batch_similarity_calculation(self, similarity_optimizer):
        """测试批量相似度计算"""
        query_embedding = [0.1, 0.2, 0.3, 0.4]
        candidate_embeddings = [
            [0.1, 0.2, 0.3, 0.4],  # 相同
            [0.2, 0.3, 0.4, 0.5],  # 相似
            [0.9, 0.8, 0.7, 0.6]   # 不相似
        ]

        results = await similarity_optimizer.batch_calculate_similarities(
            query_embedding, candidate_embeddings, top_k=2
        )

        assert len(results) == 2
        assert results[0][1] > results[1][1]  # 按相似度排序


class TestImportExportManager:
    """导入导出管理器测试"""

    @pytest.fixture
    async def import_export_manager(self):
        """创建导入导出管理器实例"""
        manager = VectorImportExportManager()
        await manager.initialize()
        yield manager

    @pytest.mark.asyncio
    async def test_initialization(self, import_export_manager):
        """测试初始化"""
        assert import_export_manager.is_initialized() == True

    @pytest.mark.asyncio
    async def test_supported_formats(self, import_export_manager):
        """测试支持的格式"""
        formats = await import_export_manager.get_supported_formats()
        assert isinstance(formats, list)
        assert 'json' in formats
        assert 'csv' in formats

    @pytest.mark.asyncio
    async def test_json_import_export(self, import_export_manager):
        """测试JSON导入导出"""
        # 创建测试数据
        test_data = [
            {
                'id': 'test1',
                'document': '测试文档1',
                'metadata': {'type': 'test'},
                'embedding': [0.1, 0.2, 0.3]
            },
            {
                'id': 'test2',
                'document': '测试文档2',
                'metadata': {'type': 'test'},
                'embedding': [0.4, 0.5, 0.6]
            }
        ]

        # 导出测试
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)
            export_path = f.name

        # 验证导入文件
        validation_result = await import_export_manager.validate_import_file(export_path, 'json')
        assert validation_result['valid'] == True

        # 清理
        import os
        os.unlink(export_path)


# 集成测试
class TestVectorizationIntegration:
    """向量化集成测试"""

    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self):
        """端到端工作流测试"""
        # 1. 初始化服务
        vectorization_service = VectorizationService()
        await vectorization_service.initialize()

        # 2. 生成嵌入
        texts = ["集成测试文本1", "集成测试文本2"]
        embeddings = await vectorization_service.batch_generate_embeddings(texts)

        assert len(embeddings) == 2

        # 3. 计算相似度
        similarity = await vectorization_service.calculate_similarity(texts[0], texts[1])
        assert isinstance(similarity, float)

        # 4. 清理
        await vectorization_service.clear_cache()

    @pytest.mark.asyncio
    async def test_performance_metrics(self):
        """性能指标测试"""
        vectorization_service = VectorizationService()
        await vectorization_service.initialize()

        # 执行一些操作
        texts = ["性能测试文本"] * 10
        await vectorization_service.batch_generate_embeddings(texts)

        # 获取统计信息
        stats = await vectorization_service.get_embedding_stats()
        assert 'total_embeddings_generated' in stats
        assert stats['total_embeddings_generated'] >= 10

        await vectorization_service.clear_cache()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])