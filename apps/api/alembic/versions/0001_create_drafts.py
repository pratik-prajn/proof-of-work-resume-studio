"""Encrypted optional workspace history."""
from alembic import op
import sqlalchemy as sa
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('drafts', sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('owner', sa.String(128), nullable=False), sa.Column('payload', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False), sa.Column('expires_at', sa.DateTime(), nullable=False))
    op.create_index('ix_drafts_owner', 'drafts', ['owner'])
    op.create_index('ix_drafts_expires_at', 'drafts', ['expires_at'])

def downgrade():
    op.drop_index('ix_drafts_expires_at', 'drafts')
    op.drop_index('ix_drafts_owner', 'drafts')
    op.drop_table('drafts')
