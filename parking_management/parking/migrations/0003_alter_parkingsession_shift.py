# Generated by Django 5.2 on 2025-04-16 08:44

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parking', '0002_captureticket_parkingsession_checked_out_by_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='parkingsession',
            name='shift',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='parking_sessions', to='parking.shift'),
        ),
    ]
