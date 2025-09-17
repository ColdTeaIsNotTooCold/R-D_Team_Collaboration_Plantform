"""
文本处理工具函数
提供文本清理、分块、格式化等功能
"""

import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import unicodedata

logger = logging.getLogger(__name__)


@dataclass
class ChunkConfig:
    """文本分块配置"""
    max_chunk_size: int = 1000  # 每个块的最大字符数
    min_chunk_size: int = 100   # 每个块的最小字符数
    overlap_size: int = 200     # 块之间的重叠字符数
    sentence_split_min_len: int = 50  # 句子分割的最小长度


class TextUtils:
    """文本处理工具类"""

    def __init__(self, config: Optional[ChunkConfig] = None):
        """初始化文本工具"""
        self.config = config or ChunkConfig()

        # 编译正则表达式
        self._compile_regex_patterns()

    def _compile_regex_patterns(self):
        """编译常用的正则表达式模式"""
        # 匹配中英文句子结束符
        self.sentence_end_pattern = re.compile(
            r'[.!?。！？]+\s*'
        )

        # 匹配代码块
        self.code_block_pattern = re.compile(
            r'```[\s\S]*?```|`[^`\n]+`'
        )

        # 匹配URL
        self.url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )

        # 匹配邮箱
        self.email_pattern = re.compile(
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        )

        # 匹配多余的空白字符
        self.whitespace_pattern = re.compile(
            r'\s+'
        )

        # 匹配中英文混合的空白字符
        self.mixed_whitespace_pattern = re.compile(
            r'([\u4e00-\u9fff])\s+([a-zA-Z])|([a-zA-Z])\s+([\u4e00-\u9fff])'
        )

    def clean_text(self, text: str) -> str:
        """
        清理文本内容

        Args:
            text: 原始文本

        Returns:
            清理后的文本
        """
        try:
            if not text or not isinstance(text, str):
                return ""

            # 规范化Unicode字符
            text = unicodedata.normalize('NFKC', text)

            # 移除控制字符（保留换行和制表符）
            text = ''.join(char for char in text if unicodedata.category(char)[0] != 'C' or char in '\n\t')

            # 处理中英文混合空白
            text = self.mixed_whitespace_pattern.sub(
                lambda m: f"{m.group(1) or m.group(3)}{m.group(2) or m.group(4)}",
                text
            )

            # 标准化空白字符
            text = self.whitespace_pattern.sub(' ', text)

            # 移除首尾空白
            text = text.strip()

            return text

        except Exception as e:
            logger.error(f"文本清理失败: {e}")
            return text if isinstance(text, str) else ""

    def chunk_text(self, text: str) -> List[str]:
        """
        将文本分割成块

        Args:
            text: 要分割的文本

        Returns:
            文本块列表
        """
        try:
            if not text or len(text) <= self.config.max_chunk_size:
                return [text] if text else []

            # 预处理文本
            cleaned_text = self.clean_text(text)
            if not cleaned_text:
                return []

            chunks = []
            current_position = 0
            text_length = len(cleaned_text)

            while current_position < text_length:
                # 计算当前块的结束位置
                chunk_end = min(current_position + self.config.max_chunk_size, text_length)

                # 如果不是最后一块，尝试在句子边界分割
                if chunk_end < text_length:
                    # 向前查找合适的分割点
                    split_position = self._find_optimal_split_position(
                        cleaned_text, current_position, chunk_end
                    )

                    if split_position > current_position + self.config.min_chunk_size:
                        chunk_end = split_position

                # 提取当前块
                chunk = cleaned_text[current_position:chunk_end].strip()

                if chunk:
                    chunks.append(chunk)

                # 更新位置（考虑重叠）
                current_position = chunk_end - self.config.overlap_size

                # 确保前进
                if current_position <= chunk_end - self.config.max_chunk_size:
                    current_position = chunk_end

            return chunks

        except Exception as e:
            logger.error(f"文本分块失败: {e}")
            return [text] if text else []

    def _find_optimal_split_position(self, text: str, start: int, end: int) -> int:
        """
        查找最优的分割位置

        Args:
            text: 文本内容
            start: 起始位置
            end: 结束位置

        Returns:
            最优分割位置
        """
        # 优先在段落边界分割
        paragraph_end = text.rfind('\n\n', start, end)
        if paragraph_end > start + self.config.min_chunk_size:
            return paragraph_end

        # 其次在句子边界分割
        sentence_end = self.sentence_end_pattern.search(text[start:end])
        if sentence_end:
            split_pos = start + sentence_end.end()
            if split_pos > start + self.config.min_chunk_size:
                return split_pos

        # 最后在标点符号分割
        for i in range(end - 1, max(start, end - 100), -1):
            if text[i] in '，,、；;：:':
                return i + 1

        # 如果都没有合适的分割点，返回原始结束位置
        return end

    def extract_keywords(self, text: str, max_keywords: int = 20) -> List[str]:
        """
        提取关键词

        Args:
            text: 文本内容
            max_keywords: 最大关键词数量

        Returns:
            关键词列表
        """
        try:
            # 移除代码块中的内容
            text = self.code_block_pattern.sub('', text)

            # 移除URL和邮箱
            text = self.url_pattern.sub('', text)
            text = self.email_pattern.sub('', text)

            # 分割文本为词语（简单的中文分词）
            words = self._simple_chinese_tokenize(text)

            # 过滤停用词
            filtered_words = self._filter_stop_words(words)

            # 统计词频
            word_freq = {}
            for word in filtered_words:
                if len(word) > 1:  # 过滤单字符
                    word_freq[word] = word_freq.get(word, 0) + 1

            # 按频率排序
            sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)

            # 返回前N个关键词
            return [word for word, freq in sorted_words[:max_keywords]]

        except Exception as e:
            logger.error(f"关键词提取失败: {e}")
            return []

    def _simple_chinese_tokenize(self, text: str) -> List[str]:
        """
        简单的中文分词

        Args:
            text: 文本内容

        Returns:
            词语列表
        """
        # 移除标点符号和特殊字符
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', ' ', text)

        # 分割词语
        words = re.findall(r'[a-zA-Z]+|\u4e00-\u9fff+', text)

        return words

    def _filter_stop_words(self, words: List[str]) -> List[str]:
        """
        过滤停用词

        Args:
            words: 词语列表

        Returns:
            过滤后的词语列表
        """
        # 基础停用词列表
        stop_words = {
            # 中文停用词
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '个',
            '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看',
            '好', '自己', '这', '那', '他', '她', '它', '们', '什么', '怎么', '为什么',
            '如何', '哪里', '哪个', '哪些', '什么时候', '多少', '几', '是否', '能否',
            # 英文停用词
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'between', 'among', 'is', 'are',
            'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does',
            'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we',
            'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her',
            'its', 'our', 'their'
        }

        return [word for word in words if word.lower() not in stop_words]

    def format_text_for_search(self, text: str) -> str:
        """
        格式化文本用于搜索

        Args:
            text: 原始文本

        Returns:
            格式化后的文本
        """
        try:
            # 清理文本
            cleaned_text = self.clean_text(text)

            # 移除代码块
            cleaned_text = self.code_block_pattern.sub(' [CODE] ', cleaned_text)

            # 移除URL和邮箱
            cleaned_text = self.url_pattern.sub(' [URL] ', cleaned_text)
            cleaned_text = self.email_pattern.sub(' [EMAIL] ', cleaned_text)

            # 标准化空白
            cleaned_text = self.whitespace_pattern.sub(' ', cleaned_text)

            return cleaned_text.strip()

        except Exception as e:
            logger.error(f"文本格式化失败: {e}")
            return text if isinstance(text, str) else ""

    def extract_metadata_from_text(self, text: str) -> Dict[str, any]:
        """
        从文本中提取元数据

        Args:
            text: 文本内容

        Returns:
            元数据字典
        """
        try:
            metadata = {
                'char_count': len(text),
                'word_count': len(text.split()),
                'line_count': len(text.splitlines()),
                'has_code': bool(self.code_block_pattern.search(text)),
                'has_urls': bool(self.url_pattern.search(text)),
                'has_emails': bool(self.email_pattern.search(text)),
                'language': self._detect_language(text),
                'keywords': self.extract_keywords(text, max_keywords=10)
            }

            return metadata

        except Exception as e:
            logger.error(f"元数据提取失败: {e}")
            return {}

    def _detect_language(self, text: str) -> str:
        """
        简单的语言检测

        Args:
            text: 文本内容

        Returns:
            语言代码 ('zh', 'en', 'mixed')
        """
        try:
            chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
            english_chars = len(re.findall(r'[a-zA-Z]', text))
            total_chars = chinese_chars + english_chars

            if total_chars == 0:
                return 'unknown'

            chinese_ratio = chinese_chars / total_chars
            english_ratio = english_chars / total_chars

            if chinese_ratio > 0.7:
                return 'zh'
            elif english_ratio > 0.7:
                return 'en'
            else:
                return 'mixed'

        except Exception as e:
            logger.error(f"语言检测失败: {e}")
            return 'unknown'

    def calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的相似度（基于关键词重叠）

        Args:
            text1: 第一个文本
            text2: 第二个文本

        Returns:
            相似度分数 (0-1)
        """
        try:
            # 提取关键词
            keywords1 = set(self.extract_keywords(text1))
            keywords2 = set(self.extract_keywords(text2))

            if not keywords1 and not keywords2:
                return 0.0

            # 计算Jaccard相似度
            intersection = len(keywords1 & keywords2)
            union = len(keywords1 | keywords2)

            if union == 0:
                return 0.0

            return intersection / union

        except Exception as e:
            logger.error(f"相似度计算失败: {e}")
            return 0.0

    def get_text_statistics(self, text: str) -> Dict[str, any]:
        """
        获取文本统计信息

        Args:
            text: 文本内容

        Returns:
            统计信息字典
        """
        try:
            lines = text.splitlines()
            words = text.split()
            chars = len(text)

            # 计算各种统计信息
            stats = {
                'total_characters': chars,
                'total_words': len(words),
                'total_lines': len(lines),
                'average_words_per_line': len(words) / len(lines) if lines else 0,
                'average_chars_per_word': chars / len(words) if words else 0,
                'empty_lines': sum(1 for line in lines if not line.strip()),
                'max_line_length': max(len(line) for line in lines) if lines else 0,
                'min_line_length': min(len(line) for line in lines) if lines else 0,
            }

            return stats

        except Exception as e:
            logger.error(f"统计信息计算失败: {e}")
            return {}