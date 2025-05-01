# Generated manually to match database state

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0013_merge_20240512_1520'),
    ]

    operations = [
        migrations.CreateModel(
            name='Webpage',
            fields=[
                ('id', models.UUIDField(primary_key=True)),
                ('url', models.CharField(max_length=200, unique=True)),
                ('title', models.CharField(max_length=100)),
            ],
            options={
                'db_table': 'home_webpage',
            },
        ),
    ] 