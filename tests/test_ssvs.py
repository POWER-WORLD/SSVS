import os
import unittest
from app import create_app
from app.models import db
from app.models.user import Teacher
from app.models.form import Form, FormField, FieldOption
from app.models.submission import Submission
from app.models.scoring import ScoreFormula, FormulaRule
from app.extractors.base import BaseExtractor
from app.extractors.mock_simulator import MockSimulator
from app.scoring_engine.formula_evaluator import FormulaEvaluator
from app.scoring_engine.normalizer import Normalizer
from app.export.excel_exporter import ExcelExporter
import openpyxl

class SSVSTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        db.create_all()

        # Seed test teacher
        self.teacher = Teacher(
            email='test@ssvs.edu',
            full_name='Dr. Test Evaluator',
            college_name='Testing Institute of Technology',
            department='Computer Science'
        )
        self.teacher.set_password('SecretPass123!')
        db.session.add(self.teacher)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_teacher_password_hashing(self):
        """Verify password hashing and verification."""
        self.assertTrue(self.teacher.check_password('SecretPass123!'))
        self.assertFalse(self.teacher.check_password('WrongPassword'))

    def test_url_extractor_parsing(self):
        """Verify regex parsing of platform profile URLs."""
        # LeetCode
        self.assertEqual(BaseExtractor.extract_username('https://leetcode.com/u/neal_wu/', 'leetcode'), 'neal_wu')
        self.assertEqual(BaseExtractor.extract_username('leetcode.com/john_doe', 'leetcode'), 'john_doe')
        self.assertEqual(BaseExtractor.extract_username('plain_user', 'leetcode'), 'plain_user')
        
        # Codeforces
        self.assertEqual(BaseExtractor.extract_username('https://codeforces.com/profile/tourist', 'codeforces'), 'tourist')
        
        # GitHub
        self.assertEqual(BaseExtractor.extract_username('https://github.com/octocat/', 'github'), 'octocat')
        
        # CodeChef
        self.assertEqual(BaseExtractor.extract_username('https://www.codechef.com/users/chef_pro', 'codechef'), 'chef_pro')

    def test_mock_simulator_determinism(self):
        """Verify simulator produces consistent realistic metrics for identical usernames."""
        s1 = MockSimulator.simulate_leetcode('neal_wu')
        s2 = MockSimulator.simulate_leetcode('neal_wu')
        self.assertEqual(s1.total_solved, s2.total_solved)
        self.assertEqual(s1.contest_rating, s2.contest_rating)
        self.assertGreater(s1.total_solved, 0)
        self.assertGreater(s1.contest_rating, 1000)

    def test_scoring_formula_and_penalties(self):
        """Verify weighted formula scoring, bonus rules, and backlog penalties."""
        form = Form(
            teacher_id=self.teacher.id,
            title='Test Assessment',
            slug='test-assessment-slug',
            is_published=True
        )
        db.session.add(form)
        db.session.flush()

        formula = ScoreFormula(
            form_id=form.id,
            name='Test Formula',
            max_total_marks=100.0,
            is_active=True
        )
        db.session.add(formula)
        db.session.flush()

        # CGPA: 10 CGPA = 30 marks
        db.session.add(FormulaRule(
            formula_id=formula.id,
            metric_key='cgpa',
            display_label='Academic CGPA',
            weight_percentage=30.0,
            max_marks=30.0,
            multiplier=3.0,
            category='academic'
        ))

        # Backlogs: -5 marks per backlog
        db.session.add(FormulaRule(
            formula_id=formula.id,
            metric_key='backlogs_penalty',
            display_label='Backlogs Penalty',
            weight_percentage=0.0,
            max_marks=0.0,
            penalty_per_unit=5.0,
            category='penalty'
        ))
        db.session.commit()

        # Create submission with CGPA 9.0 and 2 backlogs:
        # Earned = 9.0 * 3.0 = 27.0
        # Deduction = 2 * 5.0 = 10.0
        # Expected total = 17.0
        sub = Submission(
            form_id=form.id,
            student_name='Test Student',
            roll_number='2026TEST01',
            email='student@test.edu',
            cgpa=9.0,
            backlogs=2,
            status='completed'
        )
        db.session.add(sub)
        db.session.commit()

        calc = FormulaEvaluator.evaluate_submission(sub, formula)
        self.assertEqual(calc.academic_score, 27.0)
        self.assertEqual(calc.penalty_deductions, 10.0)
        self.assertEqual(calc.total_score, 17.0)

    def test_normalizer(self):
        """Verify min-max and percentile calculations."""
        scaled = Normalizer.min_max(75, 50, 100, 0, 100)
        self.assertEqual(scaled, 50.0)

        scores = [10.0, 20.0, 30.0, 40.0, 50.0]
        percentiles = Normalizer.calculate_percentiles(scores)
        self.assertEqual(len(percentiles), 5)
        self.assertGreater(percentiles[-1], percentiles[0])

    def test_excel_exporter(self):
        """Verify Excel workbook creates all 4 required sheets with valid structure."""
        form = Form(
            teacher_id=self.teacher.id,
            title='Campus Placement Test Drive',
            slug='test-drive-slug',
            is_published=True
        )
        db.session.add(form)
        db.session.flush()

        sub = Submission(
            form_id=form.id,
            student_name='Sample Candidate',
            roll_number='ROLL001',
            email='sample@college.edu',
            cgpa=8.5,
            backlogs=0
        )
        db.session.add(sub)
        db.session.commit()

        FormulaEvaluator.update_form_ranks_and_leaderboard(form.id)

        stream = ExcelExporter.generate_form_report(form)
        self.assertIsNotNone(stream)

        # Inspect workbook
        wb = openpyxl.load_workbook(stream)
        sheet_names = wb.sheetnames
        self.assertIn("Leaderboard & Ranks", sheet_names)
        self.assertIn("Raw Submissions", sheet_names)
        self.assertIn("Coding Platform Stats", sheet_names)
        self.assertIn("Executive Analytics", sheet_names)

    def test_public_pages_accessible_without_login(self):
        """Verify student zero-login accessibility for public endpoints."""
        resp = self.client.get('/leaderboard')
        self.assertEqual(resp.status_code, 200)

        form = Form(
            teacher_id=self.teacher.id,
            title='Open Form',
            slug='open-form-slug',
            is_published=True
        )
        db.session.add(form)
        db.session.commit()

        resp = self.client.get(f'/f/{form.slug}')
        self.assertEqual(resp.status_code, 200)

    def test_new_platform_extractors(self):
        """Verify URL parsing and mock simulation for AtCoder, InterviewBit, and Kaggle."""
        # URL Parsing
        self.assertEqual(BaseExtractor.extract_username('https://atcoder.jp/users/chokudai', 'atcoder'), 'chokudai')
        self.assertEqual(BaseExtractor.extract_username('https://www.interviewbit.com/profile/ib_coder_99', 'interviewbit'), 'ib_coder_99')
        self.assertEqual(BaseExtractor.extract_username('https://www.kaggle.com/data_wizard', 'kaggle'), 'data_wizard')

        # Mock simulation
        atc = MockSimulator.simulate_atcoder('chokudai')
        self.assertGreater(atc.current_rating, 0)
        self.assertIn(atc.tier_color, ['White', 'Brown', 'Green', 'Cyan', 'Blue', 'Yellow'])

        ib = MockSimulator.simulate_interviewbit('ib_coder_99')
        self.assertGreater(ib.score, 0)

        kg = MockSimulator.simulate_kaggle('data_wizard')
        self.assertGreater(kg.total_medals, 0)
        self.assertIn(kg.tier, ['Novice', 'Contributor', 'Expert', 'Master', 'Grandmaster'])

    def test_custom_excel_export_rows_and_columns(self):
        """Verify custom Excel export contains ONLY chosen columns and rows."""
        form = Form(
            teacher_id=self.teacher.id,
            title='Custom Export Test Drive',
            slug='custom-export-slug',
            is_published=True
        )
        db.session.add(form)
        db.session.flush()

        s1 = Submission(form_id=form.id, student_name='Alpha One', roll_number='R001', email='alpha@test.edu', cgpa=9.2)
        s2 = Submission(form_id=form.id, student_name='Beta Two', roll_number='R002', email='beta@test.edu', cgpa=8.4)
        s3 = Submission(form_id=form.id, student_name='Gamma Three', roll_number='R003', email='gamma@test.edu', cgpa=7.8)
        db.session.add_all([s1, s2, s3])
        db.session.commit()

        FormulaEvaluator.update_form_ranks_and_leaderboard(form.id)

        # Export only s1 and s2, with columns ['student_name', 'roll_number', 'cgpa']
        stream = ExcelExporter.generate_custom_export(
            form=form,
            submission_ids=[s1.id, s2.id],
            column_keys=['student_name', 'roll_number', 'cgpa']
        )
        self.assertIsNotNone(stream)

        wb = openpyxl.load_workbook(stream)
        ws = wb.active
        self.assertEqual(ws.title, "Custom Export")
        
        # Row 3 should be column headers: Student Name, Roll Number, CGPA
        header_vals = [ws.cell(row=3, column=c).value for c in range(1, 4)]
        self.assertEqual(header_vals, ["Student Name", "Roll Number", "CGPA"])
        
        # Row 4 and Row 5 are the 2 data rows
        # Check that only 2 data rows exist
        self.assertEqual(ws.max_row, 5)

    def test_teacher_edit_submission_and_manual_adjustment(self):
        """Verify teacher editing student data and manual score adjustments."""
        form = Form(
            teacher_id=self.teacher.id,
            title='Placement Assessment',
            slug='placement-assessment',
            is_published=True
        )
        db.session.add(form)
        db.session.flush()

        formula = ScoreFormula(form_id=form.id, name='Simple Formula', is_active=True, max_total_marks=100.0)
        db.session.add(formula)
        db.session.flush()
        db.session.add(FormulaRule(formula_id=formula.id, metric_key='cgpa', display_label='CGPA', weight_percentage=100.0, max_marks=100.0, multiplier=10.0, category='academic'))
        db.session.commit()

        sub = Submission(form_id=form.id, student_name='Candidate A', roll_number='R100', email='cand@test.edu', cgpa=8.0)
        db.session.add(sub)
        db.session.commit()

        # Initial calculation: 8.0 * 10 = 80.0
        calc = FormulaEvaluator.evaluate_submission(sub, formula)
        self.assertEqual(calc.total_score, 80.0)

        # Teacher modifies student data and adds +5 manual score adjustment
        sub.cgpa = 8.5
        sub.manual_score_adjustment = 5.0
        sub.verification_status = 'shortlisted'
        sub.teacher_remarks = 'Excellent interview performance'
        db.session.commit()

        # Recalculate: (8.5 * 10) + 5.0 = 90.0
        calc_updated = FormulaEvaluator.evaluate_submission(sub, formula)
        self.assertEqual(calc_updated.total_score, 90.0)
        self.assertEqual(sub.verification_status, 'shortlisted')

    def test_scorecard_certificate_endpoint(self):
        """Verify student official single-page scorecard/certificate rendering."""
        form = Form(
            teacher_id=self.teacher.id,
            title='Scorecard Certification Form',
            slug='scorecard-cert-slug',
            is_published=True
        )
        db.session.add(form)
        db.session.flush()

        formula = ScoreFormula(form_id=form.id, name='Placement Metric', is_active=True, max_total_marks=100.0)
        db.session.add(formula)
        db.session.flush()

        sub = Submission(
            form_id=form.id,
            student_name='Dev Sharma',
            roll_number='CS2026-99',
            email='dev@college.edu',
            department='CSE',
            cgpa=9.5,
            backlogs=0,
            status='completed'
        )
        db.session.add(sub)
        db.session.commit()

        calc = FormulaEvaluator.evaluate_submission(sub, formula)

        resp = self.client.get(f'/submission/{sub.uuid}/scorecard')
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn('Dev Sharma', html)
        self.assertIn('CS2026-99', html)
        self.assertIn('Print Scorecard', html)
        self.assertIn('data:image/png;base64,', html)
        self.assertIn('Official Performance Scorecard', html)

if __name__ == '__main__':
    unittest.main()

