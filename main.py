"""Download a basketball league schedule and write selected games as iCalendar."""

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

try:
    BERLIN_TIMEZONE = ZoneInfo("Europe/Berlin")
except ZoneInfoNotFoundError:
    BERLIN_TIMEZONE = timezone(timedelta(hours=1), "Europe/Berlin")

DEFAULT_API_URLS = (
    "https://www.basketball-bund.net/rest/competition/spielplan/id/53844",
    "https://www.basketball-bund.net/rest/competition/spielplan/id/53854",
)
DEFAULT_PAGE_URL = "https://www.basketball-bund.net/static/"
DEFAULT_TEAM = "TuS Lübeck"
DEFAULT_OUTPUT = "tus_luebeck.ics"
EVENT_DURATION = timedelta(hours=2)


def fetch_schedule(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "bballics/0.1 (+https://www.basketball-bund.net/)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except (urllib.error.URLError, json.JSONDecodeError) as error:
        raise RuntimeError(
            f"Could not download or decode the schedule: {error}"
        ) from error


def _team_name(team: dict) -> str:
    team = team or {}
    return team.get("teamname") or team.get("teamName") or ""


def find_team_games(schedule: dict, team: str) -> list[dict]:
    matches = schedule.get("data", {}).get("matches", [])
    games = []
    for match in matches:
        home = _team_name(match.get("homeTeam", {}))
        guest = _team_name(match.get("guestTeam", {}))
        if team.casefold() in {home.casefold(), guest.casefold()}:
            games.append({**match, "home": home, "guest": guest})
    return sorted(
        games,
        key=lambda game: (game.get("kickoffDate", ""), game.get("kickoffTime", "")),
    )


def _ics_text(value: str) -> str:
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _event_times(game: dict) -> tuple[str, str]:
    start = datetime.strptime(
        f"{game['kickoffDate']} {game['kickoffTime']}", "%Y-%m-%d %H:%M"
    ).replace(tzinfo=BERLIN_TIMEZONE)
    end = start + EVENT_DURATION
    return start.strftime("%Y%m%dT%H%M%S"), end.strftime("%Y%m%dT%H%M%S")


def build_calendar(games: list[dict], team: str, source_url: str) -> str:
    created = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//bballics//TuS Luebeck schedule//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:TuS Lübeck Basketball",
        "X-WR-TIMEZONE:Europe/Berlin",
    ]
    for game in games:
        start, end = _event_times(game)
        match_id = game.get("matchId", game.get("matchNo"))
        status = "CANCELLED" if game.get("abgesagt") else "CONFIRMED"
        match_url = source_url.split("#", 1)[0] + f"#/spiel/{match_id}"
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:bballics-{match_id}@basketball-bund.net",
                f"DTSTAMP:{created}",
                f"DTSTART;TZID=Europe/Berlin:{start}",
                f"DTEND;TZID=Europe/Berlin:{end}",
                f"SUMMARY:{_ics_text(game['home'])} vs. {_ics_text(game['guest'])}",
                f"STATUS:{status}",
                f"DESCRIPTION:Spiel {game.get('matchNo', '')} - {_ics_text(team)}",
                f"URL:{match_url}",
                "END:VEVENT",
            ]
        )
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Export a basketball team's games as an .ics calendar."
    )
    parser.add_argument(
        "-o",
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Output file (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--team",
        default=DEFAULT_TEAM,
        help=f"Exact team name (default: {DEFAULT_TEAM})",
    )
    parser.add_argument(
        "--url",
        action="append",
        help="Schedule API URL; repeat for multiple competitions (default: league and cup)",
    )
    args = parser.parse_args()

    try:
        games_by_id = {}
        for url in args.url or DEFAULT_API_URLS:
            for game in find_team_games(fetch_schedule(url), args.team):
                game_id = game.get("matchId") or (
                    game["kickoffDate"],
                    game["kickoffTime"],
                    game["home"],
                    game["guest"],
                )
                games_by_id[game_id] = game
        games = sorted(
            games_by_id.values(),
            key=lambda game: (game["kickoffDate"], game["kickoffTime"]),
        )
        if not games:
            raise RuntimeError(f"No games found for {args.team!r}.")
        calendar = build_calendar(games, args.team, DEFAULT_PAGE_URL)
        with open(args.output, "w", encoding="utf-8", newline="") as output:
            output.write(calendar)
    except (OSError, RuntimeError, KeyError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"Wrote {len(games)} games to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
