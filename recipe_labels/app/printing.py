"""Print dispatch for label PNGs — supports both CUPS (local) and IPP (network)."""

import os
import subprocess


class PrintError(Exception):
    """Raised when a print job fails."""
    pass


def _is_ipp_uri(printer_name):
    """Check if printer_name is an IPP URI (ipp:// or http://)."""
    return printer_name.startswith(("ipp://", "http://", "ipps://", "https://"))


def print_label(png_path, printer_name, copies=1, label_size="1.5x1.5"):
    """Send a label PNG to a printer via CUPS or direct IPP.

    If printer_name looks like an IPP URI (ipp://...), use ipptool or
    lp with the URI directly. Otherwise, treat it as a CUPS queue name.
    """
    for _ in range(copies):
        if _is_ipp_uri(printer_name):
            _print_ipp(png_path, printer_name)
        else:
            _print_cups(png_path, printer_name, label_size)


def _print_cups(png_path, printer_name, label_size):
    """Print via local CUPS queue."""
    cmd = [
        "lp",
        "-d", printer_name,
        "-o", f"media=Custom.{label_size}in",
        png_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise PrintError(f"lp failed: {result.stderr}")
    return result.stdout


def _print_ipp(png_path, ipp_uri):
    """Print via direct IPP to a network printer."""
    # Use lp with -h (remote host) by parsing the URI,
    # or use ipptool for raw IPP.
    # Simplest: use lp pointed at the IPP URI directly
    cmd = [
        "lp",
        "-d", ipp_uri,
        png_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        # Fallback: try ipptool Print-Job
        _print_ipp_raw(png_path, ipp_uri)


def _print_ipp_raw(png_path, ipp_uri):
    """Print via raw IPP Print-Job request using ipptool."""
    # Normalize URI
    uri = ipp_uri
    if uri.startswith("http://"):
        uri = "ipp://" + uri[7:]

    cmd = [
        "ipptool",
        "-tf", png_path,
        uri,
        "-d", "filetype=image/png",
        "/dev/stdin",
    ]
    ipp_request = """{
OPERATION Print-Job
GROUP operation-attributes-tag
ATTR charset attributes-charset utf-8
ATTR naturalLanguage attributes-natural-language en
ATTR uri printer-uri $uri
ATTR name requesting-user-name "recipe-labels"
ATTR mimeMediaType document-format image/png
FILE $filename
}"""
    result = subprocess.run(
        ["ipptool", "-tf", png_path, uri, "-"],
        input=ipp_request,
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise PrintError(f"IPP print failed: {result.stderr}")


def discover_printers():
    """Discover available CUPS printers.

    Returns:
        List of printer name strings.
    """
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
    """Query the current media size selected on a printer.

    Returns:
        dict with "current" (e.g. "4x6"), "available" (list of sizes),
        and "match" (bool, True if current == 1.5x1.5).
    """
    if _is_ipp_uri(printer_name):
        # Can't query media from raw IPP easily; skip
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
