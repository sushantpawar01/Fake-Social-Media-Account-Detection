import re
import requests
from urllib.parse import urlparse

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36"
}

PLATFORM_PATTERNS = {
    "instagram": r"instagram\.com/([^/?#]+)",
    "twitter":   r"(?:twitter|x)\.com/([^/?#]+)",
    "facebook":  r"facebook\.com/([^/?#]+)",
    "github":    r"github\.com/([^/?#]+)",
    "linkedin":  r"linkedin\.com/in/([^/?#]+)",
    "tiktok":    r"tiktok\.com/@([^/?#]+)",
    "youtube":   r"youtube\.com/(?:@|c/|user/)?([^/?#]+)",
}


def parse_url(url: str) -> dict:
    """Return {platform, username} from a profile URL."""
    url = url.strip()
    for platform, pattern in PLATFORM_PATTERNS.items():
        m = re.search(pattern, url, re.IGNORECASE)
        if m:
            username = m.group(1).strip("/").strip()
            if username and username not in ("home", "explore", "reel", "p", "stories"):
                return {"platform": platform, "username": username}
    # fallback: use last path segment
    path = urlparse(url).path.strip("/").split("/")[-1]
    return {"platform": "unknown", "username": path or "unknown"}


def fetch_github(username: str) -> dict:
    """Fetch real public data from GitHub API (no auth needed)."""
    try:
        r = requests.get(f"https://api.github.com/users/{username}", headers=HEADERS, timeout=8)
        if r.status_code == 200:
            d = r.json()
            return {
                "username": d.get("login", username),
                "bio": d.get("bio") or "",
                "followers": d.get("followers", 0),
                "following": d.get("following", 0),
                "posts": d.get("public_repos", 0),
                "account_age_days": _age_days(d.get("created_at", "")),
                "has_profile_pic": 0 if "avatars/u/" in (d.get("avatar_url") or "") else 1,
                "is_verified": 0,
                "platform": "github",
                "age_source": "github-api",
            }
    except Exception:
        pass
    return None


def fetch_by_url(url: str) -> dict:
    url = url.strip()
    if not url.startswith("http"):
        url = "https://" + url

    info = parse_url(url)
    platform = info["platform"]
    username = info["username"]

    if platform == "github":
        data = fetch_github(username)
        if data is not None:
            return data
        return _scrape_page(url, username, platform)

    if platform == "instagram":
        return _fetch_instagram(url, username)

    if platform == "youtube":
        about_url = url.rstrip("/") + "/about"
        return _scrape_page(about_url, username, platform)

    return _scrape_page(url, username, platform)


def _fetch_instagram(url: str, username: str) -> dict:
    """Fetch Instagram profile - tries multiple User-Agent strings to get og:description."""
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
        "Twitterbot/1.0",
    ]
    for agent in agents:
        try:
            r = requests.get(url, headers={**HEADERS, "User-Agent": agent}, timeout=10)
            d = _parse_instagram(r.text, username)
            if d["followers"] > 0 or d["posts"] > 0:
                return d
        except Exception:
            continue
    return _empty_profile(username, "instagram")


def _scrape_page(url: str, username: str, platform: str) -> dict:
    """Extract signals from raw HTML of a public profile page."""
    bio = ""
    has_profile_pic = 0
    followers = 0
    following = 0
    posts = 0
    account_age_days = 365
    age_source = "default"

    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        html = r.text

        # --- Bio: meta description ---
        m = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', html, re.IGNORECASE)
        if not m:
            m = re.search(r'<meta[^>]+content=["\'](.*?)["\'][^>]+name=["\']description["\']', html, re.IGNORECASE)
        if m:
            bio = m.group(1)[:200]

        # --- Profile picture ---
        if re.search(r'profile.?pic|profile.?photo|avatar|profile.?image', html, re.IGNORECASE):
            has_profile_pic = 1

        # --- Followers / Following / Posts ---
        nums = re.findall(r'([\d,\.]+[KkMm]?)\s*(?:Followers?|followers?)', html)
        if nums:
            followers = _parse_num(nums[0])

        nums2 = re.findall(r'([\d,\.]+[KkMm]?)\s*(?:Following|following)', html)
        if nums2:
            following = _parse_num(nums2[0])

        nums3 = re.findall(r'([\d,\.]+[KkMm]?)\s*(?:Posts?|posts?|Tweets?|tweets?|Videos?|Shorts?)', html)
        if nums3:
            posts = _parse_num(nums3[0])

        # --- Account join date extraction ---
        age, source = _extract_join_date(html, platform)
        if age:
            account_age_days = age
            age_source = source

    except Exception:
        pass

    return {
        "username": username,
        "bio": bio,
        "followers": followers,
        "following": following,
        "posts": posts,
        "account_age_days": account_age_days,
        "age_source": age_source,
        "has_profile_pic": has_profile_pic,
        "is_verified": 0,
        "platform": platform,
    }


def _empty_profile(username: str, platform: str) -> dict:
    return {"username": username, "bio": "", "followers": 0, "following": 0,
            "posts": 0, "account_age_days": 365, "age_source": "default",
            "has_profile_pic": 0, "is_verified": 0, "platform": platform}


def _parse_instagram(html: str, username: str) -> dict:
    """Parse Instagram profile data from og:description meta tag."""
    followers = 0
    following = 0
    posts     = 0
    bio       = ""
    has_pic   = 1  # Instagram always shows profile pic in og:image
    verified  = 0

    # og:description = "673M Followers, 643 Following, 4,026 Posts - ..."
    # Instagram HTML uses escaped quotes: property="og:description" content="..."
    m = re.search(r'property=.og:description.\s+content=.([^"<]+)', html, re.IGNORECASE)
    if not m:
        m = re.search(r'content=.([^"<]*?\d+[MKmk]?\s*Followers[^"<]*)', html, re.IGNORECASE)

    if m:
        desc = m.group(1)
        # Extract followers
        fm = re.search(r'([\d,\.]+[KkMm]?)\s*Followers?', desc, re.IGNORECASE)
        if fm:
            followers = _parse_num(fm.group(1))
        # Extract following
        fm2 = re.search(r'([\d,\.]+[KkMm]?)\s*Following', desc, re.IGNORECASE)
        if fm2:
            following = _parse_num(fm2.group(1))
        # Extract posts
        fm3 = re.search(r'([\d,\.]+[KkMm]?)\s*Posts?', desc, re.IGNORECASE)
        if fm3:
            posts = _parse_num(fm3.group(1))
        # Bio is text after the dash
        bio_m = re.search(r'-\s*(.+?)(?:on Instagram|$)', desc)
        if bio_m:
            bio = bio_m.group(1).strip()[:200]

    # Check verified badge in page
    if re.search(r'"is_verified"\s*:\s*true', html, re.IGNORECASE):
        verified = 1

    # Account age: Instagram rarely exposes join date, use fallback
    age, source = _extract_join_date(html, "instagram")
    account_age_days = age if age else 365
    age_source = source if source else "default"

    return {
        "username": username,
        "bio": bio,
        "followers": followers,
        "following": following,
        "posts": posts,
        "account_age_days": account_age_days,
        "age_source": age_source,
        "has_profile_pic": has_pic,
        "is_verified": verified,
        "platform": "instagram",
    }


def _extract_join_date(html: str, platform: str):
    """
    Try every known pattern to extract account creation date from HTML.
    Returns (age_in_days, source_label) or (None, None).
    """
    from datetime import datetime, timezone

    def to_days(dt):
        try:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            days = (datetime.now(timezone.utc) - dt).days
            return max(1, days) if days < 36500 else None  # sanity: ignore >100yr
        except Exception:
            return None

    def parse_dt(s):
        """Try multiple datetime formats."""
        s = s.strip()
        fmts = [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%B %d, %Y",
            "%b %d, %Y",
            "%d %B %Y",
            "%d %b %Y",
            "%B %Y",
            "%b %Y",
        ]
        for fmt in fmts:
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                continue
        return None

    # 1. JSON-LD structured data  {"dateCreated": "...", "foundingDate": "..."}
    for key in ("dateCreated", "foundingDate", "startDate", "datePublished", "uploadDate"):
        for m in re.finditer(rf'"{key}"\s*:\s*"([^"]+)"', html):
            dt = parse_dt(m.group(1))
            if dt:
                d = to_days(dt)
                if d:
                    return d, f"json-ld:{key}"

    # 2. <time> HTML element with datetime attribute
    for m in re.finditer(r'<time[^>]+datetime=["\']([^"\']+)["\']', html, re.IGNORECASE):
        dt = parse_dt(m.group(1))
        if dt:
            d = to_days(dt)
            if d:
                return d, "time-element"

    # 3. Open Graph / meta property dates
    for prop in ("article:published_time", "og:updated_time", "profile:creation_time"):
        m = re.search(
            rf'<meta[^>]+property=["\']{{prop}}["\'][^>]+content=["\']([^"\']+)["\']'.replace("{prop}", prop),
            html, re.IGNORECASE
        )
        if m:
            dt = parse_dt(m.group(1))
            if dt:
                d = to_days(dt)
                if d:
                    return d, f"og:{prop}"

    # 4. Platform-specific visible text patterns
    #    Twitter/X: "Joined March 2020"
    m = re.search(r'Joined\s+([A-Za-z]+\s+\d{4})', html)
    if m:
        dt = parse_dt(m.group(1))
        if dt:
            d = to_days(dt)
            if d:
                return d, "joined-text"

    #    YouTube: "Joined Mar 15, 2012" or "Joined 15 Mar 2012"
    #    Also handles YouTube's joinedDateText JSON field from /about page
    m = re.search(r'joinedDateText[^}]{0,120}"content"\s*:\s*"([^"]+)"', html)
    if m:
        raw = re.sub(r'^Joined\s+', '', m.group(1).strip())
        dt = parse_dt(raw)
        if dt:
            d = to_days(dt)
            if d:
                return d, "joined-text"

    m = re.search(r'Joined\s+([A-Za-z]+ \d{1,2},? \d{4}|\d{1,2} [A-Za-z]+ \d{4})', html)
    if m:
        dt = parse_dt(m.group(1).replace(",", ""))
        if dt:
            d = to_days(dt)
            if d:
                return d, "joined-text"

    #    Facebook: "Joined Facebook in March 2010" or "Member since March 2010"
    m = re.search(r'(?:Joined Facebook in|Member since)\s+([A-Za-z]+ \d{4})', html, re.IGNORECASE)
    if m:
        dt = parse_dt(m.group(1))
        if dt:
            d = to_days(dt)
            if d:
                return d, "joined-text"

    #    LinkedIn: "member since" or "on LinkedIn since"
    m = re.search(r'(?:on LinkedIn since|member since)\s+([A-Za-z]+ \d{4})', html, re.IGNORECASE)
    if m:
        dt = parse_dt(m.group(1))
        if dt:
            d = to_days(dt)
            if d:
                return d, "linkedin-since"

    # 5. Generic ISO date near account/profile/created keywords
    for m in re.finditer(
        r'(?:created|registered|joined|since|member)[^"]{0,60}(\d{4}-\d{2}-\d{2})',
        html, re.IGNORECASE
    ):
        dt = parse_dt(m.group(1))
        if dt:
            d = to_days(dt)
            if d:
                return d, "keyword-iso"

    # 6. Any ISO datetime string in the page (last resort)
    for m in re.finditer(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)', html):
        dt = parse_dt(m.group(1))
        if dt:
            d = to_days(dt)
            if d and d > 30:   # ignore very recent timestamps (post dates etc)
                return d, "iso-fallback"

    return None, None


def _age_days(created_at: str) -> int:
    if not created_at:
        return 365
    try:
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        return max(1, (datetime.now(timezone.utc) - dt).days)
    except Exception:
        return 365


def _parse_num(s: str) -> int:
    s = s.strip().replace(",", "")
    try:
        if s[-1] in "Kk":
            return int(float(s[:-1]) * 1000)
        if s[-1] in "Mm":
            return int(float(s[:-1]) * 1_000_000)
        return int(float(s))
    except Exception:
        return 0
