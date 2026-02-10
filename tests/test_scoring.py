import pytest

from sixnimmt.engine.scoring import bullheads


def test_bullheads_basic():
    assert bullheads(1) == 1
    assert bullheads(2) == 1
    assert bullheads(5) == 2
    assert bullheads(10) == 3
    assert bullheads(11) == 5
    assert bullheads(22) == 5
    assert bullheads(55) == 7


def test_bullheads_range():
    with pytest.raises(ValueError):
        bullheads(0)
    with pytest.raises(ValueError):
        bullheads(105)
