"""CUPS/IPP print dispatch for label PNGs."""

import subprocess


class PrintError(Exception):
    """Raised when a print job fails."""
    pass


def print_label(png_path, printer_name, copies=1, label_size="1.5x1.5"):
    """Send a label PNG to the specified CUPS printer.

    Args:
        png_path: Path to the PNG file.
        printer_name: CUPS printer name (e.g. "Rollo_X1040").
        copies: Number of copies to print.
        label_size: Label dimensions in inches (e.g. "1.5x1.5").

    Returns:
        stdout from the lp command.

    Raises:
        PrintError: If the lp command fails.
    """
    cmd = [
        "lp",
        "-d", printer_name,
        "-o", f"media=Custom.{label_size}in",
        "-n", str(copies),
        png_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise PrintError(f"lp failed: {result.stderr}")
    return result.stdout


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
            # Lines look like: "printer Rollo_X1040 is idle. ..."
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
    try:
        result = subprocess.run(
            ["lpoptions", "-p", printer_name, "-l"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            return {"current": None, "available": [], "match": False}

        for line in result.stdout.splitlines():
            if line.startswith("PageSize/") or line.startswith("MediaSize/"):
                # e.g. "PageSize/Media Size: 1.5x1.5 2x1 *4x6 Custom.WIDTHxHEIGHT"
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
