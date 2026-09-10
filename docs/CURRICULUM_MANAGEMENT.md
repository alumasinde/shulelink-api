# Curriculum Management

ShuleLink treats curriculum as **platform catalog data + school implementation data**.

## Platform catalog

Platform administrators maintain versioned curriculum templates containing:

- education levels
- grades
- learning areas
- subjects
- grade subject offerings
- pathways
- tracks
- subject combinations

Published templates are immutable. To change a published curriculum, clone it into a new draft version, edit it, validate it, then publish it.

## School adoption

A school selects a published template from `/school/curriculum`. Selection creates/updates a tenant-local snapshot and records the platform template/version in `tenant_curriculum_profiles`.

The school can then configure its own classes, subject offerings, teachers and timetable without mutating the platform catalog.

Platform updates never silently rewrite historical school records. A future curriculum update flow can explicitly compare the school snapshot with a newer platform version and let the school adopt it.

## Kenyan baseline

The seeded template models the current broad Kenyan structure as Pre-Primary, Primary, Junior School and Senior School, with Grade 10-12 pathway/track data. The values are database seed data, not hardcoded application rules, so the platform can revise them when official curriculum releases change.

KICD describes Grade 9 as the final grade of Junior School and states that learners explore interests and abilities before transition to Senior School pathways and tracks. Curriculum designs also contain learning outcomes, strands/sub-strands, core competencies, values, PCIs and assessment guidance. These are intentionally not hardcoded into the template catalog; they are the next layer for the CBC assessment/content model.

## API

Platform:

- `GET /api/v1/platform/curriculum/templates`
- `GET /api/v1/platform/curriculum/templates/{id}`
- `POST /api/v1/platform/curriculum/templates`
- `PUT /api/v1/platform/curriculum/templates/{id}`
- `POST /api/v1/platform/curriculum/templates/{id}/clone`
- `POST /api/v1/platform/curriculum/templates/{id}/publish`
- `POST /api/v1/platform/curriculum/templates/{id}/archive`

School:

- `GET /api/v1/curriculum/templates`
- `GET /api/v1/curriculum/configuration`
- `POST /api/v1/curriculum/select-template`

## Permissions

Platform: `curriculum.manage`

School: `curriculum.read`, `curriculum.manage`

The schema also keeps `platform_source_id` on tenant curriculum records so platform-managed data can be distinguished from school-created/custom data.
