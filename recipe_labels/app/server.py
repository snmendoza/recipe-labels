"""Flask app — routes and API for the recipe label workflow."""

import json
import os
import traceback

from flask import Flask, jsonify, request, send_from_directory, render_template

from . import labels, macros, printing, recipes

app = Flask(__name__)

DATA_DIR = os.path.abspath(os.environ.get("DATA_DIR", "/data"))
LABELS_DIR = os.path.join(DATA_DIR, "labels")
RECIPES_MD = os.path.join(DATA_DIR, "recipes.md")


def _ensure_dirs():
    os.makedirs(LABELS_DIR, exist_ok=True)
    if not os.path.exists(RECIPES_MD):
        with open(RECIPES_MD, "w") as f:
            f.write("# Recipe Label Log\n\nRecipes logged via nutrition label workflow.\n")


def _ingress_path():
    """Get the ingress base path from the request header, or empty string."""
    return request.headers.get("X-Ingress-Path", "").rstrip("/")


def _api_response(success=True, data=None, error=None, status=200):
    resp = {"success": success, "error": error, "data": data}
    return jsonify(resp), status


# --- Routes ---

@app.route("/")
def index():
    _ensure_dirs()
    base_path = _ingress_path()
    return render_template("index.html", base_path=base_path)


@app.route("/api/parse", methods=["POST"])
def api_parse():
    """Accept raw ingredient text, call Anthropic API, return structured macros."""
    _ensure_dirs()
    try:
        body = request.get_json(force=True)
        ingredient_text = body.get("ingredients", "").strip()
        if not ingredient_text:
            return _api_response(False, error="No ingredients provided", status=400)

        data = macros.compute_macros(ingredient_text)

        # Check for similar recipes
        ingredients_list = [i.get("original", "") for i in data.get("ingredients", [])]
        suggested_name = data.get("suggested_name", "")
        similar = recipes.search_similar(ingredients_list, RECIPES_MD, base_name=suggested_name)

        # Generate a suffix
        suffix = recipes.generate_suffix(RECIPES_MD)

        # For repeats, reuse existing UPC; otherwise generate new
        reuse_upc = ""
        if similar:
            reuse_upc = similar[0]["entry"].get("upc", "")

        per_100 = data.get("per_100g", {})
        totals = data.get("totals", {})
        title = f"{suggested_name} {suffix}"
        cal = int(per_100.get("cal", 0))
        fat = float(per_100.get("fat", 0))
        protein = float(per_100.get("protein", 0))
        carb = float(per_100.get("carb", 0))
        total_weight = int(totals.get("grams", 0))
        serving = os.environ.get("SERVING_SIZE_DEFAULT", "100g")
        upc_str = labels.generate_upc(prefix=2)

        slug = labels.slugify(title)
        nutrition_path = os.path.join(LABELS_DIR, f"{slug}_nutrition.png")
        recipe_path = os.path.join(LABELS_DIR, f"{slug}_recipe.png")

        labels.generate_nutrition_label(
            title=title, cal=cal, fat=fat, protein=protein, carb=carb,
            serving=serving, upc_str=upc_str, output_path=nutrition_path,
        )

        ingr_originals = [i.get("original", "") for i in data.get("ingredients", [])]
        labels.generate_recipe_label(
            title=title, suffix=suffix, ingredients_list=ingr_originals,
            cal=cal, fat=fat, protein=protein, carb=carb,
            total_weight=total_weight, output_path=recipe_path,
        )

        base = _ingress_path()
        nutrition_filename = os.path.basename(nutrition_path)
        recipe_filename = os.path.basename(recipe_path)

        # Get printer media info
        printer_name = os.environ.get("PRINTER_NAME", "")
        media_info = printing.get_printer_media(printer_name) if printer_name else {}

        result = {
            "macros": data,
            "suggested_name": suggested_name,
            "suffix": suffix,
            "title": title,
            "upc": upc_str,
            "slug": slug,
            "total_weight": total_weight,
            "nutrition_label": f"{base}/api/labels/{nutrition_filename}",
            "recipe_label": f"{base}/api/labels/{recipe_filename}",
            "nutrition_filename": nutrition_filename,
            "recipe_filename": recipe_filename,
            "similar_recipes": [
                {
                    "name": m["entry"]["full_name"],
                    "upc": m["entry"]["upc"],
                    "similarity": m["similarity"],
                    "match_type": m["match_type"],
                }
                for m in similar
            ],
            "printer_media": media_info,
        }
        return _api_response(data=result)

    except Exception as e:
        traceback.print_exc()
        return _api_response(False, error=str(e), status=500)


@app.route("/api/generate", methods=["POST"])
def api_generate():
    """Accept confirmed macros, generate label PNGs, return image URLs + UPC."""
    _ensure_dirs()
    try:
        body = request.get_json(force=True)

        title = body.get("title", "")
        cal = int(body.get("cal", 0))
        fat = float(body.get("fat", 0))
        protein = float(body.get("protein", 0))
        carb = float(body.get("carb", 0))
        serving = body.get("serving", os.environ.get("SERVING_SIZE_DEFAULT", "100g"))
        upc = body.get("upc", "")
        ingredients = body.get("ingredients", [])
        total_weight = int(body.get("total_weight", 0))
        suffix = body.get("suffix", "")
        status = body.get("status", "new")
        iteration_of = body.get("iteration_of", "")

        if not title:
            return _api_response(False, error="Title is required", status=400)

        # Generate or reuse UPC
        upc_str = upc if upc else labels.generate_upc(prefix=2)

        slug = labels.slugify(title)
        nutrition_path = os.path.join(LABELS_DIR, f"{slug}_nutrition.png")
        recipe_path = os.path.join(LABELS_DIR, f"{slug}_recipe.png")

        labels.generate_nutrition_label(
            title=title, cal=cal, fat=fat, protein=protein, carb=carb,
            serving=serving, upc_str=upc_str, output_path=nutrition_path,
        )

        labels.generate_recipe_label(
            title=title, suffix=suffix, ingredients_list=ingredients,
            cal=cal, fat=fat, protein=protein, carb=carb,
            total_weight=total_weight, output_path=recipe_path,
        )

        # Save to recipes.md
        if status != "repeat":
            recipes.append_recipe(
                {
                    "full_name": title,
                    "upc": upc_str,
                    "total_weight": f"{total_weight}g",
                    "serving_size": serving,
                    "status": status,
                    "ingredients": ingredients,
                    "macros": {"cal": cal, "fat": fat, "protein": protein, "carb": carb},
                    "iteration_of": iteration_of if status == "iteration" else "",
                },
                RECIPES_MD,
            )

        base = _ingress_path()
        nutrition_filename = os.path.basename(nutrition_path)
        recipe_filename = os.path.basename(recipe_path)

        return _api_response(data={
            "upc": upc_str,
            "slug": slug,
            "nutrition_label": f"{base}/api/labels/{nutrition_filename}",
            "recipe_label": f"{base}/api/labels/{recipe_filename}",
            "nutrition_filename": nutrition_filename,
            "recipe_filename": recipe_filename,
        })

    except Exception as e:
        traceback.print_exc()
        return _api_response(False, error=str(e), status=500)


@app.route("/api/print", methods=["POST"])
def api_print():
    """Accept label paths + copy counts, dispatch to CUPS."""
    try:
        body = request.get_json(force=True)
        printer = body.get("printer", os.environ.get("PRINTER_NAME", ""))
        if not printer:
            return _api_response(False, error="No printer configured", status=400)

        nutrition_file = body.get("nutrition_filename", "")
        recipe_file = body.get("recipe_filename", "")
        nutrition_copies = int(body.get("nutrition_copies", 1))
        recipe_copies = int(body.get("recipe_copies", 1))
        label_size = body.get("label_size", os.environ.get("LABEL_SIZE_NUTRITION", "1.5x1.5"))

        printed = []

        if nutrition_file and nutrition_copies > 0:
            path = os.path.join(LABELS_DIR, nutrition_file)
            if os.path.exists(path):
                printing.print_label(path, printer, copies=nutrition_copies, label_size=label_size)
                printed.append(f"{nutrition_copies}x nutrition")

        if recipe_file and recipe_copies > 0:
            path = os.path.join(LABELS_DIR, recipe_file)
            if os.path.exists(path):
                printing.print_label(path, printer, copies=recipe_copies, label_size=label_size)
                printed.append(f"{recipe_copies}x recipe card")

        return _api_response(data={"printed": printed, "printer": printer})

    except printing.PrintError as e:
        return _api_response(False, error=str(e), status=500)
    except Exception as e:
        traceback.print_exc()
        return _api_response(False, error=str(e), status=500)


@app.route("/api/recipes")
def api_recipes():
    """Return recipes.md parsed as a JSON array."""
    _ensure_dirs()
    try:
        entries = recipes.parse_recipes(RECIPES_MD)
        return _api_response(data=entries)
    except Exception as e:
        traceback.print_exc()
        return _api_response(False, error=str(e), status=500)


@app.route("/api/recipes/search")
def api_recipes_search():
    """Search for similar recipes."""
    _ensure_dirs()
    try:
        ingredients = request.args.get("ingredients", "")
        name = request.args.get("name", "")
        ingredients_list = [i.strip() for i in ingredients.split(",") if i.strip()]
        matches = recipes.search_similar(ingredients_list, RECIPES_MD, base_name=name)
        result = [
            {
                "name": m["entry"]["full_name"],
                "upc": m["entry"]["upc"],
                "similarity": m["similarity"],
                "match_type": m["match_type"],
            }
            for m in matches
        ]
        return _api_response(data=result)
    except Exception as e:
        traceback.print_exc()
        return _api_response(False, error=str(e), status=500)


@app.route("/api/recipes/save", methods=["POST"])
def api_recipes_save():
    """Append a recipe entry to recipes.md."""
    _ensure_dirs()
    try:
        body = request.get_json(force=True)
        recipes.append_recipe(body, RECIPES_MD)
        return _api_response(data={"saved": True})
    except Exception as e:
        traceback.print_exc()
        return _api_response(False, error=str(e), status=500)


@app.route("/api/labels/<filename>")
def api_labels(filename):
    """Serve generated label PNGs."""
    return send_from_directory(LABELS_DIR, filename)


@app.route("/api/health")
def api_health():
    """Health check endpoint."""
    _ensure_dirs()
    try:
        printers = printing.discover_printers()
        entry_count = len(recipes.parse_recipes(RECIPES_MD))
        configured_printer = os.environ.get("PRINTER_NAME", "")
        media_info = printing.get_printer_media(configured_printer) if configured_printer else {}
        return _api_response(data={
            "status": "ok",
            "printer": configured_printer,
            "printers_available": printers,
            "recipes_count": entry_count,
            "printer_media": media_info,
        })
    except Exception as e:
        return _api_response(data={"status": "degraded", "error": str(e)})


if __name__ == "__main__":
    _ensure_dirs()
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
