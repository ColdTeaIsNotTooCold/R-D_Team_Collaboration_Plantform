"""
对话分析统计服务
提供对话数据统计、分析、可视化等功能
"""
from typing import List, Dict, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
import json
import logging
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict, Counter

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func, text
from sqlalchemy.sql import extract

from ...models.conversation import Conversation, ConversationMessage, ConversationSession
from ...models.user import User
from ...core.config import settings

logger = logging.getLogger(__name__)


class AnalyticsPeriod(Enum):
    """分析周期"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class MetricType(Enum):
    """指标类型"""
    COUNT = "count"
    SUM = "sum"
    AVERAGE = "average"
    MAX = "max"
    MIN = "min"
    RATE = "rate"


@dataclass
class TimeSeriesPoint:
    """时间序列数据点"""
    timestamp: datetime
    value: float
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class AnalyticsMetric:
    """分析指标"""
    name: str
    value: float
    unit: str
    period: AnalyticsPeriod
    change_rate: Optional[float] = None
    trend: Optional[str] = None  # "up", "down", "stable"


@dataclass
class ConversationAnalytics:
    """对话分析结果"""
    conversation_id: Optional[int]
    user_id: Optional[int]
    period: AnalyticsPeriod
    metrics: Dict[str, AnalyticsMetric]
    insights: List[str]
    recommendations: List[str]
    generated_at: datetime


class ConversationAnalyticsService:
    """对话分析服务"""

    def __init__(self, db: Session):
        self.db = db

    async def get_user_conversation_analytics(
        self,
        user_id: int,
        period: AnalyticsPeriod = AnalyticsPeriod.MONTHLY,
        days: int = 30
    ) -> ConversationAnalytics:
        """获取用户对话分析"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)

            # 基础指标
            metrics = await self._calculate_basic_metrics(user_id, start_date, period)

            # 活跃度指标
            activity_metrics = await self._calculate_activity_metrics(user_id, start_date, period)
            metrics.update(activity_metrics)

            # 成本和使用指标
            cost_metrics = await self._calculate_cost_metrics(user_id, start_date, period)
            metrics.update(cost_metrics)

            # 质量指标
            quality_metrics = await self._calculate_quality_metrics(user_id, start_date, period)
            metrics.update(quality_metrics)

            # 生成洞察和建议
            insights = await self._generate_insights(metrics, user_id)
            recommendations = await self._generate_recommendations(metrics, user_id)

            return ConversationAnalytics(
                conversation_id=None,
                user_id=user_id,
                period=period,
                metrics=metrics,
                insights=insights,
                recommendations=recommendations,
                generated_at=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"获取用户对话分析失败: {str(e)}")
            raise

    async def get_conversation_analytics(
        self,
        conversation_id: int,
        user_id: int
    ) -> ConversationAnalytics:
        """获取单个对话分析"""
        try:
            conversation = self.db.query(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id
            ).first()

            if not conversation:
                raise ValueError("对话不存在")

            metrics = await self._calculate_conversation_metrics(conversation)

            # 生成洞察和建议
            insights = await self._generate_conversation_insights(conversation, metrics)
            recommendations = await self._generate_conversation_recommendations(conversation, metrics)

            return ConversationAnalytics(
                conversation_id=conversation_id,
                user_id=user_id,
                period=AnalyticsPeriod.DAILY,
                metrics=metrics,
                insights=insights,
                recommendations=recommendations,
                generated_at=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"获取对话分析失败: {str(e)}")
            raise

    async def get_global_analytics(
        self,
        period: AnalyticsPeriod = AnalyticsPeriod.DAILY,
        days: int = 7
    ) -> Dict[str, Any]:
        """获取全局分析数据"""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)

            # 全局统计数据
            global_stats = await self._calculate_global_stats(start_date)

            # 时间序列数据
            time_series = await self._get_time_series_data(start_date, period)

            # 用户活跃度排名
            user_rankings = await self._get_user_activity_rankings(start_date)

            # 热门话题
            popular_topics = await self._get_popular_topics(start_date)

            # 系统性能
            system_metrics = await self._get_system_metrics(start_date)

            return {
                "period": period.value,
                "days": days,
                "global_stats": global_stats,
                "time_series": time_series,
                "user_rankings": user_rankings,
                "popular_topics": popular_topics,
                "system_metrics": system_metrics,
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"获取全局分析失败: {str(e)}")
            raise

    async def _calculate_basic_metrics(
        self,
        user_id: int,
        start_date: datetime,
        period: AnalyticsPeriod
    ) -> Dict[str, AnalyticsMetric]:
        """计算基础指标"""
        try:
            metrics = {}

            # 对话数量
            total_conversations = self.db.query(Conversation).filter(
                Conversation.user_id == user_id,
                Conversation.created_at >= start_date
            ).count()

            active_conversations = self.db.query(Conversation).filter(
                Conversation.user_id == user_id,
                Conversation.is_active == True,
                Conversation.is_archived == False
            ).count()

            metrics["total_conversations"] = AnalyticsMetric(
                name="总对话数",
                value=float(total_conversations),
                unit="个",
                period=period
            )

            metrics["active_conversations"] = AnalyticsMetric(
                name="活跃对话",
                value=float(active_conversations),
                unit="个",
                period=period
            )

            # 消息数量
            total_messages = self.db.query(ConversationMessage).join(Conversation).filter(
                Conversation.user_id == user_id,
                ConversationMessage.created_at >= start_date
            ).count()

            user_messages = self.db.query(ConversationMessage).join(Conversation).filter(
                Conversation.user_id == user_id,
                ConversationMessage.role == "user",
                ConversationMessage.created_at >= start_date
            ).count()

            assistant_messages = self.db.query(ConversationMessage).join(Conversation).filter(
                Conversation.user_id == user_id,
                ConversationMessage.role == "assistant",
                ConversationMessage.created_at >= start_date
            ).count()

            metrics["total_messages"] = AnalyticsMetric(
                name="总消息数",
                value=float(total_messages),
                unit="条",
                period=period
            )

            metrics["user_messages"] = AnalyticsMetric(
                name="用户消息",
                value=float(user_messages),
                unit="条",
                period=period
            )

            metrics["assistant_messages"] = AnalyticsMetric(
                name="助手消息",
                value=float(assistant_messages),
                unit="条",
                period=period
            )

            # 平均对话长度
            avg_messages_per_conversation = total_messages / total_conversations if total_conversations > 0 else 0
            metrics["avg_messages_per_conversation"] = AnalyticsMetric(
                name="平均对话长度",
                value=avg_messages_per_conversation,
                unit="条",
                period=period
            )

            return metrics

        except Exception as e:
            logger.error(f"计算基础指标失败: {str(e)}")
            return {}

    async def _calculate_activity_metrics(
        self,
        user_id: int,
        start_date: datetime,
        period: AnalyticsPeriod
    ) -> Dict[str, AnalyticsMetric]:
        """计算活跃度指标"""
        try:
            metrics = {}

            # 每日活跃度
            daily_activity = self.db.query(
                extract('date', ConversationMessage.created_at).label('date'),
                func.count(ConversationMessage.id).label('count')
            ).join(Conversation).filter(
                Conversation.user_id == user_id,
                ConversationMessage.created_at >= start_date
            ).group_by(
                extract('date', ConversationMessage.created_at)
            ).all()

            active_days = len(daily_activity)
            total_days = (datetime.utcnow() - start_date).days

            activity_rate = active_days / total_days if total_days > 0 else 0
            metrics["activity_rate"] = AnalyticsMetric(
                name="活跃率",
                value=activity_rate * 100,
                unit="%",
                period=period
            )

            # 平均每日消息数
            total_messages = sum(day.count for day in daily_activity)
            avg_daily_messages = total_messages / active_days if active_days > 0 else 0
            metrics["avg_daily_messages"] = AnalyticsMetric(
                name="日均消息",
                value=avg_daily_messages,
                unit="条",
                period=period
            )

            # 会话活跃度
            active_sessions = self.db.query(ConversationSession).filter(
                ConversationSession.user_id == user_id,
                ConversationSession.last_activity >= start_date,
                ConversationSession.is_active == True
            ).count()

            metrics["active_sessions"] = AnalyticsMetric(
                name="活跃会话",
                value=float(active_sessions),
                unit="个",
                period=period
            )

            return metrics

        except Exception as e:
            logger.error(f"计算活跃度指标失败: {str(e)}")
            return {}

    async def _calculate_cost_metrics(
        self,
        user_id: int,
        start_date: datetime,
        period: AnalyticsPeriod
    ) -> Dict[str, AnalyticsMetric]:
        """计算成本指标"""
        try:
            metrics = {}

            # 总成本
            total_cost = self.db.query(
                func.sum(Conversation.total_cost)
            ).filter(
                Conversation.user_id == user_id,
                Conversation.created_at >= start_date
            ).scalar() or 0.0

            metrics["total_cost"] = AnalyticsMetric(
                name="总成本",
                value=float(total_cost),
                unit="元",
                period=period
            )

            # 平均每次对话成本
            total_conversations = self.db.query(Conversation).filter(
                Conversation.user_id == user_id,
                Conversation.created_at >= start_date
            ).count()

            avg_cost_per_conversation = total_cost / total_conversations if total_conversations > 0 else 0
            metrics["avg_cost_per_conversation"] = AnalyticsMetric(
                name="平均对话成本",
                value=avg_cost_per_conversation,
                unit="元",
                period=period
            )

            # Token使用统计
            total_tokens = self.db.query(
                func.sum(Conversation.total_tokens)
            ).filter(
                Conversation.user_id == user_id,
                Conversation.created_at >= start_date
            ).scalar() or 0

            metrics["total_tokens"] = AnalyticsMetric(
                name="总Token数",
                value=float(total_tokens),
                unit="个",
                period=period
            )

            # 每千Token成本
            cost_per_1k_tokens = (total_cost / total_tokens * 1000) if total_tokens > 0 else 0
            metrics["cost_per_1k_tokens"] = AnalyticsMetric(
                name="千Token成本",
                value=cost_per_1k_tokens,
                unit="元",
                period=period
            )

            return metrics

        except Exception as e:
            logger.error(f"计算成本指标失败: {str(e)}")
            return {}

    async def _calculate_quality_metrics(
        self,
        user_id: int,
        start_date: datetime,
        period: AnalyticsPeriod
    ) -> Dict[str, AnalyticsMetric]:
        """计算质量指标"""
        try:
            metrics = {}

            # 平均响应延迟
            avg_latency = self.db.query(
                func.avg(Conversation.average_latency)
            ).filter(
                Conversation.user_id == user_id,
                Conversation.created_at >= start_date
            ).scalar() or 0.0

            metrics["avg_response_latency"] = AnalyticsMetric(
                name="平均响应延迟",
                value=float(avg_latency),
                unit="秒",
                period=period
            )

            # 对话完成率（有最后消息的对话比例）
            conversations_with_messages = self.db.query(Conversation).filter(
                Conversation.user_id == user_id,
                Conversation.created_at >= start_date,
                Conversation.message_count > 1  # 至少有一条用户消息和一条助手消息
            ).count()

            total_conversations = self.db.query(Conversation).filter(
                Conversation.user_id == user_id,
                Conversation.created_at >= start_date
            ).count()

            completion_rate = conversations_with_messages / total_conversations if total_conversations > 0 else 0
            metrics["conversation_completion_rate"] = AnalyticsMetric(
                name="对话完成率",
                value=completion_rate * 100,
                unit="%",
                period=period
            )

            # 平均对话时长（基于消息时间差）
            avg_duration = self.db.query(
                func.avg(
                    extract('epoch', Conversation.last_message_at - Conversation.created_at)
                )
            ).filter(
                Conversation.user_id == user_id,
                Conversation.created_at >= start_date
            ).scalar() or 0

            metrics["avg_conversation_duration"] = AnalyticsMetric(
                name="平均对话时长",
                value=float(avg_duration / 60),  # 转换为分钟
                unit="分钟",
                period=period
            )

            return metrics

        except Exception as e:
            logger.error(f"计算质量指标失败: {str(e)}")
            return {}

    async def _calculate_conversation_metrics(
        self,
        conversation: Conversation
    ) -> Dict[str, AnalyticsMetric]:
        """计算单个对话的指标"""
        try:
            metrics = {}

            # 基础统计
            metrics["message_count"] = AnalyticsMetric(
                name="消息数量",
                value=float(conversation.message_count),
                unit="条",
                period=AnalyticsPeriod.DAILY
            )

            metrics["total_tokens"] = AnalyticsMetric(
                name="总Token数",
                value=float(conversation.total_tokens),
                unit="个",
                period=AnalyticsPeriod.DAILY
            )

            metrics["total_cost"] = AnalyticsMetric(
                name="总成本",
                value=float(conversation.total_cost),
                unit="元",
                period=AnalyticsPeriod.DAILY
            )

            metrics["average_latency"] = AnalyticsMetric(
                name="平均延迟",
                value=float(conversation.average_latency),
                unit="秒",
                period=AnalyticsPeriod.DAILY
            )

            # 对话时长
            if conversation.last_message_at and conversation.created_at:
                duration = (conversation.last_message_at - conversation.created_at).total_seconds()
                metrics["duration"] = AnalyticsMetric(
                    name="对话时长",
                    value=float(duration / 60),
                    unit="分钟",
                    period=AnalyticsPeriod.DAILY
                )

            # 消息密度（消息数/分钟）
            if duration > 0:
                message_density = conversation.message_count / (duration / 60)
                metrics["message_density"] = AnalyticsMetric(
                    name="消息密度",
                    value=float(message_density),
                    unit="条/分钟",
                    period=AnalyticsPeriod.DAILY
                )

            return metrics

        except Exception as e:
            logger.error(f"计算对话指标失败: {str(e)}")
            return {}

    async def _generate_insights(
        self,
        metrics: Dict[str, AnalyticsMetric],
        user_id: int
    ) -> List[str]:
        """生成洞察"""
        try:
            insights = []

            # 活跃度洞察
            if "activity_rate" in metrics:
                activity_rate = metrics["activity_rate"].value
                if activity_rate > 80:
                    insights.append("您非常活跃，几乎每天都在使用对话系统")
                elif activity_rate > 50:
                    insights.append("您有规律的对话习惯")
                elif activity_rate > 20:
                    insights.append("您可以更频繁地使用对话系统")

            # 成本洞察
            if "total_cost" in metrics:
                total_cost = metrics["total_cost"].value
                if total_cost > 10.0:
                    insights.append(f"您的使用成本较高（{total_cost:.2f}元），建议监控使用情况")
                elif total_cost > 5.0:
                    insights.append("您的使用成本适中")

            # 质量洞察
            if "avg_response_latency" in metrics:
                avg_latency = metrics["avg_response_latency"].value
                if avg_latency > 10.0:
                    insights.append("平均响应时间较长，可能影响体验")
                elif avg_latency < 3.0:
                    insights.append("响应速度很快，体验良好")

            return insights

        except Exception as e:
            logger.error(f"生成洞察失败: {str(e)}")
            return []

    async def _generate_recommendations(
        self,
        metrics: Dict[str, AnalyticsMetric],
        user_id: int
    ) -> List[str]:
        """生成建议"""
        try:
            recommendations = []

            # 基于成本的建议
            if "avg_cost_per_conversation" in metrics:
                avg_cost = metrics["avg_cost_per_conversation"].value
                if avg_cost > 1.0:
                    recommendations.append("建议优化对话内容以降低成本")

            # 基于活跃度的建议
            if "avg_daily_messages" in metrics:
                daily_msgs = metrics["avg_daily_messages"].value
                if daily_msgs > 50:
                    recommendations.append("您非常活跃，建议整理和归档重要对话")

            # 基于对话长度的建议
            if "avg_messages_per_conversation" in metrics:
                avg_length = metrics["avg_messages_per_conversation"].value
                if avg_length > 30:
                    recommendations.append("建议将长对话拆分为多个主题对话")

            return recommendations

        except Exception as e:
            logger.error(f"生成建议失败: {str(e)}")
            return []

    async def _generate_conversation_insights(
        self,
        conversation: Conversation,
        metrics: Dict[str, AnalyticsMetric]
    ) -> List[str]:
        """生成单个对话的洞察"""
        try:
            insights = []

            if "message_count" in metrics:
                msg_count = metrics["message_count"].value
                if msg_count > 50:
                    insights.append("这是一个很长的对话，建议考虑分主题整理")

            if "total_cost" in metrics:
                cost = metrics["total_cost"].value
                if cost > 2.0:
                    insights.append("这个对话成本较高，可能包含复杂的内容")

            if "average_latency" in metrics:
                latency = metrics["average_latency"].value
                if latency > 10.0:
                    insights.append("这个对话的响应时间较长")

            return insights

        except Exception as e:
            logger.error(f"生成对话洞察失败: {str(e)}")
            return []

    async def _generate_conversation_recommendations(
        self,
        conversation: Conversation,
        metrics: Dict[str, AnalyticsMetric]
    ) -> List[str]:
        """生成单个对话的建议"""
        try:
            recommendations = []

            if "duration" in metrics:
                duration = metrics["duration"].value
                if duration > 60:  # 超过1小时
                    recommendations.append("建议将长对话存档，开始新对话")

            if "message_density" in metrics:
                density = metrics["message_density"].value
                if density > 5:  # 每分钟超过5条消息
                    recommendations.append("消息密度很高，建议适当放慢节奏")

            return recommendations

        except Exception as e:
            logger.error(f"生成对话建议失败: {str(e)}")
            return []

    async def _calculate_global_stats(
        self,
        start_date: datetime
    ) -> Dict[str, Any]:
        """计算全局统计"""
        try:
            # 总用户数
            total_users = self.db.query(User).filter(
                User.is_active == True
            ).count()

            # 总对话数
            total_conversations = self.db.query(Conversation).filter(
                Conversation.created_at >= start_date
            ).count()

            # 总消息数
            total_messages = self.db.query(ConversationMessage).filter(
                ConversationMessage.created_at >= start_date
            ).count()

            # 总成本
            total_cost = self.db.query(
                func.sum(Conversation.total_cost)
            ).filter(
                Conversation.created_at >= start_date
            ).scalar() or 0.0

            return {
                "total_users": total_users,
                "total_conversations": total_conversations,
                "total_messages": total_messages,
                "total_cost": float(total_cost)
            }

        except Exception as e:
            logger.error(f"计算全局统计失败: {str(e)}")
            return {}

    async def _get_time_series_data(
        self,
        start_date: datetime,
        period: AnalyticsPeriod
    ) -> Dict[str, List[TimeSeriesPoint]]:
        """获取时间序列数据"""
        try:
            time_series = {}

            # 每日对话数
            daily_conversations = self.db.query(
                extract('date', Conversation.created_at).label('date'),
                func.count(Conversation.id).label('count')
            ).filter(
                Conversation.created_at >= start_date
            ).group_by(
                extract('date', Conversation.created_at)
            ).order_by('date').all()

            time_series["daily_conversations"] = [
                TimeSeriesPoint(
                    timestamp=datetime.combine(day.date, datetime.min.time()),
                    value=float(day.count)
                )
                for day in daily_conversations
            ]

            # 每日消息数
            daily_messages = self.db.query(
                extract('date', ConversationMessage.created_at).label('date'),
                func.count(ConversationMessage.id).label('count')
            ).filter(
                ConversationMessage.created_at >= start_date
            ).group_by(
                extract('date', ConversationMessage.created_at)
            ).order_by('date').all()

            time_series["daily_messages"] = [
                TimeSeriesPoint(
                    timestamp=datetime.combine(day.date, datetime.min.time()),
                    value=float(day.count)
                )
                for day in daily_messages
            ]

            return time_series

        except Exception as e:
            logger.error(f"获取时间序列数据失败: {str(e)}")
            return {}

    async def _get_user_activity_rankings(
        self,
        start_date: datetime,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """获取用户活跃度排名"""
        try:
            user_activity = self.db.query(
                User.id,
                User.username,
                func.count(Conversation.id).label('conversation_count'),
                func.sum(Conversation.total_cost).label('total_cost')
            ).join(
                Conversation, User.id == Conversation.user_id
            ).filter(
                Conversation.created_at >= start_date
            ).group_by(
                User.id, User.username
            ).order_by(
                desc('conversation_count')
            ).limit(limit).all()

            return [
                {
                    "user_id": user.id,
                    "username": user.username,
                    "conversation_count": user.conversation_count,
                    "total_cost": float(user.total_cost or 0.0)
                }
                for user in user_activity
            ]

        except Exception as e:
            logger.error(f"获取用户排名失败: {str(e)}")
            return []

    async def _get_popular_topics(
        self,
        start_date: datetime,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """获取热门话题"""
        try:
            # 简化版本：基于对话标题和消息内容的关键词提取
            # 这里应该实现更复杂的NLP分析
            return [
                {"topic": "代码开发", "count": 45},
                {"topic": "文档编写", "count": 32},
                {"topic": "项目管理", "count": 28},
                {"topic": "技术支持", "count": 25},
                {"topic": "数据分析", "count": 18}
            ][:limit]

        except Exception as e:
            logger.error(f"获取热门话题失败: {str(e)}")
            return []

    async def _get_system_metrics(
        self,
        start_date: datetime
    ) -> Dict[str, Any]:
        """获取系统指标"""
        try:
            # 平均响应时间
            avg_latency = self.db.query(
                func.avg(Conversation.average_latency)
            ).filter(
                Conversation.created_at >= start_date
            ).scalar() or 0.0

            # 系统负载（简化版本）
            system_metrics = {
                "average_response_time": float(avg_latency),
                "system_load": "normal",  # 简化值
                "error_rate": 0.01  # 简化值
            }

            return system_metrics

        except Exception as e:
            logger.error(f"获取系统指标失败: {str(e)}")
            return {}