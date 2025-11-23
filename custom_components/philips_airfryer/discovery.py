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


def discover_device_info(ip_address: str) -> dict[str, Any] | None:
    """Try to discover device info from a specific IP address via UPnP.

    This attempts to fetch the device description XML from common UPnP ports/paths.
    Returns device info dict if successful, None otherwise.
    """
    _LOGGER.debug("Attempting to discover device info for %s", ip_address)

    # Try common UPnP description paths
    common_paths = [
        f"http://{ip_address}/upnp/description.xml",  # Philips devices use this path
        f"http://{ip_address}:49153/description.xml",
        f"http://{ip_address}:49152/description.xml",
        f"http://{ip_address}/description.xml",
    ]

    for location in common_paths:
        _LOGGER.debug("Trying UPnP location: %s", location)
        device_info = _parse_device_description(location, ip_address)
        if device_info:
            _LOGGER.info("Successfully discovered device info at %s", location)
            return device_info

    _LOGGER.debug("Could not discover device info for %s", ip_address)
    return None


def discover_airfryers(timeout: int = 10) -> list[dict[str, Any]]:
    """Discover Philips Airfryers on the network via UPnP."""
    _LOGGER.debug("Starting UPnP discovery for Philips Airfryers")
    discovered = []
    seen_ips = set()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
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
                _LOGGER.debug("Response content: %s", response[:500])  # Log first 500 chars

                # Skip if we've already processed this IP
                if addr[0] in seen_ips:
                    _LOGGER.debug("Already processed device at %s", addr[0])
                    continue

                # Extract location from response
                location = None
                for line in response.split("\r\n"):
                    if line.lower().startswith("location:"):
                        location = line.split(":", 1)[1].strip()
                        break

                if location:
                    # Check if this response mentions Philips at all
                    is_philips = "philips" in response.lower()
                    _LOGGER.debug("Parsing device description from %s (Philips in response: %s)", location, is_philips)

                    seen_ips.add(addr[0])
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

        # Log the raw XML for debugging
        _LOGGER.debug("Device XML response: %s", response.text[:1000])

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
        serial_number = _get_element_text(device, "serialNumber", ns)
        udn = _get_element_text(device, "UDN", ns)

        # Extract MAC address from UDN if available (often in format uuid:MACADDRESS-...)
        mac_address = None
        if udn:
            # Try to extract MAC from UDN (format varies by device)
            # Common format: uuid:00000000-0000-1000-8000-XXXXXXXXXXXX where X is MAC
            if "8000-" in udn:
                potential_mac = udn.split("8000-")[-1].replace("-", ":")
                if len(potential_mac) >= 17:  # MAC address length with colons
                    mac_address = potential_mac[:17].lower()  # Lowercase for HA compatibility
            # Alternative: MAC might be in serial number
            elif serial_number and len(serial_number) >= 12:
                # Try to format as MAC if it looks like one
                cleaned = serial_number.replace(":", "").replace("-", "").lower()
                if len(cleaned) >= 12 and cleaned[:12].isalnum():
                    mac_address = ":".join([cleaned[i:i+2] for i in range(0, 12, 2)])

        _LOGGER.info(
            "Found device at %s - Type: %s, Model: %s, Number: %s, Name: %s, Manufacturer: %s, MAC: %s",
            ip_address, device_type, model_name, model_number, friendly_name, manufacturer, mac_address
        )

        # Check if it's an airfryer
        # Primary check: Philips manufacturer + DiProduct device type
        is_airfryer = False

        if manufacturer and "philips" in manufacturer.lower():
            _LOGGER.debug("Device manufacturer is Philips")

            # Check if it's a DiProduct (Philips connected appliance)
            if device_type and "diproduct" in device_type.lower():
                _LOGGER.debug("Matched: DiProduct device type - this is a Philips connected appliance")
                is_airfryer = True
            else:
                _LOGGER.debug("Not a DiProduct device (type: %s)", device_type)

        if not is_airfryer:
            _LOGGER.debug("Device is not recognized as a Philips airfryer")
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
            "mac_address": mac_address,
            "serial_number": serial_number,
            "udn": udn,
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
