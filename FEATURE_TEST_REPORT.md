# Feature verification — 30 October 2026

## Latest local merge verification: bookbooking

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
