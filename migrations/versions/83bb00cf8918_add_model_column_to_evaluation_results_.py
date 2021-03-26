"""Add model column to evaluation_results table

Revision ID: 83bb00cf8918
Revises: 72c83fe9b848
Create Date: 2021-03-26 23:03:22.923916

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '83bb00cf8918'
down_revision = '72c83fe9b848'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('evaluation_results') as batch_op:
        batch_op.add_column(
            sa.Column('model', sa.Unicode(length=500), nullable=False)
        )


def downgrade():
    with op.batch_alter_table('evaluation_results') as batch_op:
        batch_op.drop_column('model')
