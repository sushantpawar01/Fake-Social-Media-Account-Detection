import re

def extract_features(data: dict) -> dict:
    username = data.get("username", "")
    bio = data.get("bio", "")
    followers = int(data.get("followers", 0))
    following = int(data.get("following", 0))
    posts = int(data.get("posts", 0))
    account_age_days = int(data.get("account_age_days", 1))
    has_profile_pic = int(data.get("has_profile_pic", 0))
    is_verified = int(data.get("is_verified", 0))

    follower_following_ratio = followers / (following + 1)
    posts_per_day = posts / (account_age_days + 1)
    bio_length = len(bio)
    username_digit_ratio = sum(c.isdigit() for c in username) / (len(username) + 1)
    username_has_random = 1 if re.search(r'\d{4,}', username) else 0

    return {
        "follower_following_ratio": round(follower_following_ratio, 4),
        "posts_per_day": round(posts_per_day, 4),
        "bio_length": bio_length,
        "username_digit_ratio": round(username_digit_ratio, 4),
        "username_has_random": username_has_random,
        "has_profile_pic": has_profile_pic,
        "is_verified": is_verified,
        "followers": followers,
        "following": following,
        "posts": posts,
        "account_age_days": account_age_days,
    }
