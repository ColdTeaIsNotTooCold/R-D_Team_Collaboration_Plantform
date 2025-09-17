import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.search import SearchEngine
from app.models.context import Context
from app.models.user import User
from app.schemas.search import SearchQuery, SearchType, SortOrder, IndexDocument
from app.core.database import Base


@pytest.fixture
def db_session():
    """创建测试数据库会话"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture
def sample_contexts(db_session):
    """创建测试上下文数据"""
    contexts = [
        Context(
            context_type="code",
            title="Python函数示例",
            content="def hello_world():\n    print('Hello, World!')\n    return 'success'",
            metadata='{"language": "python", "lines": 3}',
            created_at=datetime.now()
        ),
        Context(
            context_type="document",
            title="项目需求文档",
            content="这是一个项目需求文档，描述了系统的基本功能需求。包括用户管理、权限控制和数据导出功能。",
            metadata='{"category": "requirements", "priority": "high"}',
            created_at=datetime.now()
        ),
        Context(
            context_type="conversation",
            title="技术讨论",
            content="讨论了关于数据库设计和API架构的技术问题，建议使用PostgreSQL和FastAPI。",
            metadata='{"participants": 3, "duration": 45}',
            created_at=datetime.now()
        )
    ]

    for context in contexts:
        db_session.add(context)
    db_session.commit()
    return contexts


@pytest.fixture
def search_engine(db_session):
    """创建搜索引擎实例"""
    with patch('app.core.search.chromadb.PersistentClient'):
        with patch('app.core.search.embedding_functions.SentenceTransformerEmbeddingFunction'):
            return SearchEngine(db_session)


class TestSearchEngine:
    """搜索引擎测试类"""

    def test_extract_keywords(self, search_engine):
        """测试关键词提取"""
        query = "Python函数和数据库设计"
        keywords = search_engine._extract_keywords(query)

        assert "python" in keywords
        assert "函数" in keywords
        assert "数据库" in keywords
        assert "设计" in keywords
        assert "和" not in keywords  # 停用词应该被过滤

    def test_calculate_keyword_score(self, search_engine, sample_contexts):
        """测试关键词分数计算"""
        context = sample_contexts[0]  # Python函数示例
        keywords = ["python", "函数", "hello"]

        score = search_engine._calculate_keyword_score(context, keywords)

        assert score > 0
        assert score <= 1.0

    def test_extract_highlights(self, search_engine, sample_contexts):
        """测试高亮文本提取"""
        context = sample_contexts[1]  # 项目需求文档
        keywords = ["项目", "需求", "功能"]

        highlights = search_engine._extract_highlights(context, keywords)

        assert len(highlights) > 0
        assert any("项目需求文档" in highlight for highlight in highlights)

    def test_sort_results_relevance(self, search_engine):
        """测试按相关度排序"""
        from app.schemas.search import SearchResult

        results = [
            SearchResult(id=1, context_type="code", title="Test 1", score=0.8, highlights=[], created_at=datetime.now()),
            SearchResult(id=2, context_type="document", title="Test 2", score=0.9, highlights=[], created_at=datetime.now()),
            SearchResult(id=3, context_type="conversation", title="Test 3", score=0.7, highlights=[], created_at=datetime.now())
        ]

        sorted_results = search_engine._sort_results(results, SortOrder.RELEVANCE)

        assert sorted_results[0].score == 0.9
        assert sorted_results[1].score == 0.8
        assert sorted_results[2].score == 0.7

    def test_apply_pagination(self, search_engine):
        """测试分页功能"""
        from app.schemas.search import SearchResult

        results = [SearchResult(id=i, context_type="test", title=f"Test {i}", score=0.5, highlights=[], created_at=datetime.now())
                  for i in range(25)]

        paginated = search_engine._apply_pagination(results, 2, 10)

        assert len(paginated) == 10
        assert paginated[0].id == 10  # 第二页的第一个结果ID应该是10

    @pytest.mark.asyncio
    async def test_keyword_search(self, search_engine, sample_contexts):
        """测试关键词搜索"""
        query = SearchQuery(query="Python函数", search_type=SearchType.KEYWORD)

        response = await search_engine.search(query)

        assert response.total > 0
        assert len(response.results) > 0
        assert response.query == "Python函数"
        assert response.search_type == SearchType.KEYWORD
        assert response.execution_time > 0

    @pytest.mark.asyncio
    async def test_search_with_filters(self, search_engine, sample_contexts):
        """测试带过滤条件的搜索"""
        query = SearchQuery(
            query="test",
            search_type=SearchType.KEYWORD,
            context_types=["code"],
            page=1,
            page_size=10
        )

        response = await search_engine.search(query)

        assert len(response.results) <= len([c for c in sample_contexts if c.context_type == "code"])

    @pytest.mark.asyncio
    async def test_semantic_search_no_chromadb(self, search_engine):
        """测试无ChromaDB时的语义搜索"""
        search_engine.chroma_client = None
        search_engine.embedding_function = None

        query = SearchQuery(query="test query", search_type=SearchType.SEMANTIC)

        response = await search_engine.search(query)

        assert response.total == 0
        assert len(response.results) == 0

    @pytest.mark.asyncio
    async def test_hybrid_search(self, search_engine, sample_contexts):
        """测试混合搜索"""
        query = SearchQuery(query="Python函数", search_type=SearchType.HYBRID)

        response = await search_engine.search(query)

        assert response.total >= 0
        assert response.search_type == SearchType.HYBRID

    @pytest.mark.asyncio
    async def test_index_document_no_chromadb(self, search_engine):
        """测试无ChromaDB时的文档索引"""
        search_engine.chroma_client = None
        search_engine.embedding_function = None

        document = IndexDocument(
            id=1,
            content="测试文档内容",
            metadata={"test": "data"},
            context_type="document",
            title="测试文档"
        )

        success = await search_engine.index_document(document)

        assert success is False

    @pytest.mark.asyncio
    async def test_get_search_stats(self, search_engine, sample_contexts):
        """测试搜索统计"""
        stats = await search_engine.get_search_stats()

        assert "total_documents" in stats
        assert "indexed_documents" in stats
        assert "search_types" in stats
        assert "chromadb_status" in stats
        assert stats["total_documents"] == len(sample_contexts)

    def test_build_chroma_filter(self, search_engine):
        """测试ChromaDB过滤条件构建"""
        query = SearchQuery(
            query="test",
            context_types=["code", "document"],
            task_id=1,
            conversation_id=2
        )

        filters = search_engine._build_chroma_filter(query)

        assert filters["context_type"]["$in"] == ["code", "document"]
        assert filters["task_id"] == 1
        assert filters["conversation_id"] == 2

    def test_build_chroma_filter_empty(self, search_engine):
        """测试空过滤条件"""
        query = SearchQuery(query="test")

        filters = search_engine._build_chroma_filter(query)

        assert filters is None

    def test_merge_results(self, search_engine):
        """测试搜索结果合并"""
        from app.schemas.search import SearchResult

        keyword_results = [
            SearchResult(id=1, context_type="code", title="Result 1", score=0.8, highlights=[], created_at=datetime.now()),
            SearchResult(id=2, context_type="document", title="Result 2", score=0.7, highlights=[], created_at=datetime.now())
        ]

        semantic_results = [
            SearchResult(id=2, context_type="document", title="Result 2", score=0.6, highlights=[], created_at=datetime.now()),
            SearchResult(id=3, context_type="conversation", title="Result 3", score=0.9, highlights=[], created_at=datetime.now())
        ]

        merged = search_engine._merge_results(keyword_results, semantic_results)

        assert len(merged) == 3  # 去重后应该有3个结果
        assert merged[0].id == 3  # 最高分的结果应该在前面
        assert merged[1].id == 1
        assert merged[2].id == 2


class TestSearchIntegration:
    """搜索集成测试"""

    @pytest.mark.asyncio
    async def test_full_search_workflow(self, db_session, sample_contexts):
        """测试完整的搜索工作流"""
        with patch('app.core.search.chromadb.PersistentClient'):
            with patch('app.core.search.embedding_functions.SentenceTransformerEmbeddingFunction'):
                search_engine = SearchEngine(db_session)

                # 1. 执行关键词搜索
                keyword_query = SearchQuery(query="Python", search_type=SearchType.KEYWORD)
                keyword_response = await search_engine.search(keyword_query)

                assert keyword_response.total >= 0
                assert keyword_response.execution_time > 0

                # 2. 执行混合搜索
                hybrid_query = SearchQuery(query="函数", search_type=SearchType.HYBRID)
                hybrid_response = await search_engine.search(hybrid_query)

                assert hybrid_response.total >= 0
                assert hybrid_response.search_type == SearchType.HYBRID

                # 3. 获取搜索统计
                stats = await search_engine.get_search_stats()

                assert "total_documents" in stats
                assert stats["total_documents"] == len(sample_contexts)

    def test_search_engine_initialization(self, db_session):
        """测试搜索引擎初始化"""
        with patch('app.core.search.chromadb.PersistentClient') as mock_chroma:
            with patch('app.core.search.embedding_functions.SentenceTransformerEmbeddingFunction'):
                search_engine = SearchEngine(db_session)

                assert search_engine.db == db_session
                assert search_engine.chroma_client is not None
                assert search_engine.embedding_function is not None