# Generated by Django 3.2.9 on 2021-11-28 07:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('splitwise', '0006_alter_expense_expense_group'),
    ]

    operations = [
        migrations.AddField(
            model_name='expense',
            name='name',
            field=models.CharField(default='1', max_length=255, unique=True),
            preserve_default=False,
        ),
    ]
