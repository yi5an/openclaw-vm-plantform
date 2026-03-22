"""rename metadata to extra_data

Revision ID: d0cf37795dce
Revises: 001
Create Date: 2026-03-22 23:30:43.962378

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd0cf37795dce'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rename metadata column to extra_data in token_usage table
    op.alter_column('token_usage', 'metadata', new_column_name='extra_data')
    
    # Rename metadata column to extra_data in orders table
    op.alter_column('orders', 'metadata', new_column_name='extra_data')


def downgrade() -> None:
    # Revert token_usage
    op.alter_column('token_usage', 'extra_data', new_column_name='metadata')
    
    # Revert orders
    op.alter_column('orders', 'extra_data', new_column_name='metadata')
