# Generated by Django 2.2.19 on 2022-04-15 06:06

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('posts', '0002_auto_20220414_1539'),
    ]

    operations = [
        migrations.RenameField(
            model_name='group',
            old_name='slug_adress',
            new_name='slug',
        ),
    ]
