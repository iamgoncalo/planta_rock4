"""sensors intelligence layer"""
from alembic import op
import sqlalchemy as sa

revision = '001_sensors'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # cluster_refs (FK target)
    op.create_table('cluster_refs',
        sa.Column('id', sa.String, primary_key=True),
        sa.Column('name', sa.String),
    )
    op.execute("INSERT INTO cluster_refs (id, name) VALUES "
               "('WC-01','WC-01'),('WC-02','WC-02'),('WC-03','WC-03'),('WC-04','WC-04'),"
               "('WC-05','WC-05 UNISSEX'),('WC-06','WC-06 UNISSEX'),('WC-07','WC-07'),('WC-08','WC-08')")

    # sensors
    op.create_table('sensors',
        sa.Column('id', sa.String, primary_key=True),
        sa.Column('cluster_id', sa.String, sa.ForeignKey('cluster_refs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('type', sa.String, nullable=False),
        sa.Column('model', sa.String, nullable=False),
        sa.Column('protocol', sa.String),
        sa.Column('location_desc', sa.String),
        sa.Column('gps_lat', sa.Float),
        sa.Column('gps_lon', sa.Float),
        sa.Column('height_cm', sa.Integer),
        sa.Column('gpio_pin', sa.Integer),
        sa.Column('has_battery', sa.Boolean, default=False),
        sa.Column('battery_mah', sa.Integer),
        sa.Column('powered_by', sa.String),
        sa.Column('ip_rating', sa.String),
        sa.Column('coverage_radius_m', sa.Integer),
        sa.Column('wifi_factor', sa.Float),
        sa.Column('fusion_weight', sa.Float),
        sa.Column('firmware', sa.String),
        sa.Column('cost_eur', sa.Float),
        sa.Column('notes', sa.Text),
        sa.Column('critical_note', sa.Text),
        sa.Column('installed_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('installed_by', sa.String),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('is_active', sa.Boolean, server_default=sa.text('true')),
    )
    op.create_index('idx_sensors_cluster', 'sensors', ['cluster_id'])
    op.create_index('idx_sensors_type', 'sensors', ['type'])

    # sensor_health
    op.create_table('sensor_health',
        sa.Column('sensor_id', sa.String, sa.ForeignKey('sensors.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('last_seen', sa.TIMESTAMP(timezone=True)),
        sa.Column('last_rssi_dbm', sa.Integer),
        sa.Column('last_uptime_s', sa.Integer),
        sa.Column('battery_pct', sa.Integer),
        sa.Column('firmware_ver', sa.String),
        sa.Column('events_today', sa.Integer, server_default=sa.text('0')),
        sa.Column('status', sa.String, server_default=sa.text("'unknown'")),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    # maintenance_log
    op.create_table('maintenance_log',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('sensor_id', sa.String, sa.ForeignKey('sensors.id', ondelete='CASCADE')),
        sa.Column('action', sa.String, nullable=False),
        sa.Column('result', sa.String),
        sa.Column('notes', sa.Text),
        sa.Column('performed_by', sa.String),
        sa.Column('performed_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_maintenance_sensor', 'maintenance_log', ['sensor_id'])

    # terminal_log
    op.create_table('terminal_log',
        sa.Column('id', sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column('session_id', sa.String),
        sa.Column('command', sa.String, nullable=False),
        sa.Column('output', sa.Text),
        sa.Column('exit_code', sa.Integer),
        sa.Column('executed_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_terminal_session', 'terminal_log', ['session_id'])


def downgrade():
    op.drop_table('terminal_log')
    op.drop_table('maintenance_log')
    op.drop_table('sensor_health')
    op.drop_table('sensors')
    op.drop_table('cluster_refs')
