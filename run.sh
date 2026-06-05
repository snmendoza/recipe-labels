#!/usr/bin/env bashio

# Read config from HA options
export ANTHROPIC_API_KEY=$(bashio::config 'anthropic_api_key')
export PRINTER_NAME=$(bashio::config 'printer_name')
export LABEL_SIZE_NUTRITION=$(bashio::config 'label_size_nutrition')
export LABEL_SIZE_RECIPE=$(bashio::config 'label_size_recipe')
export SERVING_SIZE_DEFAULT=$(bashio::config 'serving_size_default')
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
