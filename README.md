# Hostel Desk

A Django application for hostel staff, room and resident management, monthly billing, advance ledgers, receipts, reports, and audit history. It uses Django's built-in user and authentication system.

## Requirements

- Python 3.10 or newer
- PowerShell on Windows
- MySQL Server

## Windows setup

Open PowerShell in the project folder. Create and activate a virtual environment, then install dependencies:

```powershell
py -m venv .venv
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
```

Create your private environment file without overwriting an existing one:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

Generate a Django secret key:

```powershell
py -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Put the generated key and your real MySQL connection values into `.env`. Set `DJANGO_DEBUG=True` for local development. The required database names are `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT`. `DJANGO_ALLOWED_HOSTS` is optional and defaults to `127.0.0.1,localhost,testserver`. Optional `HOSTEL_NAME`, `HOSTEL_ADDRESS`, and `HOSTEL_PHONE` values prefill database-backed receipt settings during migration; Owners can later edit the receipt name, address, phone, email, and receipt text in the application. Do not commit `.env` or share its secrets.

### MySQL Server and Workbench

Start the MySQL Server service. In MySQL Workbench, connect to that server, open a SQL tab for the connection, paste the following SQL, replace the example password with a strong unique password, and execute it:

```sql
CREATE DATABASE hostel_desk
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

CREATE USER 'hostel_app'@'localhost'
    IDENTIFIED BY 'replace-with-a-strong-password';

GRANT ALL PRIVILEGES ON hostel_desk.* TO 'hostel_app'@'localhost';
```

The grant is limited to this application's database and supports Django migrations. If MySQL is on another machine, restrict the account's host rather than using `'%'`.

Check the Workbench connection's hostname and port, then put the matching host and port in `.env` (`localhost` and `3306` are common local values). Django loads `.env` from the project root using `python-dotenv`, uses MySQL only, and reports any missing database variables.

### Apply and run

Run these commands from the project folder after `.env` is filled in:

```powershell
py manage.py check
py manage.py migrate
py manage.py create_role_groups
py manage.py createsuperuser
py manage.py runserver
```

`migrate` connects to MySQL and creates the application tables. `create_role_groups` prepares the Owner, Manager, and Warden groups. `createsuperuser` makes the initial administrator; use Django admin to create staff accounts and assign their groups. Open http://127.0.0.1:8000/ after the server starts; Django admin is at http://127.0.0.1:8000/admin/.

Open http://127.0.0.1:8000/ after the server starts. Django admin is available at http://127.0.0.1:8000/admin/.

### Staff authentication and roles

Staff accounts use Django's built-in `User` model and authentication views. The login page is available at `/accounts/login/`; signed-in users can sign out with the sidebar button. The dashboard requires an authenticated user in the Owner, Manager, or Warden group. Resident pages also require Django's `is_staff` flag through `staff_member_required`. Use `@login_required` for pages available to any signed-in user and `role_required` for role-specific access.

Create the three groups after applying migrations:

```powershell
py manage.py create_role_groups
```

Sign in at `/admin/` and open **Authentication and Authorization > Users**. Create or edit each staff account, enable **Staff status**, and select its group under **Groups**. Resident pages require both `is_staff` and an Owner, Manager, or Warden group. Django admin also requires `is_staff` and the appropriate admin permissions; role groups alone do not grant admin access. No demo resident records are seeded.

### Rooms

Apply the checked-in room schema with `py manage.py migrate`. Start the app with `py manage.py runserver`; staff in the Owner, Manager, or Warden group can use the Rooms section in the dashboard or open `/rooms/`. Rooms can also be managed from Django admin. Occupant and vacancy counts reflect active room assignments.

### Residents

Apply the checked-in resident profile and room assignment tables with `py manage.py migrate`. Staff can open `/residents/` to search and filter profiles, create or edit profiles, view assignment history, assign active residents to rooms, and mark residents as exited. Exiting a resident closes their active assignment while retaining both records. Room capacity and available-bed counts use active assignment data. Identity-document numbers and images are not collected.

### Monthly billing

Apply the checked-in billing schema with `py manage.py migrate`. The dashboard uses a selected billing month to show active residents, room capacity and vacancies, expected charges, collections, remaining balance, and charge-status counts. Staff can open `/billing/` to create a monthly charge from an active resident's current agreed fee, search or filter charges by period and calculated status, record partial or full payments, and review payment receipts. `/billing/roster/paid/` lists paid residents; `/billing/roster/attention/` lists due-soon and overdue residents. These pages use the same calculated billing statuses. Due soon means the charge is due within the next seven local calendar days. Paid, pending, due soon, and overdue are calculated from the charge amount, payments, due date, and Django's configured timezone; summary totals are not stored. Payment forms use a unique submission key to prevent repeat POSTs from recording the same payment twice. No WhatsApp, SMS, or email reminders are sent, and online payment processing is not integrated.

Resident advance balances are calculated from immutable deposit, rent-application, and refund ledger entries. Managers and Owners can apply advances; only Owners can record refunds. Applying an advance creates a linked rent payment, while deposits and refunds do not count as rent collected. Existing profile balances are migrated into opening ledger deposits. Printable payment receipts show `HOSTEL_NAME` (defaults to `Hostel Desk`) and optional `HOSTEL_ADDRESS` and `HOSTEL_PHONE` values from `.env`; enter the real hostel details there if they should appear.

### Reports

Staff in Owner, Manager, or Warden groups can open `/reports/` for filtered report totals and operational CSV downloads. Residents and room occupancy exports are available to all three roles; monthly charges, payments, and advance ledger exports are restricted to Owners and Managers. Exports include only the fields needed for operations and reconciliation; user-input text is CSV-quoted and protected against spreadsheet formula execution.

### Hostel settings and audit history

Owners can update hostel name, address, phone numbers, email, and receipt text at `/workspace/settings/` or in Django admin. Payment receipts read these values from the database. Owners and Managers can filter staff audit entries at `/workspace/audit/`; entries record the actor, action, affected record, timestamp, and changed field names only. Field contents such as passwords, document data, or notes are not copied into the log.

## Environment variable loading and secrets

The project loads variables from the project-root `.env` file. `.env.example` contains placeholders only, and `.env` is ignored by Git. Never share or commit your real database password or Django secret key. `DJANGO_DEBUG` must be disabled and `DJANGO_ALLOWED_HOSTS` configured for deployment.

## Project layout

- `config/`: project settings and ASGI/WSGI entry points
- `core/`: dashboard app and URL routes
- `templates/`: shared layout, dashboard, and authentication templates
- `static/`: CSS and vanilla JavaScript