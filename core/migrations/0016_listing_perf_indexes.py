from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0015_listingsuggestion'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='listing',
            index=models.Index(fields=['subtype'], name='core_listing_subtype_idx'),
        ),
        migrations.AddIndex(
            model_name='listing',
            index=models.Index(
                fields=['status', 'last_verified_at'],
                name='core_listing_status_verified_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='listing',
            index=models.Index(
                fields=['status', 'start_date'],
                name='core_listing_status_start_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='listing',
            index=models.Index(
                fields=['status', 'category', 'subtype', 'city_town_ref'],
                name='core_listing_status_cat_sub_city_idx',
            ),
        ),
    ]
