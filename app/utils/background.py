import logging
from concurrent.futures import ThreadPoolExecutor
from flask import current_app
from app.models import db
from app.models.submission import Submission
from app.models.platform_profile import PlatformProfile
from app.extractors import extract_all_profiles
from app.scoring_engine.formula_evaluator import FormulaEvaluator

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=4)

def _process_submission_job(app, submission_id: int):
    """Background worker job to extract statistics and calculate scores."""
    with app.app_context():
        sub = db.session.get(Submission, submission_id)
        if not sub:
            return

        try:
            sub.status = 'extracting'
            db.session.commit()

            # Collect handles from submission values
            handles = {}
            for val in sub.values.all():
                if val.field and val.field.platform_metric_binding:
                    binding = val.field.platform_metric_binding.lower()
                    text_val = val.value_text or ''
                    if 'leetcode' in binding:
                        handles['leetcode'] = text_val
                    elif 'codechef' in binding:
                        handles['codechef'] = text_val
                    elif 'codeforces' in binding:
                        handles['codeforces'] = text_val
                    elif 'github' in binding:
                        handles['github'] = text_val
                    elif 'hackerrank' in binding:
                        handles['hackerrank'] = text_val
                    elif 'gfg' in binding or 'geeks' in binding:
                        handles['gfg'] = text_val
                    elif 'atcoder' in binding:
                        handles['atcoder'] = text_val
                    elif 'interviewbit' in binding:
                        handles['interviewbit'] = text_val
                    elif 'kaggle' in binding:
                        handles['kaggle'] = text_val

            # Also check direct fields if passed
            stats = extract_all_profiles(handles, cgpa=float(sub.cgpa or 0.0), backlogs=int(sub.backlogs or 0))

            # Store platform profiles
            PlatformProfile.query.filter_by(submission_id=sub.id).delete()

            if stats.leetcode:
                db.session.add(PlatformProfile(
                    submission_id=sub.id,
                    platform_name='leetcode',
                    username=stats.leetcode.username,
                    profile_url=stats.leetcode.profile_url,
                    avatar_url=stats.leetcode.avatar_url,
                    problems_solved=stats.leetcode.total_solved,
                    contest_rating=stats.leetcode.contest_rating,
                    global_rank=stats.leetcode.global_rank,
                    stars_or_badges=stats.leetcode.badges_count,
                    raw_data=stats.to_dict()['leetcode'],
                    extraction_status='simulated' if stats.leetcode.is_simulated else 'success'
                ))

            if stats.codechef:
                db.session.add(PlatformProfile(
                    submission_id=sub.id,
                    platform_name='codechef',
                    username=stats.codechef.username,
                    profile_url=stats.codechef.profile_url,
                    avatar_url=stats.codechef.avatar_url,
                    problems_solved=stats.codechef.problems_solved,
                    contest_rating=float(stats.codechef.current_rating),
                    highest_rating=float(stats.codechef.highest_rating),
                    global_rank=stats.codechef.global_rank,
                    stars_or_badges=stats.codechef.stars,
                    raw_data=stats.to_dict()['codechef'],
                    extraction_status='simulated' if stats.codechef.is_simulated else 'success'
                ))

            if stats.codeforces:
                db.session.add(PlatformProfile(
                    submission_id=sub.id,
                    platform_name='codeforces',
                    username=stats.codeforces.username,
                    profile_url=stats.codeforces.profile_url,
                    avatar_url=stats.codeforces.avatar_url,
                    problems_solved=stats.codeforces.problems_solved,
                    contest_rating=float(stats.codeforces.rating),
                    highest_rating=float(stats.codeforces.max_rating),
                    stars_or_badges=1 if stats.codeforces.rating > 1400 else 0,
                    raw_data=stats.to_dict()['codeforces'],
                    extraction_status='simulated' if stats.codeforces.is_simulated else 'success'
                ))

            if stats.github:
                db.session.add(PlatformProfile(
                    submission_id=sub.id,
                    platform_name='github',
                    username=stats.github.username,
                    profile_url=stats.github.profile_url,
                    avatar_url=stats.github.avatar_url,
                    problems_solved=stats.github.public_repos,
                    contest_rating=float(stats.github.contributions_year),
                    stars_or_badges=stats.github.stars_earned,
                    raw_data=stats.to_dict()['github'],
                    extraction_status='simulated' if stats.github.is_simulated else 'success'
                ))

            if stats.hackerrank:
                db.session.add(PlatformProfile(
                    submission_id=sub.id,
                    platform_name='hackerrank',
                    username=stats.hackerrank.username,
                    profile_url=stats.hackerrank.profile_url,
                    avatar_url=stats.hackerrank.avatar_url,
                    problems_solved=stats.hackerrank.problems_solved,
                    stars_or_badges=stats.hackerrank.badges_count,
                    raw_data=stats.to_dict()['hackerrank'],
                    extraction_status='simulated' if stats.hackerrank.is_simulated else 'success'
                ))

            if stats.gfg:
                db.session.add(PlatformProfile(
                    submission_id=sub.id,
                    platform_name='gfg',
                    username=stats.gfg.username,
                    profile_url=stats.gfg.profile_url,
                    avatar_url=stats.gfg.avatar_url,
                    problems_solved=stats.gfg.problems_solved,
                    contest_rating=float(stats.gfg.coding_score),
                    raw_data=stats.to_dict()['gfg'],
                    extraction_status='simulated' if stats.gfg.is_simulated else 'success'
                ))

            if stats.atcoder:
                db.session.add(PlatformProfile(
                    submission_id=sub.id,
                    platform_name='atcoder',
                    username=stats.atcoder.username,
                    profile_url=stats.atcoder.profile_url,
                    avatar_url=stats.atcoder.avatar_url,
                    problems_solved=stats.atcoder.problems_solved,
                    contest_rating=float(stats.atcoder.current_rating),
                    highest_rating=float(stats.atcoder.highest_rating),
                    global_rank=stats.atcoder.global_rank,
                    raw_data=stats.to_dict()['atcoder'],
                    extraction_status='simulated' if stats.atcoder.is_simulated else 'success'
                ))

            if stats.interviewbit:
                db.session.add(PlatformProfile(
                    submission_id=sub.id,
                    platform_name='interviewbit',
                    username=stats.interviewbit.username,
                    profile_url=stats.interviewbit.profile_url,
                    avatar_url=stats.interviewbit.avatar_url,
                    problems_solved=stats.interviewbit.problems_solved,
                    contest_rating=float(stats.interviewbit.score),
                    global_rank=stats.interviewbit.global_rank,
                    raw_data=stats.to_dict()['interviewbit'],
                    extraction_status='simulated' if stats.interviewbit.is_simulated else 'success'
                ))

            if stats.kaggle:
                db.session.add(PlatformProfile(
                    submission_id=sub.id,
                    platform_name='kaggle',
                    username=stats.kaggle.username,
                    profile_url=stats.kaggle.profile_url,
                    avatar_url=stats.kaggle.avatar_url,
                    problems_solved=stats.kaggle.competitions_count,
                    stars_or_badges=stats.kaggle.total_medals,
                    raw_data=stats.to_dict()['kaggle'],
                    extraction_status='simulated' if stats.kaggle.is_simulated else 'success'
                ))

            sub.status = 'scoring'
            db.session.commit()

            # Recalculate score and refresh leaderboard cache
            FormulaEvaluator.update_form_ranks_and_leaderboard(sub.form_id)

            sub.status = 'completed'
            db.session.commit()

        except Exception as e:
            logger.exception("Error processing background submission: %s", e)
            sub.status = 'failed'
            sub.error_message = str(e)
            db.session.commit()

def queue_submission_processing(submission_id: int):
    """Queue asynchronous background processing for a submission."""
    # Obtain actual app instance from proxy
    app = current_app._get_current_object()
    _executor.submit(_process_submission_job, app, submission_id)
