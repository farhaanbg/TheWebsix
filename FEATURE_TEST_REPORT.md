# Current feature test report — 28 October 2026

Tested the local working tree before committing the hike pages and account
likes fix. No application code or user records were changed during the audit.
The issues below are recorded for later work and remain unresolved in this snapshot.

- Existing test suite: **10 passed**.
- Additional functional checks: **56 run, 43 passed, 13 failed**. Several failures
  share the same cause; this is not a count of distinct bugs. One failed check
  identifies an account/community integration gap rather than a server crash.
- Django system checks, migration consistency and installed dependencies: passed.
- Additional browser verification: login, account like button, account comments
  display, community navigation and the failing comment page.
- Tests used isolated databases and in-memory upload storage. The browser used
  a separate temporary database on port 8002, not the user's project database.
- Local connectivity at the time of the audit: `/hikes/` on port **8000 returned
  HTTP 200**. Port 8001 refused connections. This audit did not change either server.

## Confirmed errors

| Priority | Feature / reproduction | Result and cause |
| --- | --- | --- |
| High | Sign out, open Community, then New Post or a sign-in action | Redirects to `/community/login/`, which crashes because `community/login.html` does not exist. Reviews use this login route too. |
| High | Sign in, click Add comment on a community post | Server error: `NoReverseMatch`. `addcomment.html:21` uses `community:post_detail`; the registered name is `community:post-detail`. Submitting an empty comment reaches the same broken error page. |
| High | Open the Delete post confirmation page | Same incorrect URL name in `deletepost.html:22`. Direct valid deletion requests succeed, but the normal confirmation page cannot render. |
| High | Account dashboard > Delete Account | Missing `accounts/delete_account.html` causes a server error. Submitting an incorrect password also crashes. Direct submission with a correct password works in the isolated test. |
| High | Forgot password > submit an existing user's email | Server error reversing `password_reset_confirm`. The app lacks its own reset email template, so Django's available default template tries an unnamespaced route while this app uses `accounts:password_reset_confirm`. Password change while already logged in works. |
| Medium | Two users share an email, then someone logs in using that email | `User.MultipleObjectsReturned` server error from `User.objects.get(email=...)`. Signup/profile forms allow duplicate email addresses. Username login and login with a unique email pass. |
| Medium | Account moment > click the likes button | Confirmed in browser: `ReferenceError: toggleLike is not defined`. The button has an onclick handler but no implementation or account like endpoint. Displaying existing counts works. |
| Medium | Modify Account > enter a username already used by another user | Edit is rejected, but the view redirects without showing validation errors. The user sees unchanged details with no explanation. |
| Medium | Change full name from `Audit Tester` to `Solo` | Saved name becomes `Solo Tester`: the edit form never clears the old last name when only one word is supplied. |
| Medium | Upload non-image contents as an account moment photo | Accepted and stored. The dashboard saves `request.FILES` directly without an image form validation step. Community photo uploads correctly reject the same invalid file. |
| Medium | Click the account avatar from Community or Reviews while signed in | Link points to `/community/login/?next=...` instead of the account dashboard. That route also has the missing-template error described above. |

## Integration gaps and incomplete controls

- Account moments and community posts are separate models/tables. Creating a
  community post does not add it to the account dashboard or its likes totals.
  The audit's shared-posts expectation failed for this reason. The team needs to
  decide whether they should be the same content before changing the models.
- Community popup markup exists, but the community template does not include
  its JavaScript file. Its comment link navigates to the separate broken page
  instead of opening a popup. The existing script also expects different markup
  (`data-comment-toggle`) than the current links (`data-comment-url`).
- The account comments popup displays and deletes existing comments; there is
  no account comment-creation route or form. The account Settings link points to
  `#` and has no settings page.
- Booking creation, payment, saving hikes, announcements and Q&A are not
  implemented as complete user flows. The `bookings` app remains a scaffold;
  the account dashboard can display separate account booking records. These
  are unfinished features, not failures of the new hike listing.
- Source-review concern: account comments are inserted using `innerHTML` with
  unescaped comment text. This can interpret stored text as HTML. Use text nodes
  when this area is fixed. No malicious payload was run during this audit.

## What passed

- Home, hike listing, community, reviews, account login/signup and dashboard pages.
- Hike search by name/district, combined location/date/price/difficulty filters,
  sorting, empty results, invalid filter handling, detail pages and missing-hike 404s.
- Hike admin create with photo, edit, delete, availability and fully booked display;
  capacity validation and blocking regular users from admin pages.
- Signup, duplicate-username validation, username and unique-email login,
  incorrect-password handling, logout and the fixed account likes totals.
- Valid profile editing with avatar/cover uploads, password change, and rejection
  of an incorrect current password.
- Account moment creation with a valid photo and owner deletion; rejecting another
  user's deletion attempt; fetching comments and owner moderation.
- Community text/photo post creation, invalid image rejection, like/unlike and
  prevention of duplicate likes.
- Direct valid comment submission, direct confirmed owner/staff deletion and
  rejection of another user's deletion attempt. Normal comment/delete page
  navigation still fails as described above.
- Review creation, average rating calculation and rejection of out-of-range ratings.
- Admin listing/form pages for hikes, community content, reviews and users.
- CSRF rejection on an untrusted community post request.

## Evidence and limits

The additional test script (`feature_audit.py`), summary
(`feature-audit-results.json`) and tracebacks (`feature-audit-log.txt`) were kept
locally outside the repository. This report records their findings for the team.
The repository's own tests can be run with `python manage.py test`.

This is a functional review of implemented paths with selected negative cases
and targeted browser checks, not a guarantee of every possible input or device.
No production deployment, real email delivery or payment system was tested.
No fixes were applied during this audit.
