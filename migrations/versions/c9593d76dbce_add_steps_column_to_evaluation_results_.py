"""Add steps column to evaluation_results table

Revision ID: c9593d76dbce
Revises: 83bb00cf8918
Create Date: 2021-04-21 10:44:40.676401

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c9593d76dbce'
down_revision = '83bb00cf8918'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('evaluation_results') as batch_op:
        batch_op.add_column(
            sa.Column('steps', sa.Integer(), nullable=True)
        )


def downgrade():
    with op.batch_alter_table('evaluation_results') as batch_op:
        batch_op.drop_column('steps')
