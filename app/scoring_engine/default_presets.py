from typing import List, Dict, Any

DEFAULT_PRESETS: Dict[str, Dict[str, Any]] = {
    'standard_placement': {
        'name': 'Standard Placement Drive Formula',
        'description': 'Balanced formula weighting LeetCode, CodeChef, GitHub, and Academics with backlog penalty.',
        'normalization_method': 'min_max',
        'max_total_marks': 100.0,
        'rules': [
            {
                'metric_key': 'cgpa',
                'display_label': 'Academic CGPA (Out of 10)',
                'weight_percentage': 25.0,
                'max_marks': 25.0,
                'multiplier': 2.5,  # 10 CGPA * 2.5 = 25 marks
                'category': 'academic'
            },
            {
                'metric_key': 'leetcode_solved',
                'display_label': 'LeetCode Problems Solved (Benchmark 300+)',
                'weight_percentage': 25.0,
                'max_marks': 25.0,
                'multiplier': 25.0 / 300.0,  # 300 solved = 25 marks
                'bonus_threshold': 500,
                'bonus_marks': 3.0,
                'category': 'coding'
            },
            {
                'metric_key': 'leetcode_rating',
                'display_label': 'LeetCode Contest Rating (Benchmark 1800+)',
                'weight_percentage': 15.0,
                'max_marks': 15.0,
                'multiplier': 15.0 / 1800.0,
                'category': 'coding'
            },
            {
                'metric_key': 'codechef_rating',
                'display_label': 'CodeChef Rating (Benchmark 1700+)',
                'weight_percentage': 15.0,
                'max_marks': 15.0,
                'multiplier': 15.0 / 1700.0,
                'category': 'coding'
            },
            {
                'metric_key': 'github_stars_repos',
                'display_label': 'GitHub Repos & Stars Earned',
                'weight_percentage': 10.0,
                'max_marks': 10.0,
                'multiplier': 0.5,
                'category': 'github'
            },
            {
                'metric_key': 'hackerrank_badges',
                'display_label': 'HackerRank Badges & Certifications',
                'weight_percentage': 10.0,
                'max_marks': 10.0,
                'multiplier': 1.25,
                'category': 'coding'
            },
            {
                'metric_key': 'backlogs_penalty',
                'display_label': 'Active Backlog Penalty',
                'weight_percentage': 0.0,
                'max_marks': 0.0,
                'penalty_per_unit': 5.0,  # -5 marks per backlog
                'category': 'penalty'
            }
        ]
    },
    'competitive_programming': {
        'name': 'Competitive Programming Specialist',
        'description': 'Heavy weight on contest ratings across LeetCode, Codeforces, and CodeChef.',
        'normalization_method': 'min_max',
        'max_total_marks': 100.0,
        'rules': [
            {
                'metric_key': 'leetcode_solved',
                'display_label': 'LeetCode Problems Solved',
                'weight_percentage': 30.0,
                'max_marks': 30.0,
                'multiplier': 30.0 / 400.0,
                'category': 'coding'
            },
            {
                'metric_key': 'leetcode_rating',
                'display_label': 'LeetCode Contest Rating',
                'weight_percentage': 25.0,
                'max_marks': 25.0,
                'multiplier': 25.0 / 1900.0,
                'category': 'coding'
            },
            {
                'metric_key': 'codeforces_rating',
                'display_label': 'Codeforces Rating',
                'weight_percentage': 25.0,
                'max_marks': 25.0,
                'multiplier': 25.0 / 1600.0,
                'category': 'coding'
            },
            {
                'metric_key': 'codechef_rating',
                'display_label': 'CodeChef Rating',
                'weight_percentage': 20.0,
                'max_marks': 20.0,
                'multiplier': 20.0 / 1800.0,
                'category': 'coding'
            }
        ]
    },
    'data_science_ai': {
        'name': 'Data Science, AI & Development Specialist',
        'description': 'Designed for AI/ML roles focusing on Kaggle performance, open-source GitHub portfolio, and core problem solving.',
        'normalization_method': 'min_max',
        'max_total_marks': 100.0,
        'rules': [
            {
                'metric_key': 'kaggle_medals',
                'display_label': 'Kaggle Medals & Competitions (Benchmark 5+ medals)',
                'weight_percentage': 30.0,
                'max_marks': 30.0,
                'multiplier': 30.0 / 5.0,
                'category': 'coding'
            },
            {
                'metric_key': 'github_stars_repos',
                'display_label': 'GitHub Open Source Repositories & Stars',
                'weight_percentage': 25.0,
                'max_marks': 25.0,
                'multiplier': 0.8,
                'category': 'github'
            },
            {
                'metric_key': 'cgpa',
                'display_label': 'Academic CGPA',
                'weight_percentage': 25.0,
                'max_marks': 25.0,
                'multiplier': 2.5,
                'category': 'academic'
            },
            {
                'metric_key': 'leetcode_solved',
                'display_label': 'LeetCode DSA Solved',
                'weight_percentage': 20.0,
                'max_marks': 20.0,
                'multiplier': 20.0 / 250.0,
                'category': 'coding'
            },
            {
                'metric_key': 'backlogs_penalty',
                'display_label': 'Active Backlog Penalty',
                'weight_percentage': 0.0,
                'max_marks': 0.0,
                'penalty_per_unit': 5.0,
                'category': 'penalty'
            }
        ]
    },
    'all_platforms_pro': {
        'name': 'All-Rounder Competitive & Placement Master',
        'description': 'Comprehensive evaluation spanning LeetCode, CodeChef, Codeforces, AtCoder, InterviewBit, and GitHub.',
        'normalization_method': 'min_max',
        'max_total_marks': 100.0,
        'rules': [
            {
                'metric_key': 'leetcode_solved',
                'display_label': 'LeetCode Solved',
                'weight_percentage': 20.0,
                'max_marks': 20.0,
                'multiplier': 20.0 / 300.0,
                'category': 'coding'
            },
            {
                'metric_key': 'codeforces_rating',
                'display_label': 'Codeforces Rating',
                'weight_percentage': 15.0,
                'max_marks': 15.0,
                'multiplier': 15.0 / 1600.0,
                'category': 'coding'
            },
            {
                'metric_key': 'atcoder_rating',
                'display_label': 'AtCoder Contest Rating',
                'weight_percentage': 15.0,
                'max_marks': 15.0,
                'multiplier': 15.0 / 1200.0,
                'category': 'coding'
            },
            {
                'metric_key': 'interviewbit_score',
                'display_label': 'InterviewBit Practice Score',
                'weight_percentage': 15.0,
                'max_marks': 15.0,
                'multiplier': 15.0 / 3000.0,
                'category': 'coding'
            },
            {
                'metric_key': 'github_stars_repos',
                'display_label': 'GitHub Repos & Stars',
                'weight_percentage': 15.0,
                'max_marks': 15.0,
                'multiplier': 0.6,
                'category': 'github'
            },
            {
                'metric_key': 'cgpa',
                'display_label': 'Academic CGPA',
                'weight_percentage': 20.0,
                'max_marks': 20.0,
                'multiplier': 2.0,
                'category': 'academic'
            },
            {
                'metric_key': 'backlogs_penalty',
                'display_label': 'Active Backlog Penalty',
                'weight_percentage': 0.0,
                'max_marks': 0.0,
                'penalty_per_unit': 5.0,
                'category': 'penalty'
            }
        ]
    }
}

