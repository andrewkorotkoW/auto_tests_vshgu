from typing import Iterable, Union

import requests


def expect_status(resp: requests.Response, expected_status: Union[int, Iterable[int]]) -> requests.Response:
    """Проверяет статус ответа, при несовпадении бросает AssertionError с телом ответа."""
    expected = (expected_status,) if isinstance(expected_status, int) else tuple(expected_status)
    if resp.status_code not in expected:
        raise AssertionError(
            f"Unexpected status {resp.status_code} (expected {expected}): {resp.text}"
        )
    return resp
