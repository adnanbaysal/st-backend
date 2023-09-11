from http import HTTPStatus

import requests

from tests.integration.conftest import delete_users_after_test

root_auth_url = "http://localhost:1337/api/v1/auth/"


@delete_users_after_test
def test_signup():
    signup_url = root_auth_url + "signup"
    signup_payload = {"email": "fredymercury@gmail.com", "password": "password"}
    response = requests.post(signup_url, data=signup_payload)

    assert response.status_code == HTTPStatus.OK.value
    assert "refresh" in response.json()
    assert "access" in response.json()
