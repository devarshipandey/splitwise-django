# Generated by Django 3.2.9 on 2021-11-28 06:55

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('splitwise', '0004_auto_20211128_0641'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Balance',
        ),
        migrations.RenameField(
            model_name='expense',
            old_name='group',
            new_name='expense_group',
        ),
    ]
