"""Create personal organizations for users without organization memberships.

Revision ID: 003_personal_organizations
Revises: 002_project_operations
"""

from alembic import op
import sqlalchemy as sa

revision = "003_personal_organizations"
down_revision = "002_project_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("""
            INSERT INTO organizations (name, slug, created_by, created_at, updated_at)
            SELECT
                'Personal workspace',
                'personal-user-' || users.id::text,
                users.id,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            FROM users
            WHERE NOT EXISTS (
                SELECT 1
                FROM organization_members
                WHERE organization_members.user_id = users.id
            )
            ON CONFLICT (slug) DO NOTHING
            """))

    op.execute(sa.text("""
            INSERT INTO organization_members (
                organization_id,
                user_id,
                role,
                joined_at
            )
            SELECT
                organizations.id,
                organizations.created_by,
                'owner',
                CURRENT_TIMESTAMP
            FROM organizations
            WHERE organizations.slug = 'personal-user-' || organizations.created_by::text
            ON CONFLICT (organization_id, user_id) DO UPDATE
            SET role = 'owner'
            """))


def downgrade() -> None:
    raise RuntimeError(
        "Downgrade is intentionally disabled: removing personal workspaces "
        "could delete or detach user project data."
    )
