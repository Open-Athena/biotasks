from bt60_core import answer

def test_regression():
    assert answer() == 1

def test_stable():
    assert isinstance(answer(), int)
