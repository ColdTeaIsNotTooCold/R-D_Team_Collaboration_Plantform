from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime

from ..core.database import get_db
from ..core.validator import ValidationEngine, validation_engine
from ..schemas.validator import (
    ValidationRequest, ValidationResponse, ValidationRule, ValidationRuleCreate,
    ValidationRuleUpdate, ValidationReport, ValidationStats, QualityMetrics,
    TaskResultValidation, ValidationResult, ValidationType
)
from ..api.deps import get_current_active_user

router = APIRouter()


@router.post("/validate", response_model=ValidationResponse)
async def validate_task_result(
    request: ValidationRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """验证任务结果"""
    try:
        # 创建验证引擎实例
        engine = ValidationEngine(db)

        # 执行验证
        response = await engine.validate_task_result(request)

        return response

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"验证执行失败: {str(e)}"
        )


@router.post("/validate/async")
async def validate_task_result_async(
    request: ValidationRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """异步验证任务结果"""
    try:
        # 创建验证任务ID
        validation_id = f"async_val_{int(datetime.now().timestamp() * 1000)}"

        # 将验证任务添加到后台任务
        background_tasks.add_task(
            _run_validation_background,
            validation_id,
            request,
            current_user.get("user_id")
        )

        return {
            "validation_id": validation_id,
            "message": "验证任务已提交，正在后台执行",
            "status": "pending"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"异步验证提交失败: {str(e)}"
        )


async def _run_validation_background(
    validation_id: str,
    request: ValidationRequest,
    user_id: int
):
    """后台执行验证任务"""
    try:
        async for db in get_db():
            engine = ValidationEngine(db)
            response = await engine.validate_task_result(request)

            # 这里可以存储验证结果或发送通知
            print(f"背景验证完成: {validation_id}, 结果: {response.result}")

    except Exception as e:
        print(f"背景验证失败: {validation_id}, 错误: {str(e)}")


@router.get("/rules", response_model=List[ValidationRule])
async def get_validation_rules(
    skip: int = 0,
    limit: int = 100,
    validation_type: Optional[ValidationType] = None,
    is_active: bool = True,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """获取验证规则列表"""
    try:
        # 这里应该从数据库查询验证规则
        # 简化实现，返回示例规则
        sample_rules = [
            ValidationRule(
                id=1,
                name="数据完整性检查",
                description="验证必填字段是否完整",
                type=ValidationType.SCHEMA,
                severity="medium",
                condition='{"required": ["title", "task_type"], "types": {"title": "str", "task_type": "str"}}',
                error_message="缺少必填字段或字段类型错误",
                is_active=True
            ),
            ValidationRule(
                id=2,
                name="响应时间检查",
                description="验证任务响应时间是否在可接受范围内",
                type=ValidationType.PERFORMANCE,
                severity="high",
                condition="response_time:5000",
                error_message="任务响应时间超过5秒",
                is_active=True
            ),
            ValidationRule(
                id=3,
                name="安全检查",
                description="验证结果中是否包含敏感信息",
                type=ValidationType.SECURITY,
                severity="critical",
                condition="no_sensitive_data",
                error_message="结果包含敏感信息",
                is_active=True
            )
        ]

        return sample_rules

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取验证规则失败: {str(e)}"
        )


@router.post("/rules", response_model=ValidationRule)
async def create_validation_rule(
    rule: ValidationRuleCreate,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """创建验证规则"""
    try:
        # 这里应该将规则保存到数据库
        # 简化实现，返回创建的规则
        new_rule = ValidationRule(
            id=int(datetime.now().timestamp()),
            **rule.dict()
        )

        return new_rule

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建验证规则失败: {str(e)}"
        )


@router.put("/rules/{rule_id}", response_model=ValidationRule)
async def update_validation_rule(
    rule_id: int,
    rule_update: ValidationRuleUpdate,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """更新验证规则"""
    try:
        # 这里应该从数据库查询并更新规则
        # 简化实现
        if rule_id <= 0:
            raise HTTPException(status_code=404, detail="验证规则不存在")

        updated_rule = ValidationRule(
            id=rule_id,
            name="更新的规则",
            description="更新的描述",
            type=ValidationType.CUSTOM,
            severity="medium",
            condition="updated_condition",
            error_message="更新的错误消息",
            is_active=True
        )

        return updated_rule

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"更新验证规则失败: {str(e)}"
        )


@router.delete("/rules/{rule_id}")
async def delete_validation_rule(
    rule_id: int,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """删除验证规则"""
    try:
        # 这里应该从数据库删除规则
        # 简化实现
        if rule_id <= 0:
            raise HTTPException(status_code=404, detail="验证规则不存在")

        return {"message": "验证规则删除成功"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除验证规则失败: {str(e)}"
        )


@router.get("/reports/{report_id}", response_model=ValidationReport)
async def get_validation_report(
    report_id: int,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """获取验证报告"""
    try:
        # 这里应该从数据库查询验证报告
        # 简化实现
        if report_id <= 0:
            raise HTTPException(status_code=404, detail="验证报告不存在")

        report = ValidationReport(
            id=report_id,
            task_id=1,
            execution_id=1,
            report_type="validation_summary",
            overall_result=ValidationResult.PASSED,
            total_checks=3,
            passed_checks=3,
            failed_checks=0,
            warning_checks=0,
            skipped_checks=0,
            execution_time=1.5,
            details={"validation_id": "val_123456"},
            created_at=datetime.now()
        )

        return report

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取验证报告失败: {str(e)}"
        )


@router.get("/reports", response_model=List[ValidationReport])
async def get_validation_reports(
    task_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """获取验证报告列表"""
    try:
        # 这里应该从数据库查询验证报告
        # 简化实现
        reports = [
            ValidationReport(
                id=1,
                task_id=task_id or 1,
                execution_id=1,
                report_type="validation_summary",
                overall_result=ValidationResult.PASSED,
                total_checks=3,
                passed_checks=3,
                failed_checks=0,
                warning_checks=0,
                skipped_checks=0,
                execution_time=1.5,
                details={"validation_id": "val_123456"},
                created_at=datetime.now()
            )
        ]

        return reports

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取验证报告列表失败: {str(e)}"
        )


@router.get("/stats", response_model=ValidationStats)
async def get_validation_stats(
    task_id: Optional[int] = None,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """获取验证统计信息"""
    try:
        engine = ValidationEngine(db)
        stats = await engine.get_validation_stats(task_id)

        return stats

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取验证统计失败: {str(e)}"
        )


@router.get("/quality/{task_id}", response_model=QualityMetrics)
async def get_quality_metrics(
    task_id: int,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """获取质量指标"""
    try:
        engine = ValidationEngine(db)
        metrics = await engine.calculate_quality_metrics(task_id)

        return metrics

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取质量指标失败: {str(e)}"
        )


@router.post("/task-result", response_model=TaskResultValidation)
async def validate_task_result_complete(
    task_id: int,
    execution_id: Optional[int] = None,
    input_data: Optional[dict] = None,
    output_data: Optional[dict] = None,
    current_user: dict = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """完整验证任务结果"""
    try:
        # 创建验证请求
        request = ValidationRequest(
            task_id=task_id,
            execution_id=execution_id,
            validation_type=ValidationType.BUSINESS_RULE,
            data={"input": input_data, "output": output_data}
        )

        # 执行验证
        engine = ValidationEngine(db)
        validation_response = await engine.validate_task_result(request)

        # 计算质量评分
        passed_ratio = validation_response.report.passed_checks / validation_response.report.total_checks if validation_response.report.total_checks > 0 else 0

        # 收集问题
        issues = []
        for check in validation_response.checks:
            if check.result == ValidationResult.FAILED:
                issues.append({
                    "rule_id": check.rule_id,
                    "check_name": check.check_name,
                    "message": check.message,
                    "severity": "high"
                })
            elif check.result == ValidationResult.WARNING:
                issues.append({
                    "rule_id": check.rule_id,
                    "check_name": check.check_name,
                    "message": check.message,
                    "severity": "medium"
                })

        # 生成建议
        recommendations = []
        if validation_response.result == ValidationResult.FAILED:
            recommendations.append("建议检查任务执行过程，修复所有失败项")
        elif validation_response.result == ValidationResult.WARNING:
            recommendations.append("建议优化任务执行以提高质量")
        else:
            recommendations.append("任务结果质量良好，继续保持")

        # 创建完整验证结果
        task_result_validation = TaskResultValidation(
            task_id=task_id,
            execution_id=execution_id,
            input_data=input_data,
            output_data=output_data,
            validation_result=validation_response.result,
            quality_score=passed_ratio,
            issues=issues,
            recommendations=recommendations,
            validated_at=datetime.now(),
            validator_version="1.0.0"
        )

        return task_result_validation

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"完整任务结果验证失败: {str(e)}"
        )


@router.get("/health")
async def validator_health_check():
    """验证器健康检查"""
    try:
        # 检查验证引擎状态
        engine_status = "healthy" if validation_engine else "unhealthy"

        return {
            "status": engine_status,
            "service": "validator",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "validator",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/types")
async def get_validation_types():
    """获取支持的验证类型"""
    return {
        "validation_types": [
            {
                "value": "schema",
                "label": "架构验证",
                "description": "验证数据结构和类型"
            },
            {
                "value": "business_rule",
                "label": "业务规则验证",
                "description": "验证业务逻辑规则"
            },
            {
                "value": "data_quality",
                "label": "数据质量验证",
                "description": "验证数据完整性和一致性"
            },
            {
                "value": "performance",
                "label": "性能验证",
                "description": "验证性能指标"
            },
            {
                "value": "security",
                "label": "安全验证",
                "description": "验证安全性要求"
            },
            {
                "value": "custom",
                "label": "自定义验证",
                "description": "自定义验证逻辑"
            }
        ]
    }