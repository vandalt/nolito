import pytest

from nolito.errors import NolioApiError, NolitoError, OAuthFlowError


@pytest.mark.parametrize("error_type", [OAuthFlowError, NolioApiError])
def test_package_errors_inherit_base_exception(error_type):
    assert isinstance(error_type("failure"), NolitoError)
