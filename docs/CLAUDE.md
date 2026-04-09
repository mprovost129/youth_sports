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

