# Feature verification — 31 October 2026

## Current progress: latest main and Q&A integrated

This section is the current status. All sections below are dated historical
records; their statements about unfinished features, known errors and uncommitted
work describe those earlier snapshots, not the current integration.

- Fetched all remote branches on 31 October 2026. Fast-forwarded local `main`
  from `9f6a4bb` to `origin/main` (`3b40d02`), including login-return fixes
  (`ba252f0`) and review management (`3b40d02`).
- Merged the new `origin/feature/qa` branch (`3d1f8d0`) in merge commit
  `ef4a0f8`. No conflicts occurred. Every fetched remote branch tip is now an
  ancestor of local `main`; no other branch has outstanding commits to merge.
- Integration remains local; no push or deployment was performed. Existing
  untracked `debug.log` and `tmp/` files were left untouched.

| Area | Current progress |
| --- | --- |
| Accounts/login | Login preserves safe local `next` destinations, including for signed-in users; external destinations fall back to the dashboard. Login, dashboard and logout responses now disable caching. |
| Reviews | Owners and staff can edit reviews and confirm deletion. Other users are forbidden; invalid ratings do not overwrite the saved review. |
| Q&A | Public page, text search, categories and answered/unanswered filters are integrated. Signed-in users can ask and delete their own questions. Staff answer and moderate visibility in Django admin. |
| Existing features | Home, accounts, community, hikes, galleries, saved hikes, announcements and booking capacity behavior retain passing regression coverage. |
| Remaining work | Payment status and Scan-to-Pay instructions remain unfinished. Legacy account bookings/moments remain separate stored records, without automatic migration. |

### Verification of this integration

- Full Django suite: **135 tests passed**, including the branch's 12 Q&A tests
  and 9 added integration tests for login destinations and review management.
- Login checks cover local destinations, external-host rejection, authenticated
  redirects, failed-login destination retention and the no-store response header.
- Review checks cover owner editing, prefilled forms, invalid ratings, confirmation
  before deletion, unrelated-user rejection, staff access and guest login redirects.
- Q&A branch tests cover public reading, authentication, server-assigned ownership,
  validation, duplicate questions, ownership on deletion, hidden questions,
  answers/timestamps, admin attribution, search and category filtering.
- Django system checks, migration-state consistency and whitespace checks passed.
- Backed up the local database to `db.sqlite3-before-qa-20261031-153933`, then
  applied `qa.0001_initial` successfully. No migrations remain pending.
- README now documents Q&A setup and moderation, review management and login
  return behavior. No browser/device audit, production deployment, real email
  delivery or payment verification was performed for this integration.

The old known-error table below is historical: duplicate-email login handling,
comment text rendering, upload validation and local comment timestamps were
addressed in the earlier fixed-accounts integration and retain regression coverage.
This update does not claim a fresh comprehensive functional or browser audit.

## Latest local update: hike detail design and multiple photos

- Rebuilt hike details from the local Easy and Sold Out reference images:
  large gallery with thumbnails, title and tags, four trail metrics, description,
  optional highlights/packing sections, guide cards, location and a booking panel.
  Shared navigation and the hikes directory retain their existing layouts.
- Added ordered `HikePhoto` records with optional captions, managed through
  photo rows in the hike admin. The existing cover stays first and is preserved;
  gallery-only, single-photo and no-photo details are supported.
- Added optional highlights, packing items and meeting-point instructions.
  No fictional guide credentials, cancellation policies, contact numbers or
  waitlist actions are added to live hike data.
- Existing booking eligibility, saved-hike actions, schedule history and
  announcements remain available. Cancelled/full hikes retain closed states.
- Full Django suite: **114 tests passed**. New checks cover gallery ordering,
  existing-cover preservation, empty/single-photo cases, escaped optional text,
  draft privacy, admin multi-photo upload/removal and invalid-image rejection.
  Existing admin form submissions now include the photo formset metadata.
- Desktop (1440px) and mobile (390px) visual checks used an isolated rendered
  Django page with synthetic in-memory records and local project images.
  Thumbnail clicks and keyboard navigation passed; all images loaded, no
  JavaScript errors occurred, and mobile had no horizontal page overflow.
  Share fallback displayed the page URL. Native sharing and clipboard delivery
  on the running site were not verified; local preview networking was unavailable.
- Backed up SQLite to `db.sqlite3-before-gallery-20261030` and applied
  `hikes.0003` successfully. Migration-state consistency passed. Preview records
  were not added to the local database, and the preview server was stopped.

## Earlier local update: hike link appearance review

- Reviewed the supplied regular-account and admin-account screenshots. The
  regular-account screenshot shows purple links without the intended spacing;
  the admin-account screenshot shows yellow, spaced links.
- Checked `hikes/templates/hikes/list.html` and the hike stylesheets. Both
  accounts use the same quick-link markup and styles; there is no role-based
  colour rule. The current stylesheet sets non-button hike links to yellow
  and the quick-link row to a 20px gap with 12px text.
- The screenshots are consistent with default visited-link styling and an
  older cached stylesheet in the regular-account browser. Caching is a likely
  explanation, not a confirmed browser diagnosis. A hard refresh (`Ctrl+F5`)
  was recommended; the resulting appearance has not been verified.
- No application code changed for this review. No new browser checks or tests
  were run for the appearance finding; the latest focused test result remains
  the 75 passing hikes/bookings tests recorded below.

## Earlier local update: demo cleanup and requirements review

- Ran `python manage.py hike_demo --clear` successfully. Demo records, demo
  accounts and copied demo assets were removed using the tracked manifest.
- Verified zero hikes, guides, saved hikes, announcements, bookings,
  participants and booking notifications remain. The two other user accounts
  remain in the local database.
- Rechecked the hikes scope against the functional requirements in the system
  specification (pages 5–11). The public hike directory, filters, detail pages,
  saved hikes, announcements and admin schedule/status management are present.
- Focused Django suite: **75 hikes/bookings tests passed**, with no system-check
  issues. Tests used a separate database and did not add local demo records.
- Payment status and Scan-to-Pay instructions remain booking/payment work.
  The public directory supports price filtering; the Django hike admin list
  does not currently have a price filter.

## Earlier local update: temporary demo data (subsequently removed)

- Added local `[DEMO]` records with `python manage.py hike_demo`: 8 hikes,
  3 guides, 6 bookings with participants, 3 saved hikes, 3 announcements and
  2 private booking notifications. Scenarios include available/full, cancelled,
  postponed, past, free and incomplete-draft hikes.
- Added normal customer `demo_hiker` and scoped staff `demo_admin`, limited to
  hikes/bookings admin permissions. Both accounts are synthetic local test data.
- SQLite backup before seeding: `db.sqlite3-before-dummy-data-f91a2ab5`.
- Six isolated helper tests passed: seed scenarios, repeat-run idempotence,
  cleanup preserving unrelated records and capacity, account collisions,
  manifest/label checks and the DEBUG-only restriction.
- Authenticated local request checks returned HTTP 200 for the hikes directory,
  saved hikes, announcements and My Bookings with the seeded records.
- `python manage.py hike_demo --clear` removes tracked demo data, the copied
  assets and the manifest. Existing accounts, unrelated records and uploaded
  files are preserved. Cleanup was subsequently completed as recorded above.

No data was sent externally, and nothing was staged, committed or pushed.

## Earlier local update: remaining hike requirements

All changes remain local, unstaged and uncommitted.

- Full Django suite: **103 tests passed**. System checks, migration-state
  consistency and whitespace checks passed.
- Hikes have Scheduled, Postponed and Cancelled states. Cancellation closes
  booking and cancels active reservations with capacity release. Postponement
  keeps reservations. Schedule/status changes record old/new values, actor and
  reason and create private in-app booking notifications in the same transaction.
- Admin actions and ordinary admin schedule edits have regression coverage.
  Actions require change permission; read-only staff cannot perform them.
- The default directory, statistics and location options use upcoming published
  hikes. An explicit archive scope includes past events. Same-day departure
  times, fully booked visibility and cancelled-hike visibility are covered.
- Multiple guide records replace the single text field. The migration test
  verifies preservation of legacy guide names and reserved spots. Complete
  legacy hikes stay public; incomplete hikes become drafts.
- Publishing requires guides and a departure time. Public queries, detail
  access and booking checks exclude incomplete or unpublished hikes.
- Saved hikes have per-user ownership, unique user/hike pairs and protected
  POST actions. Tests cover repeat saves, privacy, removal and CSRF enforcement.
- General and hike-specific announcements support admin creation, editing and
  deletion. Public visibility, draft privacy and escaped content are tested.
- Browser checks used a separate in-memory database with synthetic records.
  The listing, cancelled-hike detail and announcements page rendered correctly.
  Preview servers were stopped and their sample records did not enter the
  user's database.
- Before applying hikes.0002 and bookings.0003 locally, the SQLite database was
  backed up. Both migrations applied successfully. The database had no existing
  hikes at that point. Legacy-data preservation was tested separately.

Notifications appear in My Bookings; no real email or SMS was sent. Payment
status and Scan-to-Pay instructions are outside these hike requirements.
No simultaneous-request stress test or comprehensive device audit is claimed.

## Earlier local update: booking cancellation and capacity

These changes remain local and uncommitted.

- Full Django suite: **84 tests passed**. System checks, model/migration
  consistency and whitespace checks passed. No database migration is needed.
- Owners can cancel bookings through a CSRF-protected POST action in My
  Bookings. Other users, including staff using the customer endpoint, cannot
  cancel someone else's booking. Staff use the admin interface instead.
- Booking creation, status changes, spot edits and transfers between hikes
  adjust reserved spots within the same transaction as the booking change.
- Repeated cancellation, stale instances and deletion of cancelled bookings do
  not release capacity twice. Confirmation does not reserve the same spots twice.
- Admin single/bulk cancellation and deletion, reactivation, overbooking
  rejection, transactional rollback and rebooking freed spots have regression
  coverage. Direct queryset deletion also releases active reservations.
- Reserved spots are read-only in the hike admin. Saving an older hike form
  does not overwrite a newer reservation count. Existing manually entered
  reservations remain intact, rather than resetting counters from booking totals.
- Bulk creation and direct queryset updates of booking capacity/status fields
  are rejected; callers must use the transactional model save path.

Payment-status management, payment instructions, hike cancellation/postponement
and notifications remain outside this update. No browser audit or simultaneous
request stress test is claimed.

## Earlier local merge verification: bookbooking

The `bookbooking` branch integrates booking forms, participants, server-side
price calculation, pending reservations and user-specific booking listings.
The merge is local only; no GitHub push is part of this update.

- Full Django suite: **65 tests passed**, including account, community, hikes
  and home regression tests. The old unavailable-booking assertion now checks
  that full hikes do not offer a booking link.
- Additional checks cover blank or mismatched participants, the 20-person
  limit, full/past/departed hikes, dashboard integration and transaction rollback.
- Capacity reservation uses a conditional database update within the booking
  transaction, in addition to row locking where the database supports it.
- The existing account/community fixes, shared profile link, site footer,
  availability display and hikes styles remain in place.
- The dashboard uses the new booking model and its related hike fields.
- Database migrations and model/migration consistency are checked locally.

Cancellation with capacity release, payment-status management and payment/QR
instructions remain incomplete. Admin status edits and deletions do not
automatically reconcile hike capacity. No concurrent-request stress test,
real payment transaction, browser audit or notification delivery is claimed.
Legacy account booking records remain stored separately from new bookings.

## Earlier merge verification: fixed-accounts

The `fixed-accounts` branch now integrates with the current main branch. The
older audit below remains historical evidence, not a fresh audit of this merge.

- Full Django suite: **49 tests passed**, including the hikes and home tests.
- Django system checks, model/migration consistency and whitespace checks passed.
- Dashboard posts, likes, comments and deletion now use community records.
  New posts use the community form, including its image validation.
- The shared navigation and photo-free posts render in dashboard tests.
- Duplicate-email login no longer raises `MultipleObjectsReturned`; username
  login remains available. The duplicate-email signup test is retained.
- Dashboard comment rendering uses DOM text nodes for user text. Community
  detail rendering escapes comment markup. Comment creation and listing now
  return the same local-time formatting.
- Ownership tests reject deletion of unrelated users' posts and comments.
- The login-route conflict retains the existing configurable account login,
  friendly 404 handling, home app, community editing and hikes redesign.

The previous 71-check audit and browser checks were not rerun for this merge.
No new browser or real email-delivery verification is claimed.

Legacy `accounts.Moment` records are retained in the database, but the dashboard
now displays `community.Post` records. The local database contained zero legacy
moments when checked. Other databases containing legacy moments need a reviewed
data migration before adopting the unified dashboard; this merge does not copy
private account content into the public community feed automatically.

## Earlier feature audit

Verified the current code before committing the 404 page, legacy login redirect
and hikes listing redesign. This report supersedes the issue status from 29 October.

## Latest verification

- Django test suite: **44 passed**, including 8 new tests for missing pages and
  the legacy community login redirect. The 15 hikes tests also pass independently.
- Expanded functional audit rerun: **71 checks, 69 passed and 2 failed**.
  Failures reproduce existing duplicate-email login crashes and acceptance of
  invalid account photo uploads. These audit checks are separate from the suite.
- Django system checks and installed dependency consistency: passed.
- Model/migration consistency: passed; no missing or pending migrations.
- Whitespace check: passed.
- Browser checks: custom 404 rendering and its Hikes link; redesigned hikes
  listing on desktop and a 390px mobile viewport; search submission; final
  statistics-focused header and distinct banner image on both screen sizes.

## Changes included in this update

- Added a branded 404 page with Home and Hikes links. Unknown URLs and missing
  hike records return HTTP 404 with the friendly page in local (`DEBUG=True`)
  and production (`DEBUG=False`) settings. JSON errors and HTTP 500 responses
  are preserved. This does not conceal application failures behind a 404 page.
- Redirected the legacy `/community/login/` address to `/accounts/login/`,
  retaining its query string, including `next`. Guest and signed-in cases pass.
  Normal protected community/review actions already use the accounts login;
  their signed-out flows also pass the expanded audit.
- Refreshed the hikes listing: statistics-led header, a separate forest-valley
  banner photo, clearer filter panel, larger cards, date/difficulty badges,
  trail metrics, availability bars and prices. Search, filters and sorting retain
  their existing behavior. The listing stylesheet is scoped separately from
  hike details; no model changes or migrations were needed.

The current main branch also contains the separate `home` app, home search
integration fixes, community post editing and rating-star display changes from
previous updates. Post-edit image replacement/removal edge cases were not part
of this verification; no comprehensive claim is made for those flows.

## Fixed issues and added controls

| Previous issue | Current status / evidence |
| --- | --- |
| Signed-out Community > New Post or Leave Review crashes at login | Fixed. Both reach `/accounts/login/` and render successfully in the latest audit. |
| Opening the old `/community/login/` address crashes | Fixed in this update. Redirect and query-string preservation pass regression tests in both local and production settings. Signed-in users reach the dashboard. |
| Unknown links show Django's technical 404 page locally | Friendly 404 added. Unknown URLs and missing hike records pass in both debug modes; browser rendering and recovery link verified. |
| Community comment page and empty submission crash | Fixed. Pages render and valid comments save; checked again in the expanded audit. |
| Delete post confirmation crashes | Fixed. Page renders, owner deletion succeeds and unauthorized deletion is rejected. |
| Delete Account page and wrong-password response crash | Fixed. Both render; correct-password deletion works and wrong-password deletion retains the account. |
| Password reset email fails to generate | Fixed. Regression tests verify the generated email link, new password and completion page with simulated delivery. |
| Account likes lack a handler and endpoint | Fixed. Direct like/unlike and dashboard totals pass. Browser counts were verified on 29 October. |
| Invalid username edit gives no feedback | Fixed. Validation feedback appears after redirecting, verified in this audit. |
| Single-word full name retains old surname | Fixed. Editing clears the old surname, verified in this audit. |
| Community/Reviews profile avatar links to the wrong page | Fixed. Signed-in destination checks pass. |
| Community comment panel is not connected | Fixed. Browser toggle and saved-comment display verified on 29 October; comment submission passes again. |
| Account comments have no creation route/form | Added. Valid comments save, empty comments are rejected and moderation permissions pass. |
| Signup/profile editing allow duplicate emails | Forms now reject duplicates without regard to case; regression tests pass. Existing duplicate-email login still fails below. |
| Blank homepage difficulty filters hide all hikes | Fixed in the previously pulled homepage search update; its integration tests pass. |

## Known errors still present

| Priority | Reproduction | Current evidence |
| --- | --- | --- |
| High | Add HTML markup to an account comment, then view it | Account comments still insert user-controlled text using `innerHTML`. A harmless `<strong>` marker became a real DOM element in the 29 October browser audit, confirming HTML injection and a stored script-injection risk. That rendering code remains unchanged. No executable payload was submitted. |
| Medium | Log in using an email already shared by two accounts | Latest isolated audit reproduces HTTP 500 from `User.MultipleObjectsReturned` in `User.objects.get(email=...)`. Form validation does not resolve existing duplicates or handle ambiguous login. |
| Medium | Upload non-image contents as an account moment photo | Latest isolated audit confirms the file is accepted and stored. Dashboard creation still saves uploads without image-form validation. Community uploads reject the same invalid contents. |
| Low | Compare account and community comment timestamps | Account responses still use direct UTC `strftime`; community templates display local time. The 29 October browser audit showed a four-hour difference. This formatting code remains unchanged; the timestamp discrepancy was not browser-retested today. |

The login failures previously listed in this section are now marked fixed above.
Passing regression tests do not mean all known issues are resolved.

## Integration gaps and incomplete controls

- Account moments and community posts remain separate models/tables; community
  posts do not become account moments or contribute to account likes totals.
- Account Settings and the My Bookings sidebar link remain `#` placeholders.
- Complete booking creation/payment, saved hikes, announcements and Q&A remain
  unfinished user flows. The dashboard can display separate account booking records.
- The legacy login redirect preserves `next`; the custom account login currently
  sends successful sign-ins to the dashboard rather than resuming that destination.

## Coverage and limits

The expanded audit rechecked public pages, signup/login, profile/image edits,
account moments/comments/likes and ownership checks, community posts/comments/
likes/deletion, reviews/averages/invalid ratings, hike filters/details/404s,
admin access/listings, CSRF, password changes/session retention and account deletion.

The regression suite additionally covers password reset, dashboard totals,
name/email validation, home routing/assets and search integration, hike capacity,
sorting/empty states/admin creation, the friendly 404 and legacy login redirect.
Tests are in `accounts/tests.py`, `community/tests.py`, `hikes/tests.py` and
`home/tests.py`. Run them with `python manage.py test`.

The 71-check audit script and dated result files remain outside the repository
in this chat's artifact workspace under `hiking-audit/`. On 29 October the same
check set passed 67 of 71 checks; the two signed-out login checks now pass.
The older 28 October audit used a different 56-check set and is not a direct comparison.

Automated checks used isolated databases; upload probes used in-memory storage.
Browser design previews used the local dummy records at port 8013. Temporary
preview servers were stopped. The dummy records, images and demo-account sessions
were removed before committing/pushing; the original account was retained.
The local cleanup helper and database/uploads are not tracked by Git.

No real email delivery, production deployment, payment system or exhaustive
responsive/accessibility audit was performed. The 390px and desktop checks are
selected visual checks, not coverage of every device. No known-error fixes beyond
those explicitly marked above are claimed.
