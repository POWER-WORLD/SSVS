# Student Score View System (SSVS)

**Student Score View System (SSVS)** is an enterprise-ready, production-grade academic assessment and student competitive programming evaluation platform built with **Python, Flask, SQLAlchemy, Jinja2, Bootstrap 5, Chart.js, and OpenPyXL**.

It allows university faculty and placement cells to create dynamic evaluation forms, collect student academic and competitive coding handles, automatically extract statistics across platforms (LeetCode, CodeChef, Codeforces, GitHub, HackerRank, GeeksforGeeks), compute normalized performance scores using customizable mathematical formulas, display interactive live leaderboards with medal podiums, and generate executive multi-sheet Excel reports.

---

## Key Features

1. **Teacher-Authenticated, Student Zero-Login Workflow**:
   - **Teachers**: Register, create unlimited assessment forms, customize scoring formulas, view submissions, monitor live analytics, and export Excel reports.
   - **Students**: Never register or log in. Students access public form links or QR codes, submit their academic details and coding profiles, and track their score and cohort rank in real time.
2. **Dynamic Visual Form Builder**:
   - Visual drag-and-drop palette (Text, Textarea, Email, Number, Dropdown, File Upload, LeetCode, CodeChef, GitHub, etc.).
   - Dynamic field ordering, section dividers, validation rules (min/max, regex, required), and direct metric bindings.
   - Form publishing controls: unique URL, QR code generator, submission deadlines, response caps, duplicate roll-number/email prevention, and public leaderboard toggles.
- **Platforms Supported**: LeetCode, CodeChef, Codeforces, GitHub, HackerRank, GeeksforGeeks, **AtCoder**, **InterviewBit**, and **Kaggle**.
- **Granular Custom Excel Export**: Download only selected rows and columns with custom formatting, frozen headers, and auto-sized columns.
- **Faculty Data Editing & Moderation**: Teachers can edit submitted records, fix typos in handles, assign verification statuses (**Verified**, **Shortlisted**, **Flagged**), add remarks, and apply manual score adjustments.
- **Candidate Head-to-Head Comparison**: Compare 2 to 5 candidates side-by-side with an interactive Chart.js **Skill Radar Chart** and benchmark metrics.
- **Batch Operations**: Bulk shortlist, verify, flag, recalculate scores, or delete candidates.
- **Integrity & Plagiarism Alert**: Automatic detection of duplicate profile handles and roll numbers.

---

## Technology Stack

- **Backend**: Python 3.13, Flask 3.1, Flask-SQLAlchemy 3.1, Flask-Login 0.6, Flask-Migrate 4.1, Flask-WTF 1.3, WTForms 3.2, Pydantic 2.13
- **Database**: PostgreSQL (Neon Cloud Serverless) & SQLite (local fallback)
- **Frontend**: HTML5, Bootstrap 5.3, Jinja2, Vanilla JavaScript, Chart.js
- **Excel & Analytics**: OpenPyXL, Pandas
- **Extraction & Networking**: Requests, BeautifulSoup4, QRCode, Pillow

---

## Directory Structure

```
d:/Agents/SSVS/
├── app/
│   ├── __init__.py                # Flask application factory
│   ├── config.py                  # Configuration loader (.env, PostgreSQL / SQLite)
│   ├── models/
│   │   ├── __init__.py            # DB extensions & User loader
│   │   ├── user.py                # Teacher model (password hashing & profiles)
│   │   ├── form.py                # Form, FormField, FieldOption models
│   │   ├── submission.py          # Submission & SubmissionValue models
│   │   ├── platform_profile.py    # Extracted stats model
│   │   ├── scoring.py             # ScoreFormula, FormulaRule, CalculatedScore, LeaderboardEntry
│   │   └── audit.py               # ActivityLog model
│   ├── auth/                      # Teacher registration, login, logout, profile
│   ├── dashboard/                 # Faculty overview, KPI cards, recent feeds
│   ├── forms_mgr/                 # Form CRUD, drag-and-drop builder, QR codes, settings
│   ├── student/                   # Zero-auth public forms, status tracker, public leaderboard
│   ├── scoring_engine/            # Formula evaluator, normalizer, default presets
│   ├── extractors/                # LeetCode, CodeChef, Codeforces, GitHub, HackerRank extractors
│   ├── analytics/                 # Chart.js analytics dashboard & Excel export
│   ├── export/                    # Multi-sheet OpenPyXL report generator
│   ├── api/                       # REST APIs for async builder save, status polling & tester
│   ├── static/                    # CSS design system, JS form builder & status trackers
│   └── templates/                 # Jinja2 templates (SaaS layout, dark/light themes)
├── tests/
│   └── test_ssvs.py               # Automated unit & integration tests
├── .env                           # Environment variables (Neon PostgreSQL connection string)
├── requirements.txt               # Pinned dependencies
├── seed_data.py                   # Realistic 25-student cohort seeder
└── run.py                         # Application runner
```

---

## Quick Start Guide

### 1. Environment Setup
```bash
# Clone or navigate to the directory
cd d:/Agents/SSVS

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Configuration
The application automatically reads `DATABASE_URL` from `.env`.
To use PostgreSQL (Neon, Supabase, AWS RDS, etc.):
```env
DATABASE_URL=postgresql://<username>:<password>@<host>/<database>?sslmode=require
SECRET_KEY=your-production-secret-key-here
```
Or for local SQLite development, leave `DATABASE_URL` blank or set:
```env
DATABASE_URL=sqlite:///instance/ssvs_dev.db
```

### 3. Optional: Seed Sample Demo Cohort (Local Development Only)
```bash
python seed_data.py
```
This sets up a sample faculty account and 25 student records for local interface demonstration.

### 4. Run Application Server
```bash
python run.py
```
Open your browser at:
- **Landing Page**: `http://localhost:5000/`
- **Live Leaderboard**: `http://localhost:5000/leaderboard/iitd-cse-placement-2026`
- **Student Public Form**: `http://localhost:5000/f/iitd-cse-placement-2026`
- **Faculty Login**: `http://localhost:5000/auth/login` (Use **Quick Fill** button)
- **Analytics Dashboard**: `http://localhost:5000/analytics/1`
- **Form Builder**: `http://localhost:5000/forms/1/builder`

### 5. Running Automated Tests
```bash
python -m unittest tests/test_ssvs.py
```
All tests verify authentication, URL regex parsing, deterministic simulation, scoring formulas, normalizer calculations, Excel export sheets, and public accessibility.
