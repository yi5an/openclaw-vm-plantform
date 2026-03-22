"""Initial database schema

Revision ID: 001
Revises: 
Create Date: 2026-03-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('username', sa.String(100), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('balance', sa.Numeric(10, 2), server_default='0.00'),
        sa.Column('role', sa.Enum('USER', 'ADMIN', name='userrole'), server_default='USER'),
        sa.Column('status', sa.Enum('ACTIVE', 'SUSPENDED', 'DELETED', name='userstatus'), server_default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_username', 'users', ['username'])
    op.create_index('idx_users_status', 'users', ['status'])

    # Create plans table
    op.create_table(
        'plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('cpu', sa.Integer, nullable=False),
        sa.Column('memory', sa.Integer, nullable=False),
        sa.Column('disk', sa.Integer, nullable=False),
        sa.Column('max_agents', sa.Integer, nullable=False),
        sa.Column('max_channels', sa.Integer, nullable=False),
        sa.Column('price_per_month', sa.Numeric(10, 2), nullable=False),
        sa.Column('features', postgresql.JSONB, server_default='[]'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('sort_order', sa.Integer, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_plans_active', 'plans', ['is_active', 'sort_order'])

    # Create vms table
    op.create_table(
        'vms',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('plans.id'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('status', sa.Enum('CREATING', 'RUNNING', 'STOPPED', 'ERROR', 'DELETING', name='vmstatus'), server_default='CREATING'),
        sa.Column('libvirt_domain_name', sa.String(255), unique=True),
        sa.Column('ip_address', postgresql.INET),
        sa.Column('mac_address', sa.String(17)),
        sa.Column('cpu', sa.Integer, nullable=False),
        sa.Column('memory', sa.Integer, nullable=False),
        sa.Column('disk', sa.Integer, nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_start_at', sa.DateTime(timezone=True)),
        sa.Column('last_stop_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_vms_user', 'vms', ['user_id'])
    op.create_index('idx_vms_status', 'vms', ['status'])
    op.create_index('idx_vms_expires', 'vms', ['expires_at'])

    # Create agent_templates table
    op.create_table(
        'agent_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('system_prompt', sa.Text, nullable=False),
        sa.Column('default_config', postgresql.JSONB, server_default='{}'),
        sa.Column('features', postgresql.JSONB, server_default='[]'),
        sa.Column('preview_image', sa.String(255)),
        sa.Column('is_popular', sa.Boolean, server_default='false'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_templates_category', 'agent_templates', ['category'])
    op.create_index('idx_templates_active', 'agent_templates', ['is_active', 'is_popular'])

    # Create agents table
    op.create_table(
        'agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('vm_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vms.id', ondelete='CASCADE'), nullable=False),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agent_templates.id')),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('status', sa.Enum('CREATING', 'RUNNING', 'STOPPED', 'ERROR', name='agentstatus'), server_default='CREATING'),
        sa.Column('system_prompt', sa.Text),
        sa.Column('model_config', postgresql.JSONB, nullable=False),
        sa.Column('messages_count', sa.Integer, server_default='0'),
        sa.Column('last_active_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_agents_vm', 'agents', ['vm_id'])
    op.create_index('idx_agents_status', 'agents', ['status'])

    # Create channels table
    op.create_table(
        'channels',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('type', sa.Enum('FEISHU', 'TELEGRAM', 'WHATSAPP', 'WEBCHAT', name='channeltype'), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'CONFIGURING', 'ACTIVE', 'ERROR', name='channelstatus'), server_default='PENDING'),
        sa.Column('config', postgresql.JSONB, nullable=False),
        sa.Column('configuration_steps', postgresql.JSONB, server_default='[]'),
        sa.Column('test_message_sent', sa.Boolean, server_default='false'),
        sa.Column('last_test_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_channels_agent', 'channels', ['agent_id'])
    op.create_index('idx_channels_type', 'channels', ['type'])
    op.create_index('idx_channels_status', 'channels', ['status'])

    # Create token_usage table
    op.create_table(
        'token_usage',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('vm_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vms.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('model', sa.String(100), nullable=False),
        sa.Column('prompt_tokens', sa.Integer, nullable=False),
        sa.Column('completion_tokens', sa.Integer, nullable=False),
        sa.Column('total_tokens', sa.Integer, nullable=False),
        sa.Column('cost', sa.Numeric(10, 6), nullable=False),
        sa.Column('request_id', sa.String(255)),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_token_usage_agent', 'token_usage', ['agent_id', sa.text('created_at DESC')])
    op.create_index('idx_token_usage_vm', 'token_usage', ['vm_id', sa.text('created_at DESC')])
    op.create_index('idx_token_usage_user', 'token_usage', ['user_id', sa.text('created_at DESC')])

    # Create orders table
    op.create_table(
        'orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('vm_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('vms.id')),
        sa.Column('type', sa.Enum('RECHARGE', 'SUBSCRIPTION', 'TOKEN_USAGE', 'DISK_EXPANSION', 'BACKUP', name='ordertype'), nullable=False),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('balance_before', sa.Numeric(10, 2), nullable=False),
        sa.Column('balance_after', sa.Numeric(10, 2), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('status', sa.Enum('PENDING', 'COMPLETED', 'FAILED', 'REFUNDED', name='orderstatus'), server_default='COMPLETED'),
        sa.Column('payment_method', sa.String(20)),
        sa.Column('payment_transaction_id', sa.String(255)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_orders_user', 'orders', ['user_id', sa.text('created_at DESC')])
    op.create_index('idx_orders_vm', 'orders', ['vm_id'])
    op.create_index('idx_orders_type', 'orders', ['type', sa.text('created_at DESC')])

    # Create models table
    op.create_table(
        'models',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('api_endpoint', sa.String(255), nullable=False),
        sa.Column('api_key_encrypted', sa.Text, nullable=False),
        sa.Column('price_per_1k_tokens', sa.Numeric(10, 4), nullable=False),
        sa.Column('max_tokens', sa.Integer),
        sa.Column('default_config', postgresql.JSONB, server_default='{}'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    op.create_index('idx_models_active', 'models', ['is_active'])

    # Create system_configs table
    op.create_table(
        'system_configs',
        sa.Column('key', sa.String(100), primary_key=True),
        sa.Column('value', postgresql.JSONB, nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id')),
    )


def downgrade() -> None:
    op.drop_table('system_configs')
    op.drop_table('models')
    op.drop_table('orders')
    op.drop_table('token_usage')
    op.drop_table('channels')
    op.drop_table('agents')
    op.drop_table('agent_templates')
    op.drop_table('vms')
    op.drop_table('plans')
    op.drop_table('users')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS userrole')
    op.execute('DROP TYPE IF EXISTS userstatus')
    op.execute('DROP TYPE IF EXISTS vmstatus')
    op.execute('DROP TYPE IF EXISTS agentstatus')
    op.execute('DROP TYPE IF EXISTS channeltype')
    op.execute('DROP TYPE IF EXISTS channelstatus')
    op.execute('DROP TYPE IF EXISTS ordertype')
    op.execute('DROP TYPE IF EXISTS orderstatus')
