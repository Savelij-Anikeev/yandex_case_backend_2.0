# Generated by Django 4.2.7 on 2023-12-08 16:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('event_app', '0004_alter_event_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='photo_url',
            field=models.CharField(blank=True, default='https://cdn.dribbble.com/users/55871/screenshots/2158022/media/8f2a4a2c9126a9f265fb9e1023b1698a.jpg?resize=400x0', max_length=1024, null=True),
        ),
        migrations.AlterField(
            model_name='event',
            name='photo',
            field=models.ImageField(blank=True, null=True, upload_to=''),
        ),
    ]
