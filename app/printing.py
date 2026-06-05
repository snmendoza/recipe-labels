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
