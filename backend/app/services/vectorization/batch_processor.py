"""
批量向量化处理模块
提供高效的批量文档处理、并行计算和结果管理功能
"""
import logging
from typing import List, Dict, Any, Optional, Tuple, AsyncGenerator
import asyncio
import time
from datetime import datetime
import json
import os
from pathlib import Path
import aiofiles
import concurrent.futures
from ..core.config import settings
from .service import VectorizationService

logger = logging.getLogger(__name__)


class BatchVectorizationProcessor:
    """批量向量化处理器"""

    def __init__(self, max_workers: int = 4):
        self.vectorization_service = VectorizationService()
        self.max_workers = max_workers
        self._initialized = False
        self._batch_metrics = {
            'total_batches_processed': 0,
            'total_documents_processed': 0,
            'average_batch_time': 0.0,
            'total_processing_time': 0.0,
            'failed_batches': 0,
            'success_rate': 0.0
        }

    async def initialize(self) -> bool:
        """初始化批量处理器"""
        try:
            if not await self.vectorization_service.initialize():
                logger.error("向量化服务初始化失败")
                return False

            self._initialized = True
            logger.info("批量向量化处理器初始化成功")
            return True

        except Exception as e:
            logger.error(f"批量向量化处理器初始化失败: {str(e)}")
            return False

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized

    async def process_text_batch(
        self,
        texts: List[str],
        batch_size: int = None,
        use_cache: bool = True,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """处理文本批量向量化"""
        if not self.is_initialized():
            logger.error("批量向量化处理器未初始化")
            return {}

        try:
            start_time = time.time()
            batch_size = batch_size or settings.embedding_batch_size
            total_texts = len(texts)

            logger.info(f"开始处理 {total_texts} 个文本的批量向量化")

            all_embeddings = []
            processed_count = 0
            failed_count = 0

            # 分批处理
            for i in range(0, len(texts), batch_size):
                batch_start = i
                batch_end = min(i + batch_size, len(texts))
                batch_texts = texts[batch_start:batch_end]

                try:
                    # 处理批次
                    batch_embeddings = await self.vectorization_service.batch_generate_embeddings(
                        batch_texts,
                        use_cache=use_cache
                    )

                    if batch_embeddings:
                        all_embeddings.extend(batch_embeddings)
                        processed_count += len(batch_texts)
                    else:
                        failed_count += len(batch_texts)

                    # 进度回调
                    if progress_callback:
                        await progress_callback(
                            processed=processed_count + failed_count,
                            total=total_texts,
                            batch_number=i // batch_size + 1,
                            total_batches=(total_texts + batch_size - 1) // batch_size
                        )

                    # 批次间小延迟
                    await asyncio.sleep(0.001)

                except Exception as e:
                    logger.error(f"处理批次 {batch_start}-{batch_end} 失败: {str(e)}")
                    failed_count += len(batch_texts)

            operation_time = time.time() - start_time

            # 更新指标
            self._batch_metrics['total_batches_processed'] += 1
            self._batch_metrics['total_documents_processed'] += processed_count
            self._batch_metrics['total_processing_time'] += operation_time
            self._batch_metrics['average_batch_time'] = self._batch_metrics['total_processing_time'] / self._batch_metrics['total_batches_processed']
            self._batch_metrics['success_rate'] = processed_count / total_texts if total_texts > 0 else 0.0

            result = {
                'embeddings': all_embeddings,
                'processed_count': processed_count,
                'failed_count': failed_count,
                'success_rate': processed_count / total_texts if total_texts > 0 else 0.0,
                'total_texts': total_texts,
                'processing_time': operation_time,
                'average_text_length': sum(len(text) for text in texts) / len(texts) if texts else 0,
                'timestamp': datetime.now().isoformat()
            }

            logger.info(f"批量向量化完成，成功: {processed_count}, 失败: {failed_count}, 耗时: {operation_time:.2f}秒")
            return result

        except Exception as e:
            logger.error(f"批量向量化处理失败: {str(e)}")
            return {}

    async def process_documents_stream(
        self,
        documents: List[Dict[str, Any]],
        text_field: str = "content",
        batch_size: int = None,
        use_cache: bool = True,
        progress_callback: Optional[callable] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """流式处理文档向量化"""
        if not self.is_initialized():
            logger.error("批量向量化处理器未初始化")
            return

        try:
            batch_size = batch_size or settings.embedding_batch_size
            total_docs = len(documents)

            logger.info(f"开始流式处理 {total_docs} 个文档")

            for i in range(0, len(documents), batch_size):
                batch_docs = documents[i:i + batch_size]
                batch_texts = []
                batch_metadata = []

                # 提取文本和元数据
                for doc in batch_docs:
                    if text_field in doc:
                        batch_texts.append(doc[text_field])
                        batch_metadata.append({k: v for k, v in doc.items() if k != text_field})

                # 处理批次
                batch_result = await self.process_text_batch(
                    batch_texts,
                    batch_size=batch_size,
                    use_cache=use_cache
                )

                if batch_result and batch_result['embeddings']:
                    yield {
                        'batch_index': i // batch_size,
                        'documents': batch_docs,
                        'embeddings': batch_result['embeddings'],
                        'metadata': batch_metadata,
                        'processed_count': batch_result['processed_count'],
                        'failed_count': batch_result['failed_count'],
                        'processing_time': batch_result['processing_time']
                    }

                # 进度回调
                if progress_callback:
                    await progress_callback(
                        processed=min(i + batch_size, total_docs),
                        total=total_docs,
                        batch_number=i // batch_size + 1,
                        total_batches=(total_docs + batch_size - 1) // batch_size
                    )

                # 批次间延迟
                await asyncio.sleep(0.001)

        except Exception as e:
            logger.error(f"流式文档处理失败: {str(e)}")
            yield {'error': str(e)}

    async def process_file_batch(
        self,
        file_paths: List[str],
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        use_cache: bool = True,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """处理文件批量向量化"""
        if not self.is_initialized():
            logger.error("批量向量化处理器未初始化")
            return {}

        try:
            start_time = time.time()
            total_files = len(file_paths)

            logger.info(f"开始处理 {total_files} 个文件的批量向量化")

            all_results = []
            processed_count = 0
            failed_count = 0
            total_text_length = 0

            for i, file_path in enumerate(file_paths):
                try:
                    # 检查文件大小
                    file_size = os.path.getsize(file_path)
                    if file_size > max_file_size:
                        logger.warning(f"文件 {file_path} 超过大小限制 ({file_size} bytes)")
                        failed_count += 1
                        continue

                    # 读取文件内容
                    async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                        content = await f.read()

                    if not content.strip():
                        logger.warning(f"文件 {file_path} 为空")
                        failed_count += 1
                        continue

                    # 生成嵌入
                    embedding = await self.vectorization_service.generate_embedding(
                        content,
                        use_cache=use_cache
                    )

                    if embedding:
                        all_results.append({
                            'file_path': file_path,
                            'embedding': embedding,
                            'file_size': file_size,
                            'content_length': len(content),
                            'processing_time': time.time() - start_time
                        })
                        processed_count += 1
                        total_text_length += len(content)
                    else:
                        failed_count += 1

                    # 进度回调
                    if progress_callback:
                        await progress_callback(
                            processed=processed_count + failed_count,
                            total=total_files,
                            current_file=file_path
                        )

                    # 文件间延迟
                    await asyncio.sleep(0.001)

                except Exception as e:
                    logger.error(f"处理文件 {file_path} 失败: {str(e)}")
                    failed_count += 1

            operation_time = time.time() - start_time

            result = {
                'results': all_results,
                'processed_count': processed_count,
                'failed_count': failed_count,
                'success_rate': processed_count / total_files if total_files > 0 else 0.0,
                'total_files': total_files,
                'total_text_length': total_text_length,
                'average_file_size': sum(r['file_size'] for r in all_results) / len(all_results) if all_results else 0,
                'processing_time': operation_time,
                'timestamp': datetime.now().isoformat()
            }

            logger.info(f"文件批量向量化完成，成功: {processed_count}, 失败: {failed_count}, 耗时: {operation_time:.2f}秒")
            return result

        except Exception as e:
            logger.error(f"文件批量向量化处理失败: {str(e)}")
            return {}

    async def parallel_process_batch(
        self,
        texts: List[str],
        max_workers: int = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """并行处理批量向量化"""
        if not self.is_initialized():
            logger.error("批量向量化处理器未初始化")
            return {}

        try:
            start_time = time.time()
            max_workers = max_workers or self.max_workers
            total_texts = len(texts)

            logger.info(f"开始并行处理 {total_texts} 个文本，使用 {max_workers} 个工作线程")

            # 分割任务
            chunk_size = max(1, total_texts // max_workers)
            text_chunks = [texts[i:i + chunk_size] for i in range(0, len(texts), chunk_size)]

            all_embeddings = []
            processed_count = 0

            # 创建线程池
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交任务
                loop = asyncio.get_event_loop()
                futures = [
                    loop.run_in_executor(
                        executor,
                        self._process_chunk_sync,
                        chunk,
                        use_cache
                    )
                    for chunk in text_chunks
                ]

                # 等待结果
                for future in asyncio.as_completed(futures):
                    try:
                        chunk_result = await future
                        if chunk_result and chunk_result['embeddings']:
                            all_embeddings.extend(chunk_result['embeddings'])
                            processed_count += chunk_result['processed_count']
                    except Exception as e:
                        logger.error(f"并行处理任务失败: {str(e)}")

            operation_time = time.time() - start_time

            result = {
                'embeddings': all_embeddings,
                'processed_count': processed_count,
                'total_texts': total_texts,
                'success_rate': processed_count / total_texts if total_texts > 0 else 0.0,
                'processing_time': operation_time,
                'max_workers': max_workers,
                'timestamp': datetime.now().isoformat()
            }

            logger.info(f"并行批量向量化完成，处理了 {processed_count} 个文本，耗时: {operation_time:.2f}秒")
            return result

        except Exception as e:
            logger.error(f"并行批量向量化处理失败: {str(e)}")
            return {}

    def _process_chunk_sync(self, texts: List[str], use_cache: bool) -> Dict[str, Any]:
        """同步处理文本块（用于线程池）"""
        try:
            # 这里需要同步处理，简化实现
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            embeddings = loop.run_until_complete(
                self.vectorization_service.batch_generate_embeddings(texts, use_cache=use_cache)
            )

            loop.close()

            return {
                'embeddings': embeddings,
                'processed_count': len(embeddings)
            }

        except Exception as e:
            logger.error(f"同步处理文本块失败: {str(e)}")
            return {'embeddings': [], 'processed_count': 0}

    async def save_batch_results(
        self,
        results: Dict[str, Any],
        output_path: str,
        format: str = "json"
    ) -> bool:
        """保存批量处理结果"""
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            if format.lower() == "json":
                async with aiofiles.open(output_path, 'w', encoding='utf-8') as f:
                    await f.write(json.dumps(results, ensure_ascii=False, indent=2))
            else:
                logger.error(f"不支持的输出格式: {format}")
                return False

            logger.info(f"批量处理结果已保存到: {output_path}")
            return True

        except Exception as e:
            logger.error(f"保存批量处理结果失败: {str(e)}")
            return False

    async def get_batch_metrics(self) -> Dict[str, Any]:
        """获取批量处理指标"""
        return {
            'metrics': self._batch_metrics,
            'max_workers': self.max_workers,
            'service_initialized': self._initialized,
            'timestamp': datetime.now().isoformat()
        }

    async def reset_batch_metrics(self) -> bool:
        """重置批量处理指标"""
        try:
            self._batch_metrics = {
                'total_batches_processed': 0,
                'total_documents_processed': 0,
                'average_batch_time': 0.0,
                'total_processing_time': 0.0,
                'failed_batches': 0,
                'success_rate': 0.0
            }
            logger.info("批量处理指标已重置")
            return True
        except Exception as e:
            logger.error(f"重置批量处理指标失败: {str(e)}")
            return False


# 全局批量向量化处理器实例
batch_processor = BatchVectorizationProcessor()


async def get_batch_processor() -> BatchVectorizationProcessor:
    """获取批量向量化处理器实例"""
    return batch_processor