import pytest
from param import ParameterSpecification, Missing


def test_param_spec_no_default() -> None:
    assert ParameterSpecification().default is Missing


def test_param_spec_default() -> None:
    assert ParameterSpecification(default=123).default == 123


def test_param_spec_default_factory() -> None:
    assert ParameterSpecification(default_factory=dict).default == {}


def test_param_spec_default_and_default_factory() -> None:
    with pytest.raises(ValueError):
        ParameterSpecification(default=123, default_factory=lambda: 123)