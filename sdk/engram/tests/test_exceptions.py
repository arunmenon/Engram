from __future__ import annotations

from engram.exceptions import (
    AuthenticationError,
    ConfigurationError,
    EngramError,
    NotFoundError,
    RateLimitError,
    ServerError,
    TransportError,
    ValidationError,
)


class TestExceptionHierarchy:
    def test_engram_error_hierarchy(self):
        assert issubclass(TransportError, EngramError)
        assert issubclass(AuthenticationError, EngramError)
        assert issubclass(RateLimitError, EngramError)
        assert issubclass(ValidationError, EngramError)
        assert issubclass(NotFoundError, EngramError)
        assert issubclass(ServerError, EngramError)
        assert issubclass(ConfigurationError, EngramError)

    def test_transport_error_attrs(self):
        err = TransportError("failed", status_code=500, response_body={"detail": "bad"})
        assert err.status_code == 500
        assert err.response_body == {"detail": "bad"}
        assert str(err) == "failed"

    def test_rate_limit_error_retry_after(self):
        err = RateLimitError("too fast", retry_after=2.5)
        assert err.retry_after == 2.5
        assert err.status_code == 429

    def test_validation_error_errors_list(self):
        errors = [{"loc": ["body", "event_type"], "msg": "required"}]
        err = ValidationError("invalid", errors=errors)
        assert err.errors == errors
        assert str(err) == "invalid"

    def test_authentication_error_is_transport(self):
        err = AuthenticationError("unauthorized", status_code=401)
        assert isinstance(err, TransportError)
        assert isinstance(err, EngramError)
        assert err.status_code == 401
