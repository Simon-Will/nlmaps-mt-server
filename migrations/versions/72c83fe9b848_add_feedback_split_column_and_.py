"""Add feedback.split column and evaluation_results table

Revision ID: 72c83fe9b848
Revises: 9e340041eda8
Create Date: 2021-03-21 16:00:43.043708

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '72c83fe9b848'
down_revision = '9e340041eda8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('evaluation_results',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('created', sa.DateTime(timezone=True), nullable=False),
    sa.Column('label', sa.Unicode(length=50), nullable=False),
    sa.Column('correct', sa.Integer(), nullable=False),
    sa.Column('total', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('feedback', sa.Column('split', sa.Unicode(length=50), server_default='train', nullable=False))


def downgrade():
    op.drop_column('feedback', 'split')
    op.drop_table('evaluation_results')
