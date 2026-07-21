from booking.selection import order_resources, select_floors

BASE = "https://b.anny.eu/api/v1/resources"
F1 = (f"{BASE}/1-lehrbuchsammlung-eg-und-1-og/children", "449", "1. Lehrbuchsammlung EG und 1. OG")
F2 = (f"{BASE}/lesesaal-medienzentrum-xyz/children", "455", "3. Lesesaal Medienzentrum")
F3 = (f"{BASE}/2-lesesaal-naturwissenschaften/children", "452", "2a. Lesesaal Naturwissenschaften")


class TestSelectFloors:
    def test_empty_patterns_returns_all_unchanged(self):
        assert select_floors([F1, F2, F3], []) == [F1, F2, F3]

    def test_filters_to_matching_only(self):
        assert select_floors([F1, F2, F3], ["medienzentrum"]) == [F2]

    def test_orders_by_pattern_priority_not_input_order(self):
        # Medienzentrum listed first as priority even though F1 comes first in input
        result = select_floors([F1, F2, F3], ["medienzentrum", "lehrbuchsammlung"])
        assert result == [F2, F1]

    def test_matches_by_slug(self):
        # "eg-und-1-og" only appears in the slug, not the display name
        assert select_floors([F1, F2], ["eg-und-1-og"]) == [F1]

    def test_matches_by_name_case_insensitive(self):
        assert select_floors([F1, F2], ["naturwissenschaften"]) == []
        assert select_floors([F1, F2, F3], ["NATURwissen"]) == [F3]


class TestOrderResources:
    def test_empty_preferred_keeps_order(self):
        res = [("1", "449", "1.001"), ("2", "449", "1.007"), ("3", "449", "1.010")]
        assert order_resources(res, []) == res

    def test_favorite_moved_to_front(self):
        res = [("1", "449", "1.001"), ("2", "449", "1.007"), ("3", "449", "1.010")]
        assert order_resources(res, ["1.007"])[0] == ("2", "449", "1.007")

    def test_priority_order_across_multiple_favorites(self):
        res = [("1", "449", "1.001"), ("2", "449", "1.007"), ("3", "449", "1.008")]
        ordered = order_resources(res, ["1.008", "1.007"])
        assert [r[2] for r in ordered] == ["1.008", "1.007", "1.001"]

    def test_non_favorites_keep_relative_order(self):
        res = [("a", "449", "1.001"), ("b", "449", "1.007"), ("c", "449", "1.002")]
        ordered = order_resources(res, ["1.007"])
        assert [r[2] for r in ordered] == ["1.007", "1.001", "1.002"]

    def test_accepts_two_tuples_without_name(self):
        res = [("1", "449"), ("2", "449")]
        assert order_resources(res, []) == [("1", "449", ""), ("2", "449", "")]

    def test_anny_favorite_ids_prioritized(self):
        res = [("100", "449", "1.001"), ("200", "449", "1.007"), ("300", "449", "1.010")]
        ordered = order_resources(res, [], favorite_ids=["200"])
        assert ordered[0][0] == "200"

    def test_manual_names_beat_anny_favorites(self):
        res = [("100", "449", "1.001"), ("200", "449", "1.007")]
        # manual prefers 1.001, anny favorite is id 200 (1.007) → manual wins
        ordered = order_resources(res, ["1.001"], favorite_ids=["200"])
        assert [r[2] for r in ordered] == ["1.001", "1.007"]


class TestFavoriteFloors:
    def test_favorite_floors_first_when_no_patterns(self):
        result = select_floors([F1, F2, F3], [], favorite_urls=[F2[0]])
        assert result[0] == F2

    def test_patterns_override_favorites(self):
        # explicit patterns are authoritative; favorites ignored for filtering
        result = select_floors([F1, F2, F3], ["lehrbuchsammlung"], favorite_urls=[F2[0]])
        assert result == [F1]
