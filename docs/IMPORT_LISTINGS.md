## Import Listings From CSV

Use the management command below to bulk import sports and activity listings.

```bash
python manage.py import_listings docs/listings_import_template.csv
```

### Options
- `--dry-run`: parse and validate rows without writing to the database
- `--update-existing`: update matches based on `title + organization_name + city_town`

Example:

```bash
python manage.py import_listings path/to/listings.csv --dry-run
python manage.py import_listings path/to/listings.csv --update-existing
```

### Required Columns
- `title`
- `category` (`sport` or `activity`)
- `subtype`
- `organization_name`
- `city_town`
- `location_name`
- `age_min`
- `age_max`
- `season_or_dates`
- `registration_url`
- `description`

### Optional Columns
- `address`
- `gender` (`boys`, `girls`, `coed`, `not_specified`)
- `start_date` (`YYYY-MM-DD`)
- `end_date` (`YYYY-MM-DD`)
- `cost`
- `last_verified_at` (ISO datetime)
- `status` (`draft`, `published`, `archived`)

Use `docs/listings_import_template.csv` as your starter format.
