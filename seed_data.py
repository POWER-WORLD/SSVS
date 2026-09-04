import sys
from app import create_app
from app.models import db
from app.models.user import Teacher
from app.models.form import Form, FormField, FieldOption
from app.models.submission import Submission
from app.models.platform_profile import PlatformProfile
from app.models.scoring import ScoreFormula, FormulaRule, CalculatedScore, LeaderboardEntry
from app.models.audit import ActivityLog
from app.scoring_engine.default_presets import DEFAULT_PRESETS
from app.scoring_engine.formula_evaluator import FormulaEvaluator
from app.extractors.mock_simulator import MockSimulator

def seed():
    app = create_app('development')
    with app.app_context():
        print("Starting seed on:", db.engine.url, flush=True)

        # Truncate tables with CASCADE for lightning fast clean state in Postgres
        if 'postgresql' in str(db.engine.url):
            with db.engine.connect() as conn:
                conn.execute(db.text("TRUNCATE TABLE leaderboard_cache, calculated_scores, platform_profiles, submission_values, submissions, formula_rules, score_formulas, field_options, form_fields, forms, activity_logs, teachers RESTART IDENTITY CASCADE;"))
                conn.commit()
            print("PostgreSQL tables truncated.", flush=True)
        else:
            db.drop_all()
            db.create_all()

        # 1. Create Teacher
        teacher = Teacher(
            email='teacher@ssvs.edu',
            full_name='Dr. Ramesh K. Sharma',
            college_name='Indian Institute of Technology, Delhi',
            department='Computer Science & Engineering',
            designation='Professor & Head of Placements',
            phone='+91 98765 43210',
            avatar_url='https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&auto=format&fit=crop&q=80'
        )
        pwd = os.environ.get('DEFAULT_TEACHER_PASSWORD', 'SecureFacultyPass#2026')
        teacher.set_password(pwd)
        db.session.add(teacher)
        db.session.flush()
        print("Teacher created.", flush=True)

        # 2. Create Assessment Form
        form = Form(
            teacher_id=teacher.id,
            title='Campus Placement 2026 — Technical & Coding Evaluation',
            slug='iitd-cse-placement-2026',
            description='Mandatory technical assessment and coding profile evaluation for final year engineering students appearing for Tier-1 software engineering drives.',
            instructions='Ensure all competitive programming profile handles are publicly accessible. Your statistics will be extracted in real time to generate your technical index score.',
            theme_color='#4f46e5',
            is_published=True,
            is_closed=False,
            one_per_roll=True,
            one_per_email=True,
            enable_leaderboard=True,
            is_public=True
        )
        db.session.add(form)
        db.session.flush()
        print("Form created with slug:", form.slug, flush=True)

        # Form Fields
        field_configs = [
            ('student_name', 'Student Full Name', 'text', True, 1, 'student_name', 'Personal Information', 'e.g. Aarav Sharma', None),
            ('roll_number', 'College Roll Number / ID', 'text', True, 2, 'roll_number', 'Personal Information', 'e.g. 2022CSB101', None),
            ('email', 'Official University Email', 'email', True, 3, 'email', 'Personal Information', 'aarav.sharma@iitd.ac.in', None),
            ('department', 'Engineering Department', 'dropdown', True, 4, 'department', 'Academic Background', None, ['Computer Science & Engineering', 'Information Technology', 'Electronics & Comm. Engineering', 'Electrical Engineering']),
            ('cgpa', 'Cumulative GPA (Scale of 10.0)', 'decimal', True, 5, 'cgpa', 'Academic Background', 'e.g. 8.85', None),
            ('backlogs', 'Number of Active Backlogs', 'number', True, 6, 'backlogs', 'Academic Background', '0', None),
            ('leetcode_handle', 'LeetCode Username or Profile URL', 'url', True, 7, 'leetcode_handle', 'Competitive Coding Profiles', 'https://leetcode.com/u/coder_aarav/', None),
            ('codechef_handle', 'CodeChef Username or Profile URL', 'url', False, 8, 'codechef_handle', 'Competitive Coding Profiles', 'https://www.codechef.com/users/aarav_cc', None),
            ('codeforces_handle', 'Codeforces Handle (Optional)', 'text', False, 9, 'codeforces_handle', 'Competitive Coding Profiles', 'aarav_cf', None),
            ('github_handle', 'GitHub Profile URL or Username', 'url', False, 10, 'github_handle', 'Development & Open Source', 'https://github.com/aaravsharma', None),
            ('hackerrank_handle', 'HackerRank Profile URL (Optional)', 'url', False, 11, 'hackerrank_handle', 'Development & Open Source', 'hackerrank.com/aarav_hr', None)
        ]

        for key, label, ftype, req, order, bind, sec, ph, opts in field_configs:
            f = FormField(
                form_id=form.id,
                field_key=key,
                label=label,
                field_type=ftype,
                is_required=req,
                display_order=order,
                platform_metric_binding=bind,
                section_title=sec,
                placeholder=ph
            )
            db.session.add(f)
            db.session.flush()
            if opts:
                for idx, opt_text in enumerate(opts):
                    db.session.add(FieldOption(
                        field_id=f.id,
                        label=opt_text,
                        value=opt_text,
                        display_order=idx
                    ))

        # 3. Create Scoring Formula
        std_preset = DEFAULT_PRESETS['standard_placement']
        formula = ScoreFormula(
            form_id=form.id,
            name=std_preset['name'],
            description=std_preset['description'],
            normalization_method=std_preset['normalization_method'],
            max_total_marks=std_preset['max_total_marks'],
            is_active=True
        )
        db.session.add(formula)
        db.session.flush()

        for r in std_preset['rules']:
            rule = FormulaRule(
                formula_id=formula.id,
                metric_key=r['metric_key'],
                display_label=r['display_label'],
                weight_percentage=r.get('weight_percentage', 10.0),
                max_marks=r.get('max_marks', 10.0),
                multiplier=r.get('multiplier', 1.0),
                penalty_per_unit=r.get('penalty_per_unit', 0.0),
                bonus_threshold=r.get('bonus_threshold', 0.0),
                bonus_marks=r.get('bonus_marks', 0.0),
                category=r.get('category', 'coding')
            )
            db.session.add(rule)

        # 4. Generate 25 Realistic Student Submissions
        student_data = [
            ("Aarav Sharma", "2022CSB101", "Computer Science & Engineering", 9.65, 0, "aarav_algo", "aarav_cc", "aarav_cf", "aaravdev"),
            ("Ananya Verma", "2022CSB102", "Computer Science & Engineering", 9.45, 0, "ananya_code", "ananya_chef", "ananya_cf", "ananya-v"),
            ("Rohan Iyer", "2022CSB103", "Computer Science & Engineering", 9.20, 0, "rohaniyer_cp", "rohan_i", "rohan_cf", "rohaniyer"),
            ("Priya Patel", "2022CSB104", "Information Technology", 9.10, 0, "priya_leetcode", "priya_p", "priyacp", "priyapatel-code"),
            ("Siddharth Malhotra", "2022CSB105", "Information Technology", 8.85, 0, "sid_m", "sid_coder", "sid_force", "sidmalhotra"),
            ("Tanvi Gupta", "2022CSB106", "Computer Science & Engineering", 8.95, 0, "tanvi_g", "tanvi_cc", "tanvicf", "tanvigupta"),
            ("Aditya Nair", "2022CSB107", "Computer Science & Engineering", 8.60, 0, "adityanair_01", "aditya_chef", "aditya_cf", "adityanair"),
            ("Vikram Chauhan", "2022CSB108", "Electronics & Comm. Engineering", 8.40, 1, "vikram_cp", "vikram_cc", "vikram_cf", "vikramc"),
            ("Neha Reddy", "2022CSB109", "Computer Science & Engineering", 8.75, 0, "neha_reddy", "neha_cc", "neha_cf", "nehareddy"),
            ("Devansh Joshi", "2022CSB110", "Information Technology", 8.30, 0, "devansh_j", "devansh_chef", "devansh_cf", "devanshj"),
            ("Ishita Sengupta", "2022CSB111", "Computer Science & Engineering", 9.05, 0, "ishita_sg", "ishita_cc", "ishitacf", "ishitasg"),
            ("Karthik Raman", "2022CSB112", "Electrical Engineering", 8.15, 0, "karthik_r", "karthik_cc", "karthik_cf", "karthikr"),
            ("Sanya Kapoor", "2022CSB113", "Information Technology", 8.50, 0, "sanya_k", "sanya_chef", "sanyacf", "sanyakapoor"),
            ("Arjun Pillai", "2022CSB114", "Computer Science & Engineering", 8.90, 0, "arjun_pillai", "arjun_cc", "arjun_cf", "arjunpillai"),
            ("Riya Mukherjee", "2022CSB115", "Computer Science & Engineering", 8.70, 0, "riya_m", "riya_cc", "riyacf", "riyamukherjee"),
            ("Varun Deshmukh", "2022CSB116", "Electronics & Comm. Engineering", 7.90, 0, "varun_d", "varun_cc", "varuncf", "varundeshmukh"),
            ("Sneha Kulkarni", "2022CSB117", "Information Technology", 8.40, 0, "sneha_k", "sneha_chef", "snehacf", "snehak"),
            ("Rahul Saxena", "2022CSB118", "Computer Science & Engineering", 7.80, 2, "rahul_saxena", "rahul_cc", "rahulcf", "rahulsaxena"),
            ("Meera Nambiar", "2022CSB119", "Computer Science & Engineering", 9.15, 0, "meera_n", "meera_cc", "meeracf", "meeranambiar"),
            ("Harshvardhan Rao", "2022CSB120", "Information Technology", 8.25, 0, "harsh_rao", "harsh_cc", "harshcf", "harshrao"),
            ("Pooja Chawla", "2022CSB121", "Computer Science & Engineering", 8.65, 0, "pooja_c", "pooja_chef", "poojacf", "poojachawla"),
            ("Yash Singhania", "2022CSB122", "Electrical Engineering", 7.60, 1, "yash_s", "yash_cc", "yashcf", "yashs"),
            ("Divya Bansal", "2022CSB123", "Computer Science & Engineering", 9.30, 0, "divya_b", "divya_cc", "divyacf", "divyabansal"),
            ("Akash Choudhary", "2022CSB124", "Information Technology", 8.05, 0, "akash_c", "akash_cc", "akashcf", "akashc"),
            ("Shreya Menon", "2022CSB125", "Computer Science & Engineering", 8.80, 0, "shreya_m", "shreya_chef", "shreyacf", "shreyamenon")
        ]

        submissions_to_add = []
        for s_name, s_roll, s_dept, s_cgpa, s_backlogs, lc_u, cc_u, cf_u, gh_u in student_data:
            s_email = f"{s_name.lower().replace(' ', '.')}@iitd.ac.in"
            sub = Submission(
                form_id=form.id,
                student_name=s_name,
                roll_number=s_roll,
                email=s_email,
                department=s_dept,
                semester='6',
                batch='2026',
                cgpa=s_cgpa,
                backlogs=s_backlogs,
                status='completed'
            )
            db.session.add(sub)
            submissions_to_add.append((sub, lc_u, cc_u, cf_u, gh_u))

        db.session.flush()

        for sub, lc_u, cc_u, cf_u, gh_u in submissions_to_add:
            # Generate realistic platform stats
            lc_stats = MockSimulator.simulate_leetcode(lc_u)
            cc_stats = MockSimulator.simulate_codechef(cc_u)
            cf_stats = MockSimulator.simulate_codeforces(cf_u)
            gh_stats = MockSimulator.simulate_github(gh_u)
            hr_stats = MockSimulator.simulate_hackerrank(lc_u)

            db.session.add(PlatformProfile(
                submission_id=sub.id,
                platform_name='leetcode',
                username=lc_stats.username,
                profile_url=lc_stats.profile_url,
                avatar_url=lc_stats.avatar_url,
                problems_solved=lc_stats.total_solved,
                contest_rating=lc_stats.contest_rating,
                global_rank=lc_stats.global_rank,
                stars_or_badges=lc_stats.badges_count,
                raw_data={
                    'total_solved': lc_stats.total_solved,
                    'easy_solved': lc_stats.easy_solved,
                    'medium_solved': lc_stats.medium_solved,
                    'hard_solved': lc_stats.hard_solved,
                    'contest_rating': lc_stats.contest_rating,
                    'acceptance_rate': lc_stats.acceptance_rate,
                    'badges_count': lc_stats.badges_count
                },
                extraction_status='success'
            ))

            db.session.add(PlatformProfile(
                submission_id=sub.id,
                platform_name='codechef',
                username=cc_stats.username,
                profile_url=cc_stats.profile_url,
                avatar_url=cc_stats.avatar_url,
                problems_solved=cc_stats.problems_solved,
                contest_rating=float(cc_stats.current_rating),
                highest_rating=float(cc_stats.highest_rating),
                global_rank=cc_stats.global_rank,
                stars_or_badges=cc_stats.stars,
                raw_data={
                    'current_rating': cc_stats.current_rating,
                    'highest_rating': cc_stats.highest_rating,
                    'stars': cc_stats.stars,
                    'global_rank': cc_stats.global_rank,
                    'problems_solved': cc_stats.problems_solved
                },
                extraction_status='success'
            ))

            db.session.add(PlatformProfile(
                submission_id=sub.id,
                platform_name='codeforces',
                username=cf_stats.username,
                profile_url=cf_stats.profile_url,
                avatar_url=cf_stats.avatar_url,
                problems_solved=cf_stats.problems_solved,
                contest_rating=float(cf_stats.rating),
                highest_rating=float(cf_stats.max_rating),
                stars_or_badges=1 if cf_stats.rating > 1400 else 0,
                raw_data={
                    'rating': cf_stats.rating,
                    'max_rating': cf_stats.max_rating,
                    'rank': cf_stats.rank,
                    'problems_solved': cf_stats.problems_solved
                },
                extraction_status='success'
            ))

            db.session.add(PlatformProfile(
                submission_id=sub.id,
                platform_name='github',
                username=gh_stats.username,
                profile_url=gh_stats.profile_url,
                avatar_url=gh_stats.avatar_url,
                problems_solved=gh_stats.public_repos,
                contest_rating=float(gh_stats.contributions_year),
                stars_or_badges=gh_stats.stars_earned,
                raw_data={
                    'public_repos': gh_stats.public_repos,
                    'stars_earned': gh_stats.stars_earned,
                    'followers': gh_stats.followers,
                    'contributions_year': gh_stats.contributions_year
                },
                extraction_status='success'
            ))

            db.session.add(PlatformProfile(
                submission_id=sub.id,
                platform_name='hackerrank',
                username=hr_stats.username,
                profile_url=hr_stats.profile_url,
                avatar_url=hr_stats.avatar_url,
                problems_solved=hr_stats.problems_solved,
                stars_or_badges=hr_stats.badges_count,
                raw_data={
                    'badges_count': hr_stats.badges_count,
                    'stars_count': hr_stats.stars_count,
                    'certificates_count': hr_stats.certificates_count
                },
                extraction_status='success'
            ))

        db.session.commit()
        print("Submissions and profiles committed. Calculating ranks...", flush=True)

        # 5. Evaluate all scores and generate leaderboard
        FormulaEvaluator.update_form_ranks_and_leaderboard(form.id)

        # Log action
        db.session.add(ActivityLog(
            teacher_id=teacher.id,
            action='SEED_DATA',
            description='Initialized demo cohort with 25 student evaluations and live leaderboard',
            ip_address='127.0.0.1'
        ))
        db.session.commit()

        print("Seeding complete! 25 students scored and ranked on database.", flush=True)
        print(f"Teacher Login: {teacher.email}", flush=True)
        print(f"Form Slug: {form.slug}", flush=True)

if __name__ == '__main__':
    seed()
