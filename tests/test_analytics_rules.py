from decimal import Decimal as D

from services.analytics_rules import category_summary, month_cell, rankings, round_up

NONE = (0, D("0"))


def cell(spent, allocated, tin=NONE, tout=NONE, month="2026-05"):
    allocated = None if allocated is None else D(str(allocated))
    return month_cell(month, D(str(spent)), allocated, tin, tout, active=bool(spent or tin[0] or tout[0]))


class TestMonthCell:
    def test_over_allocation(self):
        c = cell(3450, 3000)
        assert c["over"] and c["uncovered"] and not c["tight"]
        assert round(c["percent"]) == 115

    def test_top_up_covers_the_overrun_but_it_still_counts_as_over(self):
        c = cell(3450, 3000, tin=(1, D("500")))
        assert c["over"] and not c["uncovered"]

    def test_ninety_to_ninety_nine_percent_is_tight(self):
        assert cell(2700, 3000)["tight"] and cell(2999, 3000)["tight"]
        assert not cell(2690, 3000)["tight"]

    def test_exactly_on_plan_is_neutral(self):
        c = cell(25000, 25000)
        assert not c["over"] and not c["tight"]

    def test_no_snapshot_means_no_judgement(self):
        c = cell(5000, None)
        assert c["percent"] is None and not c["over"] and not c["tight"] and c["active"]

    def test_no_activity(self):
        assert not cell(0, 3000)["active"]


def eating_out():
    # Prototype history: over in 5 of 6 months, topped up in some of them.
    spends = [3750, 3300, 3900, 4200, 3600, 1500]
    tops = [(1, D("1000")), NONE, (1, D("1000")), NONE, (1, D("1000")), NONE]
    cells = [cell(s, 3000, tin=t, month=f"2026-0{i + 4}") for i, (s, t) in enumerate(zip(spends, tops))]
    return category_summary(9, "Eating out", D("3000"), cells)


def test_eating_out_is_squeezed_with_a_tip():
    s = eating_out()
    assert (s["months"], s["over"], s["top_ups"]) == (6, 5, 3)
    assert s["uncovered"] == 2          # the two overruns without a top-up
    assert s["average"] == D("3375")
    assert s["suggested"] == D("3400")  # average rounded up to 100


def test_average_that_fits_gives_no_suggestion():
    cells = [cell(s, 3000) for s in (3200, 1000, 1000, 1000)]
    assert category_summary(1, "Gifts", D("3000"), cells)["suggested"] is None


def test_rankings():
    squeezed = eating_out()
    spare = category_summary(6, "Entertainment", D("4000"),
                             [cell(s, 4000, tout=(1, D("500"))) for s in (1600, 2200, 1200, 2400)])
    once = category_summary(4, "Utilities", D("6360"), [cell(s, 6360) for s in (6500, 6000, 5800)])
    r = rankings([once, spare, squeezed])
    assert [s["name"] for s in r["squeezed"]] == ["Eating out"]
    assert [s["name"] for s in r["room_to_spare"]] == ["Entertainment"]
    assert r["order"][0]["name"] == "Eating out"
    assert [s["name"] for s in r["topped_up_most"]] == ["Eating out"]
    assert [s["name"] for s in r["gave_most"]] == ["Entertainment"]
    assert spare["gave"] == D("2000")


def test_round_up():
    assert round_up(D("3375")) == D("3400")
    assert round_up(D("3400")) == D("3400")
