# Generated by Django 3.2 on 2021-07-02 23:14

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('snow', '0001_initial'),
        ('rds', '0001_initial'),
        ('accum', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('kuband', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
                ('rds_season_groups', models.ManyToManyField(to='rds.season_groups')),
                ('rds_layer_groups', models.ManyToManyField(to='rds.layer_groups')),
                ('accum_season_groups', models.ManyToManyField(to='accum.season_groups')),
                ('accum_layer_groups', models.ManyToManyField(to='accum.layer_groups')),
                ('snow_season_groups', models.ManyToManyField(to='snow.season_groups')),
                ('snow_layer_groups', models.ManyToManyField(to='snow.layer_groups')),
                ('kuband_season_groups', models.ManyToManyField(to='kuband.season_groups')),
                ('kuband_layer_groups', models.ManyToManyField(to='kuband.layer_groups')),
                ('layerGroupRelease', models.BooleanField(default=False)),
                ('seasonRelease', models.BooleanField(default=False)),
                ('createData', models.BooleanField(default=False)),
                ('bulkDeleteData', models.BooleanField(default=False)),
                ('isRoot', models.BooleanField(default=False)),
            ],
        ),
    ]
