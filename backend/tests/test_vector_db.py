"""
ChromaDB向量数据库集成测试
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
import sys
import os

# 添加应用路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.vector_db import VectorDBManager
from app.core.embeddings import EmbeddingGenerator, TextChunker


class TestVectorDBManager:
    """向量数据库管理器测试"""

    @pytest.fixture
    def vector_db(self):
        """创建向量数据库管理器实例"""
        return VectorDBManager("test_collection")

    @pytest.mark.asyncio
    async def test_initialization(self, vector_db):
        """测试初始化"""
        # 模拟chromadb客户端
        mock_client = MagicMock()
        mock_collection = MagicMock()

        # 模拟chromadb.Client
        with pytest.MonkeyPatch().context() as m:
            import chromadb
            mock_chromadb = MagicMock()
            mock_chromadb.Client.return_value = mock_client
            mock_client.get_collection.side_effect = Exception("Collection not found")
            mock_client.create_collection.return_value = mock_collection
            m.setattr(chromadb, "Client", mock_chromadb)

            result = await vector_db.initialize()
            assert result is True
            assert vector_db._initialized is True
            assert vector_db.collection == mock_collection

    @pytest.mark.asyncio
    async def test_add_documents(self, vector_db):
        """测试添加文档"""
        # 设置已初始化状态
        vector_db._initialized = True
        vector_db.collection = MagicMock()

        # 测试添加文档
        documents = ["测试文档1", "测试文档2"]
        metadatas = [{"source": "test1"}, {"source": "test2"}]
        ids = ["doc1", "doc2"]

        result = await vector_db.add_documents(documents, metadatas, ids)

        assert result is True
        vector_db.collection.add.assert_called_once_with(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    @pytest.mark.asyncio
    async def test_search(self, vector_db):
        """测试搜索功能"""
        # 设置已初始化状态
        vector_db._initialized = True
        vector_db.collection = MagicMock()

        # 模拟搜索结果
        mock_results = {
            'documents': [['文档1', '文档2']],
            'metadatas': [[{'source': 'test1'}, {'source': 'test2'}]],
            'ids': [['id1', 'id2']],
            'distances': [[0.1, 0.2]]
        }
        vector_db.collection.query.return_value = mock_results

        # 执行搜索
        results = await vector_db.search("测试查询", n_results=2)

        assert len(results) == 2
        assert results[0]['document'] == '文档1'
        assert results[0]['metadata'] == {'source': 'test1'}
        assert results[0]['id'] == 'id1'
        assert results[0]['distance'] == 0.1

        vector_db.collection.query.assert_called_once_with(
            query_texts=['测试查询'],
            n_results=2,
            where=None,
            where_document=None
        )


class TestEmbeddingGenerator:
    """嵌入生成器测试"""

    @pytest.fixture
    def embedding_generator(self):
        """创建嵌入生成器实例"""
        return EmbeddingGenerator()

    @pytest.mark.asyncio
    async def test_initialization(self, embedding_generator):
        """测试初始化"""
        # 模拟sentence-transformers
        with pytest.MonkeyPatch().context() as m:
            from sentence_transformers import SentenceTransformer
            mock_model = MagicMock()
            mock_sentence_transformers = MagicMock()
            mock_sentence_transformers.SentenceTransformer.return_value = mock_model
            m.setattr(SentenceTransformer, "SentenceTransformer", mock_sentence_transformers)

            result = await embedding_generator.initialize()
            assert result is True
            assert embedding_generator._initialized is True
            assert embedding_generator.model == mock_model

    def test_preprocess_text(self, embedding_generator):
        """测试文本预处理"""
        # 测试多余空白字符
        text = "  这是   一个  测试  文档  "
        result = embedding_generator._preprocess_text(text)
        assert result == "这是一个测试文档"

        # 测试空文本
        result = embedding_generator._preprocess_text("")
        assert result == ""

        # 测试None
        result = embedding_generator._preprocess_text(None)
        assert result == ""

    @pytest.mark.asyncio
    async def test_calculate_similarity(self, embedding_generator):
        """测试相似度计算"""
        # 测试向量
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        vec3 = [1.0, 0.0, 0.0]

        # 测试正交向量
        similarity = await embedding_generator.calculate_similarity(vec1, vec2)
        assert similarity == 0.0

        # 测试相同向量
        similarity = await embedding_generator.calculate_similarity(vec1, vec3)
        assert similarity == 1.0

        # 测试空向量
        similarity = await embedding_generator.calculate_similarity([], [])
        assert similarity == 0.0


class TestTextChunker:
    """文本分块器测试"""

    @pytest.fixture
    def chunker(self):
        """创建文本分块器实例"""
        return TextChunker(chunk_size=50, chunk_overlap=10)

    def test_chunk_text(self, chunker):
        """测试文本分块"""
        # 创建一个较长的测试文本
        long_text = "这是一个测试句子。这是第二个测试句子。这是第三个测试句子。这是第四个测试句子。这是第五个测试句子。这是第六个测试句子。"

        chunks = chunker.chunk_text(long_text)

        assert len(chunks) > 1
        assert all(len(chunk) <= 50 for chunk in chunks)
        assert all(chunk.strip() for chunk in chunks)  # 没有空块

    def test_chunk_single_sentence(self, chunker):
        """测试单个句子分块"""
        short_text = "这是一个短句子。"
        chunks = chunker.chunk_text(short_text)

        assert len(chunks) == 1
        assert chunks[0] == short_text

    def test_chunk_empty_text(self, chunker):
        """测试空文本分块"""
        chunks = chunker.chunk_text("")
        assert chunks == [""]

        chunks = chunker.chunk_text(None)
        assert chunks == [""]


@pytest.mark.asyncio
async def test_vector_db_integration():
    """向量数据库集成测试"""
    # 创建测试实例
    vector_db = VectorDBManager("integration_test")
    embedding_generator = EmbeddingGenerator()

    # 由于这些需要实际的模型和数据库，这里只测试接口存在性
    assert hasattr(vector_db, 'initialize')
    assert hasattr(vector_db, 'add_documents')
    assert hasattr(vector_db, 'search')
    assert hasattr(embedding_generator, 'initialize')
    assert hasattr(embedding_generator, 'generate_embeddings')
    assert hasattr(embedding_generator, 'calculate_similarity')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])