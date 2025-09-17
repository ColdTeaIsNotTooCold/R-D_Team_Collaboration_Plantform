from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ValidationResult(str, Enum):
    """验证结果枚举"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


class ValidationType(str, Enum):
    """验证类型枚举"""
    SCHEMA = "schema"
    BUSINESS_RULE = "business_rule"
    DATA_QUALITY = "data_quality"
    PERFORMANCE = "performance"
    SECURITY = "security"
    CUSTOM = "custom"


class ValidationSeverity(str, Enum):
    """验证严重程度枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ValidationRule(BaseModel):
    """验证规则"""
    id: int = Field(..., description="规则ID")
    name: str = Field(..., description="规则名称")
    description: Optional[str] = Field(None, description="规则描述")
    type: ValidationType = Field(..., description="验证类型")
    severity: ValidationSeverity = Field(ValidationSeverity.MEDIUM, description="严重程度")
    condition: str = Field(..., description="验证条件")
    expected_result: Optional[str] = Field(None, description="预期结果")
    error_message: Optional[str] = Field(None, description="错误消息")
    is_active: bool = Field(True, description="是否启用")
    metadata: Optional[Dict[str, Any]] = Field(None, description="规则元数据")


class ValidationCheck(BaseModel):
    """验证检查项"""
    id: int = Field(..., description="检查项ID")
    rule_id: int = Field(..., description="关联规则ID")
    task_id: Optional[int] = Field(None, description="关联任务ID")
    execution_id: Optional[int] = Field(None, description="执行ID")
    check_name: str = Field(..., description="检查名称")
    actual_value: Optional[str] = Field(None, description="实际值")
    expected_value: Optional[str] = Field(None, description="期望值")
    result: ValidationResult = Field(..., description="验证结果")
    message: Optional[str] = Field(None, description="验证消息")
    execution_time: Optional[float] = Field(None, description="执行时间（秒）")
    created_at: datetime = Field(..., description="创建时间")

    class Config:
        from_attributes = True


class ValidationReport(BaseModel):
    """验证报告"""
    id: int = Field(..., description="报告ID")
    task_id: Optional[int] = Field(None, description="关联任务ID")
    execution_id: Optional[int] = Field(None, description="执行ID")
    report_type: str = Field(..., description="报告类型")
    overall_result: ValidationResult = Field(..., description="总体结果")
    total_checks: int = Field(..., description="总检查数")
    passed_checks: int = Field(..., description="通过检查数")
    failed_checks: int = Field(..., description="失败检查数")
    warning_checks: int = Field(..., description="警告检查数")
    skipped_checks: int = Field(..., description="跳过检查数")
    execution_time: Optional[float] = Field(None, description="总执行时间（秒）")
    details: Optional[Dict[str, Any]] = Field(None, description="详细信息")
    created_at: datetime = Field(..., description="创建时间")

    class Config:
        from_attributes = True


class ValidationSummary(BaseModel):
    """验证摘要"""
    total_tasks: int = Field(..., description="总任务数")
    validated_tasks: int = Field(..., description="已验证任务数")
    overall_success_rate: float = Field(..., ge=0, le=1, description="总体成功率")
    average_execution_time: Optional[float] = Field(None, description="平均执行时间（秒）")
    critical_issues: int = Field(..., description="关键问题数")
    high_issues: int = Field(..., description="高优先级问题数")
    medium_issues: int = Field(..., description="中优先级问题数")
    low_issues: int = Field(..., description="低优先级问题数")
    last_updated: datetime = Field(..., description="最后更新时间")


class ValidationRequest(BaseModel):
    """验证请求"""
    task_id: Optional[int] = Field(None, description="任务ID")
    execution_id: Optional[int] = Field(None, description="执行ID")
    validation_type: ValidationType = Field(..., description="验证类型")
    rules: Optional[List[int]] = Field(None, description="要应用的规则ID列表")
    data: Optional[Dict[str, Any]] = Field(None, description="要验证的数据")
    context: Optional[Dict[str, Any]] = Field(None, description="验证上下文")
    timeout: Optional[int] = Field(300, description="超时时间（秒）")


class ValidationResponse(BaseModel):
    """验证响应"""
    validation_id: str = Field(..., description="验证ID")
    task_id: Optional[int] = Field(None, description="任务ID")
    execution_id: Optional[int] = Field(None, description="执行ID")
    result: ValidationResult = Field(..., description="验证结果")
    checks: List[ValidationCheck] = Field([], description="验证检查项")
    execution_time: Optional[float] = Field(None, description="执行时间（秒）")
    report: Optional[ValidationReport] = Field(None, description="验证报告")
    message: Optional[str] = Field(None, description="消息")
    created_at: datetime = Field(..., description="创建时间")


class ValidationRuleCreate(BaseModel):
    """创建验证规则请求"""
    name: str = Field(..., description="规则名称")
    description: Optional[str] = Field(None, description="规则描述")
    type: ValidationType = Field(..., description="验证类型")
    severity: ValidationSeverity = Field(ValidationSeverity.MEDIUM, description="严重程度")
    condition: str = Field(..., description="验证条件")
    expected_result: Optional[str] = Field(None, description="预期结果")
    error_message: Optional[str] = Field(None, description="错误消息")
    metadata: Optional[Dict[str, Any]] = Field(None, description="规则元数据")


class ValidationRuleUpdate(BaseModel):
    """更新验证规则请求"""
    name: Optional[str] = Field(None, description="规则名称")
    description: Optional[str] = Field(None, description="规则描述")
    type: Optional[ValidationType] = Field(None, description="验证类型")
    severity: Optional[ValidationSeverity] = Field(None, description="严重程度")
    condition: Optional[str] = Field(None, description="验证条件")
    expected_result: Optional[str] = Field(None, description="预期结果")
    error_message: Optional[str] = Field(None, description="错误消息")
    is_active: Optional[bool] = Field(None, description="是否启用")
    metadata: Optional[Dict[str, Any]] = Field(None, description="规则元数据")


class QualityMetrics(BaseModel):
    """质量指标"""
    accuracy: Optional[float] = Field(None, ge=0, le=1, description="准确度")
    completeness: Optional[float] = Field(None, ge=0, le=1, description="完整度")
    consistency: Optional[float] = Field(None, ge=0, le=1, description="一致性")
    timeliness: Optional[float] = Field(None, ge=0, le=1, description="及时性")
    validity: Optional[float] = Field(None, ge=0, le=1, description="有效性")
    uniqueness: Optional[float] = Field(None, ge=0, le=1, description="唯一性")
    overall_score: Optional[float] = Field(None, ge=0, le=1, description="总体评分")
    calculated_at: Optional[datetime] = Field(None, description="计算时间")


class ValidationStats(BaseModel):
    """验证统计"""
    total_validations: int = Field(..., description="总验证次数")
    successful_validations: int = Field(..., description="成功验证次数")
    failed_validations: int = Field(..., description="失败验证次数")
    success_rate: float = Field(..., ge=0, le=1, description="成功率")
    average_validation_time: Optional[float] = Field(None, description="平均验证时间（秒）")
    last_validation_time: Optional[datetime] = Field(None, description="最后验证时间")
    most_common_errors: List[Dict[str, Any]] = Field([], description="最常见错误")
    performance_metrics: Optional[QualityMetrics] = Field(None, description="性能指标")


class TaskResultValidation(BaseModel):
    """任务结果验证"""
    task_id: int = Field(..., description="任务ID")
    execution_id: Optional[int] = Field(None, description="执行ID")
    input_data: Optional[Dict[str, Any]] = Field(None, description="输入数据")
    output_data: Optional[Dict[str, Any]] = Field(None, description="输出数据")
    validation_result: ValidationResult = Field(..., description="验证结果")
    quality_score: Optional[float] = Field(None, ge=0, le=1, description="质量评分")
    issues: List[Dict[str, Any]] = Field([], description="问题列表")
    recommendations: List[str] = Field([], description="建议列表")
    validated_at: datetime = Field(..., description="验证时间")
    validator_version: Optional[str] = Field(None, description="验证器版本")