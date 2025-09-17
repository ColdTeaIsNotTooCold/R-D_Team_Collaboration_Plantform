import pytest
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.validator import ValidationEngine
from app.schemas.validator import (
    ValidationRequest, ValidationResponse, ValidationRule, ValidationResult,
    ValidationType, ValidationSeverity, ValidationCheck, ValidationReport,
    QualityMetrics, ValidationStats, TaskResultValidation
)
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
def validation_engine(db_session):
    """创建验证引擎实例"""
    return ValidationEngine(db_session)


@pytest.fixture
def sample_validation_rules():
    """创建测试验证规则"""
    return [
        ValidationRule(
            id=1,
            name="必填字段检查",
            description="检查必填字段是否存在",
            type=ValidationType.SCHEMA,
            severity=ValidationSeverity.HIGH,
            condition='{"required": ["title", "task_type"], "types": {"title": "str", "task_type": "str"}}',
            error_message="缺少必填字段",
            is_active=True
        ),
        ValidationRule(
            id=2,
            name="响应时间检查",
            description="检查响应时间是否超限",
            type=ValidationType.PERFORMANCE,
            severity=ValidationSeverity.MEDIUM,
            condition="response_time:5000",
            error_message="响应时间超限",
            is_active=True
        ),
        ValidationRule(
            id=3,
            name="业务规则检查",
            description="检查业务规则",
            type=ValidationType.BUSINESS_RULE,
            severity=ValidationSeverity.MEDIUM,
            condition="eq:status=completed",
            error_message="业务规则验证失败",
            is_active=True
        )
    ]


@pytest.fixture
def sample_validation_request():
    """创建测试验证请求"""
    return ValidationRequest(
        task_id=1,
        execution_id=1,
        validation_type=ValidationType.BUSINESS_RULE,
        data={
            "title": "测试任务",
            "task_type": "code_review",
            "status": "completed",
            "response_time": 3000,
            "output": {"result": "success", "files_reviewed": 5}
        },
        context={"user_id": 1, "project_id": 1}
    )


class TestValidationEngine:
    """验证引擎测试类"""

    @pytest.mark.asyncio
    async def test_validate_task_result_success(self, validation_engine, sample_validation_request):
        """测试成功验证任务结果"""
        with patch.object(validation_engine, '_get_validation_rules') as mock_get_rules:
            # 模拟返回验证规则
            mock_rules = [
                ValidationRule(
                    id=1,
                    name="测试规则",
                    description="测试规则描述",
                    type=ValidationType.BUSINESS_RULE,
                    severity=ValidationSeverity.MEDIUM,
                    condition="eq:status=completed",
                    error_message="状态验证失败",
                    is_active=True
                )
            ]
            mock_get_rules.return_value = mock_rules

            with patch.object(validation_engine, '_store_validation_results') as mock_store:
                # 执行验证
                result = await validation_engine.validate_task_result(sample_validation_request)

                # 验证结果
                assert isinstance(result, ValidationResponse)
                assert result.task_id == 1
                assert result.execution_id == 1
                assert len(result.checks) == 1
                assert result.result == ValidationResult.PASSED
                assert "验证完成" in result.message

                # 验证存储方法被调用
                mock_store.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_task_result_failure(self, validation_engine, sample_validation_request):
        """测试验证失败的情况"""
        with patch.object(validation_engine, '_get_validation_rules') as mock_get_rules:
            # 模拟返回会导致失败的验证规则
            mock_rules = [
                ValidationRule(
                    id=1,
                    name="测试规则",
                    description="测试规则描述",
                    type=ValidationType.BUSINESS_RULE,
                    severity=ValidationSeverity.MEDIUM,
                    condition="eq:status=failed",
                    error_message="状态应该为failed",
                    is_active=True
                )
            ]
            mock_get_rules.return_value = mock_rules

            with patch.object(validation_engine, '_store_validation_results') as mock_store:
                # 执行验证
                result = await validation_engine.validate_task_result(sample_validation_request)

                # 验证结果
                assert isinstance(result, ValidationResponse)
                assert result.result == ValidationResult.FAILED
                assert len(result.checks) == 1
                assert result.checks[0].result == ValidationResult.FAILED

    @pytest.mark.asyncio
    async def test_validate_task_result_exception(self, validation_engine, sample_validation_request):
        """测试验证过程中发生异常"""
        with patch.object(validation_engine, '_get_validation_rules') as mock_get_rules:
            # 模拟异常
            mock_get_rules.side_effect = Exception("数据库连接失败")

            # 执行验证
            result = await validation_engine.validate_task_result(sample_validation_request)

            # 验证结果
            assert isinstance(result, ValidationResponse)
            assert result.result == ValidationResult.FAILED
            assert "验证过程中发生错误" in result.message

    @pytest.mark.asyncio
    async def test_validate_schema_validation(self, validation_engine):
        """测试架构验证"""
        rule = ValidationRule(
            id=1,
            name="架构验证",
            description="验证数据架构",
            type=ValidationType.SCHEMA,
            severity=ValidationSeverity.HIGH,
            condition='{"required": ["title", "task_type"], "types": {"title": "str", "task_type": "str"}}',
            error_message="架构验证失败",
            is_active=True
        )

        # 测试有效数据
        valid_data = {"title": "测试任务", "task_type": "code_review", "description": "测试描述"}
        result, actual_value, message = await validation_engine._validate_schema(rule.condition, valid_data)
        assert result == ValidationResult.PASSED
        assert actual_value == 0

        # 测试缺少必填字段
        invalid_data = {"title": "测试任务"}  # 缺少 task_type
        result, actual_value, message = await validation_engine._validate_schema(rule.condition, invalid_data)
        assert result == ValidationResult.FAILED
        assert "缺少必填字段" in message

    @pytest.mark.asyncio
    async def test_validate_business_rule(self, validation_engine):
        """测试业务规则验证"""
        # 测试等于规则
        rule_eq = ValidationRule(
            id=1,
            name="等于规则",
            description="测试等于规则",
            type=ValidationType.BUSINESS_RULE,
            severity=ValidationSeverity.MEDIUM,
            condition="eq:status=completed",
            error_message="状态不等于completed",
            is_active=True
        )

        data = {"status": "completed"}
        result, actual_value, message = await validation_engine._validate_business_rule(rule_eq.condition, data, {})
        assert result == ValidationResult.PASSED
        assert actual_value == "completed"

        data = {"status": "pending"}
        result, actual_value, message = await validation_engine._validate_business_rule(rule_eq.condition, data, {})
        assert result == ValidationResult.FAILED

        # 测试大于规则
        rule_gt = ValidationRule(
            id=2,
            name="大于规则",
            description="测试大于规则",
            type=ValidationType.BUSINESS_RULE,
            severity=ValidationSeverity.MEDIUM,
            condition="gt:score=80",
            error_message="分数不大于80",
            is_active=True
        )

        data = {"score": 90}
        result, actual_value, message = await validation_engine._validate_business_rule(rule_gt.condition, data, {})
        assert result == ValidationResult.PASSED

        data = {"score": 70}
        result, actual_value, message = await validation_engine._validate_business_rule(rule_gt.condition, data, {})
        assert result == ValidationResult.FAILED

    @pytest.mark.asyncio
    async def test_validate_data_quality(self, validation_engine):
        """测试数据质量验证"""
        # 测试完整度检查
        rule_completeness = ValidationRule(
            id=1,
            name="完整度检查",
            description="测试数据完整度",
            type=ValidationType.DATA_QUALITY,
            severity=ValidationSeverity.MEDIUM,
            condition="completeness",
            error_message="数据完整度不足",
            is_active=True
        )

        # 高完整度数据
        high_quality_data = {"field1": "value1", "field2": "value2", "field3": "value3"}
        result, actual_value, message = await validation_engine._validate_data_quality(rule_completeness.condition, high_quality_data)
        assert result == ValidationResult.PASSED
        assert actual_value >= 0.9

        # 低完整度数据
        low_quality_data = {"field1": "value1", "field2": None, "field3": None}
        result, actual_value, message = await validation_engine._validate_data_quality(rule_completeness.condition, low_quality_data)
        assert result == ValidationResult.FAILED

    @pytest.mark.asyncio
    async def test_validate_performance(self, validation_engine):
        """测试性能验证"""
        rule = ValidationRule(
            id=1,
            name="响应时间检查",
            description="检查响应时间",
            type=ValidationType.PERFORMANCE,
            severity=ValidationSeverity.HIGH,
            condition="response_time:5000",
            error_message="响应时间超限",
            is_active=True
        )

        # 正常响应时间
        good_data = {"response_time": 3000}
        result, actual_value, message = await validation_engine._validate_performance(rule.condition, good_data)
        assert result == ValidationResult.PASSED
        assert actual_value == 3000

        # 超时响应时间
        bad_data = {"response_time": 8000}
        result, actual_value, message = await validation_engine._validate_performance(rule.condition, bad_data)
        assert result == ValidationResult.FAILED
        assert actual_value == 8000

    @pytest.mark.asyncio
    async def test_validate_security(self, validation_engine):
        """测试安全验证"""
        rule = ValidationRule(
            id=1,
            name="安全检查",
            description="检查敏感数据",
            type=ValidationType.SECURITY,
            severity=ValidationSeverity.CRITICAL,
            condition="no_sensitive_data",
            error_message="发现敏感数据",
            is_active=True
        )

        # 安全数据
        safe_data = {"user_id": 123, "content": "这是一段普通文本"}
        result, actual_value, message = await validation_engine._validate_security(rule.condition, safe_data)
        assert result == ValidationResult.PASSED

        # 包含敏感数据
        sensitive_data = {"credit_card": "4111-1111-1111-1111", "user_id": 123}
        result, actual_value, message = await validation_engine._validate_security(rule.condition, sensitive_data)
        assert result == ValidationResult.FAILED

    def test_calculate_overall_result(self, validation_engine):
        """测试计算总体验证结果"""
        # 测试全部通过
        checks = [
            ValidationCheck(id=1, rule_id=1, check_name="检查1", result=ValidationResult.PASSED, created_at=datetime.now()),
            ValidationCheck(id=2, rule_id=2, check_name="检查2", result=ValidationResult.PASSED, created_at=datetime.now())
        ]
        result = validation_engine._calculate_overall_result(checks)
        assert result == ValidationResult.PASSED

        # 测试包含失败
        checks = [
            ValidationCheck(id=1, rule_id=1, check_name="检查1", result=ValidationResult.PASSED, created_at=datetime.now()),
            ValidationCheck(id=2, rule_id=2, check_name="检查2", result=ValidationResult.FAILED, created_at=datetime.now())
        ]
        result = validation_engine._calculate_overall_result(checks)
        assert result == ValidationResult.FAILED

        # 测试包含警告
        checks = [
            ValidationCheck(id=1, rule_id=1, check_name="检查1", result=ValidationResult.PASSED, created_at=datetime.now()),
            ValidationCheck(id=2, rule_id=2, check_name="检查2", result=ValidationResult.WARNING, created_at=datetime.now())
        ]
        result = validation_engine._calculate_overall_result(checks)
        assert result == ValidationResult.WARNING

        # 测试空列表
        result = validation_engine._calculate_overall_result([])
        assert result == ValidationResult.SKIPPED

    @pytest.mark.asyncio
    async def test_get_validation_stats(self, validation_engine):
        """测试获取验证统计"""
        stats = await validation_engine.get_validation_stats(task_id=1)
        assert isinstance(stats, ValidationStats)
        assert stats.total_validations == 0
        assert stats.success_rate == 0.0

    @pytest.mark.asyncio
    async def test_calculate_quality_metrics(self, validation_engine):
        """测试计算质量指标"""
        metrics = await validation_engine.calculate_quality_metrics(task_id=1)
        assert isinstance(metrics, QualityMetrics)
        assert metrics.accuracy is not None
        assert metrics.overall_score is not None
        assert metrics.calculated_at is not None


class TestValidationSchemas:
    """验证器数据模型测试类"""

    def test_validation_rule_creation(self):
        """测试验证规则创建"""
        rule = ValidationRule(
            id=1,
            name="测试规则",
            description="测试规则描述",
            type=ValidationType.SCHEMA,
            severity=ValidationSeverity.MEDIUM,
            condition='{"required": ["field1"]}',
            error_message="验证失败",
            is_active=True
        )
        assert rule.id == 1
        assert rule.name == "测试规则"
        assert rule.type == ValidationType.SCHEMA
        assert rule.severity == ValidationSeverity.MEDIUM

    def test_validation_request_creation(self):
        """测试验证请求创建"""
        request = ValidationRequest(
            task_id=1,
            execution_id=1,
            validation_type=ValidationType.BUSINESS_RULE,
            data={"field1": "value1"},
            context={"user_id": 1}
        )
        assert request.task_id == 1
        assert request.validation_type == ValidationType.BUSINESS_RULE
        assert request.data["field1"] == "value1"

    def test_validation_response_creation(self):
        """测试验证响应创建"""
        response = ValidationResponse(
            validation_id="val_123",
            task_id=1,
            execution_id=1,
            result=ValidationResult.PASSED,
            checks=[],
            created_at=datetime.now()
        )
        assert response.validation_id == "val_123"
        assert response.result == ValidationResult.PASSED
        assert response.checks == []

    def test_quality_metrics_creation(self):
        """测试质量指标创建"""
        metrics = QualityMetrics(
            accuracy=0.95,
            completeness=0.90,
            consistency=0.88,
            timeliness=0.92,
            validity=0.94,
            uniqueness=0.96,
            overall_score=0.92,
            calculated_at=datetime.now()
        )
        assert metrics.accuracy == 0.95
        assert metrics.overall_score == 0.92
        assert metrics.calculated_at is not None

    def test_task_result_validation_creation(self):
        """测试任务结果验证创建"""
        validation = TaskResultValidation(
            task_id=1,
            execution_id=1,
            input_data={"input": "test"},
            output_data={"output": "result"},
            validation_result=ValidationResult.PASSED,
            quality_score=0.95,
            issues=[],
            recommendations=["建议"],
            validated_at=datetime.now()
        )
        assert validation.task_id == 1
        assert validation.validation_result == ValidationResult.PASSED
        assert validation.quality_score == 0.95


@pytest.mark.asyncio
async def test_validation_engine_integration():
    """验证引擎集成测试"""
    engine = ValidationEngine()

    # 创建测试请求
    request = ValidationRequest(
        task_id=1,
        execution_id=1,
        validation_type=ValidationType.BUSINESS_RULE,
        data={"status": "completed", "score": 85},
        context={"test": True}
    )

    # 模拟规则加载（没有数据库）
    with patch.object(engine, '_get_validation_rules') as mock_get_rules:
        mock_get_rules.return_value = []

        # 执行验证
        result = await engine.validate_task_result(request)

        # 验证基本结构
        assert isinstance(result, ValidationResponse)
        assert result.validation_id is not None
        assert result.task_id == 1
        assert result.execution_id == 1
        assert result.result == ValidationResult.SKIPPED  # 没有规则时跳过


if __name__ == "__main__":
    pytest.main([__file__, "-v"])