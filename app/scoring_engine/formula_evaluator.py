import math
from typing import Dict, Any, List, Optional
from app.models.scoring import ScoreFormula, FormulaRule, CalculatedScore, LeaderboardEntry
from app.models.submission import Submission, SubmissionValue
from app.models.platform_profile import PlatformProfile
from app.models import db
from .normalizer import Normalizer

def safe_float(val: Any, default: float = 0.0) -> float:
    """Defensively parse numeric values with protection against NaN, Inf, and type errors."""
    if val is None:
        return default
    try:
        f = float(val)
        return default if math.isnan(f) or math.isinf(f) else f
    except (ValueError, TypeError):
        return default


class FormulaEvaluator:
    """Evaluates student scores based on formula rules, platform metrics, and normalization methods."""

    @staticmethod
    def extract_metric_values(
        submission: Submission,
        profiles: Optional[List[PlatformProfile]] = None,
        values: Optional[List[SubmissionValue]] = None
    ) -> Dict[str, float]:
        """Flatten submission attributes, platform profiles, and custom form fields into a numeric metrics dictionary."""
        metrics: Dict[str, float] = {
            'cgpa': max(0.0, min(10.0, safe_float(submission.cgpa, 0.0))),
            'backlogs': max(0.0, safe_float(submission.backlogs, 0.0)),
            'backlogs_penalty': max(0.0, safe_float(submission.backlogs, 0.0)),
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
            'gfg_score': 0.0,
            'atcoder_rating': 0.0,
            'atcoder_highest': 0.0,
            'atcoder_contests': 0.0,
            'interviewbit_score': 0.0,
            'interviewbit_solved': 0.0,
            'kaggle_medals': 0.0,
            'kaggle_score': 0.0
        }

        # Inspect extracted platform profiles (using preloaded list when provided)
        profile_list = profiles if profiles is not None else submission.platform_profiles.all()
        for profile in profile_list:
            p_name = profile.platform_name.lower()
            raw = profile.raw_data or {}

            if p_name == 'leetcode':
                metrics['leetcode_solved'] = safe_float(profile.problems_solved or raw.get('total_solved', 0))
                metrics['leetcode_rating'] = safe_float(profile.contest_rating or raw.get('contest_rating', 0.0))
                metrics['leetcode_hard'] = safe_float(raw.get('hard_solved', 0))
            elif p_name == 'codechef':
                metrics['codechef_rating'] = safe_float(profile.contest_rating or raw.get('current_rating', 0))
                metrics['codechef_stars'] = safe_float(profile.stars_or_badges or raw.get('stars', 0))
            elif p_name == 'codeforces':
                metrics['codeforces_rating'] = safe_float(profile.contest_rating or raw.get('rating', 0))
            elif p_name == 'github':
                repos = safe_float(raw.get('public_repos', 0) or profile.problems_solved or 0)
                stars = safe_float(raw.get('stars_earned', 0) or profile.stars_or_badges or 0)
                metrics['github_repos'] = repos
                metrics['github_stars'] = stars
                metrics['github_stars_repos'] = repos * 0.8 + stars * 1.5
                metrics['github_contributions'] = safe_float(raw.get('contributions_year', 0) or profile.contest_rating or 0)
            elif p_name == 'hackerrank':
                metrics['hackerrank_badges'] = safe_float(profile.stars_or_badges or raw.get('badges_count', 0))
            elif p_name in ('gfg', 'geeksforgeeks'):
                metrics['gfg_problems'] = safe_float(profile.problems_solved or raw.get('problems_solved', 0))
                metrics['gfg_score'] = safe_float(raw.get('coding_score', 0) or profile.contest_rating or 0)
            elif p_name == 'atcoder':
                metrics['atcoder_rating'] = safe_float(profile.contest_rating or raw.get('current_rating', 0))
                metrics['atcoder_highest'] = safe_float(profile.highest_rating or raw.get('highest_rating', 0))
                metrics['atcoder_contests'] = safe_float(raw.get('contests_attended', 0))
            elif p_name == 'interviewbit':
                metrics['interviewbit_score'] = safe_float(raw.get('score', 0) or profile.contest_rating or 0)
                metrics['interviewbit_solved'] = safe_float(profile.problems_solved or raw.get('problems_solved', 0))
            elif p_name == 'kaggle':
                metrics['kaggle_medals'] = safe_float(profile.stars_or_badges or raw.get('total_medals', 0))
                comp = safe_float(raw.get('competitions_count', 0))
                ds = safe_float(raw.get('datasets_count', 0))
                nb = safe_float(raw.get('notebooks_count', 0))
                metrics['kaggle_score'] = comp * 10.0 + ds * 5.0 + nb * 5.0

        # Inspect custom form submission values (custom fields)
        val_list = values if values is not None else (submission.values.all() if hasattr(submission, 'values') else [])
        for v in val_list:
            if v and v.field and v.field.field_key:
                val_text = (v.value_text or '').strip()
                try:
                    metrics[v.field.field_key] = float(val_text)
                except (ValueError, TypeError):
                    pass

        return metrics

    @staticmethod
    def calculate_submission_score(
        metrics: Dict[str, float],
        formula: ScoreFormula,
        rules: Optional[List[FormulaRule]] = None,
        manual_score_adjustment: float = 0.0
    ) -> Dict[str, Any]:
        """Core mathematical calculation for scoring metrics against formula rules."""
        academic_score = 0.0
        coding_score = 0.0
        github_score = 0.0
        penalties = 0.0
        bonuses = 0.0
        breakdown = {}

        rule_list = rules if rules is not None else formula.rules.all()

        for rule in rule_list:
            m_key = rule.metric_key
            raw_val = safe_float(metrics.get(m_key, 0.0))

            if rule.category == 'penalty':
                # Penalties deduct marks. Enforce non-negative unit count.
                units = max(0.0, raw_val)
                deduction = units * max(0.0, safe_float(rule.penalty_per_unit, 0.0))
                penalties += deduction
                breakdown[m_key] = {
                    'label': rule.display_label,
                    'raw_value': round(units, 2),
                    'deduction': round(deduction, 2),
                    'earned': -round(deduction, 2),
                    'bonus': 0.0,
                    'max_marks': rule.max_marks or 0.0,
                    'category': 'penalty'
                }
                continue

            # Multiplier calculation
            mult = rule.multiplier if (rule.multiplier and rule.multiplier > 0) else 1.0
            max_m = rule.max_marks if rule.max_marks is not None else 10.0
            rule_earned = max(0.0, min(max_m, raw_val * mult))

            # Bonus calculation (awarded when raw_val meets or exceeds bonus_threshold)
            rule_bonus = 0.0
            if rule.bonus_threshold and rule.bonus_threshold > 0 and raw_val >= rule.bonus_threshold:
                rule_bonus = max(0.0, safe_float(rule.bonus_marks, 0.0))
                bonuses += rule_bonus

            # Accumulate category subtotals (pure earned marks without double-counting bonuses)
            if rule.category == 'academic':
                academic_score += rule_earned
            elif rule.category == 'github':
                github_score += rule_earned
            else:
                coding_score += rule_earned

            breakdown[m_key] = {
                'label': rule.display_label,
                'raw_value': round(raw_val, 2),
                'earned': round(rule_earned, 2),
                'bonus': round(rule_bonus, 2),
                'max_marks': max_m,
                'category': rule.category
            }

        # Calculate subtotal: academic + coding + github + bonuses - penalties
        subtotal = academic_score + coding_score + github_score + bonuses - penalties

        # Apply teacher manual score adjustment if present
        if manual_score_adjustment != 0.0:
            subtotal += manual_score_adjustment
            breakdown['teacher_adjustment'] = {
                'label': 'Teacher Manual Score Adjustment',
                'raw_value': round(manual_score_adjustment, 2),
                'earned': round(manual_score_adjustment, 2),
                'bonus': 0.0,
                'max_marks': 0.0,
                'category': 'adjustment'
            }

        max_total = float(formula.max_total_marks or 100.0)
        total = max(0.0, min(max_total, subtotal))

        # Percentage-based letter grade calculation
        pct_score = (total / max_total * 100.0) if max_total > 0 else 0.0
        if pct_score >= 85:
            grade = 'A+'
        elif pct_score >= 70:
            grade = 'A'
        elif pct_score >= 55:
            grade = 'B'
        elif pct_score >= 40:
            grade = 'C'
        else:
            grade = 'D'

        return {
            'total_score': round(total, 2),
            'academic_score': round(academic_score, 2),
            'coding_score': round(coding_score, 2),
            'github_score': round(github_score, 2),
            'penalty_deductions': round(penalties, 2),
            'bonus_awarded': round(bonuses, 2),
            'grade': grade,
            'breakdown': breakdown,
            'subtotal': round(subtotal, 2)
        }

    @classmethod
    def evaluate_submission(cls, submission: Submission, formula: ScoreFormula) -> CalculatedScore:
        """Calculate score breakdown for a single submission using the given formula."""
        metrics = cls.extract_metric_values(submission)
        manual_adj = getattr(submission, 'manual_score_adjustment', 0.0) or 0.0
        res = cls.calculate_submission_score(metrics, formula, manual_score_adjustment=manual_adj)

        calc_score = CalculatedScore(
            submission_id=submission.id,
            formula_id=formula.id,
            total_score=res['total_score'],
            academic_score=res['academic_score'],
            coding_score=res['coding_score'],
            github_score=res['github_score'],
            penalty_deductions=res['penalty_deductions'],
            bonus_awarded=res['bonus_awarded'],
            grade=res['grade'],
            breakdown_json=res['breakdown']
        )
        return calc_score

    @classmethod
    def update_form_ranks_and_leaderboard(cls, form_id: int):
        """Batch recalculates ranks, percentiles, normalizes scores, and updates leaderboard cache for all submissions in a form."""
        submissions = Submission.query.filter_by(form_id=form_id).all()
        if not submissions:
            return

        # Fetch active formula
        formula = ScoreFormula.query.filter_by(form_id=form_id, is_active=True).first()
        if not formula:
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

        sub_ids = [s.id for s in submissions]
        CalculatedScore.query.filter(CalculatedScore.submission_id.in_(sub_ids)).delete(synchronize_session='fetch')
        LeaderboardEntry.query.filter_by(form_id=form_id).delete(synchronize_session='fetch')
        db.session.commit()

        # Pre-fetch all profiles and custom values in batch to eliminate N+1 queries
        all_profiles = PlatformProfile.query.filter(PlatformProfile.submission_id.in_(sub_ids)).all()
        profiles_by_sub: Dict[int, List[PlatformProfile]] = {}
        for p in all_profiles:
            profiles_by_sub.setdefault(p.submission_id, []).append(p)

        all_values = SubmissionValue.query.filter(SubmissionValue.submission_id.in_(sub_ids)).all()
        values_by_sub: Dict[int, List[SubmissionValue]] = {}
        for v in all_values:
            values_by_sub.setdefault(v.submission_id, []).append(v)

        rules = formula.rules.all()

        # Phase 1: Score all submissions with formula engine
        scored_data: List[Dict[str, Any]] = []
        for sub in submissions:
            sub_profs = profiles_by_sub.get(sub.id, [])
            sub_vals = values_by_sub.get(sub.id, [])
            metrics = cls.extract_metric_values(sub, profiles=sub_profs, values=sub_vals)
            manual_adj = getattr(sub, 'manual_score_adjustment', 0.0) or 0.0

            res = cls.calculate_submission_score(metrics, formula, rules=rules, manual_score_adjustment=manual_adj)
            scored_data.append({
                'submission': sub,
                'sub_profs': sub_profs,
                'result': res,
                'raw_score': res['total_score']
            })

        # Phase 2: Apply cohort normalization method if requested
        norm_method = (formula.normalization_method or 'min_max').lower()
        max_marks = float(formula.max_total_marks or 100.0)
        raw_scores = [item['raw_score'] for item in scored_data]

        if norm_method == 'cohort_min_max' and len(raw_scores) > 1:
            min_raw = min(raw_scores)
            max_raw = max(raw_scores)
            if max_raw > min_raw:
                for item in scored_data:
                    scaled = Normalizer.min_max(item['raw_score'], min_raw, max_raw, 0.0, max_marks)
                    item['final_score'] = round(scaled, 2)
            else:
                for item in scored_data:
                    item['final_score'] = item['raw_score']
        elif norm_method == 'z_score' and len(raw_scores) > 1:
            mean_score = sum(raw_scores) / len(raw_scores)
            variance = sum((x - mean_score) ** 2 for x in raw_scores) / len(raw_scores)
            std_dev = math.sqrt(variance)
            if std_dev > 0:
                for item in scored_data:
                    z_scaled = Normalizer.z_score(item['raw_score'], mean_score, std_dev)
                    item['final_score'] = round((z_scaled / 100.0) * max_marks, 2)
            else:
                for item in scored_data:
                    item['final_score'] = item['raw_score']
        else:
            # Default 'min_max' (rule-level bounded scaling) or 'weighted_sum'
            for item in scored_data:
                item['final_score'] = item['raw_score']

        # Phase 3: Sort by final_score descending and compute percentiles
        scored_data.sort(key=lambda item: item['final_score'], reverse=True)
        final_scores_list = [item['final_score'] for item in scored_data]
        percentiles = Normalizer.calculate_percentiles(final_scores_list)

        # If percentile normalization is explicitly selected:
        if norm_method == 'percentile':
            for i, item in enumerate(scored_data):
                pct = percentiles[i] if i < len(percentiles) else 50.0
                item['final_score'] = round((pct / 100.0) * max_marks, 2)
            scored_data.sort(key=lambda item: item['final_score'], reverse=True)

        # Phase 4: Persist CalculatedScore and LeaderboardEntry records
        for rank, item in enumerate(scored_data, start=1):
            sub = item['submission']
            sub_profs = item['sub_profs']
            res = item['result']
            final_s = item['final_score']
            pct = percentiles[rank - 1] if rank - 1 < len(percentiles) else 50.0

            # Percentage-based grade evaluation on final normalized score
            pct_final = (final_s / max_marks * 100.0) if max_marks > 0 else 0.0
            grade = 'A+' if pct_final >= 85 else ('A' if pct_final >= 70 else ('B' if pct_final >= 55 else ('C' if pct_final >= 40 else 'D')))

            calc = CalculatedScore(
                submission_id=sub.id,
                formula_id=formula.id,
                total_score=final_s,
                academic_score=res['academic_score'],
                coding_score=res['coding_score'],
                github_score=res['github_score'],
                penalty_deductions=res['penalty_deductions'],
                bonus_awarded=res['bonus_awarded'],
                rank=rank,
                percentile=pct,
                grade=grade,
                breakdown_json=res['breakdown']
            )
            db.session.add(calc)

            badge_cnt = sum(p.stars_or_badges or 0 for p in sub_profs)
            entry = LeaderboardEntry(
                form_id=form_id,
                submission_id=sub.id,
                rank=rank,
                student_name=sub.student_name,
                roll_number=sub.roll_number,
                department=sub.department,
                total_score=final_s,
                percentile=pct,
                cgpa=sub.cgpa,
                coding_score=res['coding_score'],
                github_score=res['github_score'],
                badge_count=badge_cnt
            )
            db.session.add(entry)

        db.session.commit()
