"""network ACL

Revision ID: f4a1f5d7ec43
Revises: 6a8c19565060
Create Date: 2016-04-26 13:34:54.910541

"""

revision = 'f4a1f5d7ec43'
down_revision = '6a8c19565060'
branch_labels = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('network_projects',
    sa.Column('project_id', sa.Integer(), nullable=True),
    sa.Column('network_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['network_id'], ['network.id'], ),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], )
    )
    network_projects = sa.sql.table('network_projects',
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('network_id', sa.Integer(), nullable=True),
    )
    conn = op.get_bind()
    res = conn.execute("select id, access_id from network where access_id >= 1")
    results = res.fetchall()
    networks = [{'network_id': r[0], 'project_id': r[1]} for r in results]
    op.bulk_insert(network_projects, networks)
    op.alter_column(u'network', 'creator_id', new_column_name='owner_id')
    op.drop_constraint(u'network_access_id_fkey', 'network', type_='foreignkey')
    op.drop_column(u'network', 'access_id')


def downgrade():
    op.add_column(u'network', sa.Column('access_id', sa.INTEGER(), autoincrement=False, nullable=True))
    op.alter_column(u'network', 'owner_id', new_column_name='creator_id')
    op.create_foreign_key(u'network_access_id_fkey', 'network', 'project', ['access_id'], ['id'])
    op.drop_constraint(u'network_projects_project_id_fkey', 'network_projects', type_='foreignkey')
    op.drop_constraint(u'network_projects_network_id_fkey', 'network_projects', type_='foreignkey')
    op.drop_table('network_projects')
