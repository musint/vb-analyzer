"""Balltime API client and match import logic.

Combined from balltime_client.py and balltime_import.py into a single standalone module.
"""

import sys
import json
import re
import httpx
from dataclasses import dataclass, field
from collections import defaultdict


# ---------------------------------------------------------------------------
# Balltime API Client
# ---------------------------------------------------------------------------

BALLTIME_BACKEND = "https://backend.balltime.com"


class BalltimeClient:
    def __init__(self):
        self._token: str | None = None
        self._http: httpx.Client | None = None
        self._team_id: str | None = None

    @property
    def is_authenticated(self) -> bool:
        return self._token is not None

    def authenticate(self, email: str, password: str) -> dict:
        """Authenticate with Balltime by logging into Hudl via Playwright
        and capturing the Bearer token from network requests."""
        from playwright.sync_api import sync_playwright

        captured_token = None

        def on_request(request):
            nonlocal captured_token
            auth = request.headers.get("authorization", "")
            if auth.startswith("Bearer ") and "backend.balltime.com" in request.url:
                captured_token = auth.split("Bearer ", 1)[1]

        print("Launching browser to authenticate with Balltime...", file=sys.stderr)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            # Listen for requests to capture the token
            page.on("request", on_request)

            # Step 1: Log into Hudl (two-step: email first, then password)
            print("  Logging into Hudl...", file=sys.stderr)
            page.goto("https://www.hudl.com/login")
            page.wait_for_load_state("networkidle")

            # Enter email and submit
            email_input = page.locator('input[type="email"]:visible, input[name="username"]:visible').first
            email_input.fill(email)
            email_input.press("Enter")
            page.wait_for_timeout(2000)

            # Enter password (appears after email step)
            pw_input = page.locator('input[type="password"]:visible').first
            pw_input.fill(password)
            pw_input.press("Enter")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(3000)

            # Step 2: Navigate to Balltime stats page
            print("  Loading Balltime stats page...", file=sys.stderr)
            page.goto("https://app.hudl.com/bt/stats")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(5000)  # Give Auth0 time to exchange tokens

            # If we haven't captured a token yet, try navigating to trigger API calls
            if not captured_token:
                print("  Waiting for API calls...", file=sys.stderr)
                page.wait_for_timeout(5000)

            # Try clicking on something to trigger more API calls
            if not captured_token:
                print("  Triggering API activity...", file=sys.stderr)
                try:
                    page.goto("https://app.hudl.com/bt/stats")
                    page.wait_for_timeout(5000)
                except Exception:
                    pass

            browser.close()

        if captured_token:
            self._token = captured_token
            self._http = httpx.Client(
                base_url=BALLTIME_BACKEND,
                timeout=30.0,
                headers={
                    "Authorization": f"Bearer {captured_token}",
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                },
            )
            print("  Balltime authentication successful!", file=sys.stderr)
            return {"ok": True}
        else:
            print("  Failed to capture Balltime token.", file=sys.stderr)
            return {"ok": False, "error": "Could not capture Bearer token from Balltime"}

    def _get(self, path: str) -> dict:
        """Make an authenticated GET request."""
        if not self._http:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        resp = self._http.get(f"/{path}")
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, body: dict = None) -> dict:
        """Make an authenticated POST request."""
        if not self._http:
            raise RuntimeError("Not authenticated. Call authenticate() first.")
        resp = self._http.post(f"/{path}", json=body or {})
        resp.raise_for_status()
        return resp.json()

    def get_user_data(self) -> dict:
        """Get current user data from Balltime."""
        return self._get("user-management/user-data")

    def get_teams(self) -> list:
        """Get teams from Balltime."""
        data = self._get("user-management/teams")
        return data if isinstance(data, list) else data.get("teams", [])

    def get_videos_metadata(self, video_ids: list[str] = None) -> dict:
        """Get metadata for videos."""
        body = {}
        if video_ids:
            body["video_ids"] = video_ids
        return self._post("videos-metadata", body)

    def generate_multi_video_stats(self, video_ids: list[str]) -> dict:
        """Generate aggregated stats across multiple videos (the Report view)."""
        return self._post("generate-multi-video-stats", {"video_ids": video_ids})

    def actions_export(self, video_ids: list[str] = None) -> dict:
        """Export all actions (the CSV export functionality)."""
        body = {}
        if video_ids:
            body["video_ids"] = video_ids
        return self._post("library/actions-export", body)

    def get_report(self, report_id: str) -> dict:
        """Get a saved report."""
        return self._get(f"reports/report/{report_id}")

    def generate_insights_stats(self, video_ids: list[str]) -> dict:
        """Generate insights stats."""
        return self._post("generate-insights-stats", {"video_ids": video_ids})

    def generate_trends_stats(self, video_ids: list[str]) -> dict:
        """Generate trends stats."""
        return self._post("generate-trends-stats", {"video_ids": video_ids})

    def raw_get(self, path: str) -> dict:
        """Make a raw GET request for exploration."""
        if not self._http:
            raise RuntimeError("Not authenticated.")
        resp = self._http.get(f"/{path}")
        return {"status": resp.status_code, "body": resp.json() if resp.status_code == 200 else resp.text[:2000]}

    def raw_post(self, path: str, body: dict = None) -> dict:
        """Make a raw POST request for exploration."""
        if not self._http:
            raise RuntimeError("Not authenticated.")
        resp = self._http.post(f"/{path}", json=body or {})
        return {"status": resp.status_code, "body": resp.json() if resp.status_code == 200 else resp.text[:2000]}


# ---------------------------------------------------------------------------
# Data classes and match import logic
# ---------------------------------------------------------------------------

@dataclass
class Rally:
    """A single rally with all its actions and outcome."""
    rally_id: int
    set_number: int  # 1-based
    actions: list[dict] = field(default_factory=list)
    point_winner: str = ""  # "us" or "them"
    our_score_after: int = 0
    opp_score_after: int = 0
    serving_team: str = ""  # "us" or "them"


@dataclass
class MatchData:
    """Full processed data for one match."""
    video_id: str
    title: str
    date: str
    set_scores: list[dict] = field(default_factory=list)  # [{"a": 26, "b": 24}, ...]
    sets_won: int = 0
    sets_lost: int = 0
    rallies: list[Rally] = field(default_factory=list)
    raw_actions: list[dict] = field(default_factory=list)
    our_team_name: str = ""


def _determine_rally_winner(actions: list[dict], our_team: str) -> str:
    """Determine who won a rally based on the last terminal action."""
    if not actions:
        return ""

    last = actions[-1]
    quality = str(last.get("quality") or "").lower()
    team = last.get("team", "")
    action_type = (last.get("action_type") or "").lower()
    is_us = team == our_team

    if quality == "kill" or quality == "ace":
        return "us" if is_us else "them"
    elif quality == "error":
        return "them" if is_us else "us"
    elif quality == "block_kill":
        return "us" if is_us else "them"

    # Look backwards for terminal actions
    for a in reversed(actions):
        q = str(a.get("quality") or "").lower()
        t = a.get("team", "")
        is_us_a = t == our_team
        if q in ("kill", "ace", "block_kill"):
            return "us" if is_us_a else "them"
        elif q == "error":
            return "them" if is_us_a else "us"

    return ""


def _determine_serving_team(actions: list[dict], our_team: str) -> str:
    """Determine who served based on the first action."""
    for a in actions:
        if (a.get("action_type") or "").lower() == "serve":
            return "us" if a.get("team") == our_team else "them"
    return ""


def process_match(video: dict, raw_actions: list[dict], our_team: str) -> MatchData:
    """Process raw actions into a structured MatchData."""
    score_data = video.get("score", {})
    set_scores = score_data.get("sets", [])

    match = MatchData(
        video_id=video["id"],
        title=video.get("title", ""),
        date=video.get("date", "")[:10],
        set_scores=set_scores,
        sets_won=score_data.get("team_a_sets_won", 0),
        sets_lost=score_data.get("team_b_sets_won", 0),
        raw_actions=raw_actions,
        our_team_name=our_team,
    )

    # Group actions by rally_id
    rallies_map = defaultdict(list)
    for a in raw_actions:
        rallies_map[a["rally_id"]].append(a)

    # Build rallies with running score
    set_number = 1
    our_score = 0
    opp_score = 0
    max_set_score = set_scores[0] if set_scores else {"a": 25, "b": 25}

    for rid in sorted(rallies_map.keys()):
        actions = rallies_map[rid]
        winner = _determine_rally_winner(actions, our_team)
        serving = _determine_serving_team(actions, our_team)

        if winner == "us":
            our_score += 1
        elif winner == "them":
            opp_score += 1

        rally = Rally(
            rally_id=rid,
            set_number=set_number,
            actions=actions,
            point_winner=winner,
            our_score_after=our_score,
            opp_score_after=opp_score,
            serving_team=serving,
        )
        match.rallies.append(rally)

        # Check for set transition
        if set_number <= len(set_scores):
            expected = set_scores[set_number - 1]
            if our_score >= expected.get("a", 99) and opp_score >= expected.get("b", 99):
                set_number += 1
                our_score = 0
                opp_score = 0
            elif our_score >= expected.get("a", 99) or opp_score >= expected.get("b", 99):
                # One team won this set
                set_number += 1
                our_score = 0
                opp_score = 0

    return match


def import_all_matches(bt: BalltimeClient) -> list[MatchData]:
    """Import all match actions from Balltime for the 13-2 Blue team."""
    data = bt.raw_get("library/videos")["body"]
    videos = data.get("videos", [])

    team_id_132 = "ac699a8b-d173-50a0-8b26-ebbbd25ceb01"
    match_videos = [
        v for v in videos
        if v.get("team_id") == team_id_132
        and v.get("video_type") == "match"
        and v.get("stats_status") == "stats_available"
    ]
    match_videos.sort(key=lambda v: v.get("date", ""))

    our_team = "NorCal 13-2 Blue"
    matches = []

    print(f"Importing {len(match_videos)} matches...", file=sys.stderr)
    for i, v in enumerate(match_videos):
        try:
            r = bt.raw_post("library/actions-export", {"video_id": v["id"]})
            if r["status"] != 200:
                print(f"  [{i+1}] {v['title'][:30]:30s} - ERROR {r['status']}", file=sys.stderr)
                continue
            rows = r["body"].get("rows", [])
            match = process_match(v, rows, our_team)
            matches.append(match)
            print(
                f"  [{i+1}] {v['title'][:30]:30s} {v['date'][:10]}  "
                f"{len(rows):4d} actions  {len(match.rallies):3d} rallies  "
                f"{match.sets_won}-{match.sets_lost}",
                file=sys.stderr,
            )
        except Exception as e:
            print(f"  [{i+1}] {v['title'][:30]:30s} - ERROR: {e}", file=sys.stderr)

    print(f"\nImported {len(matches)} matches", file=sys.stderr)
    return matches
