"""Pure floor/resource selection & prioritization helpers.

Kept free of any network or config imports so they are trivially unit-testable.
"""


def _slug(url):
    return url.split('/')[-2].lower()


def select_floors(floor_tuples, patterns, favorite_urls=()):
    """Filter and order floors by preference.

    floor_tuples : iterable of (url, service_id, name)
    patterns     : list of lowercase substrings, in priority order.
    favorite_urls: floor urls starred in anny (only used when patterns is empty).

    patterns set  → authoritative filter: only floors matching a pattern, in that
                    priority order (manual config wins; favorites ignored).
    patterns empty→ all floors, but favorited floors first (in favorite order),
                    then the rest in their original order.
    """
    floors = list(floor_tuples)
    if patterns:
        pats = [p.lower() for p in patterns]
        ranked = []
        for url, svc, name in floors:
            slug, low = _slug(url), (name or '').lower()
            rank = next((i for i, p in enumerate(pats) if p in slug or p in low), None)
            if rank is not None:
                ranked.append((rank, url, svc, name))
        ranked.sort(key=lambda x: x[0])
        return [(url, svc, name) for _, url, svc, name in ranked]

    if favorite_urls:
        fav_rank = {u: i for i, u in enumerate(favorite_urls)}
        return sorted(floors, key=lambda f: fav_rank.get(f[0], len(fav_rank)))

    return floors


def order_resources(resources, preferred_names=(), favorite_ids=()):
    """Order resources so favorites come first (a preference, not a filter).

    resources     : iterable of (id, service_id, name) — name optional per item.
    preferred_names: manual PREFERRED_RESOURCES substrings (highest priority).
    favorite_ids  : resource ids starred in anny (next priority).
    Order: manual name matches → anny favorites → everything else. Stable within
    each tier (non-favorites keep their relative order).
    """
    res = [(r[0], r[1], r[2] if len(r) > 2 else '') for r in resources]
    if not preferred_names and not favorite_ids:
        return res

    names = [p.lower() for p in preferred_names]
    fav = {str(i): n for n, i in enumerate(favorite_ids)}

    def rank(item):
        rid, _svc, name = item
        low = (name or '').lower()
        for i, p in enumerate(names):
            if p in low:
                return (0, i)          # manual favorites first
        if str(rid) in fav:
            return (1, fav[str(rid)])  # anny favorites next
        return (2, 0)                  # everything else

    return sorted(res, key=rank)
