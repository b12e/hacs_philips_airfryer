"""Philips Airfryer API client."""
import base64
import hashlib
import json
import logging
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from requests.packages.urllib3.exceptions import InsecureRequestWarning

_LOGGER = logging.getLogger(__name__)

# Disable SSL warnings for local device communication
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class AirfryerAPI:
    """API client for Philips Airfryer."""

    def __init__(
        self,
        ip_address: str,
        client_id: str,
        client_secret: str,
        command_url: str = "/di/v1/products/1/airfryer",
    ) -> None:
        """Initialize the API client."""
        self.ip_address = ip_address
        self.client_id = client_id
        self.client_secret = client_secret
        self.command_url = command_url
        self.token = ""

        # Create session with custom settings to prevent connection reuse issues
        self.session = requests.Session()
        # Configure adapter with connection settings
        adapter = HTTPAdapter(
            pool_connections=1,
            pool_maxsize=1,
            max_retries=Retry(total=0, connect=0, read=0, redirect=0, status=0),
            pool_block=False
        )
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)

    def _decode(self, txt: str) -> bytes:
        """Decode base64 string."""
        return base64.standard_b64decode(txt)

    def _get_auth(self, challenge: str) -> str:
        """Generate authentication token."""
        vvv = (
            self._decode(challenge)
            + self._decode(self.client_id)
            + self._decode(self.client_secret)
        )
        myhash = hashlib.sha256(vvv).hexdigest()
        myhashhex = bytes.fromhex(myhash)
        res = self._decode(self.client_id) + myhashhex
        encoded = base64.b64encode(res)
        return encoded.decode("ascii")

    def get_status(self) -> dict[str, Any] | None:
        """Get current status from the airfryer."""
        if self.token:
            headers = {
                "User-Agent": "cml",
                "Content-Type": "application/json",
                "Authorization": f"PHILIPS-Condor {self.token}",
                "Connection": "close",
            }
        else:
            headers = {
                "User-Agent": "cml",
                "Content-Type": "application/json",
                "Connection": "close",
            }

        try:
            response = self.session.get(
                f"https://{self.ip_address}{self.command_url}",
                headers=headers,
                verify=False,
                timeout=10,
            )
        except requests.exceptions.RequestException as e:
            _LOGGER.error("Failed to get status: %s", e)
            return None

        try:
            if response.status_code == 401:
                # Need to authenticate
                challenge = response.headers.get("WWW-Authenticate", "")
                challenge = challenge.replace("PHILIPS-Condor ", "")
                self.token = self._get_auth(challenge)
                _LOGGER.info("New token generated")
                # Retry with new token
                return self.get_status()
            elif response.status_code != 200:
                _LOGGER.error("Status request failed with code: %s", response.status_code)
                return None
            else:
                try:
                    data = response.json()
                    return data
                except json.JSONDecodeError:
                    _LOGGER.error("Failed to decode JSON response")
                    return None
        finally:
            # Always close the response to free up connection
            response.close()

    def send_command(self, command: dict[str, Any]) -> dict[str, Any] | None:
        """Send a command to the airfryer."""
        headers = {
            "User-Agent": "cml",
            "Content-Type": "application/json",
            "Authorization": f"PHILIPS-Condor {self.token}",
            "Connection": "close",
        }

        try:
            response = self.session.put(
                f"https://{self.ip_address}{self.command_url}",
                headers=headers,
                data=json.dumps(command),
                verify=False,
                timeout=10,
            )
        except requests.exceptions.RequestException as e:
            _LOGGER.error("Failed to send command: %s", e)
            return None

        try:
            if response.status_code != 200:
                _LOGGER.error("Command failed with code: %s", response.status_code)
                return None
            else:
                try:
                    data = response.json()
                    return data
                except json.JSONDecodeError:
                    _LOGGER.error("Failed to decode JSON response")
                    return None
        finally:
            # Always close the response to free up connection
            response.close()

    def test_connection(self) -> bool:
        """Test the connection to the airfryer."""
        result = self.get_status()
        return result is not None
