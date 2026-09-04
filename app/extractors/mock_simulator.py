import hashlib
from typing import Dict, Any
from .schema import (
    LeetCodeStats, CodeChefStats, CodeforcesStats, GitHubStats, HackerRankStats, GeeksforGeeksStats,
    AtCoderStats, InterviewBitStats, KaggleStats
)

class MockSimulator:
    """Generates realistic, deterministic mock metrics based on username hash when APIs fail or rate limit."""

    @staticmethod
    def _seed(username: str) -> int:
        h = hashlib.sha256(username.lower().encode('utf-8')).hexdigest()
        return int(h[:8], 16)

    @classmethod
    def simulate_leetcode(cls, username: str) -> LeetCodeStats:
        seed = cls._seed(username)
        easy = 50 + (seed % 150)
        medium = 40 + ((seed >> 2) % 180)
        hard = 5 + ((seed >> 4) % 45)
        total = easy + medium + hard
        rating = 1450.0 + float((seed >> 6) % 750)
        rank = 15000 + ((seed >> 8) % 85000)
        acceptance = round(52.0 + float((seed % 30)), 1)
        badges = 2 + (seed % 10)
        
        return LeetCodeStats(
            username=username,
            profile_url=f"https://leetcode.com/u/{username}/",
            avatar_url=f"https://api.dicebear.com/7.x/identicon/svg?seed={username}",
            total_solved=total,
            easy_solved=easy,
            medium_solved=medium,
            hard_solved=hard,
            contest_rating=rating,
            global_rank=rank,
            contests_attended=5 + (seed % 25),
            acceptance_rate=acceptance,
            badges_count=badges,
            top_languages=['Python', 'C++', 'Java'],
            is_simulated=True
        )

    @classmethod
    def simulate_codechef(cls, username: str) -> CodeChefStats:
        seed = cls._seed(username)
        rating = 1400 + (seed % 750)
        stars = 1
        if rating >= 2000:
            stars = 5
        elif rating >= 1800:
            stars = 4
        elif rating >= 1600:
            stars = 3
        elif rating >= 1400:
            stars = 2
            
        return CodeChefStats(
            username=username,
            profile_url=f"https://www.codechef.com/users/{username}",
            avatar_url=f"https://api.dicebear.com/7.x/identicon/svg?seed={username}",
            current_rating=rating,
            highest_rating=rating + 65,
            stars=stars,
            global_rank=12000 + (seed % 40000),
            country_rank=6000 + (seed % 20000),
            problems_solved=60 + (seed % 220),
            contests_participated=8 + (seed % 30),
            is_simulated=True
        )

    @classmethod
    def simulate_codeforces(cls, username: str) -> CodeforcesStats:
        seed = cls._seed(username)
        rating = 1200 + (seed % 650)
        ranks = ['newbie', 'pupil', 'specialist', 'expert', 'candidate master']
        idx = min(len(ranks) - 1, max(0, (rating - 1100) // 180))
        
        return CodeforcesStats(
            username=username,
            profile_url=f"https://codeforces.com/profile/{username}",
            avatar_url=f"https://api.dicebear.com/7.x/identicon/svg?seed={username}",
            rating=rating,
            max_rating=rating + 80,
            rank=ranks[idx],
            max_rank=ranks[min(len(ranks) - 1, idx + 1)],
            problems_solved=80 + (seed % 300),
            contribution=(seed % 15) - 5,
            is_simulated=True
        )

    @classmethod
    def simulate_github(cls, username: str) -> GitHubStats:
        seed = cls._seed(username)
        repos = 8 + (seed % 35)
        stars = 4 + (seed % 80)
        followers = 5 + (seed % 50)
        contributions = 120 + (seed % 600)
        
        return GitHubStats(
            username=username,
            profile_url=f"https://github.com/{username}",
            avatar_url=f"https://github.com/{username}.png",
            public_repos=repos,
            stars_earned=stars,
            followers=followers,
            following=followers + 3,
            contributions_year=contributions,
            longest_streak=7 + (seed % 35),
            top_languages=['Python', 'JavaScript', 'TypeScript', 'C++'],
            is_simulated=True
        )

    @classmethod
    def simulate_hackerrank(cls, username: str) -> HackerRankStats:
        seed = cls._seed(username)
        return HackerRankStats(
            username=username,
            profile_url=f"https://www.hackerrank.com/profile/{username}",
            avatar_url=f"https://api.dicebear.com/7.x/identicon/svg?seed={username}",
            badges_count=3 + (seed % 8),
            stars_count=4 + (seed % 2),
            certificates_count=1 + (seed % 4),
            problems_solved=45 + (seed % 160),
            is_simulated=True
        )

    @classmethod
    def simulate_gfg(cls, username: str) -> GeeksforGeeksStats:
        seed = cls._seed(username)
        total = 70 + (seed % 280)
        return GeeksforGeeksStats(
            username=username,
            profile_url=f"https://www.geeksforgeeks.org/user/{username}/",
            avatar_url=f"https://api.dicebear.com/7.x/identicon/svg?seed={username}",
            problems_solved=total,
            coding_score=350 + (seed % 1200),
            institute_rank=15 + (seed % 150),
            school_solved=10 + (seed % 20),
            basic_solved=15 + (seed % 30),
            easy_solved=25 + (seed % 90),
            medium_solved=15 + (seed % 80),
            hard_solved=5 + (seed % 25),
            is_simulated=True
        )

    @classmethod
    def simulate_atcoder(cls, username: str) -> AtCoderStats:
        seed = cls._seed(username)
        rating = 600 + (seed % 1400)
        # AtCoder Color Tiers
        tier = "White"
        if rating >= 2000:
            tier = "Yellow"
        elif rating >= 1600:
            tier = "Blue"
        elif rating >= 1200:
            tier = "Cyan"
        elif rating >= 800:
            tier = "Green"
        elif rating >= 400:
            tier = "Brown"

        return AtCoderStats(
            username=username,
            profile_url=f"https://atcoder.jp/users/{username}",
            avatar_url=f"https://api.dicebear.com/7.x/identicon/svg?seed={username}",
            current_rating=rating,
            highest_rating=rating + 70,
            rank=2500 + (seed % 18000),
            tier_color=tier,
            contests_attended=6 + (seed % 25),
            is_simulated=True
        )

    @classmethod
    def simulate_interviewbit(cls, username: str) -> InterviewBitStats:
        seed = cls._seed(username)
        score = 850 + (seed % 4500)
        return InterviewBitStats(
            username=username,
            profile_url=f"https://www.interviewbit.com/profile/{username}",
            avatar_url=f"https://api.dicebear.com/7.x/identicon/svg?seed={username}",
            score=score,
            global_rank=1500 + (seed % 35000),
            problems_solved=30 + (seed % 150),
            streak_days=4 + (seed % 30),
            is_simulated=True
        )

    @classmethod
    def simulate_kaggle(cls, username: str) -> KaggleStats:
        seed = cls._seed(username)
        tiers = ['Novice', 'Contributor', 'Expert', 'Master', 'Grandmaster']
        idx = min(len(tiers) - 1, (seed % 100) // 25)
        medals = 1 + (seed % 12)
        return KaggleStats(
            username=username,
            profile_url=f"https://www.kaggle.com/{username}",
            avatar_url=f"https://api.dicebear.com/7.x/identicon/svg?seed={username}",
            tier=tiers[idx],
            total_medals=medals,
            competitions_count=2 + (seed % 8),
            datasets_count=1 + (seed % 5),
            notebooks_count=4 + (seed % 15),
            followers=8 + (seed % 80),
            is_simulated=True
        )

