"""Print dispatch for label PNGs — supports both CUPS (local) and IPP (network)."""

import os
import ssl
import struct
import subprocess
import urllib.request

# Printers use self-signed certs — skip verification
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


class PrintError(Exception):
    """Raised when a print job fails."""
    pass


def _is_ipp_uri(printer_name):
    """Check if printer_name is an IPP URI."""
    return printer_name.startswith(("ipp://", "http://", "ipps://", "https://"))


def print_label(png_path, printer_name, copies=1, label_size="1.5x1.5"):
    """Send a label PNG to a printer via CUPS or direct IPP."""
    for _ in range(copies):
        if _is_ipp_uri(printer_name):
            _print_ipp(png_path, printer_name)
        else:
            _print_cups(png_path, printer_name, label_size)


def _print_cups(png_path, printer_name, label_size):
    """Print via local CUPS queue."""
    cmd = [
        "lp", "-d", printer_name,
        "-o", f"media=Custom.{label_size}in",
        png_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise PrintError(f"lp failed: {result.stderr}")


def _print_ipp(png_path, ipp_uri):
    """Print via direct IPP Print-Job request (pure Python, no ipptool)."""
    # Convert ipp(s):// to https:// — most modern printers require TLS
    http_url = ipp_uri
    if http_url.startswith("ipp://"):
        http_url = "https://" + http_url[6:]
    elif http_url.startswith("ipps://"):
        http_url = "https://" + http_url[7:]

    with open(png_path, "rb") as f:
        file_data = f.read()

    # Build IPP Print-Job request body
    ipp_body = _build_ipp_print_job(ipp_uri, file_data)

    req = urllib.request.Request(
        http_url,
        data=ipp_body,
        headers={"Content-Type": "application/ipp"},
        method="POST",
    )

    try:
        resp = urllib.request.urlopen(req, timeout=30, context=_SSL_CTX)
        resp_data = resp.read()
        # Check IPP status in response (bytes 2-3)
        if len(resp_data) >= 4:
            status = struct.unpack(">H", resp_data[2:4])[0]
            if status > 0x00FF:
                raise PrintError(f"IPP error status: 0x{status:04x}")
    except urllib.error.URLError as e:
        raise PrintError(f"IPP connection failed: {e}")


def _build_ipp_print_job(printer_uri, file_data):
    """Build a raw IPP Print-Job request."""
    buf = bytearray()

    # IPP version 1.1
    buf += struct.pack(">BB", 1, 1)
    # Operation: Print-Job (0x0002)
    buf += struct.pack(">H", 0x0002)
    # Request ID
    buf += struct.pack(">I", 1)

    # Operation attributes group (tag 0x01)
    buf.append(0x01)

    # attributes-charset = utf-8
    buf += _ipp_attr(0x47, "attributes-charset", "utf-8")
    # attributes-natural-language = en
    buf += _ipp_attr(0x48, "attributes-natural-language", "en")
    # printer-uri
    buf += _ipp_attr(0x45, "printer-uri", printer_uri)
    # requesting-user-name
    buf += _ipp_attr(0x42, "requesting-user-name", "recipe-labels")
    # document-format = image/png
    buf += _ipp_attr(0x49, "document-format", "image/png")

    # End of attributes
    buf.append(0x03)

    # Document data
    buf += file_data

    return bytes(buf)


def _ipp_attr(tag, name, value):
    """Encode a single IPP attribute."""
    name_bytes = name.encode("utf-8")
    value_bytes = value.encode("utf-8")
    buf = bytearray()
    buf.append(tag)
    buf += struct.pack(">H", len(name_bytes))
    buf += name_bytes
    buf += struct.pack(">H", len(value_bytes))
    buf += value_bytes
    return bytes(buf)


def discover_printers():
    """Discover available CUPS printers."""
    try:
        result = subprocess.run(
            ["lpstat", "-p"], capture_output=True, text=True
        )
        if result.returncode != 0:
            return []
        printers = []
        for line in result.stdout.splitlines():
            if line.startswith("printer "):
                parts = line.split()
                if len(parts) >= 2:
                    printers.append(parts[1])
        return printers
    except FileNotFoundError:
        return []


def get_printer_media(printer_name):
    """Query the current media size selected on a printer."""
    if _is_ipp_uri(printer_name):
        return {"current": None, "available": [], "match": True}
    try:
        result = subprocess.run(
            ["lpoptions", "-p", printer_name, "-l"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            return {"current": None, "available": [], "match": False}
        for line in result.stdout.splitlines():
            if line.startswith("PageSize/") or line.startswith("MediaSize/"):
                _, _, options_str = line.partition(": ")
                options = options_str.split()
                current = None
                available = []
                for opt in options:
                    clean = opt.lstrip("*")
                    if clean.startswith("Custom"):
                        continue
                    available.append(clean)
                    if opt.startswith("*"):
                        current = clean
                return {
                    "current": current,
                    "available": available,
                    "match": current == "1.5x1.5",
                }
        return {"current": None, "available": [], "match": False}
    except FileNotFoundError:
        return {"current": None, "available": [], "match": False}
