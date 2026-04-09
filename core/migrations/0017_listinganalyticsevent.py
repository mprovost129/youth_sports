from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0016_listing_perf_indexes'),
    ]

    operations = [
        migrations.CreateModel(
            name='ListingAnalyticsEvent',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'event_type',
                    models.CharField(
                        choices=[
                            ('search', 'Search'),
                            ('empty_search', 'Empty search'),
                            ('outbound_click', 'Outbound click'),
                        ],
                        max_length=30,
                    ),
                ),
                ('section', models.CharField(blank=True, max_length=30)),
                ('query', models.CharField(blank=True, max_length=255)),
                ('subtype', models.CharField(blank=True, max_length=120)),
                ('city_town', models.CharField(blank=True, max_length=120)),
                ('result_count', models.PositiveIntegerField(default=0)),
                ('target_url', models.URLField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                (
                    'listing',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=models.SET_NULL,
                        related_name='analytics_events',
                        to='core.listing',
                    ),
                ),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='listinganalyticsevent',
            index=models.Index(
                fields=['event_type', 'created_at'],
                name='core_listin_event_t_11f5d6_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='listinganalyticsevent',
            index=models.Index(fields=['query'], name='core_listin_query_435b11_idx'),
        ),
        migrations.AddIndex(
            model_name='listinganalyticsevent',
            index=models.Index(fields=['section'], name='core_listin_section_2c7fe3_idx'),
        ),
    ]
