"""add updated_at to tokens

Revision ID: add_updated_at_to_tokens
Revises: a59ce48fbdfe
Create Date: 2024-03-12 08:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime
from sqlalchemy.engine.reflection import Inspector

# revision identifiers, used by Alembic.
revision = 'add_updated_at_to_tokens'
down_revision = 'a59ce48fbdfe'
branch_labels = None
depends_on = None

def upgrade():
    # Get the bind connection
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = [c['name'] for c in inspector.get_columns('tokens')]
    
    # Only add the column if it doesn't exist
    if 'updated_at' not in columns:
        op.add_column('tokens', sa.Column('updated_at', sa.DateTime(), nullable=True))
        
        # Update existing rows to have updated_at same as created_at
        op.execute("""
            UPDATE tokens 
            SET updated_at = created_at 
            WHERE updated_at IS NULL
        """)
        
        # Make updated_at not nullable after setting default values
        op.alter_column('tokens', 'updated_at',
                        existing_type=sa.DateTime(),
                        nullable=False)
    else:
        print("Column 'updated_at' already exists in 'tokens' table")

def downgrade():
    # Check if column exists before trying to drop it
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    columns = [c['name'] for c in inspector.get_columns('tokens')]
    
    if 'updated_at' in columns:
        op.drop_column('tokens', 'updated_at') 