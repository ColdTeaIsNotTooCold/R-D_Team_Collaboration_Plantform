"""
向量数据库文档模型
定义向量数据库中存储的文档结构和相关操作
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
from typing import Dict, Any, Optional

Base = declarative_base()


class VectorDocument(Base):
    """向量数据库文档模型"""
    __tablename__ = "vector_documents"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(String(255), unique=True, index=True, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(JSON)  # 存储嵌入向量
    metadata = Column(JSON)  # 存储文档元数据
    chunk_index = Column(Integer, default=0)  # 分块索引
    document_type = Column(String(50), default="text")  # 文档类型
    source = Column(String(255))  # 文档来源
    created_by = Column(String(100))  # 创建者
    updated_by = Column(String(100))  # 更新者
    created_at = Column(DateTime, default=func.now())  # 创建时间
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())  # 更新时间
    embedding_dimension = Column(Integer)  # 嵌入维度
    similarity_score = Column(Float, default=0.0)  # 相似度分数
    is_active = Column(Boolean, default=True)  # 是否活跃
    batch_id = Column(String(100))  # 批处理ID
    file_path = Column(String(500))  # 文件路径（如果是文件）
    file_size = Column(Integer)  # 文件大小
    content_length = Column(Integer)  # 内容长度

    # 创建索引
    __table_args__ = (
        Index('idx_document_id', 'document_id'),
        Index('idx_created_at', 'created_at'),
        Index('idx_document_type', 'document_type'),
        Index('idx_source', 'source'),
        Index('idx_created_by', 'created_by'),
        Index('idx_batch_id', 'batch_id'),
        Index('idx_is_active', 'is_active'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'document_id': self.document_id,
            'content': self.content,
            'embedding': self.embedding,
            'metadata': self.metadata,
            'chunk_index': self.chunk_index,
            'document_type': self.document_type,
            'source': self.source,
            'created_by': self.created_by,
            'updated_by': self.updated_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'embedding_dimension': self.embedding_dimension,
            'similarity_score': self.similarity_score,
            'is_active': self.is_active,
            'batch_id': self.batch_id,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'content_length': self.content_length,
        }

    def __repr__(self):
        return f"<VectorDocument(id={self.id}, document_id='{self.document_id}', type='{self.document_type}')>"


class VectorCollection(Base):
    """向量集合模型"""
    __tablename__ = "vector_collections"

    id = Column(Integer, primary_key=True, index=True)
    collection_name = Column(String(255), unique=True, nullable=False)
    description = Column(Text)
    document_count = Column(Integer, default=0)
    embedding_dimension = Column(Integer)
    created_by = Column(String(100))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    config = Column(JSON)  # 集合配置

    __table_args__ = (
        Index('idx_collection_name', 'collection_name'),
        Index('idx_is_active', 'is_active'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'collection_name': self.collection_name,
            'description': self.description,
            'document_count': self.document_count,
            'embedding_dimension': self.embedding_dimension,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'config': self.config,
        }

    def __repr__(self):
        return f"<VectorCollection(name='{self.collection_name}', docs={self.document_count})>"


class VectorCache(Base):
    """向量缓存模型"""
    __tablename__ = "vector_cache"

    id = Column(Integer, primary_key=True, index=True)
    cache_key = Column(String(255), unique=True, nullable=False)
    cache_type = Column(String(50), nullable=False)  # embedding, similarity, search
    cache_data = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime)
    hit_count = Column(Integer, default=0)
    last_accessed = Column(DateTime, default=func.now())
    is_active = Column(Boolean, default=True)

    __table_args__ = (
        Index('idx_cache_key', 'cache_key'),
        Index('idx_cache_type', 'cache_type'),
        Index('idx_expires_at', 'expires_at'),
        Index('idx_is_active', 'is_active'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'cache_key': self.cache_key,
            'cache_type': self.cache_type,
            'cache_data': self.cache_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'hit_count': self.hit_count,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'is_active': self.is_active,
        }

    def __repr__(self):
        return f"<VectorCache(key='{self.cache_key}', type='{self.cache_type}')>"


class VectorSearchLog(Base):
    """向量搜索日志模型"""
    __tablename__ = "vector_search_logs"

    id = Column(Integer, primary_key=True, index=True)
    query_text = Column(Text, nullable=False)
    search_type = Column(String(50), default="vector")  # vector, hybrid, semantic
    results_count = Column(Integer, default=0)
    search_time = Column(Float)  # 搜索耗时（秒）
    user_id = Column(String(100))
    collection_name = Column(String(255))
    filters = Column(JSON)  # 搜索过滤器
    score_threshold = Column(Float, default=0.0)
    top_k = Column(Integer, default=5)
    cache_hit = Column(Boolean, default=False)
    error_message = Column(Text)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index('idx_created_at', 'created_at'),
        Index('idx_user_id', 'user_id'),
        Index('idx_collection_name', 'collection_name'),
        Index('idx_search_type', 'search_type'),
        Index('idx_cache_hit', 'cache_hit'),
    )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'id': self.id,
            'query_text': self.query_text,
            'search_type': self.search_type,
            'results_count': self.results_count,
            'search_time': self.search_time,
            'user_id': self.user_id,
            'collection_name': self.collection_name,
            'filters': self.filters,
            'score_threshold': self.score_threshold,
            'top_k': self.top_k,
            'cache_hit': self.cache_hit,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<VectorSearchLog(query='{self.query_text[:50]}...', results={self.results_count})>"