"""UPnP discovery for Philips Airfryer."""
import logging
import socket
import xml.etree.ElementTree as ET
from typing import Any

_LOGGER = logging.getLogger(__name__)

SSDP_DISCOVER = (
    "M-SEARCH * HTTP/1.1\r\n"
    "HOST: 239.255.255.250:1900\r\n"
    'MAN: "ssdp:discover"\r\n'
    "MX: 3\r\n"
    "ST: upnp:rootdevice\r\n"
    "\r\n"
)


def discover_airfryers(timeout: int = 5) -> list[dict[str, Any]]:
    """Discover Philips Airfryers on the network via UPnP."""
    discovered = []
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(timeout)

    try:
        sock.sendto(SSDP_DISCOVER.encode(), ("239.255.255.250", 1900))

        while True:
            try:
                data, addr = sock.recvfrom(65507)
                response = data.decode("utf-8", errors="ignore")

                # Check if this is a Philips device
                if "philips" not in response.lower():
                    continue

                # Extract location from response
                location = None
                for line in response.split("\r\n"):
                    if line.lower().startswith("location:"):
                        location = line.split(":", 1)[1].strip()
                        break

                if location:
                    device_info = _parse_device_description(location, addr[0])
                    if device_info and device_info.get("is_airfryer"):
                        discovered.append(device_info)

            except socket.timeout:
                break
            except Exception as e:
                _LOGGER.debug("Error processing UPnP response: %s", e)
                continue

    except Exception as e:
        _LOGGER.error("Error during UPnP discovery: %s", e)
    finally:
        sock.close()

    return discovered


def _parse_device_description(location: str, ip_address: str) -> dict[str, Any] | None:
    """Parse device description XML from location URL."""
    try:
        import requests

        response = requests.get(location, timeout=5)
        if response.status_code != 200:
            return None

        # Parse XML
        root = ET.fromstring(response.content)

        # Define namespaces
        ns = {"upnp": "urn:schemas-upnp-org:device-1-0"}

        # Extract device info
        device = root.find("upnp:device", ns) or root.find("device")
        if device is None:
            return None

        device_type = _get_element_text(device, "deviceType", ns)
        model_name = _get_element_text(device, "modelName", ns)
        model_number = _get_element_text(device, "modelNumber", ns)
        friendly_name = _get_element_text(device, "friendlyName", ns)

        # Check if it's an airfryer
        is_airfryer = (
            "philips" in (device_type or "").lower()
            and "venus" in (model_name or "").lower()
        )

        if not is_airfryer:
            return None

        # Detect model configuration
        model_config = detect_model_config(model_number)

        return {
            "is_airfryer": True,
            "ip_address": ip_address,
            "model_name": model_name,
            "model_number": model_number,
            "friendly_name": friendly_name,
            "suggested_model": model_config["model"],
            "config": model_config,
        }

    except Exception as e:
        _LOGGER.debug("Error parsing device description from %s: %s", location, e)
        return None


def _get_element_text(element: ET.Element, tag: str, ns: dict) -> str | None:
    """Get text from XML element with namespace support."""
    # Try with namespace
    child = element.find(f"upnp:{tag}", ns)
    if child is not None and child.text:
        return child.text

    # Try without namespace
    child = element.find(tag)
    if child is not None and child.text:
        return child.text

    return None


def detect_model_config(model_number: str | None) -> dict[str, Any]:
    """Detect configuration based on model number."""
    if not model_number:
        return {
            "model": "Other (untested)",
            "command_url": "/di/v1/products/1/airfryer",
            "airspeed": False,
            "probe": False,
            "time_remaining": "disp_time",
            "time_total": "total_time",
        }

    model_upper = model_number.upper()

    # HD9880/90 - Advanced model with airspeed and probe
    if "HD9880" in model_upper:
        return {
            "model": "HD9880/90",
            "command_url": "/di/v1/products/1/venusaf",
            "airspeed": True,
            "probe": True,
            "time_remaining": "disp_time",
            "time_total": "total_time",
        }

    # HD9875/90 - Model with probe but no airspeed
    if "HD9875" in model_upper:
        return {
            "model": "HD9875/90",
            "command_url": "/di/v1/products/1/airfryer",
            "airspeed": False,
            "probe": True,
            "time_remaining": "disp_time",
            "time_total": "total_time",
        }

    # HD9255 - Older model with different time fields
    if "HD9255" in model_upper:
        return {
            "model": "HD9255",
            "command_url": "/di/v1/products/1/airfryer",
            "airspeed": False,
            "probe": False,
            "time_remaining": "cur_time",
            "time_total": "time",
        }

    # Default configuration for unknown models
    return {
        "model": "Other (untested)",
        "command_url": "/di/v1/products/1/airfryer",
        "airspeed": False,
        "probe": False,
        "time_remaining": "disp_time",
        "time_total": "total_time",
    }
