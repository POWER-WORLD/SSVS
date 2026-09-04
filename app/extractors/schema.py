from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List

@dataclass
class LeetCodeStats:
    username: str = ""
    profile_url: str = ""
    avatar_url: str = ""
    total_solved: int = 0
    easy_solved: int = 0
    medium_solved: int = 0
    hard_solved: int = 0
    contest_rating: float = 0.0
    global_rank: int = 0
    contests_attended: int = 0
    acceptance_rate: float = 0.0
    badges_count: int = 0
    top_languages: List[str] = field(default_factory=list)
    is_simulated: bool = False

@dataclass
class CodeChefStats:
    username: str = ""
    profile_url: str = ""
    avatar_url: str = ""
    current_rating: int = 0
    highest_rating: int = 0
    stars: int = 0
    global_rank: int = 0
    country_rank: int = 0
    problems_solved: int = 0
    contests_participated: int = 0
    is_simulated: bool = False

@dataclass
class CodeforcesStats:
    username: str = ""
    profile_url: str = ""
    avatar_url: str = ""
    rating: int = 0
    max_rating: int = 0
    rank: str = "unrated"
    max_rank: str = "unrated"
    problems_solved: int = 0
    contribution: int = 0
    is_simulated: bool = False

@dataclass
class GitHubStats:
    username: str = ""
    profile_url: str = ""
    avatar_url: str = ""
    public_repos: int = 0
    stars_earned: int = 0
    followers: int = 0
    following: int = 0
    contributions_year: int = 0
    longest_streak: int = 0
    top_languages: List[str] = field(default_factory=list)
    is_simulated: bool = False

@dataclass
class HackerRankStats:
    username: str = ""
    profile_url: str = ""
    avatar_url: str = ""
    badges_count: int = 0
    stars_count: int = 0
    certificates_count: int = 0
    problems_solved: int = 0
    is_simulated: bool = False

@dataclass
class GeeksforGeeksStats:
    username: str = ""
    profile_url: str = ""
    avatar_url: str = ""
    problems_solved: int = 0
    coding_score: int = 0
    institute_rank: int = 0
    school_solved: int = 0
    basic_solved: int = 0
    easy_solved: int = 0
    medium_solved: int = 0
    hard_solved: int = 0
    is_simulated: bool = False

@dataclass
class AtCoderStats:
    username: str = ""
    profile_url: str = ""
    avatar_url: str = ""
    current_rating: int = 0
    highest_rating: int = 0
    rank: int = 0
    tier_color: str = "White"  # White, Brown, Green, Cyan, Blue, Yellow, Orange, Red
    contests_attended: int = 0
    is_simulated: bool = False

@dataclass
class InterviewBitStats:
    username: str = ""
    profile_url: str = ""
    avatar_url: str = ""
    score: int = 0
    global_rank: int = 0
    problems_solved: int = 0
    streak_days: int = 0
    is_simulated: bool = False

@dataclass
class KaggleStats:
    username: str = ""
    profile_url: str = ""
    avatar_url: str = ""
    tier: str = "Contributor"  # Novice, Contributor, Expert, Master, Grandmaster
    total_medals: int = 0
    competitions_count: int = 0
    datasets_count: int = 0
    notebooks_count: int = 0
    followers: int = 0
    is_simulated: bool = False

@dataclass
class UnifiedStudentStats:
    leetcode: Optional[LeetCodeStats] = None
    codechef: Optional[CodeChefStats] = None
    codeforces: Optional[CodeforcesStats] = None
    github: Optional[GitHubStats] = None
    hackerrank: Optional[HackerRankStats] = None
    gfg: Optional[GeeksforGeeksStats] = None
    atcoder: Optional[AtCoderStats] = None
    interviewbit: Optional[InterviewBitStats] = None
    kaggle: Optional[KaggleStats] = None
    
    # Academics
    cgpa: float = 0.0
    backlogs: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            'cgpa': self.cgpa,
            'backlogs': self.backlogs,
            'leetcode': asdict(self.leetcode) if self.leetcode else None,
            'codechef': asdict(self.codechef) if self.codechef else None,
            'codeforces': asdict(self.codeforces) if self.codeforces else None,
            'github': asdict(self.github) if self.github else None,
            'hackerrank': asdict(self.hackerrank) if self.hackerrank else None,
            'gfg': asdict(self.gfg) if self.gfg else None,
            'atcoder': asdict(self.atcoder) if self.atcoder else None,
            'interviewbit': asdict(self.interviewbit) if self.interviewbit else None,
            'kaggle': asdict(self.kaggle) if self.kaggle else None,
        }
        return result
