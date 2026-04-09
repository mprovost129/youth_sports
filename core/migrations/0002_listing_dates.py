# Add start/end date fields for date-driven upcoming views (created on 2026-04-06)

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='listing',
            name='end_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='listing',
            name='start_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name='listing',
            index=models.Index(fields=['start_date'], name='core_listin_start_d_00df4d_idx'),
        ),
        migrations.AddConstraint(
            model_name='listing',
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(start_date__isnull=True)
                    | models.Q(end_date__isnull=True)
                    | models.Q(end_date__gte=models.F('start_date'))
                ),
                name='listing_end_date_gte_start_date',
            ),
        ),
    ]
