from alembic import op
import sqlalchemy as sa
revision='0001_initial'; down_revision=None; branch_labels=None; depends_on=None
def upgrade():
 op.create_table('users',sa.Column('id',sa.String(36),primary_key=True),sa.Column('email',sa.String(320),nullable=False),sa.Column('password_hash',sa.Text(),nullable=False)); op.create_index('ix_users_email','users',['email'],unique=True)
 op.create_table('projects',sa.Column('id',sa.String(36),primary_key=True),sa.Column('user_id',sa.String(36),sa.ForeignKey('users.id'),nullable=False),sa.Column('name',sa.String(200),nullable=False),sa.Column('snapshot',sa.JSON(),nullable=False),sa.Column('version',sa.Integer(),nullable=False),sa.Column('updated_at',sa.DateTime(timezone=True))); op.create_index('ix_projects_user_id','projects',['user_id'])
 op.create_table('approvals',sa.Column('id',sa.String(36),primary_key=True),sa.Column('user_id',sa.String(36),sa.ForeignKey('users.id'),nullable=False),sa.Column('command',sa.Text(),nullable=False),sa.Column('status',sa.String(20),nullable=False),sa.Column('decided_by',sa.String(36)),sa.Column('expires_at',sa.DateTime(timezone=True),nullable=False)); op.create_index('ix_approvals_user_id','approvals',['user_id'])
 op.create_table('refresh_tokens',sa.Column('id',sa.String(36),primary_key=True),sa.Column('user_id',sa.String(36),sa.ForeignKey('users.id'),nullable=False),sa.Column('token_hash',sa.String(64),unique=True,nullable=False),sa.Column('expires_at',sa.DateTime(timezone=True),nullable=False),sa.Column('revoked_at',sa.DateTime(timezone=True))); op.create_index('ix_refresh_tokens_user_id','refresh_tokens',['user_id'])
def downgrade():
 op.drop_table('refresh_tokens'); op.drop_table('approvals'); op.drop_table('projects'); op.drop_table('users')
