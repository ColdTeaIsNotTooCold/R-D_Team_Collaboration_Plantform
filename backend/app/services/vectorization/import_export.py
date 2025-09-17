"""
向量数据导入导出模块
提供向量数据的批量导入、导出和格式转换功能
"""
import logging
from typing import List, Dict, Any, Optional, Tuple, AsyncGenerator
import asyncio
import time
import json
import csv
import aiofiles
from pathlib import Path
from datetime import datetime
import numpy as np
import pandas as pd

from ..core.config import settings
from ..core.vector_db import get_vector_db
from .service import VectorizationService

logger = logging.getLogger(__name__)


class VectorImportExportManager:
    """向量数据导入导出管理器"""

    def __init__(self):
        self.vectorization_service = VectorizationService()
        self._initialized = False
        self._supported_formats = ['json', 'csv', 'parquet', 'numpy', 'txt']

    async def initialize(self) -> bool:
        """初始化导入导出管理器"""
        try:
            if not await self.vectorization_service.initialize():
                logger.error("向量化服务初始化失败")
                return False

            self._initialized = True
            logger.info("向量数据导入导出管理器初始化成功")
            return True

        except Exception as e:
            logger.error(f"向量数据导入导出管理器初始化失败: {str(e)}")
            return False

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized

    async def export_vectors(
        self,
        output_path: str,
        format: str = "json",
        where: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        include_embeddings: bool = True,
        batch_size: int = 1000
    ) -> Dict[str, Any]:
        """导出向量数据"""
        if not self.is_initialized():
            logger.error("向量数据导入导出管理器未初始化")
            return {}

        try:
            start_time = time.time()
            vector_db = await get_vector_db()

            if not vector_db.is_initialized():
                logger.error("向量数据库未初始化")
                return {}

            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            # 获取所有文档
            all_results = []
            processed_count = 0

            # 分批获取文档
            while True:
                # 这里需要根据实际的ChromaDB API调整
                # 临时实现，需要根据实际数据库结构调整
                batch_results = await self._get_batch_documents(vector_db, batch_size, where, processed_count)

                if not batch_results:
                    break

                all_results.extend(batch_results)
                processed_count += len(batch_results)

                if limit and processed_count >= limit:
                    all_results = all_results[:limit]
                    break

                # 避免过载
                await asyncio.sleep(0.001)

            # 根据格式导出
            if format.lower() == "json":
                await self._export_json(all_results, output_path, include_embeddings)
            elif format.lower() == "csv":
                await self._export_csv(all_results, output_path, include_embeddings)
            elif format.lower() == "parquet":
                await self._export_parquet(all_results, output_path, include_embeddings)
            elif format.lower() == "numpy":
                await self._export_numpy(all_results, output_path)
            else:
                raise ValueError(f"不支持的导出格式: {format}")

            operation_time = time.time() - start_time

            result = {
                'success': True,
                'exported_count': len(all_results),
                'output_path': output_path,
                'format': format,
                'include_embeddings': include_embeddings,
                'processing_time': operation_time,
                'timestamp': datetime.now().isoformat()
            }

            logger.info(f"向量数据导出完成，导出 {len(all_results)} 个文档，耗时: {operation_time:.2f}秒")
            return result

        except Exception as e:
            logger.error(f"向量数据导出失败: {str(e)}")
            return {'success': False, 'error': str(e)}

    async def import_vectors(
        self,
        input_path: str,
        format: str = "json",
        collection_name: Optional[str] = None,
        batch_size: int = 100,
        skip_duplicates: bool = True,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """导入向量数据"""
        if not self.is_initialized():
            logger.error("向量数据导入导出管理器未初始化")
            return {}

        try:
            start_time = time.time()
            vector_db = await get_vector_db()

            if not vector_db.is_initialized():
                logger.error("向量数据库未初始化")
                return {}

            input_file = Path(input_path)
            if not input_file.exists():
                raise FileNotFoundError(f"输入文件不存在: {input_path}")

            # 根据格式导入
            if format.lower() == "json":
                data = await self._import_json(input_path)
            elif format.lower() == "csv":
                data = await self._import_csv(input_path)
            elif format.lower() == "parquet":
                data = await self._import_parquet(input_path)
            elif format.lower() == "numpy":
                data = await self._import_numpy(input_path)
            else:
                raise ValueError(f"不支持的导入格式: {format}")

            # 处理导入数据
            processed_count = await self._process_import_data(
                vector_db, data, batch_size, skip_duplicates, progress_callback
            )

            operation_time = time.time() - start_time

            result = {
                'success': True,
                'imported_count': processed_count,
                'input_path': input_path,
                'format': format,
                'processing_time': operation_time,
                'timestamp': datetime.now().isoformat()
            }

            logger.info(f"向量数据导入完成，导入 {processed_count} 个文档，耗时: {operation_time:.2f}秒")
            return result

        except Exception as e:
            logger.error(f"向量数据导入失败: {str(e)}")
            return {'success': False, 'error': str(e)}

    async def _export_json(self, data: List[Dict[str, Any]], output_path: str, include_embeddings: bool) -> None:
        """导出为JSON格式"""
        export_data = []
        for item in data:
            export_item = {
                'id': item.get('id'),
                'document': item.get('document'),
                'metadata': item.get('metadata', {})
            }
            if include_embeddings and 'embedding' in item:
                export_item['embedding'] = item['embedding']
            export_data.append(export_item)

        async with aiofiles.open(output_path, 'w', encoding='utf-8') as f:
            await f.write(json.dumps(export_data, ensure_ascii=False, indent=2))

    async def _export_csv(self, data: List[Dict[str, Any]], output_path: str, include_embeddings: bool) -> None:
        """导出为CSV格式"""
        if not data:
            return

        # 准备CSV数据
        csv_data = []
        for item in data:
            row = {
                'id': item.get('id'),
                'document': item.get('document', ''),
                'metadata': json.dumps(item.get('metadata', {}), ensure_ascii=False)
            }
            if include_embeddings and 'embedding' in item:
                row['embedding'] = json.dumps(item['embedding'])
            csv_data.append(row)

        # 写入CSV
        df = pd.DataFrame(csv_data)
        df.to_csv(output_path, index=False, encoding='utf-8')

    async def _export_parquet(self, data: List[Dict[str, Any]], output_path: str, include_embeddings: bool) -> None:
        """导出为Parquet格式"""
        export_data = []
        for item in data:
            export_item = {
                'id': item.get('id'),
                'document': item.get('document'),
                'metadata': json.dumps(item.get('metadata', {}), ensure_ascii=False)
            }
            if include_embeddings and 'embedding' in item:
                export_item['embedding'] = item['embedding']
            export_data.append(export_item)

        df = pd.DataFrame(export_data)
        df.to_parquet(output_path, index=False)

    async def _export_numpy(self, data: List[Dict[str, Any]], output_path: str) -> None:
        """导出为NumPy格式"""
        embeddings = []
        metadata = []

        for item in data:
            if 'embedding' in item:
                embeddings.append(item['embedding'])
                metadata.append({
                    'id': item.get('id'),
                    'document': item.get('document'),
                    'metadata': item.get('metadata', {})
                })

        if embeddings:
            np.save(output_path, np.array(embeddings))
            # 保存元数据
            metadata_path = output_path.replace('.npy', '_metadata.json')
            async with aiofiles.open(metadata_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(metadata, ensure_ascii=False, indent=2))

    async def _import_json(self, input_path: str) -> List[Dict[str, Any]]:
        """从JSON导入"""
        async with aiofiles.open(input_path, 'r', encoding='utf-8') as f:
            content = await f.read()
            return json.loads(content)

    async def _import_csv(self, input_path: str) -> List[Dict[str, Any]]:
        """从CSV导入"""
        df = pd.read_csv(input_path)
        data = []

        for _, row in df.iterrows():
            item = {
                'id': row.get('id'),
                'document': row.get('document', ''),
                'metadata': json.loads(row.get('metadata', '{}'))
            }
            if 'embedding' in row and pd.notna(row['embedding']):
                item['embedding'] = json.loads(row['embedding'])
            data.append(item)

        return data

    async def _import_parquet(self, input_path: str) -> List[Dict[str, Any]]:
        """从Parquet导入"""
        df = pd.read_parquet(input_path)
        data = []

        for _, row in df.iterrows():
            item = {
                'id': row.get('id'),
                'document': row.get('document', ''),
                'metadata': json.loads(row.get('metadata', '{}'))
            }
            if 'embedding' in row and pd.notna(row['embedding']):
                item['embedding'] = row['embedding']
            data.append(item)

        return data

    async def _import_numpy(self, input_path: str) -> List[Dict[str, Any]]:
        """从NumPy导入"""
        embeddings = np.load(input_path)
        metadata_path = input_path.replace('.npy', '_metadata.json')

        data = []
        if Path(metadata_path).exists():
            async with aiofiles.open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.loads(await f.read())

            for i, embedding in enumerate(embeddings):
                if i < len(metadata):
                    item = metadata[i]
                    item['embedding'] = embedding.tolist()
                    data.append(item)

        return data

    async def _get_batch_documents(self, vector_db, batch_size: int, where: Optional[Dict[str, Any]], offset: int) -> List[Dict[str, Any]]:
        """分批获取文档（需要根据实际数据库API调整）"""
        # 这里应该根据实际的ChromaDB API实现
        # 临时返回空列表，需要根据实际数据库结构调整
        return []

    async def _process_import_data(
        self,
        vector_db,
        data: List[Dict[str, Any]],
        batch_size: int,
        skip_duplicates: bool,
        progress_callback: Optional[callable]
    ) -> int:
        """处理导入数据"""
        processed_count = 0

        for i in range(0, len(data), batch_size):
            batch_data = data[i:i + batch_size]

            documents = []
            embeddings = []
            metadatas = []
            ids = []

            for item in batch_data:
                if 'document' in item:
                    documents.append(item['document'])
                    embeddings.append(item.get('embedding'))
                    metadatas.append(item.get('metadata', {}))
                    ids.append(item.get('id', f"import_{int(time.time())}_{i}"))

            # 如果有嵌入向量，直接添加到数据库
            if embeddings and all(embedding is not None for embedding in embeddings):
                # 这里应该实现直接添加嵌入向量到数据库的逻辑
                pass
            else:
                # 如果没有嵌入向量，先生成嵌入
                if documents:
                    generated_embeddings = await self.vectorization_service.batch_generate_embeddings(
                        documents,
                        use_cache=False
                    )

                    # 添加到数据库
                    await vector_db.add_documents(
                        documents=documents,
                        metadatas=metadatas,
                        ids=ids
                    )

            processed_count += len(batch_data)

            # 进度回调
            if progress_callback:
                await progress_callback(
                    processed=processed_count,
                    total=len(data),
                    batch_number=i // batch_size + 1,
                    total_batches=(len(data) + batch_size - 1) // batch_size
                )

            # 批次间延迟
            await asyncio.sleep(0.001)

        return processed_count

    async def backup_collection(
        self,
        collection_name: str,
        backup_path: str,
        format: str = "json"
    ) -> Dict[str, Any]:
        """备份向量集合"""
        try:
            backup_file = Path(backup_path) / f"{collection_name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"

            result = await self.export_vectors(
                output_path=str(backup_file),
                format=format,
                where={'collection': collection_name}
            )

            result['backup_path'] = str(backup_file)
            result['collection_name'] = collection_name

            return result

        except Exception as e:
            logger.error(f"备份集合失败: {str(e)}")
            return {'success': False, 'error': str(e)}

    async def restore_collection(
        self,
        backup_path: str,
        collection_name: str,
        clear_existing: bool = False
    ) -> Dict[str, Any]:
        """恢复向量集合"""
        try:
            if clear_existing:
                vector_db = await get_vector_db()
                await vector_db.clear_collection()

            result = await self.import_vectors(
                input_path=backup_path,
                collection_name=collection_name
            )

            result['collection_name'] = collection_name
            result['backup_path'] = backup_path

            return result

        except Exception as e:
            logger.error(f"恢复集合失败: {str(e)}")
            return {'success': False, 'error': str(e)}

    async def get_supported_formats(self) -> List[str]:
        """获取支持的格式"""
        return self._supported_formats.copy()

    async def validate_import_file(self, input_path: str, format: str) -> Dict[str, Any]:
        """验证导入文件"""
        try:
            input_file = Path(input_path)
            if not input_file.exists():
                return {'valid': False, 'error': '文件不存在'}

            if format.lower() not in self._supported_formats:
                return {'valid': False, 'error': f'不支持的格式: {format}'}

            # 尝试读取文件进行验证
            if format.lower() == "json":
                async with aiofiles.open(input_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    data = json.loads(content)
                    if not isinstance(data, list):
                        return {'valid': False, 'error': 'JSON数据必须是数组格式'}
            elif format.lower() == "csv":
                df = pd.read_csv(input_path)
                if df.empty:
                    return {'valid': False, 'error': 'CSV文件为空'}
            elif format.lower() == "parquet":
                df = pd.read_parquet(input_path)
                if df.empty:
                    return {'valid': False, 'error': 'Parquet文件为空'}
            elif format.lower() == "numpy":
                try:
                    np.load(input_path)
                except Exception as e:
                    return {'valid': False, 'error': f'NumPy文件格式错误: {str(e)}'}

            return {'valid': True, 'message': '文件验证通过'}

        except Exception as e:
            return {'valid': False, 'error': str(e)}


# 全局向量数据导入导出管理器实例
import_export_manager = VectorImportExportManager()


async def get_import_export_manager() -> VectorImportExportManager:
    """获取向量数据导入导出管理器实例"""
    return import_export_manager