"""persist challenge variant seeds"""

from alembic import op
import sqlalchemy as sa


revision = "0003_variant_seed"
down_revision = "0002_benchmark_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "challenge_instances",
        sa.Column("variant_seed", sa.String(length=128), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_column("challenge_instances", "variant_seed")
