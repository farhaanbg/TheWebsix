# TheWebsix

University hiking website project using Django, SQLite and Django's default admin.
The project has four apps: accounts, hikes, bookings and community.

## First-time setup (Windows PowerShell)

Install Git and Python 3.12 or newer. To push changes, accept the repository
owner's GitHub collaborator invitation and sign in when Git asks.

```powershell
git clone https://github.com/farhaanbg/TheWebsix.git
cd TheWebsix
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/ for the site or http://127.0.0.1:8000/admin/
to log in with the superuser you created. The site initially shows Django's
welcome page. Stop the server with `Ctrl+C`.

If PowerShell blocks activation, run the following and try activation again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

For Command Prompt, activate with `.venv\Scripts\activate.bat` instead.
Activate the environment each time you open a new terminal. Use `deactivate`
to leave it.

## Where to work

| Folder | Intended features |
| --- | --- |
| `accounts/` | Registration and profiles using Django's built-in user model |
| `hikes/` | Hikes, guides, saved hikes and announcements |
| `bookings/` | Reservations, participants and payment status |
| `community/` | Moments/posts, comments, likes, reviews and Q&A |
| `thewebsix/` | Shared project settings and main URL configuration |

Inside each app, `models.py` defines data, `views.py` handles requests, and
`admin.py` registers models with Django's admin. Coordinate changes to shared
files such as `thewebsix/settings.py` and `thewebsix/urls.py` with the team.

## Managing hikes

After pulling the hike pages, run `python manage.py migrate`. Sign in to
`/admin/` with your local superuser and open **Hikes > Add hike**. Enter the
trail information, date, departure time, price, difficulty, duration (in minutes)
and capacity. Create guide records under **Hikes > Guides**, then assign one or
more guides. New hikes start as drafts. Set **Is published** after assigning
guides and a departure time. Incomplete drafts are not public or bookable.
Reserved spots are maintained automatically. You can also upload a photo,
add a description and comma-separated tags. A placeholder appears without a photo.

Hike details support a cover photo plus additional gallery photos. In the hike
admin, use the **Hike photos** rows to upload images, add optional captions and
set their position (lower numbers first). Save the hike to apply additions,
reordering or deletions. The existing image remains the cover and appears first;
gallery-only hikes also display their photos on the detail page. Visitors can
select thumbnails or use Left/Right, Home and End while a thumbnail is focused.
Optional **Highlights** and **What to bring** fields accept one item per line;
**Meeting point** supplies additional location instructions. Empty optional
sections are hidden. Run `python manage.py migrate` after pulling this update.

Published hikes appear at `/hikes/`, with search, location/date/price/difficulty
filters and sorting. The default view shows upcoming departures in local time.
Choose **All hikes and past events** to include older hikes. Statistics and
location options follow the selected directory scope. Fully booked hikes
remain visible. Signed-in users can book an upcoming hike from its detail page.
Bookings support up to 20 participants, calculate prices on the server and
reserve capacity while awaiting admin confirmation. Users can see their own
bookings at `/bookings/my-bookings/` and on their account dashboard.

Run `python manage.py migrate` after merging the booking branch. The new
`bookings.Booking` records drive the dashboard; older `accounts.Booking`
records remain stored separately and are not migrated automatically.
Users can cancel their own bookings from My Bookings. Cancellation releases
spots once; deleting an active booking also releases its spots. Admin status,
spot-count and hike changes adjust capacity and recalculate the total when
needed. Reactivating a booking checks available capacity and departure time.
Admin bulk confirmation, cancellation and deletion use the same capacity rules.
Previously entered manual reservations remain included in the stored counts.
Payment-status management and Scan-to-Pay instructions are still unfinished.

Use the hike admin actions to cancel a hike or postpone it to a new date/time.
Cancellation closes booking and cancels active reservations transactionally;
postponement retains reservations. Both record history and create private
in-app notices in **My Bookings**. Editing a date/time directly also records a
postponement. Cancelled hikes remain visible. Reopening a hike does not revive
previously cancelled bookings automatically.

The guide migration preserves existing names and reservation counts. Existing
hikes with a guide and departure time stay published; incomplete records become
drafts for the team to complete. No guide or schedule details are invented.

Signed-in users can save or remove hikes from their detail pages and review
them at `/hikes/saved/`. Published general and hike-specific announcements appear
at `/hikes/announcements/` and on relevant hike details. Staff manage them under
**Hikes > Announcements**. Notifications stay inside the application; this update
does not send email or SMS.

When extending booking code, create records individually and use `save()` for
status, spots or hike changes. Direct queryset updates of those fields and bulk
creation are rejected because they bypass capacity accounting. Queryset deletion
is supported and releases the relevant reservations transactionally.

No sample hikes are added automatically. Use the admin to create your own
records. Run `python manage.py test hikes` to check the hike features.

## Before starting a new task

### Temporary local test data

Run `python manage.py hike_demo` to add clearly labelled `[DEMO]` records:
eight hikes covering available, full, postponed, cancelled, past, free and draft
states, three guides, six bookings with participants, saved hikes, announcements
and private booking notifications. Repeating the command does not duplicate data.

Sign in as `demo_hiker` to test customer features or `demo_admin` to test the
hikes and bookings admin. Both use `TrailDemo!2026`. The admin account has only
hikes/bookings permissions, and the command runs only with `DEBUG=True`.

Remove these records later with `python manage.py hike_demo --clear`. Cleanup
uses the local manifest in `media/temporary-hike-demo/manifest.json` and preserves
unrelated records and files. Keep the `[DEMO]` labels and demo usernames while
testing so cleanup can verify ownership. The media and manifest are untracked.

### Starting a work branch

From the repository folder, with your previous work committed and your virtual
environment activated:

```powershell
git switch main
git pull --ff-only origin main
python -m pip install -r requirements.txt
python manage.py migrate
git switch -c feature/hike-list
```

Replace `feature/hike-list` with a short branch name for your task. Work on one
task per branch so teammates can review changes before they reach `main`.

## Save and share your changes

After editing the code, check it and try your feature locally:

```powershell
python manage.py check
python manage.py test
python manage.py runserver
```

Stop the server, then review and commit your changes:

```powershell
git status
git diff
git add hikes/views.py
git commit -m "Add hike listing view"
git push -u origin feature/hike-list
```

The file, message and branch above are examples. Stage each file belonging to
your task, including new files, before committing.

On GitHub, open a pull request from your branch into `main`. Describe what you
changed and how you checked it. Ask a teammate to review it, then merge it on
GitHub. Everyone can get the merged changes using the commands in
"Before starting a new task".

## Database and dependency changes

If you change models, generate and apply migrations:

```powershell
python manage.py makemigrations
python manage.py migrate
```

Commit the generated files in the app's `migrations/` folder along with your
model changes. Teammates run `python manage.py migrate` after pulling them.

Each teammate has their own SQLite database, test data and admin account.
The `.gitignore` excludes `db.sqlite3`, `.venv/` and Python caches; keep these
local. Share database structure through migrations, not the database file.

If the team adds a Python package, add its name and agreed version to
`requirements.txt` and commit that file. Teammates install it with
`python -m pip install -r requirements.txt`.

## If your branch falls behind main

Commit your current work, then bring the latest shared changes into your branch:

```powershell
git fetch origin
git merge origin/main
```

If Git reports conflicts, use `git status` to find the affected files. Agree
with the teammate who edited them on what to keep, remove the conflict markers,
then stage the resolved files and run `git commit`. Check your code again and
push your branch. Avoid force-pushing or overwriting another teammate's work.
