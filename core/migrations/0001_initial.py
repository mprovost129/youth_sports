# Initial migration for core.Listing (created on 2026-04-06)

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Listing',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('category', models.CharField(choices=[('sport', 'Sport'), ('activity', 'Activity')], max_length=20)),
                ('subtype', models.CharField(max_length=100)),
                ('organization_name', models.CharField(max_length=255)),
                ('city_town', models.CharField(max_length=120)),
                ('location_name', models.CharField(max_length=255)),
                ('address', models.CharField(blank=True, max_length=255)),
                ('age_min', models.PositiveSmallIntegerField()),
                ('age_max', models.PositiveSmallIntegerField()),
                ('gender', models.CharField(choices=[('boys', 'Boys'), ('girls', 'Girls'), ('coed', 'Co-ed'), ('not_specified', 'Not specified')], default='not_specified', max_length=20)),
                ('season_or_dates', models.CharField(max_length=255)),
                ('registration_url', models.URLField()),
                ('cost', models.CharField(blank=True, max_length=100)),
                ('description', models.TextField()),
                ('last_verified_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('status', models.CharField(choices=[('active', 'Active'), ('inactive', 'Inactive'), ('archived', 'Archived')], default='active', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['title'],
                'indexes': [
                    models.Index(fields=['category'], name='core_listin_categor_c80164_idx'),
                    models.Index(fields=['city_town'], name='core_listin_city_to_17f18b_idx'),
                    models.Index(fields=['gender'], name='core_listin_gender_e2f83d_idx'),
                    models.Index(fields=['status'], name='core_listin_status_7d1160_idx'),
                    models.Index(fields=['last_verified_at'], name='core_listin_last_ve_f1f9af_idx'),
                ],
                'constraints': [
                    models.CheckConstraint(condition=models.Q(age_max__gte=models.F('age_min')), name='listing_age_max_gte_age_min'),
                ],
            },
        ),
    ]
