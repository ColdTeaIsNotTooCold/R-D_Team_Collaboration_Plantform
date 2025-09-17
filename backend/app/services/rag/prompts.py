"""
RAG提示词模板系统
提供动态提示词生成、模板管理和优化功能
"""
import logging
import json
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import re
from .retrieval import RetrievedDocument
from .context import ContextWindow

logger = logging.getLogger(__name__)


class PromptTemplateType(Enum):
    """提示词模板类型"""
    QA = "qa"  # 问答
    SUMMARY = "summary"  # 摘要
    ANALYSIS = "analysis"  # 分析
    GENERATION = "generation"  # 生成
    TRANSLATION = "translation"  # 翻译
    CODE = "code"  # 代码
    CREATIVE = "creative"  # 创意


class PromptRole(Enum):
    """提示词角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class PromptTemplate:
    """提示词模板"""
    id: str
    name: str
    type: PromptTemplateType
    template: str
    description: str = ""
    variables: List[str] = None
    version: str = "1.0"
    author: str = "system"
    created_at: str = None
    updated_at: str = None
    is_active: bool = True
    tags: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.variables is None:
            self.variables = []
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.now().isoformat()


@dataclass
class PromptVariable:
    """提示词变量"""
    name: str
    type: str
    description: str = ""
    required: bool = True
    default_value: Any = None
    validation_rules: Dict[str, Any] = None


@dataclass
class RenderedPrompt:
    """渲染后的提示词"""
    content: str
    role: PromptRole
    template_id: str
    variables: Dict[str, Any]
    tokens: int
    metadata: Dict[str, Any] = None


class PromptTemplateManager:
    """提示词模板管理器"""

    def __init__(self):
        self._templates: Dict[str, PromptTemplate] = {}
        self._variables: Dict[str, PromptVariable] = {}
        self._init_default_templates()

    def _init_default_templates(self):
        """初始化默认模板"""
        # QA模板
        self.add_template(PromptTemplate(
            id="qa_basic",
            name="基础问答",
            type=PromptTemplateType.QA,
            template="""你是一个专业的助手。请根据以下提供的上下文信息回答用户的问题。

上下文信息：
{context}

用户问题：{question}

请基于上述上下文信息，提供准确、详细的回答。如果上下文中没有足够的信息，请说明情况。

回答：""",
            description="基础问答模板，适用于一般性问题",
            variables=["context", "question"],
            tags=["qa", "basic", "general"]
        ))

        # 摘要模板
        self.add_template(PromptTemplate(
            id="summary_basic",
            name="基础摘要",
            type=PromptTemplateType.SUMMARY,
            template="""请对以下文本进行摘要，提取关键信息。

文本内容：
{text}

摘要要求：
1. 保留原文的主要观点和关键信息
2. 控制在 {max_length} 字以内
3. 语言简洁明了

摘要：""",
            description="基础摘要模板，适用于一般文本摘要",
            variables=["text", "max_length"],
            tags=["summary", "basic"]
        ))

        # 分析模板
        self.add_template(PromptTemplate(
            id="analysis_basic",
            name="基础分析",
            type=PromptTemplateType.ANALYSIS,
            template="""请对以下内容进行深入分析。

分析内容：
{content}

分析要求：
{requirements}

请提供结构化的分析结果，包括：
1. 主要观点
2. 关键发现
3. 潜在影响
4. 建议和结论

分析结果：""",
            description="基础分析模板，适用于各种分析任务",
            variables=["content", "requirements"],
            tags=["analysis", "structured"]
        ))

        # 代码模板
        self.add_template(PromptTemplate(
            id="code_basic",
            name="基础代码生成",
            type=PromptTemplateType.CODE,
            template="""请根据以下要求生成代码。

编程语言：{language}
功能需求：{requirements}
具体描述：{description}

请生成符合要求的代码，并添加必要的注释。

代码：""",
            description="基础代码生成模板",
            variables=["language", "requirements", "description"],
            tags=["code", "generation"]
        ))

        # RAG专用模板
        self.add_template(PromptTemplate(
            id="rag_qa_detailed",
            name="RAG详细问答",
            type=PromptTemplateType.QA,
            template="""你是一个知识渊博的专业助手。我需要你根据提供的参考文档来回答用户的问题。

参考文档信息：
{context_documents}

用户问题：{question}

回答要求：
1. 必须基于提供的参考文档进行回答
2. 如果参考文档中没有相关信息，请明确说明
3. 引用具体的文档内容来支持你的回答
4. 提供准确、详细、有深度的回答
5. 如果需要，可以提供多个角度的分析

请开始你的回答：""",
            description="RAG系统专用详细问答模板",
            variables=["context_documents", "question"],
            tags=["rag", "qa", "detailed"]
        ))

        # 系统提示模板
        self.add_template(PromptTemplate(
            id="system_assistant",
            name="系统助手",
            type=PromptTemplateType.QA,
            template="""你是一个专业的AI助手，具备以下特点：

1. 知识渊博：在多个领域都有深入的了解
2. 逻辑清晰：能够进行有条理的分析和推理
3. 语言准确：使用准确、专业的语言表达
4. 负责任：只提供可验证的信息，不编造内容
5. 乐于助人：耐心解答用户的问题

请记住你的角色，为用户提供最好的服务。""",
            description="系统助手角色定义模板",
            variables=[],
            tags=["system", "role"]
        ))

    def add_template(self, template: PromptTemplate):
        """添加模板"""
        template.updated_at = datetime.now().isoformat()
        self._templates[template.id] = template
        logger.info(f"添加提示词模板: {template.name} ({template.id})")

    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """获取模板"""
        return self._templates.get(template_id)

    def list_templates(self, template_type: PromptTemplateType = None, active_only: bool = True) -> List[PromptTemplate]:
        """列出模板"""
        templates = []
        for template in self._templates.values():
            if template_type and template.type != template_type:
                continue
            if active_only and not template.is_active:
                continue
            templates.append(template)
        return templates

    def update_template(self, template_id: str, **kwargs) -> bool:
        """更新模板"""
        if template_id not in self._templates:
            return False

        template = self._templates[template_id]
        for key, value in kwargs.items():
            if hasattr(template, key):
                setattr(template, key, value)

        template.updated_at = datetime.now().isoformat()
        logger.info(f"更新提示词模板: {template.name} ({template_id})")
        return True

    def delete_template(self, template_id: str) -> bool:
        """删除模板"""
        if template_id in self._templates:
            del self._templates[template_id]
            logger.info(f"删除提示词模板: {template_id}")
            return True
        return False

    def search_templates(self, query: str, template_type: PromptTemplateType = None) -> List[PromptTemplate]:
        """搜索模板"""
        results = []
        query_lower = query.lower()

        for template in self._templates.values():
            if template_type and template.type != template_type:
                continue

            # 搜索名称、描述和标签
            if (query_lower in template.name.lower() or
                query_lower in template.description.lower() or
                any(query_lower in tag.lower() for tag in template.tags)):
                results.append(template)

        return results

    def get_template_variables(self, template_id: str) -> List[PromptVariable]:
        """获取模板变量"""
        template = self.get_template(template_id)
        if not template:
            return []

        variables = []
        for var_name in template.variables:
            # 创建默认变量定义
            variable = PromptVariable(
                name=var_name,
                type="string",
                description=f"模板变量: {var_name}",
                required=True
            )
            variables.append(variable)

        return variables

    def validate_template(self, template: PromptTemplate) -> List[str]:
        """验证模板"""
        errors = []

        # 检查必需字段
        if not template.id:
            errors.append("模板ID不能为空")
        if not template.name:
            errors.append("模板名称不能为空")
        if not template.template:
            errors.append("模板内容不能为空")

        # 检查变量引用
        template_vars = self._extract_template_variables(template.template)
        defined_vars = set(template.variables)
        used_vars = set(template_vars)

        # 检查未定义的变量
        undefined_vars = used_vars - defined_vars
        if undefined_vars:
            errors.append(f"模板中使用了未定义的变量: {', '.join(undefined_vars)}")

        # 检查未使用的变量
        unused_vars = defined_vars - used_vars
        if unused_vars:
            errors.append(f"模板中定义了未使用的变量: {', '.join(unused_vars)}")

        return errors

    def _extract_template_variables(self, template_content: str) -> List[str]:
        """提取模板中的变量"""
        # 使用正则表达式匹配 {variable} 格式的变量
        pattern = r'\{([^}]+)\}'
        matches = re.findall(pattern, template_content)
        return matches


class PromptRenderer:
    """提示词渲染器"""

    def __init__(self, template_manager: PromptTemplateManager):
        self.template_manager = template_manager
        self._render_cache = {}

    def render_template(self, template_id: str, variables: Dict[str, Any], role: PromptRole = PromptRole.USER) -> RenderedPrompt:
        """渲染模板"""
        # 检查缓存
        cache_key = self._generate_cache_key(template_id, variables)
        if cache_key in self._render_cache:
            cached_result = self._render_cache[cache_key]
            return cached_result

        # 获取模板
        template = self.template_manager.get_template(template_id)
        if not template:
            raise ValueError(f"模板不存在: {template_id}")

        # 验证变量
        self._validate_variables(template, variables)

        # 渲染模板
        rendered_content = self._render_content(template.template, variables)

        # 计算token数量
        tokens = self._count_tokens(rendered_content)

        # 创建渲染结果
        rendered_prompt = RenderedPrompt(
            content=rendered_content,
            role=role,
            template_id=template_id,
            variables=variables,
            tokens=tokens,
            metadata={
                'template_name': template.name,
                'template_type': template.type.value,
                'rendered_at': datetime.now().isoformat()
            }
        )

        # 缓存结果
        self._render_cache[cache_key] = rendered_prompt

        return rendered_prompt

    def _validate_variables(self, template: PromptTemplate, variables: Dict[str, Any]):
        """验证变量"""
        missing_vars = []
        for var_name in template.variables:
            if var_name not in variables:
                missing_vars.append(var_name)

        if missing_vars:
            raise ValueError(f"缺少必需的变量: {', '.join(missing_vars)}")

    def _render_content(self, template_content: str, variables: Dict[str, Any]) -> str:
        """渲染内容"""
        try:
            # 使用str.format进行变量替换
            return template_content.format(**variables)
        except KeyError as e:
            raise ValueError(f"模板变量未提供: {e}")
        except Exception as e:
            raise ValueError(f"模板渲染失败: {e}")

    def _count_tokens(self, text: str) -> int:
        """计算token数量"""
        # 简化的token计算
        return len(text.split())

    def _generate_cache_key(self, template_id: str, variables: Dict[str, Any]) -> str:
        """生成缓存键"""
        # 简化的缓存键生成
        return f"{template_id}_{hash(str(sorted(variables.items())))}"

    def clear_cache(self):
        """清理缓存"""
        self._render_cache.clear()
        logger.info("提示词渲染缓存已清理")

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            'cache_size': len(self._render_cache),
            'timestamp': datetime.now().isoformat()
        }


class PromptOptimizer:
    """提示词优化器"""

    def __init__(self, template_manager: PromptTemplateManager):
        self.template_manager = template_manager

    def optimize_for_rag(self, context_window: ContextWindow, query: str,
                        template_id: str = "rag_qa_detailed") -> RenderedPrompt:
        """为RAG优化提示词"""
        # 准备上下文文档
        context_documents = self._format_context_documents(context_window.documents)

        # 准备变量
        variables = {
            "context_documents": context_documents,
            "question": query
        }

        # 渲染模板
        renderer = PromptRenderer(self.template_manager)
        return renderer.render_template(template_id, variables)

    def _format_context_documents(self, documents: List[RetrievedDocument]) -> str:
        """格式化上下文文档"""
        if not documents:
            return "没有提供相关的参考文档。"

        formatted_docs = []
        for i, doc in enumerate(documents, 1):
            doc_text = f"""文档 {i}:
内容: {doc.content}
来源: {doc.metadata.get('source', '未知')}
相似度分数: {doc.score:.2f}
"""
            formatted_docs.append(doc_text)

        return "\n".join(formatted_docs)

    def optimize_for_context_length(self, rendered_prompt: RenderedPrompt, max_tokens: int) -> RenderedPrompt:
        """根据上下文长度优化提示词"""
        if rendered_prompt.tokens <= max_tokens:
            return rendered_prompt

        # 需要压缩
        compression_ratio = max_tokens / rendered_prompt.tokens

        # 简单的压缩策略：截断
        new_content = rendered_prompt.content[:int(len(rendered_prompt.content) * compression_ratio)]
        new_tokens = self._count_tokens(new_content)

        # 创建新的渲染结果
        optimized_prompt = RenderedPrompt(
            content=new_content,
            role=rendered_prompt.role,
            template_id=rendered_prompt.template_id,
            variables=rendered_prompt.variables,
            tokens=new_tokens,
            metadata={
                **rendered_prompt.metadata,
                'optimized': True,
                'original_tokens': rendered_prompt.tokens,
                'compression_ratio': compression_ratio,
                'optimized_at': datetime.now().isoformat()
            }
        )

        return optimized_prompt

    def _count_tokens(self, text: str) -> int:
        """计算token数量"""
        return len(text.split())

    def suggest_template(self, query: str, context_size: int, task_type: str = "qa") -> str:
        """建议模板"""
        if task_type == "qa":
            if context_size > 2000:
                return "rag_qa_detailed"
            else:
                return "qa_basic"
        elif task_type == "summary":
            return "summary_basic"
        elif task_type == "analysis":
            return "analysis_basic"
        elif task_type == "code":
            return "code_basic"
        else:
            return "qa_basic"

    def create_custom_template(self, base_template_id: str, customizations: Dict[str, Any]) -> PromptTemplate:
        """创建自定义模板"""
        base_template = self.template_manager.get_template(base_template_id)
        if not base_template:
            raise ValueError(f"基础模板不存在: {base_template_id}")

        # 创建自定义模板
        custom_template = PromptTemplate(
            id=f"custom_{base_template_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            name=f"自定义{base_template.name}",
            type=base_template.type,
            template=self._apply_customizations(base_template.template, customizations),
            description=f"基于{base_template.name}的自定义模板",
            variables=base_template.variables,
            tags=base_template.tags + ["custom"],
            metadata={
                "base_template": base_template_id,
                "customizations": customizations
            }
        )

        return custom_template

    def _apply_customizations(self, template: str, customizations: Dict[str, Any]) -> str:
        """应用自定义设置"""
        # 这里可以实现各种自定义逻辑
        # 例如：添加指令、修改格式等
        customized_template = template

        if "additional_instructions" in customizations:
            customized_template += f"\n\n{customizations['additional_instructions']}"

        if "format_requirements" in customizations:
            customized_template += f"\n\n格式要求: {customizations['format_requirements']}"

        return customized_template


class PromptSystem:
    """提示词系统"""

    def __init__(self):
        self.template_manager = PromptTemplateManager()
        self.renderer = PromptRenderer(self.template_manager)
        self.optimizer = PromptOptimizer(self.template_manager)

    def get_system_prompt(self, role: str = "assistant") -> RenderedPrompt:
        """获取系统提示"""
        return self.renderer.render_template("system_assistant", {}, PromptRole.SYSTEM)

    def generate_rag_prompt(self, context_window: ContextWindow, query: str) -> RenderedPrompt:
        """生成RAG提示"""
        return self.optimizer.optimize_for_rag(context_window, query)

    def render_template(self, template_id: str, variables: Dict[str, Any],
                        role: PromptRole = PromptRole.USER) -> RenderedPrompt:
        """渲染模板"""
        return self.renderer.render_template(template_id, variables, role)

    def get_template_manager(self) -> PromptTemplateManager:
        """获取模板管理器"""
        return self.template_manager

    def get_optimizer(self) -> PromptOptimizer:
        """获取优化器"""
        return self.optimizer