#!/usr/bin/with-contenv bash

# Read config from /data/options.json (always available in HA add-ons)
OPTIONS="/data/options.json"

if [ -f "$OPTIONS" ]; then
  export ANTHROPIC_API_KEY=$(jq -r '.anthropic_api_key' "$OPTIONS")
  export PRINTER_NAME=$(jq -r '.printer_name' "$OPTIONS")
  export LABEL_SIZE_NUTRITION=$(jq -r '.label_size_nutrition' "$OPTIONS")
  export LABEL_SIZE_RECIPE=$(jq -r '.label_size_recipe' "$OPTIONS")
  export SERVING_SIZE_DEFAULT=$(jq -r '.serving_size_default' "$OPTIONS")
fi

export DATA_DIR="/data"

# Ensure data dirs exist
mkdir -p "$DATA_DIR/labels"

# Initialize recipes.md if missing
if [ ! -f "$DATA_DIR/recipes.md" ]; then
  echo -e "# Recipe Label Log\n\nRecipes logged via nutrition label workflow." > "$DATA_DIR/recipes.md"
fi

# Start Flask
cd /app
exec python3 -m app.server
