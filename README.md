# Recipe Labels

A Home Assistant add-on that turns dictated recipe ingredients into computed nutrition data and printed 1.5" round labels. Speak or type your ingredients, confirm the macro breakdown, and print nutrition facts labels (with UPC-A barcodes for MacroFactor scanning) and recipe card labels to a WiFi Rollo printer.

![UI Screenshot](docs/screenshot-placeholder.png)

## Architecture

```
Browser (phone/tablet) --> Flask (HA add-on) --> Anthropic API (macro computation)
                                             --> Pillow + barcode --> PNG labels
                                             --> CUPS --> WiFi Rollo printer
                                             --> recipes.md (persistent log)
```

## Features

- **Voice dictation** via Web Speech API (Chrome/Safari)
- **Automatic macro computation** using Claude API with USDA reference values
- **1.5" round nutrition label** with UPC-A barcode (prefix-2, no retail collision)
- **1.5" round recipe card** with ingredient list and macro summary
- **Recipe deduplication** detects similar recipes for reprints or iterations
- **CUPS printing** to any network label printer
- **Dark mode UI** optimized for kitchen use on phones and tablets
- **Persistent recipe log** in Markdown format

## Installation (Home Assistant)

1. Add this repository as a custom add-on repository in HA:
   - Settings > Add-ons > Add-on Store > ... > Repositories
   - Paste the GitHub URL
2. Install "Recipe Labels" from the add-on store
3. Configure:
   - `anthropic_api_key`: Your Anthropic API key
   - `printer_name`: CUPS printer name (e.g., `Rollo_X1040`)
4. Start the add-on and open the web UI from the sidebar

## Development (Local)

```bash
git clone https://github.com/snmendoza/recipe-labels.git
cd recipe-labels
pip install -r requirements.txt

export ANTHROPIC_API_KEY="sk-ant-..."
export PRINTER_NAME="Rollo_X1040"
export DATA_DIR="./dev_data"

python3 -m app.server
# Open http://localhost:5000
```

## Testing

```bash
pip install pytest
pytest tests/ -v
```

## License

MIT
