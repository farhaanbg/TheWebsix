# Current feature test report — 29 October 2026

Re-audited the current local `main` after merging the accounts and community fixes.
This report includes a fresh regression run, expanded functional checks and browser
verification on 29 October. No application fixes were made during this audit.

## Latest verification

- Django test suite: **25 passed** (10 existing tests and 15 new regression tests).
- Expanded functional audit: **71 checks, 67 passed and 4 failed**. The four
  failures cover three distinct known problems: signed-out community login
  (two routes), existing duplicate-email login, and invalid account photo uploads.
- Django system checks and installed dependency consistency: passed.
- Model/migration consistency: passed; no missing migrations.
- Local migration plan: no pending operations.
- Whitespace check: passed.
- Browser verification: login, account like/unlike and comment creation, community
  comment panel and submission, post details, review display and account navigation.
- Browser checks additionally confirmed unsafe HTML interpretation in account
  comments and a four-hour difference in comment timestamp display. These are
  separate findings from the 71 functional checks.
- Passing regression tests do not mean all known issues are fixed.

## Fixed issues and added controls

| Previous issue | Current result / verification |
| --- | --- |
| Community Add comment page crashes with `NoReverseMatch` | Fixed. The page and empty-submission error page render; valid comments save. |
| Delete post confirmation crashes | Fixed. Confirmation renders and owner deletion succeeds. Another user's deletion is rejected. |
| Delete Account page and incorrect-password response crash | Fixed. Both render; an incorrect password leaves the account intact. |
| Password reset email fails to generate | Fixed. Request, generated email link, new password submission and completion page pass end to end using simulated email delivery. |
| Account likes button lacks a handler and endpoint | Fixed. Direct requests and browser clicks like/unlike successfully; card counts and the dashboard total update. |
| Invalid account username edit gives no feedback | Fixed. Duplicate-username validation feedback appears after redirecting. |
| Changing full name to one word retains the old surname | Fixed. Saving `Solo` clears the previous last name. |
| Community/Reviews account avatar links to the wrong page | Fixed. Rendered signed-in links point to the account dashboard on both pages. |
| Community comment popup is not connected | Fixed. Browser toggle opens the comment panel; submitting returns to Community, and the saved comment appears on post details. |
| Account comments have no creation route or form | Fixed. Direct requests and browser form submission save and display comments; empty comments are rejected. |
| Signup/profile editing allow duplicate emails | Both forms now reject duplicates without regard to case. Existing duplicate-email login remains broken, as detailed below. |

Account editing retains login protection. The merge also corrects the new
password-reset completion template's filename so the intended page is used.
Your hike pages, filtering, account likes counts and shared navigation were preserved.

## Confirmed errors still present

These cases were reproduced during this re-audit, using isolated test data.

| Priority | Feature / reproduction | Result and cause |
| --- | --- | --- |
| High | Sign out, then open Community > New Post | Redirects to `/community/login/`, which returns HTTP 500 because `community/login.html` is missing. Protected community/review actions still use this route. The navbar avatar now links to the accounts login page. |
| Medium | Two existing users share an email, then someone logs in using that email | HTTP 500 from `User.MultipleObjectsReturned` in `User.objects.get(email=...)`. New form validation prevents duplicates through signup/profile editing, but does not resolve existing records or handle ambiguous login. |
| Medium | Upload non-image contents as an account moment photo | Invalid contents are still accepted and stored. The dashboard saves `request.FILES` without image-form validation. |
| High | Add HTML markup to an account comment, then view it | Confirmed HTML interpretation: a harmless `<strong>` formatting marker becomes a real DOM element instead of literal text. Comment text is interpolated into `innerHTML`; this leaves a stored script-injection risk. No executable payload was submitted. |
| Low | Compare newly created account/community comment times | Account comments display UTC using direct `strftime`, while community templates display local time. Browser examples from the same session showed account `04:02` and community `08:02` (UTC+4). Account times need local-time conversion or an explicit timezone label. |

## Integration gaps and incomplete controls

The following remain in the source and were not resolved by the merged branches:

- Account moments and community posts use separate models/tables. Community
  posts do not appear as account moments or contribute to account likes totals.
  The team needs to decide whether these should represent the same content.
- Account Settings remains a `#` placeholder with no settings page.
- Booking creation, payment, saving hikes, announcements and Q&A remain incomplete
  user flows. The `bookings` app is a scaffold; the dashboard can display separate
  account booking records. These are unfinished features.

## Additional merged behavior

- Likes submitted from community post details return to that detail page;
  redirect behavior passes.
- Review creation dates render in day/month/year format; rendering passes.
  The timestamp field already existed; the branch changes its display.
- Community styling, footer, post metadata and visible action counts were updated.
  Community and reviews were inspected in the browser at its default viewport;
  responsive layouts and visual polish were not exhaustively reviewed.

## Current functional coverage

The expanded audit exercised:

- Public home, hikes, community, reviews, login, signup and reset-request pages.
- Signed-out access to protected community/review and account pages.
- Signup, duplicate-email rejection, username/email login, wrong passwords,
  existing duplicate-email handling and session creation.
- Profile name/avatar/cover edits, duplicate-username feedback, valid/invalid
  moment uploads, account like/unlike, comment creation and empty-comment rejection.
- Account comment moderation and moment deletion permission checks.
- Community text/photo post creation, invalid-image rejection, comment/delete
  confirmation pages, valid/empty comments, duplicate-like prevention, unlike
  redirects, owner deletion and rejection of unauthorized deletion.
- Review creation, invalid-rating rejection and average calculation.
- Combined hike filters, invalid filters, detail pages, missing-hike 404s,
  admin access restrictions, admin listings and CSRF rejection.
- Account deletion with correct/incorrect passwords and password change with
  session retention.

The 25-test regression suite additionally rechecked the complete password-reset
flow with captured email, duplicate-email profile validation, review-date rendering,
hike availability/capacity behavior, sorting, empty listings and hike admin creation.

Browser checks confirmed the working account/community comment controls,
like/unlike counts, review dates, post details and Reviews-to-account navigation.
The account Settings and My Bookings sidebar links still point to `#`.
Reviews use an inline All Reviews fallback; a review modal was not asserted.

For historical context, the 28 October audit ran 56 additional checks: 43 passed
and 13 failed. Those historical counts are separate from this re-audit; no direct
percentage comparison is appropriate because the check sets differ.

## Evidence and limits

Regression tests are saved in `accounts/tests.py`, `community/tests.py` and
`hikes/tests.py`. Run them with `python manage.py test`.
The separate audit script and its 71-check JSON results are saved outside the
repository in this chat's artifact workspace under `hiking-audit/`.

Functional checks used isolated test databases and in-memory upload storage.
Browser checks used a separate temporary SQLite database and media directory on
port 8013 with generated audit accounts. That audit server was stopped and its
temporary database/uploads were removed afterward. The project's database,
accounts, uploads and existing servers were not modified.

Password reset captured email in memory; real email delivery was not tested.
The markup probe used harmless formatting and did not execute a script.
No production deployment, real payment system or exhaustive device/responsive
review was performed. This is targeted functional and browser verification.
