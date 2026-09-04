from typing import Dict, Any, List, Optional
from app.models.scoring import ScoreFormula, FormulaRule, CalculatedScore, LeaderboardEntry
from app.models.submission import Submission
from app.models.platform_profile import PlatformProfile
from app.models import db
from .normalizer import Normalizer

class FormulaEvaluator:
    """Evaluates student scores based on formula rules and platform metrics."""

    @staticmethod
    def extract_metric_values(submission: Submission) -> Dict[str, float]:
        """Flatten submission values and platform profiles into a numeric metrics dictionary."""
        metrics: Dict[str, float] = {
            'cgpa': float(submission.cgpa or 0.0),
            'backlogs': float(submission.backlogs or 0),
            'backlogs_penalty': float(submission.backlogs or 0),
            'leetcode_solved': 0.0,
            'leetcode_rating': 0.0,
            'leetcode_hard': 0.0,
            'codechef_rating': 0.0,
            'codechef_stars': 0.0,
            'codeforces_rating': 0.0,
            'github_repos': 0.0,
            'github_stars': 0.0,
            'github_stars_repos': 0.0,
            'github_contributions': 0.0,
            'hackerrank_badges': 0.0,
            'gfg_problems': 0.0,
            'gfg_score': 0.0
        }

        # Inspect extracted platform profiles
        for profile in submission.platform_profiles.all():
            p_name = profile.platform_name.lower()
            raw = profile.raw_data or {}
            
            if p_name == 'leetcode':
                metrics['leetcode_solved'] = float(profile.problems_solved or raw.get('total_solved', 0))
                metrics['leetcode_rating'] = float(profile.contest_rating or raw.get('contest_rating', 0.0))
                metrics['leetcode_hard'] = float(raw.get('hard_solved', 0))
            elif p_name == 'codechef':
                metrics['codechef_rating'] = float(profile.contest_rating or raw.get('current_rating', 0))
                metrics['codechef_stars'] = float(profile.stars_or_badges or raw.get('stars', 0))
            elif p_name == 'codeforces':
                metrics['codeforces_rating'] = float(profile.contest_rating or raw.get('rating', 0))
            elif p_name == 'github':
                repos = float(raw.get('public_repos', 0))
                stars = float(raw.get('stars_earned', 0))
                metrics['github_repos'] = repos
                metrics['github_stars'] = stars
                metrics['github_stars_repos'] = repos * 0.8 + stars * 1.5
                metrics['github_contributions'] = float(raw.get('contributions_year', 0))
            elif p_name == 'hackerrank':
                metrics['hackerrank_badges'] = float(profile.stars_or_badges or raw.get('badges_count', 0))
            elif p_name in ('gfg', 'geeksforgeeks'):
                metrics['gfg_problems'] = float(profile.problems_solved or raw.get('problems_solved', 0))
                metrics['gfg_score'] = float(raw.get('coding_score', 0))
            elif p_name == 'atcoder':
                metrics['atcoder_rating'] = float(profile.contest_rating or raw.get('current_rating', 0))
                metrics['atcoder_highest'] = float(profile.highest_rating or raw.get('highest_rating', 0))
                metrics['atcoder_contests'] = float(raw.get('contests_attended', 0))
            elif p_name == 'interviewbit':
                metrics['interviewbit_score'] = float(raw.get('score', 0) or profile.contest_rating or 0)
                metrics['interviewbit_solved'] = float(profile.problems_solved or raw.get('problems_solved', 0))
            elif p_name == 'kaggle':
                metrics['kaggle_medals'] = float(profile.stars_or_badges or raw.get('total_medals', 0))
                metrics['kaggle_score'] = float(raw.get('competitions_count', 0) * 10 + raw.get('datasets_count', 0) * 5 + raw.get('notebooks_count', 0) * 5)

        return metrics

    @classmethod
    def evaluate_submission(cls, submission: Submission, formula: ScoreFormula) -> CalculatedScore:
        """Calculate score breakdown for a single submission using the given formula."""
        metrics = cls.extract_metric_values(submission)
        
        academic_score = 0.0
        coding_score = 0.0
        github_score = 0.0
        penalties = 0.0
        bonuses = 0.0
        
        breakdown = {}
        
        for rule in formula.rules.all():
            m_key = rule.metric_key
            raw_val = metrics.get(m_key, 0.0)
            rule_earned = 0.0
            
            if rule.category == 'penalty':
                # Penalties deduct marks
                deduction = raw_val * rule.penalty_per_unit
                penalties += deduction
                breakdown[m_key] = {
                    'label': rule.display_label,
                    'raw_value': raw_val,
                    'deduction': round(deduction, 2),
                    'category': 'penalty'
                }
                continue

            # Standard weighted score
            if rule.multiplier and rule.multiplier > 0:
                rule_earned = min(rule.max_marks, raw_val * rule.multiplier)
            else:
                rule_earned = min(rule.max_marks, (raw_val / 100.0) * rule.max_marks)

            # Bonus rule
            rule_bonus = 0.0
            if rule.bonus_threshold and raw_val >= rule.bonus_threshold:
                rule_bonus = rule.bonus_marks
                bonuses += rule_bonus

            total_rule_val = rule_earned + rule_bonus

            # Accumulate category subtotals
            if rule.category == 'academic':
                academic_score += total_rule_val
            elif rule.category == 'github':
                github_score += total_rule_val
            else:
                coding_score += total_rule_val

            breakdown[m_key] = {
                'label': rule.display_label,
                'raw_value': raw_val,
                'earned': round(rule_earned, 2),
                'bonus': round(rule_bonus, 2),
                'max_marks': rule.max_marks,
                'category': rule.category
            }

        # Calculate total score
        subtotal = academic_score + coding_score + github_score + bonuses - penalties
        
        # Apply teacher manual score adjustment if any
        manual_adj = getattr(submission, 'manual_score_adjustment', 0.0) or 0.0
        if manual_adj != 0.0:
            subtotal += manual_adj
            breakdown['teacher_adjustment'] = {
                'label': 'Teacher Manual Score Adjustment',
                'raw_value': manual_adj,
                'earned': round(manual_adj, 2),
                'bonus': 0.0,
                'max_marks': 0.0,
                'category': 'adjustment'
            }

        total = max(0.0, min(formula.max_total_marks, subtotal))

        # Assign letter grade
        if total >= 85:
            grade = 'A+'
        elif total >= 70:
            grade = 'A'
        elif total >= 55:
            grade = 'B'
        elif total >= 40:
            grade = 'C'
        else:
            grade = 'D'

        calc_score = CalculatedScore(
            submission_id=submission.id,
            formula_id=formula.id,
            total_score=round(total, 2),
            academic_score=round(academic_score, 2),
            coding_score=round(coding_score, 2),
            github_score=round(github_score, 2),
            penalty_deductions=round(penalties, 2),
            bonus_awarded=round(bonuses, 2),
            grade=grade,
            breakdown_json=breakdown
        )
        return calc_score

    @classmethod
    def update_form_ranks_and_leaderboard(cls, form_id: int):
        """Batch recalculates ranks, percentiles, and updates leaderboard cache for all submissions in a form."""
        submissions = Submission.query.filter_by(form_id=form_id).all()
        if not submissions:
            return

        # Fetch active formula
        formula = ScoreFormula.query.filter_by(form_id=form_id, is_active=True).first()
        if not formula:
            # Create standard default formula if none exists
            from .default_presets import DEFAULT_PRESETS
            std = DEFAULT_PRESETS['standard_placement']
            formula = ScoreFormula(
                form_id=form_id,
                name=std['name'],
                description=std['description'],
                normalization_method=std['normalization_method'],
                max_total_marks=std['max_total_marks'],
                is_active=True
            )
            db.session.add(formula)
            db.session.flush()
            for r in std['rules']:
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
            db.session.commit()

        # Clear old calculated scores and leaderboard cache for this form in 2 queries
        sub_ids = [s.id for s in submissions]
        CalculatedScore.query.filter(CalculatedScore.submission_id.in_(sub_ids)).delete(synchronize_session=False)
        LeaderboardEntry.query.filter_by(form_id=form_id).delete(synchronize_session=False)

        # Pre-fetch all profiles for all submissions to avoid N+1 queries
        all_profiles = PlatformProfile.query.filter(PlatformProfile.submission_id.in_(sub_ids)).all()
        profiles_by_sub = {}
        for p in all_profiles:
            profiles_by_sub.setdefault(p.submission_id, []).append(p)

        # Score all submissions
        scored_pairs = []
        for sub in submissions:
            metrics = {
                'cgpa': float(sub.cgpa or 0.0),
                'backlogs': float(sub.backlogs or 0),
                'backlogs_penalty': float(sub.backlogs or 0),
                'leetcode_solved': 0.0,
                'leetcode_rating': 0.0,
                'leetcode_hard': 0.0,
                'codechef_rating': 0.0,
                'codechef_stars': 0.0,
                'codeforces_rating': 0.0,
                'github_repos': 0.0,
                'github_stars': 0.0,
                'github_stars_repos': 0.0,
                'github_contributions': 0.0,
                'hackerrank_badges': 0.0,
                'gfg_problems': 0.0,
                'gfg_score': 0.0
            }

            sub_profs = profiles_by_sub.get(sub.id, [])
            for profile in sub_profs:
                p_name = profile.platform_name.lower()
                raw = profile.raw_data or {}
                if p_name == 'leetcode':
                    metrics['leetcode_solved'] = float(profile.problems_solved or raw.get('total_solved', 0))
                    metrics['leetcode_rating'] = float(profile.contest_rating or raw.get('contest_rating', 0.0))
                    metrics['leetcode_hard'] = float(raw.get('hard_solved', 0))
                elif p_name == 'codechef':
                    metrics['codechef_rating'] = float(profile.contest_rating or raw.get('current_rating', 0))
                    metrics['codechef_stars'] = float(profile.stars_or_badges or raw.get('stars', 0))
                elif p_name == 'codeforces':
                    metrics['codeforces_rating'] = float(profile.contest_rating or raw.get('rating', 0))
                elif p_name == 'github':
                    repos = float(raw.get('public_repos', 0))
                    stars = float(raw.get('stars_earned', 0))
                    metrics['github_repos'] = repos
                    metrics['github_stars'] = stars
                    metrics['github_stars_repos'] = repos * 0.8 + stars * 1.5
                    metrics['github_contributions'] = float(raw.get('contributions_year', 0))
                elif p_name == 'hackerrank':
                    metrics['hackerrank_badges'] = float(profile.stars_or_badges or raw.get('badges_count', 0))
                elif p_name in ('gfg', 'geeksforgeeks'):
                    metrics['gfg_problems'] = float(profile.problems_solved or raw.get('problems_solved', 0))
                    metrics['gfg_score'] = float(raw.get('coding_score', 0))

            academic_score = 0.0
            coding_score = 0.0
            github_score = 0.0
            penalties = 0.0
            bonuses = 0.0
            breakdown = {}

            for rule in formula.rules.all():
                m_key = rule.metric_key
                raw_val = metrics.get(m_key, 0.0)
                if rule.category == 'penalty':
                    deduction = raw_val * rule.penalty_per_unit
                    penalties += deduction
                    breakdown[m_key] = {'label': rule.display_label, 'raw_value': raw_val, 'deduction': round(deduction, 2), 'category': 'penalty'}
                    continue

                rule_earned = min(rule.max_marks, raw_val * rule.multiplier) if rule.multiplier and rule.multiplier > 0 else min(rule.max_marks, (raw_val / 100.0) * rule.max_marks)
                rule_bonus = rule.bonus_marks if rule.bonus_threshold and raw_val >= rule.bonus_threshold else 0.0
                bonuses += rule_bonus
                total_rule_val = rule_earned + rule_bonus

                if rule.category == 'academic':
                    academic_score += total_rule_val
                elif rule.category == 'github':
                    github_score += total_rule_val
                else:
                    coding_score += total_rule_val

                breakdown[m_key] = {'label': rule.display_label, 'raw_value': raw_val, 'earned': round(rule_earned, 2), 'bonus': round(rule_bonus, 2), 'max_marks': rule.max_marks, 'category': rule.category}

            subtotal = academic_score + coding_score + github_score + bonuses - penalties
            total = max(0.0, min(formula.max_total_marks, subtotal))
            grade = 'A+' if total >= 85 else ('A' if total >= 70 else ('B' if total >= 55 else ('C' if total >= 40 else 'D')))

            calc = CalculatedScore(
                submission_id=sub.id,
                formula_id=formula.id,
                total_score=round(total, 2),
                academic_score=round(academic_score, 2),
                coding_score=round(coding_score, 2),
                github_score=round(github_score, 2),
                penalty_deductions=round(penalties, 2),
                bonus_awarded=round(bonuses, 2),
                grade=grade,
                breakdown_json=breakdown
            )
            db.session.add(calc)
            scored_pairs.append((sub, calc, sub_profs))

        # Sort by total_score descending
        scored_pairs.sort(key=lambda item: item[1].total_score, reverse=True)
        scores_list = [item[1].total_score for item in scored_pairs]
        percentiles = Normalizer.calculate_percentiles(scores_list)

        # Assign ranks and save leaderboard entries
        for rank, (sub, calc, sub_profs) in enumerate(scored_pairs, start=1):
            pct = percentiles[rank - 1] if rank - 1 < len(percentiles) else 50.0
            calc.rank = rank
            calc.percentile = pct
            
            badge_cnt = sum(p.stars_or_badges or 0 for p in sub_profs)

            entry = LeaderboardEntry(
                form_id=form_id,
                submission_id=sub.id,
                rank=rank,
                student_name=sub.student_name,
                roll_number=sub.roll_number,
                department=sub.department,
                total_score=calc.total_score,
                percentile=pct,
                cgpa=sub.cgpa,
                coding_score=calc.coding_score,
                github_score=calc.github_score,
                badge_count=badge_cnt
            )
            db.session.add(entry)

        db.session.commit()
