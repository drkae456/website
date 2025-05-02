from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('chatbot_app', '0007_searchablepost'),
    ]

    operations = [
        migrations.CreateModel(
            name='UnsearchableModel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('count', models.IntegerField()),
            ],
            options={
                'managed': True,
            },
        ),
    ] 