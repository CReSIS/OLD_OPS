# Generated by Django 3.2 on 2021-11-17 23:03

from django.conf import settings
import django.contrib.gis.db.models.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='locations',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=20)),
            ],
        ),
        migrations.CreateModel(
            name='season_groups',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('description', models.CharField(blank=True, max_length=200)),
                ('public', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='layer_groups',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('description', models.CharField(blank=True, max_length=200)),
                ('public', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='radars',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=20)),
            ],
        ),
        migrations.CreateModel(
            name='seasons',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('location', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rds.locations')),
                ('season_group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rds.season_groups')),
                ('name', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='layers',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('layer_group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rds.layer_groups')),
                ('name', models.CharField(max_length=20)),
                ('description', models.CharField(blank=True, max_length=200)),
                ('deleted', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='layer_links',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('layer_1', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='layer_link_fk_1', to='rds.layers')),
                ('layer_2', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='layer_link_fk_2', to='rds.layers')),
            ],
        ),
        migrations.CreateModel(
            name='segments',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('season', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rds.seasons')),
                ('radar', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rds.radars')),
                ('name', models.CharField(max_length=20)),
                ('geom', django.contrib.gis.db.models.fields.LineStringField(srid=4326)),
                ('crossover_calc', models.BooleanField(default=True)),
            ],
        ),
        migrations.CreateModel(
            name='frames',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('segment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rds.segments')),
                ('name', models.CharField(max_length=20)),
            ],
        ),
        migrations.CreateModel(
            name='point_paths',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('location', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rds.locations')),
                ('season', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rds.seasons')),
                ('segment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rds.segments')),
                ('frame', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rds.frames')),
                ('gps_time', models.DecimalField(db_index=True, decimal_places=6, max_digits=16)),
                ('roll', models.DecimalField(decimal_places=5, max_digits=6)),
                ('pitch', models.DecimalField(decimal_places=5, max_digits=6)),
                ('heading', models.DecimalField(decimal_places=5, max_digits=6)),
                ('geom', django.contrib.gis.db.models.fields.PointField(dim=3, srid=4326)),
            ],
        ),
        migrations.CreateModel(
            name='crossovers',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('point_path_1', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='point_paths_link_fk_1', to='rds.point_paths')),
                ('point_path_2', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='point_paths_link_fk_2', to='rds.point_paths')),
                ('angle', models.DecimalField(decimal_places=3, max_digits=6)),
                ('geom', django.contrib.gis.db.models.fields.PointField(srid=4326)),
            ],
        ),
        migrations.CreateModel(
            name='landmarks',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('radar', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rds.radars')),
                ('segment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rds.segments')),
                ('point_path_1', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='point_paths_link_fk2_1', to='rds.point_paths')),
                ('point_path_2', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='point_paths_link_fk2_2', to='rds.point_paths')),
                ('start_twtt', models.DecimalField(db_index=True, decimal_places=11, max_digits=12)),
                ('stop_twtt', models.DecimalField(db_index=True, decimal_places=11, max_digits=12)),
                ('description', models.CharField(blank=True, max_length=200, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='layer_points',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('layer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rds.layers')),
                ('point_path', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='rds.point_paths')),
                ('twtt', models.DecimalField(blank=True, decimal_places=11, max_digits=12, null=True)),
                ('type', models.IntegerField(blank=True, null=True)),
                ('quality', models.IntegerField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rds_user_id_fk', to=settings.AUTH_USER_MODEL)),
                ('last_updated', models.DateTimeField(auto_now=True)),
            ],
            options={
                'unique_together': {('layer', 'point_path')},
            },
        ),
    ]
