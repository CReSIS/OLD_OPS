# Generated by Django 3.2 on 2022-06-27 19:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accum', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='point_paths',
            name='key_point',
            field=models.BooleanField(default=True),
        ),
    ]
