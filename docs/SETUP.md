# Setup Guide

## First-Time Setup

### 1. Anthropic API Key

You need an Anthropic API key for macro computation. Get one at [console.anthropic.com](https://console.anthropic.com/).

Set it in the add-on configuration:
- HA > Settings > Add-ons > Recipe Labels > Configuration
- Set `anthropic_api_key` to your key

### 2. Printer Configuration

The add-on uses CUPS to print to network printers.

**Find your printer name:**
```bash
lpstat -p
```

Common Rollo printer names:
- `Rollo` or `Rollo_X1040` (USB or WiFi)

Set the printer name in the add-on configuration:
- `printer_name`: Your CUPS printer name

**Printer not showing up?**
1. Make sure the printer is on the same network
2. On the HA host, install the printer via CUPS admin (`http://your-ha:631`)
3. The add-on uses `host_network: true` to access local network printers

### 3. Label Size

Default label size is 1.5" x 1.5" round labels. If using a different size:
- `label_size_nutrition`: e.g., `1.5x1.5`
- `label_size_recipe`: e.g., `1.5x1.5`

## Usage

### Basic Workflow

1. Open Recipe Labels from the HA sidebar
2. Type or dictate ingredients (e.g., "800g whole milk, 2 tbsp butter, 1 cup water")
3. Click "Parse Ingredients" to compute macros via Claude
4. Review the per-ingredient breakdown and per-100g totals
5. Adjust recipe name, macros, or copy counts if needed
6. Click "Generate & Print"
7. Labels print automatically; UPC code is displayed for MacroFactor scanning

### Voice Dictation

Click the microphone button to start dictation. Speak your ingredients naturally. Click again to stop. Works in Chrome and Safari.

### Reprinting

Open Recipe History at the bottom, find the recipe, and click it to populate the ingredients. Parse again or change status to "Repeat" to reprint with the same UPC.

### Iterations

When you modify a recipe (different quantities or ingredients), the system detects the similarity and suggests "Iteration". This creates a new entry with a new UPC, linked to the original.

## Data

All recipe data is stored in `/data/` on the HA host (persistent across add-on updates):
- `/data/recipes.md` — master recipe log
- `/data/labels/` — generated label PNG files

## Troubleshooting

### "No printer configured"
Set `printer_name` in the add-on configuration and restart.

### "ANTHROPIC_API_KEY not set"
Set your API key in the add-on configuration and restart.

### Labels look wrong
Check that DejaVu fonts are installed (included in the Docker image). The add-on falls back to system fonts if DejaVu is unavailable.

### Barcode won't scan
Ensure the label is printed at 300 DPI on a white background. The UPC-A format uses prefix 2 (in-store/variable weight) to avoid conflicts with retail products.
