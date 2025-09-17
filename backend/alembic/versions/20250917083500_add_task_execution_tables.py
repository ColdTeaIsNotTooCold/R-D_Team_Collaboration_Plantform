"""Add task execution tables

Revision ID: 20250917083500
Revises: 20250917153300, 20250917081500
Create Date: 2025-09-17 08:35:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20250917083500'
down_revision = '20250917153300'
branch_labels = None
depends_on = None


def upgrade():
    # Create task_executions table
    op.create_table('task_executions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.Integer(), nullable=False),
        sa.Column('message_id', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='pending', nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('execution_time', sa.Float(), nullable=True),
        sa.Column('output_data', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), server_default='0', nullable=True),
        sa.Column('max_retries', sa.Integer(), server_default='3', nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_task_executions_id'), 'task_executions', ['id'], unique=False)
    op.create_index(op.f('ix_task_executions_task_id'), 'task_executions', ['task_id'], unique=False)
    op.create_index(op.f('ix_task_executions_agent_id'), 'task_executions', ['agent_id'], unique=False)

    # Create execution_logs table
    op.create_table('execution_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('execution_id', sa.Integer(), nullable=False),
        sa.Column('level', sa.String(length=20), server_default='info', nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('context', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['execution_id'], ['task_executions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_execution_logs_id'), 'execution_logs', ['id'], unique=False)
    op.create_index(op.f('ix_execution_logs_execution_id'), 'execution_logs', ['execution_id'], unique=False)

    # Create execution_metrics table
    op.create_table('execution_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.Integer(), nullable=False),
        sa.Column('total_executions', sa.Integer(), server_default='0', nullable=True),
        sa.Column('successful_executions', sa.Integer(), server_default='0', nullable=True),
        sa.Column('failed_executions', sa.Integer(), server_default='0', nullable=True),
        sa.Column('timeout_executions', sa.Integer(), server_default='0', nullable=True),
        sa.Column('cancelled_executions', sa.Integer(), server_default='0', nullable=True),
        sa.Column('average_execution_time', sa.Float(), server_default='0.0', nullable=True),
        sa.Column('max_execution_time', sa.Float(), server_default='0.0', nullable=True),
        sa.Column('min_execution_time', sa.Float(), server_default='0.0', nullable=True),
        sa.Column('error_rate', sa.Float(), server_default='0.0', nullable=True),
        sa.Column('metric_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('metric_hour', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_execution_metrics_id'), 'execution_metrics', ['id'], unique=False)
    op.create_index(op.f('ix_execution_metrics_agent_id'), 'execution_metrics', ['agent_id'], unique=False)
    op.create_index(op.f('ix_execution_metrics_metric_date'), 'execution_metrics', ['metric_date'], unique=False)

    # Create agent_workloads table
    op.create_table('agent_workloads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.Integer(), nullable=False),
        sa.Column('current_tasks', sa.Integer(), server_default='0', nullable=True),
        sa.Column('max_concurrent_tasks', sa.Integer(), server_default='5', nullable=True),
        sa.Column('avg_task_completion_time', sa.Float(), server_default='0.0', nullable=True),
        sa.Column('tasks_per_hour', sa.Float(), server_default='0.0', nullable=True),
        sa.Column('is_overloaded', sa.String(length=10), server_default='false', nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_workloads_id'), 'agent_workloads', ['id'], unique=False)
    op.create_index(op.f('ix_agent_workloads_agent_id'), 'agent_workloads', ['agent_id'], unique=False)

    # Create execution_queues table
    op.create_table('execution_queues',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('execution_id', sa.Integer(), nullable=False),
        sa.Column('queue_status', sa.String(length=50), server_default='pending', nullable=True),
        sa.Column('priority', sa.String(length=20), server_default='medium', nullable=True),
        sa.Column('queue_position', sa.Integer(), nullable=True),
        sa.Column('estimated_start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('estimated_completion_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actual_start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actual_completion_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('wait_time', sa.Float(), server_default='0.0', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['execution_id'], ['task_executions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_execution_queues_id'), 'execution_queues', ['id'], unique=False)
    op.create_index(op.f('ix_execution_queues_execution_id'), 'execution_queues', ['execution_id'], unique=False)


def downgrade():
    # Drop execution_queues table
    op.drop_index(op.f('ix_execution_queues_execution_id'), table_name='execution_queues')
    op.drop_index(op.f('ix_execution_queues_id'), table_name='execution_queues')
    op.drop_table('execution_queues')

    # Drop agent_workloads table
    op.drop_index(op.f('ix_agent_workloads_agent_id'), table_name='agent_workloads')
    op.drop_index(op.f('ix_agent_workloads_id'), table_name='agent_workloads')
    op.drop_table('agent_workloads')

    # Drop execution_metrics table
    op.drop_index(op.f('ix_execution_metrics_metric_date'), table_name='execution_metrics')
    op.drop_index(op.f('ix_execution_metrics_agent_id'), table_name='execution_metrics')
    op.drop_index(op.f('ix_execution_metrics_id'), table_name='execution_metrics')
    op.drop_table('execution_metrics')

    # Drop execution_logs table
    op.drop_index(op.f('ix_execution_logs_execution_id'), table_name='execution_logs')
    op.drop_index(op.f('ix_execution_logs_id'), table_name='execution_logs')
    op.drop_table('execution_logs')

    # Drop task_executions table
    op.drop_index(op.f('ix_task_executions_agent_id'), table_name='task_executions')
    op.drop_index(op.f('ix_task_executions_task_id'), table_name='task_executions')
    op.drop_index(op.f('ix_task_executions_id'), table_name='task_executions')
    op.drop_table('task_executions')