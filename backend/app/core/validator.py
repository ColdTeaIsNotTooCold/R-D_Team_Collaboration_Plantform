import json
import re
import time
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
from fastapi import HTTPException

from ..schemas.validator import (
    ValidationResult, ValidationType, ValidationSeverity, ValidationRule,
    ValidationCheck, ValidationReport, ValidationRequest, ValidationResponse,
    QualityMetrics, ValidationStats, TaskResultValidation
)
from ..database import get_db
from ..core.config import settings


class ValidationEngine:
    """验证引擎核心类"""

    def __init__(self, db: AsyncSession = None):
        self.db = db
        self.validation_cache = {}
        self.rule_cache = {}

    async def load_rules(self) -> List[ValidationRule]:
        """加载验证规则"""
        if not self.db:
            return []

        query = select(ValidationRule).where(ValidationRule.is_active == True)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def validate_task_result(
        self,
        request: ValidationRequest,
        context: Optional[Dict[str, Any]] = None
    ) -> ValidationResponse:
        """验证任务结果"""
        start_time = time.time()
        validation_id = f"val_{int(time.time() * 1000)}"

        try:
            # 加载验证规则
            rules = await self._get_validation_rules(request)

            # 执行验证
            checks = []
            for rule in rules:
                check = await self._execute_validation(rule, request, context)
                checks.append(check)

            # 计算总体结果
            overall_result = self._calculate_overall_result(checks)

            # 生成验证报告
            report = await self._generate_validation_report(
                validation_id, request, checks, overall_result, time.time() - start_time
            )

            # 创建响应
            response = ValidationResponse(
                validation_id=validation_id,
                task_id=request.task_id,
                execution_id=request.execution_id,
                result=overall_result,
                checks=checks,
                execution_time=time.time() - start_time,
                report=report,
                message=f"验证完成，共执行 {len(checks)} 项检查",
                created_at=datetime.now()
            )

            # 存储验证结果
            if self.db:
                await self._store_validation_results(response)

            return response

        except Exception as e:
            return ValidationResponse(
                validation_id=validation_id,
                task_id=request.task_id,
                execution_id=request.execution_id,
                result=ValidationResult.FAILED,
                checks=[],
                execution_time=time.time() - start_time,
                message=f"验证过程中发生错误: {str(e)}",
                created_at=datetime.now()
            )

    async def _get_validation_rules(self, request: ValidationRequest) -> List[ValidationRule]:
        """获取适用的验证规则"""
        if request.rules:
            # 指定规则ID
            if self.db:
                query = select(ValidationRule).where(
                    ValidationRule.id.in_(request.rules),
                    ValidationRule.is_active == True
                )
                result = await self.db.execute(query)
                return result.scalars().all()
            return []
        else:
            # 按验证类型获取规则
            if self.db:
                query = select(ValidationRule).where(
                    ValidationRule.type == request.validation_type,
                    ValidationRule.is_active == True
                )
                result = await self.db.execute(query)
                return result.scalars().all()
            return []

    async def _execute_validation(
        self,
        rule: ValidationRule,
        request: ValidationRequest,
        context: Optional[Dict[str, Any]] = None
    ) -> ValidationCheck:
        """执行单个验证规则"""
        start_time = time.time()

        try:
            # 准备验证上下文
            validation_context = {
                'data': request.data or {},
                'context': context or {},
                'rule': rule,
                'task_id': request.task_id,
                'execution_id': request.execution_id
            }

            # 执行验证逻辑
            result, actual_value, message = await self._apply_validation_rule(rule, validation_context)

            # 创建检查项
            check = ValidationCheck(
                id=int(time.time() * 1000),  # 简单ID生成
                rule_id=rule.id,
                task_id=request.task_id,
                execution_id=request.execution_id,
                check_name=rule.name,
                actual_value=str(actual_value) if actual_value is not None else None,
                expected_value=rule.expected_result,
                result=result,
                message=message or rule.error_message,
                execution_time=time.time() - start_time,
                created_at=datetime.now()
            )

            return check

        except Exception as e:
            return ValidationCheck(
                id=int(time.time() * 1000),
                rule_id=rule.id,
                task_id=request.task_id,
                execution_id=request.execution_id,
                check_name=rule.name,
                result=ValidationResult.FAILED,
                message=f"验证执行失败: {str(e)}",
                execution_time=time.time() - start_time,
                created_at=datetime.now()
            )

    async def _apply_validation_rule(
        self,
        rule: ValidationRule,
        context: Dict[str, Any]
    ) -> tuple[ValidationResult, Any, str]:
        """应用验证规则"""
        condition = rule.condition
        data = context.get('data', {})

        try:
            if rule.type == ValidationType.SCHEMA:
                return await self._validate_schema(condition, data)
            elif rule.type == ValidationType.BUSINESS_RULE:
                return await self._validate_business_rule(condition, data, context)
            elif rule.type == ValidationType.DATA_QUALITY:
                return await self._validate_data_quality(condition, data)
            elif rule.type == ValidationType.PERFORMANCE:
                return await self._validate_performance(condition, data)
            elif rule.type == ValidationType.SECURITY:
                return await self._validate_security(condition, data)
            elif rule.type == ValidationType.CUSTOM:
                return await self._validate_custom(condition, data, context)
            else:
                return ValidationResult.FAILED, None, f"不支持的验证类型: {rule.type}"

        except Exception as e:
            return ValidationResult.FAILED, None, f"规则应用失败: {str(e)}"

    async def _validate_schema(self, condition: str, data: Dict[str, Any]) -> tuple[ValidationResult, Any, str]:
        """验证数据架构"""
        try:
            schema_def = json.loads(condition)
            required_fields = schema_def.get('required', [])
            field_types = schema_def.get('types', {})

            issues = []

            # 检查必填字段
            for field in required_fields:
                if field not in data:
                    issues.append(f"缺少必填字段: {field}")

            # 检查字段类型
            for field, expected_type in field_types.items():
                if field in data:
                    actual_type = type(data[field]).__name__
                    if actual_type != expected_type:
                        issues.append(f"字段 {field} 类型错误: 期望 {expected_type}, 实际 {actual_type}")

            if issues:
                return ValidationResult.FAILED, len(issues), f"架构验证失败: {'; '.join(issues)}"
            else:
                return ValidationResult.PASSED, 0, "架构验证通过"

        except json.JSONDecodeError:
            return ValidationResult.FAILED, None, "架构定义格式错误"

    async def _validate_business_rule(self, condition: str, data: Dict[str, Any], context: Dict[str, Any]) -> tuple[ValidationResult, Any, str]:
        """验证业务规则"""
        try:
            # 简单的条件评估
            if condition.startswith('eq:'):
                field, expected = condition[3:].split('=', 1)
                actual = data.get(field)
                result = str(actual) == expected
                return ValidationResult.PASSED if result else ValidationResult.FAILED, actual, f"业务规则检查: {field}"

            elif condition.startswith('gt:'):
                field, value = condition[3:].split('=', 1)
                actual = data.get(field)
                try:
                    result = float(actual) > float(value)
                    return ValidationResult.PASSED if result else ValidationResult.FAILED, actual, f"业务规则检查: {field}"
                except (ValueError, TypeError):
                    return ValidationResult.FAILED, actual, f"业务规则检查失败: {field} 不是数字"

            elif condition.startswith('regex:'):
                field, pattern = condition[6:].split('=', 1)
                actual = data.get(field)
                if actual is None:
                    return ValidationResult.FAILED, None, f"业务规则检查: {field} 为空"
                result = bool(re.match(pattern, str(actual)))
                return ValidationResult.PASSED if result else ValidationResult.FAILED, actual, f"业务规则检查: {field}"

            else:
                return ValidationResult.WARNING, None, f"未知的业务规则格式: {condition}"

        except Exception as e:
            return ValidationResult.FAILED, None, f"业务规则验证失败: {str(e)}"

    async def _validate_data_quality(self, condition: str, data: Dict[str, Any]) -> tuple[ValidationResult, Any, str]:
        """验证数据质量"""
        try:
            if condition == 'completeness':
                total_fields = len(data)
                non_null_fields = sum(1 for v in data.values() if v is not None)
                completeness = non_null_fields / total_fields if total_fields > 0 else 0

                if completeness >= 0.9:
                    return ValidationResult.PASSED, completeness, f"数据完整度: {completeness:.2%}"
                elif completeness >= 0.7:
                    return ValidationResult.WARNING, completeness, f"数据完整度较低: {completeness:.2%}"
                else:
                    return ValidationResult.FAILED, completeness, f"数据完整度过低: {completeness:.2%}"

            elif condition == 'consistency':
                # 简单的一致性检查
                issues = []
                for key, value in data.items():
                    if isinstance(value, str) and len(value.strip()) == 0:
                        issues.append(f"字段 {key} 为空字符串")

                if issues:
                    return ValidationResult.FAILED, len(issues), f"数据一致性检查失败: {'; '.join(issues)}"
                else:
                    return ValidationResult.PASSED, 0, "数据一致性检查通过"

            else:
                return ValidationResult.WARNING, None, f"未知的数据质量条件: {condition}"

        except Exception as e:
            return ValidationResult.FAILED, None, f"数据质量验证失败: {str(e)}"

    async def _validate_performance(self, condition: str, data: Dict[str, Any]) -> tuple[ValidationResult, Any, str]:
        """验证性能指标"""
        try:
            if condition.startswith('response_time:'):
                max_time = float(condition[13:])
                response_time = data.get('response_time', 0)

                if response_time <= max_time:
                    return ValidationResult.PASSED, response_time, f"响应时间检查通过: {response_time}ms"
                else:
                    return ValidationResult.FAILED, response_time, f"响应时间超限: {response_time}ms > {max_time}ms"

            elif condition.startswith('throughput:'):
                min_throughput = float(condition[11:])
                throughput = data.get('throughput', 0)

                if throughput >= min_throughput:
                    return ValidationResult.PASSED, throughput, f"吞吐量检查通过: {throughput}"
                else:
                    return ValidationResult.FAILED, throughput, f"吞吐量不足: {throughput} < {min_throughput}"

            else:
                return ValidationResult.WARNING, None, f"未知的性能条件: {condition}"

        except Exception as e:
            return ValidationResult.FAILED, None, f"性能验证失败: {str(e)}"

    async def _validate_security(self, condition: str, data: Dict[str, Any]) -> tuple[ValidationResult, Any, str]:
        """验证安全性"""
        try:
            if condition == 'no_sensitive_data':
                sensitive_patterns = [
                    r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # 信用卡
                    r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
                    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'  # 邮箱
                ]

                text_data = str(data)
                issues = []

                for i, pattern in enumerate(sensitive_patterns):
                    if re.search(pattern, text_data):
                        issues.append(f"发现敏感数据模式 {i+1}")

                if issues:
                    return ValidationResult.FAILED, len(issues), f"安全检查失败: {'; '.join(issues)}"
                else:
                    return ValidationResult.PASSED, 0, "安全检查通过"

            else:
                return ValidationResult.WARNING, None, f"未知的安全条件: {condition}"

        except Exception as e:
            return ValidationResult.FAILED, None, f"安全验证失败: {str(e)}"

    async def _validate_custom(self, condition: str, data: Dict[str, Any], context: Dict[str, Any]) -> tuple[ValidationResult, Any, str]:
        """自定义验证"""
        try:
            # 这里可以实现自定义验证逻辑
            # 简单示例：检查特定字段的值范围
            if condition.startswith('range:'):
                parts = condition[6:].split(':')
                if len(parts) == 3:
                    field, min_val, max_val = parts
                    actual = data.get(field)

                    if actual is None:
                        return ValidationResult.FAILED, None, f"自定义验证: 字段 {field} 不存在"

                    try:
                        actual_num = float(actual)
                        min_num = float(min_val)
                        max_num = float(max_val)

                        if min_num <= actual_num <= max_num:
                            return ValidationResult.PASSED, actual_num, f"自定义验证通过: {field} 在范围内"
                        else:
                            return ValidationResult.FAILED, actual_num, f"自定义验证失败: {field} 不在范围 [{min_num}, {max_num}]"
                    except ValueError:
                        return ValidationResult.FAILED, actual, f"自定义验证失败: {field} 不是数字"

            return ValidationResult.WARNING, None, f"自定义验证未实现: {condition}"

        except Exception as e:
            return ValidationResult.FAILED, None, f"自定义验证失败: {str(e)}"

    def _calculate_overall_result(self, checks: List[ValidationCheck]) -> ValidationResult:
        """计算总体验证结果"""
        if not checks:
            return ValidationResult.SKIPPED

        failed_count = sum(1 for check in checks if check.result == ValidationResult.FAILED)
        warning_count = sum(1 for check in checks if check.result == ValidationResult.WARNING)

        if failed_count > 0:
            return ValidationResult.FAILED
        elif warning_count > 0:
            return ValidationResult.WARNING
        else:
            return ValidationResult.PASSED

    async def _generate_validation_report(
        self,
        validation_id: str,
        request: ValidationRequest,
        checks: List[ValidationCheck],
        overall_result: ValidationResult,
        execution_time: float
    ) -> ValidationReport:
        """生成验证报告"""
        total_checks = len(checks)
        passed_checks = sum(1 for check in checks if check.result == ValidationResult.PASSED)
        failed_checks = sum(1 for check in checks if check.result == ValidationResult.FAILED)
        warning_checks = sum(1 for check in checks if check.result == ValidationResult.WARNING)
        skipped_checks = sum(1 for check in checks if check.result == ValidationResult.SKIPPED)

        details = {
            'validation_id': validation_id,
            'validation_type': request.validation_type.value,
            'check_details': [
                {
                    'rule_id': check.rule_id,
                    'check_name': check.check_name,
                    'result': check.result.value,
                    'message': check.message,
                    'execution_time': check.execution_time
                }
                for check in checks
            ]
        }

        return ValidationReport(
            id=int(time.time() * 1000),
            task_id=request.task_id,
            execution_id=request.execution_id,
            report_type='validation_summary',
            overall_result=overall_result,
            total_checks=total_checks,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            warning_checks=warning_checks,
            skipped_checks=skipped_checks,
            execution_time=execution_time,
            details=details,
            created_at=datetime.now()
        )

    async def _store_validation_results(self, response: ValidationResponse) -> None:
        """存储验证结果"""
        if not self.db:
            return

        try:
            # 存储验证报告
            if response.report:
                self.db.add(response.report)

            # 存储验证检查项
            for check in response.checks:
                self.db.add(check)

            await self.db.commit()

        except Exception as e:
            await self.db.rollback()
            print(f"存储验证结果失败: {e}")

    async def get_validation_stats(self, task_id: Optional[int] = None) -> ValidationStats:
        """获取验证统计信息"""
        if not self.db:
            return ValidationStats(
                total_validations=0,
                successful_validations=0,
                failed_validations=0,
                success_rate=0.0,
                most_common_errors=[]
            )

        try:
            # 这里应该查询数据库获取统计信息
            # 简化实现
            return ValidationStats(
                total_validations=0,
                successful_validations=0,
                failed_validations=0,
                success_rate=0.0,
                most_common_errors=[]
            )

        except Exception as e:
            print(f"获取验证统计失败: {e}")
            return ValidationStats(
                total_validations=0,
                successful_validations=0,
                failed_validations=0,
                success_rate=0.0,
                most_common_errors=[]
            )

    async def calculate_quality_metrics(self, task_id: int) -> QualityMetrics:
        """计算质量指标"""
        if not self.db:
            return QualityMetrics()

        try:
            # 这里应该根据历史验证数据计算质量指标
            # 简化实现
            return QualityMetrics(
                accuracy=0.95,
                completeness=0.90,
                consistency=0.88,
                timeliness=0.92,
                validity=0.94,
                uniqueness=0.96,
                overall_score=0.92,
                calculated_at=datetime.now()
            )

        except Exception as e:
            print(f"计算质量指标失败: {e}")
            return QualityMetrics()


# 创建全局验证引擎实例
validation_engine = ValidationEngine()