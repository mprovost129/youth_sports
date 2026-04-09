## Product Vision
Create a website that helps families find youth sports and youth activities in the Attleboro, MA area.

Start with Attleboro and nearby towns. Expand to Bristol County, then broader Massachusetts coverage, then other states over time.

## Target Users
- Parents and guardians looking for programs for children and teens
- Program organizers who want their listings discovered
- Community members looking for trusted local resources

## Geographic Scope
- Phase 1: Attleboro + surrounding towns
- Phase 2: Bristol County
- Phase 3: Massachusetts-wide
- Phase 4: Multi-state expansion

## MVP Scope (Phase 1)
The first release should focus on discoverability and quality listings.

### Included
- Home page with:
  - Upcoming sports and activities
  - Recently added listings
- Sports index page
- Activities index page
- Filters for:
  - Category/type
  - Age group
  - Gender
  - City/town
- Global search
- Resources page
- Contact page
- Placeholder text logo in navbar: `Youth Sports & Activities`

### Excluded (for now)
- Public user submissions
- Login/register workflows
- Organizer self-service dashboards

## Navigation (Initial)
- Left: logo placeholder (`Youth Sports & Activities`)
- Center: `Sports`, `Activities`, `Resources`, `Contact`
- Right: `Search`, `Help` icon

Note: Use page-level filters instead of overly deep navbar dropdowns.

## Listing Data Schema (Required Fields)
Each listing should include:
- `title`
- `category` (sport or activity)
- `subtype` (example: soccer, dance, robotics)
- `organization_name`
- `city_town`
- `location_name`
- `address` (optional if not public)
- `age_min`
- `age_max`
- `gender` (boys, girls, co-ed, not specified)
- `season_or_dates`
- `registration_url`
- `cost` (optional)
- `description`
- `last_verified_at`
- `status` (draft, published, archived)

## Content Quality Rules
- All listings must include a valid registration link or clear signup instructions.
- Listings without verification updates should be flagged after 90 days.
- Inactive or expired programs should not appear in default search results.
- Admin/editor review is required for new or updated listings.

## Success Metrics (Phase 1)
- 100+ verified listings across 5+ towns
- Users can find a relevant listing in 3 clicks or less
- At least 90% of visible listings have been verified within 90 days

## Phase Plan
### Phase 1: Discovery Foundation
- Launch home, sports, activities, resources, and contact pages
- Implement filters and search
- Seed verified listings for Attleboro + nearby towns

### Phase 2: Operations and Quality
- Add admin-only listing management tools
- Add stale-data monitoring and verification workflows
- Expand coverage to Bristol County

### Phase 3: Community Features
- Add optional login/register
- Add moderated user submissions and approval queue
- Add audit trail for edits

### Phase 4: Geographic Expansion
- Expand statewide in MA
- Prepare repeatable process for adding new states

## Open Decisions
- Final list of "surrounding towns" in Phase 1
- Exact age-group taxonomy (examples: 4-6, 7-9, 10-12, 13-15, 16-18)
- Whether cost should be searchable/filterable in MVP or Phase 2
- Whether resources should include legal/regulatory summaries at launch

## Recommendations Backlog (One At A Time)
We will execute these in order, one item at a time, and verify each before moving to the next.

1. Improve parent-facing trust signals
- Show a clear badge on list cards: `Verified recently` vs `Needs review`
- Show both `Last updated` and `Last verified` in more places

2. Make search smarter
- Add typo-tolerant/fuzzy matching for sport, activity, and town
- Add sort options: `Soonest start`, `Recently added`, `Ages low-high`

3. Add listing status workflow
- Add statuses such as `draft`, `published`, `archived`
- Keep new and edited listings as `draft` until staff review

4. Add image quality controls
- Enforce max upload size and basic dimension guidance
- Add optional auto-resize/compression for performance

5. Strengthen edit/audit history
- Track who created/edited each listing and when
- Add a simple change log for staff review

6. Expand verification queue automation
- Add one-click `Mark verified today`
- Add queue filters: stale only, has reports, town, sport
- Add queue pagination

7. Add public contribution pipeline
- Add public `Suggest a listing` form
- Route suggestions into staff review (not direct publish)

8. Improve SEO and discoverability
- Add clean URL pages (example: `/sports/baseball/attleboro/`)
- Add metadata/schema markup for listing pages

9. Prepare for performance and scale
- Add indexes for common filters (`subtype`, `city_town_ref`, `start_date`, `last_verified_at`)
- Consider caching popular queries and homepage data
 - Status: completed on April 7, 2026 (indexes + short-lived homepage/list query caching)

10. Improve operations and safety
- Add recurring checks for stale data and unresolved reports
- Add backup/restore runbook and basic admin activity alerts
 - Status: completed on April 7, 2026 (`listing_health_check` command + `docs/BACKUP_RESTORE.md` + email alerts via `OPS_ALERT_EMAIL`)

## Post-Backlog Enhancements
- Duplicate detection on Add/Suggest forms with intentional override checkbox
  - Status: completed on April 7, 2026
- `sitemap.xml` + `robots.txt` + Open Graph/canonical metadata improvements
  - Status: completed on April 7, 2026
- Lightweight analytics events (`search`, `empty_search`, `outbound_click`) with tracked outbound redirect
  - Status: completed on April 7, 2026
- Verification queue status snapshot panel (draft/stale/reports/suggestions + generated timestamp)
  - Status: completed on April 7, 2026

