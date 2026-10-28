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
trail information, date, price, difficulty, duration (in minutes), capacity
and reserved spots. You can also upload a photo, add a guide name, description
and comma-separated tags. A placeholder appears when no photo is uploaded.

Saved hikes appear at `/hikes/`, with search, location/date/price/difficulty
filters and sorting. Each card opens a basic detail page. Fully booked hikes
remain visible. Reserved spots are managed manually for now; these pages do
not create bookings or connect to the separate account booking model yet.

No sample hikes are added automatically. Use the admin to create your own
records. Run `python manage.py test hikes` to check the hike features.

## Before starting a new task

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
