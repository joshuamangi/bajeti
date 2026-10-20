"""Bearer tokens must never be written to the logs."""
import logging

SECRET_LOOKING_TOKEN = "not.a.real.jwt-aaaaaaaaaaaaaaaaaaaa"


def test_invalid_token_is_not_logged(client, caplog):
    with caplog.at_level(logging.DEBUG):
        response = client.get(
            "/api/auth/users/me",
            headers={"Authorization": f"Bearer {SECRET_LOOKING_TOKEN}"},
        )

    assert response.status_code == 401
    assert SECRET_LOOKING_TOKEN not in caplog.text
    assert "JWT decoding failed" in caplog.text  # still logs that it failed
