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
    _LOGGER.debug("Starting UPnP discovery for Philips Airfryers")
    discovered = []
    seen_ips = set()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(timeout)

    try:
        sock.sendto(SSDP_DISCOVER.encode(), ("239.255.255.250", 1900))
        _LOGGER.debug("Sent SSDP M-SEARCH request")

        response_count = 0
        while True:
            try:
                data, addr = sock.recvfrom(65507)
                response_count += 1
                response = data.decode("utf-8", errors="ignore")

                _LOGGER.debug("Received UPnP response %d from %s", response_count, addr[0])

                # Check if this is a Philips device
                if "philips" not in response.lower():
                    _LOGGER.debug("Response from %s is not a Philips device", addr[0])
                    continue

                # Skip if we've already processed this IP
                if addr[0] in seen_ips:
                    _LOGGER.debug("Already processed device at %s", addr[0])
                    continue

                seen_ips.add(addr[0])

                # Extract location from response
                location = None
                for line in response.split("\r\n"):
                    if line.lower().startswith("location:"):
                        location = line.split(":", 1)[1].strip()
                        break

                if location:
                    _LOGGER.debug("Parsing device description from %s", location)
                    device_info = _parse_device_description(location, addr[0])
                    if device_info and device_info.get("is_airfryer"):
                        _LOGGER.info("Discovered Philips Airfryer at %s: %s", addr[0], device_info.get("model_number"))
                        discovered.append(device_info)
                    else:
                        _LOGGER.debug("Device at %s is not an airfryer", addr[0])
                else:
                    _LOGGER.debug("No location header found in response from %s", addr[0])

            except socket.timeout:
                _LOGGER.debug("UPnP discovery timeout after %d responses", response_count)
                break
            except Exception as e:
                _LOGGER.debug("Error processing UPnP response: %s", e)
                continue

    except Exception as e:
        _LOGGER.error("Error during UPnP discovery: %s", e)
    finally:
        sock.close()

    _LOGGER.debug("UPnP discovery complete. Found %d airfryer(s)", len(discovered))
    return discovered


def _parse_device_description(location: str, ip_address: str) -> dict[str, Any] | None:
    """Parse device description XML from location URL."""
    try:
        import requests

        _LOGGER.debug("Fetching device description from %s", location)
        response = requests.get(location, timeout=5, verify=False)
        if response.status_code != 200:
            _LOGGER.debug("Device description returned status code %d", response.status_code)
            return None

        # Parse XML
        root = ET.fromstring(response.content)

        # Define namespaces - try multiple common ones
        ns = {"upnp": "urn:schemas-upnp-org:device-1-0"}

        # Extract device info
        device = root.find("upnp:device", ns) or root.find("device") or root.find(".//{*}device")
        if device is None:
            _LOGGER.debug("No device element found in XML")
            return None

        device_type = _get_element_text(device, "deviceType", ns)
        model_name = _get_element_text(device, "modelName", ns)
        model_number = _get_element_text(device, "modelNumber", ns)
        friendly_name = _get_element_text(device, "friendlyName", ns)
        manufacturer = _get_element_text(device, "manufacturer", ns)

        _LOGGER.debug(
            "Device info - Type: %s, Model: %s, Number: %s, Name: %s, Manufacturer: %s",
            device_type, model_name, model_number, friendly_name, manufacturer
        )

        # Check if it's an airfryer - be more flexible with detection
        is_airfryer = False

        # Check multiple indicators
        if manufacturer and "philips" in manufacturer.lower():
            if model_name and "venus" in model_name.lower():
                is_airfryer = True
            elif model_number and any(model in model_number.upper() for model in ["HD9880", "HD9875", "HD9255"]):
                is_airfryer = True
            elif friendly_name and "airfryer" in friendly_name.lower():
                is_airfryer = True

        if not is_airfryer:
            _LOGGER.debug("Device is not recognized as an airfryer")
            return None

        # Detect model configuration
        model_config = detect_model_config(model_number)

        return {
            "is_airfryer": True,
            "ip_address": ip_address,
            "model_name": model_name,
            "model_number": model_number,
            "friendly_name": friendly_name or "Philips Airfryer",
            "suggested_model": model_config["model"],
            "config": model_config,
        }

    except Exception as e:
        _LOGGER.debug("Error parsing device description from %s: %s", location, e, exc_info=True)
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
