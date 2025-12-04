# Generated manually for demo account feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial_customuser'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='is_demo_account',
            field=models.BooleanField(
                default=False,
                help_text='Указывает, является ли это демонстрационным аккаунтом для быстрого тестирования.',
                verbose_name='Демо-аккаунт'
            ),
        ),
    ]



