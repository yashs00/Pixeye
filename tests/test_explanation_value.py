from cqse.ingest.explanation import final_value


def test_explicit_answers_are_high_confidence():
    assert final_value("<p>Total = 7 x 3 + 6 x 2 = 33</p><p>Ans. 33</p>") == ("33", "high")
    assert final_value("So, the value of x is 3.") == ("3", "high")
    assert final_value(r"$$\boxed{23 \times 10^2}$$") == ("23", "high")


def test_final_equation_is_medium_confidence():
    assert final_value(r"$$\Rightarrow \alpha=1011 \end{aligned}$$") == ("1011", "medium")
    assert final_value(r"$$\Rightarrow T = {57^\circ }$$ C") == ("57", "medium")
    assert final_value(r"$$=19.85 \%$$") == ("19.85", "medium")


def test_no_clear_value_returns_none():
    assert final_value("Which is not possible as x is in [0, pi]. No solution") == (None, None)
    assert final_value(r"$$k = 2 \times {10^{-3}} s^{-1}$$") == (None, None)  # scientific form: not guessed
    assert final_value("") == (None, None)
