#!/usr/bin/env python3
"""
ChromaDB集成验证脚本
"""
import sys
import os
import asyncio
import logging

# 添加应用路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.vector_db import VectorDBManager
from app.core.embeddings import EmbeddingGenerator, TextChunker

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_vector_db():
    """测试向量数据库功能"""
    print("=== 测试向量数据库功能 ===")

    # 创建向量数据库管理器
    vector_db = VectorDBManager("test_collection")

    # 测试初始化
    print("1. 测试初始化...")
    try:
        result = await vector_db.initialize()
        print(f"   初始化结果: {result}")
        print(f"   是否已初始化: {vector_db.is_initialized()}")
    except Exception as e:
        print(f"   初始化失败: {str(e)}")

    # 测试获取集合信息
    print("2. 测试获取集合信息...")
    try:
        info = await vector_db.get_collection_info()
        print(f"   集合信息: {info}")
    except Exception as e:
        print(f"   获取集合信息失败: {str(e)}")

    # 测试添加文档
    print("3. 测试添加文档...")
    try:
        documents = [
            "团队协作平台是一个用于团队协作的工具。",
            "ChromaDB是一个开源的向量数据库。",
            "FastAPI是一个现代的Python Web框架。"
        ]
        metadatas = [
            {"source": "doc1.txt", "type": "text"},
            {"source": "doc2.txt", "type": "text"},
            {"source": "doc3.txt", "type": "text"}
        ]
        result = await vector_db.add_documents(documents, metadatas)
        print(f"   添加文档结果: {result}")
    except Exception as e:
        print(f"   添加文档失败: {str(e)}")

    # 测试搜索
    print("4. 测试搜索功能...")
    try:
        results = await vector_db.search("团队协作", n_results=3)
        print(f"   搜索结果数量: {len(results)}")
        for i, result in enumerate(results):
            print(f"   结果 {i+1}: {result['document'][:50]}...")
    except Exception as e:
        print(f"   搜索失败: {str(e)}")

    print()


async def test_embedding_generator():
    """测试嵌入生成器功能"""
    print("=== 测试嵌入生成器功能 ===")

    # 创建嵌入生成器
    embedding_generator = EmbeddingGenerator()

    # 测试初始化
    print("1. 测试初始化...")
    try:
        result = await embedding_generator.initialize()
        print(f"   初始化结果: {result}")
        print(f"   是否已初始化: {embedding_generator.is_initialized()}")
    except Exception as e:
        print(f"   初始化失败: {str(e)}")

    # 测试生成嵌入
    print("2. 测试生成嵌入...")
    try:
        texts = [
            "这是一个测试句子。",
            "这是另一个测试句子。"
        ]
        embeddings = await embedding_generator.generate_embeddings(texts)
        print(f"   生成的嵌入数量: {len(embeddings)}")
        if embeddings:
            print(f"   嵌入维度: {len(embeddings[0])}")
            print(f"   第一个嵌入前5个值: {embeddings[0][:5]}")
    except Exception as e:
        print(f"   生成嵌入失败: {str(e)}")

    # 测试相似度计算
    print("3. 测试相似度计算...")
    try:
        text1 = "团队协作平台"
        text2 = "协作管理系统"
        text3 = "天气预报"

        embedding1 = await embedding_generator.generate_embedding(text1)
        embedding2 = await embedding_generator.generate_embedding(text2)
        embedding3 = await embedding_generator.generate_embedding(text3)

        similarity1 = await embedding_generator.calculate_similarity(embedding1, embedding2)
        similarity2 = await embedding_generator.calculate_similarity(embedding1, embedding3)

        print(f"   '{text1}' 和 '{text2}' 的相似度: {similarity1:.4f}")
        print(f"   '{text1}' 和 '{text3}' 的相似度: {similarity2:.4f}")
    except Exception as e:
        print(f"   相似度计算失败: {str(e)}")

    print()


async def test_text_chunker():
    """测试文本分块功能"""
    print("=== 测试文本分块功能 ===")

    # 创建文本分块器
    chunker = TextChunker(chunk_size=100, chunk_overlap=20)

    # 测试文本分块
    print("1. 测试文本分块...")
    try:
        long_text = (
            "这是一个很长的测试文本，用于验证文本分块功能。"
            "文本分块是处理长文档的重要步骤，它将长文档分割成较小的块。"
            "每个块都有合适的大小，便于后续的嵌入生成和向量检索。"
            "重叠区域确保了上下文的连续性，提高了搜索的准确性。"
            "这是文本分块器的测试内容，包含多个句子和段落。"
        )

        chunks = chunker.chunk_text(long_text)
        print(f"   原始文本长度: {len(long_text)}")
        print(f"   分块数量: {len(chunks)}")
        for i, chunk in enumerate(chunks):
            print(f"   块 {i+1}: {chunk[:50]}... (长度: {len(chunk)})")
    except Exception as e:
        print(f"   文本分块失败: {str(e)}")

    print()


async def main():
    """主测试函数"""
    print("ChromaDB集成验证")
    print("=" * 50)

    await test_vector_db()
    await test_embedding_generator()
    await test_text_chunker()

    print("测试完成！")


if __name__ == "__main__":
    asyncio.run(main())