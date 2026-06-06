/* Recipe Labels — client logic + Web Speech API */

const BASE = document.querySelector('meta[name="base-path"]')?.content || '';

// --- DOM refs ---
const ingredientsInput = document.getElementById('ingredients-input');
const micBtn = document.getElementById('mic-btn');
const parseBtn = document.getElementById('parse-btn');
const parseError = document.getElementById('parse-error');

const confirmSection = document.getElementById('confirm-section');
const inputSection = document.getElementById('input-section');

const recipeName = document.getElementById('recipe-name');
const recipeSuffix = document.getElementById('recipe-suffix');
const ingredientTableBody = document.querySelector('#ingredient-table tbody');
const totalsRow = document.getElementById('totals-row');
const per100Cal = document.getElementById('per100-cal');
const per100Fat = document.getElementById('per100-fat');
const per100Protein = document.getElementById('per100-protein');
const per100Carb = document.getElementById('per100-carb');
const calorieWarning = document.getElementById('calorie-warning');
const similarWarning = document.getElementById('similar-warning');
const nutritionPreview = document.getElementById('nutrition-preview');
const recipePreview = document.getElementById('recipe-preview');
const upcCode = document.getElementById('upc-code');
const mediaWarning = document.getElementById('media-warning');
const mediaWarningConfirm = document.getElementById('media-warning-confirm');
const recipeStatus = document.getElementById('recipe-status');
const iterationOfRow = document.getElementById('iteration-of-row');
const iterationOf = document.getElementById('iteration-of');
const reuseUpc = document.getElementById('reuse-upc');
const nutritionCopies = document.getElementById('nutrition-copies');
const recipeCopies = document.getElementById('recipe-copies');
const backBtn = document.getElementById('back-btn');
const printBtn = document.getElementById('print-btn');
const printError = document.getElementById('print-error');
const printStatus = document.getElementById('print-status');
const healthStatus = document.getElementById('health-status');
const historySearch = document.getElementById('history-search');
const historyList = document.getElementById('history-list');

// --- State ---
let currentData = null;  // full data for the active recipe (from parse or history)
let isReprintMode = false; // true when viewing a stored recipe

// --- API helper ---
async function api(path, options = {}) {
  const url = `${BASE}${path}`;
  const resp = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  return resp.json();
}

// --- Health check + media warning ---
async function checkHealth() {
  try {
    const r = await api('/api/health');
    if (r.success && r.data?.status === 'ok') {
      healthStatus.className = 'status-dot ok';
      healthStatus.title = `Printer: ${r.data.printer || 'none'} | Recipes: ${r.data.recipes_count}`;

      const media = r.data.printer_media;
      if (media && media.current && !media.match) {
        mediaWarning.textContent = `Warning: Rollo has ${media.current} labels loaded — need 1.5x1.5`;
        mediaWarning.classList.remove('hidden');
      } else if (media && media.match) {
        mediaWarning.classList.add('hidden');
      }
    } else {
      healthStatus.className = 'status-dot error';
      healthStatus.title = r.data?.error || 'Unhealthy';
    }
  } catch {
    healthStatus.className = 'status-dot error';
    healthStatus.title = 'Cannot reach server';
  }
}

// --- Web Speech API ---
let recognition = null;
if (window.SpeechRecognition || window.webkitSpeechRecognition) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SpeechRecognition();
  recognition.continuous = true;
  recognition.interimResults = true;
  recognition.lang = 'en-US';

  recognition.onresult = (event) => {
    const transcript = Array.from(event.results)
      .map(r => r[0].transcript)
      .join('');
    ingredientsInput.value = transcript;
  };

  recognition.onend = () => micBtn.classList.remove('recording');
  recognition.onerror = () => micBtn.classList.remove('recording');
}

micBtn.addEventListener('click', () => {
  if (!recognition) {
    alert('Speech recognition not supported in this browser.');
    return;
  }
  if (micBtn.classList.contains('recording')) {
    recognition.stop();
  } else {
    recognition.start();
    micBtn.classList.add('recording');
  }
});

// --- Parse (also generates labels) ---
parseBtn.addEventListener('click', async () => {
  const text = ingredientsInput.value.trim();
  if (!text) return;

  parseBtn.disabled = true;
  parseBtn.classList.add('loading');
  parseBtn.textContent = 'Parsing';
  parseError.classList.add('hidden');

  try {
    const r = await api('/api/parse', {
      method: 'POST',
      body: JSON.stringify({ ingredients: text }),
    });

    if (!r.success) {
      parseError.textContent = r.error || 'Parse failed';
      parseError.classList.remove('hidden');
      return;
    }

    currentData = r.data;
    isReprintMode = false;
    showConfirmation(r.data);
  } catch (e) {
    parseError.textContent = `Error: ${e.message}`;
    parseError.classList.remove('hidden');
  } finally {
    parseBtn.disabled = false;
    parseBtn.classList.remove('loading');
    parseBtn.textContent = 'Parse Ingredients';
  }
});

function showConfirmation(data) {
  const macros = data.macros;

  recipeName.value = data.title;
  recipeSuffix.value = data.suffix;

  // Ingredient table
  ingredientTableBody.innerHTML = '';
  const ingredients = macros.ingredients || [];
  ingredients.forEach(ing => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${escHtml(ing.original)}</td>
      <td>${ing.grams}</td>
      <td>${ing.cal}</td>
      <td>${ing.fat}</td>
      <td>${ing.protein}</td>
      <td>${ing.carb}</td>
    `;
    ingredientTableBody.appendChild(tr);
  });

  // Totals
  const t = macros.totals || {};
  const cells = totalsRow.querySelectorAll('td');
  cells[1].textContent = t.grams || '';
  cells[2].textContent = t.cal || '';
  cells[3].textContent = t.fat || '';
  cells[4].textContent = t.protein || '';
  cells[5].textContent = t.carb || '';

  // Per 100g
  const p = macros.per_100g || {};
  per100Cal.value = p.cal || 0;
  per100Fat.value = p.fat || 0;
  per100Protein.value = p.protein || 0;
  per100Carb.value = p.carb || 0;

  // Warnings
  const warnings = macros.warnings || [];
  if (warnings.length) {
    calorieWarning.textContent = warnings.join('; ');
    calorieWarning.classList.remove('hidden');
  } else {
    calorieWarning.classList.add('hidden');
  }

  // Similar recipes
  const similar = data.similar_recipes || [];
  if (similar.length && !isReprintMode) {
    const names = similar.map(s => `${s.name} (${Math.round(s.similarity * 100)}%)`).join(', ');
    similarWarning.textContent = `Similar recipes found: ${names}`;
    similarWarning.classList.remove('hidden');
    recipeStatus.value = 'iteration';
    iterationOfRow.classList.remove('hidden');
    iterationOf.value = similar[0].name;
    reuseUpc.value = similar[0].upc || '';
  } else {
    similarWarning.classList.add('hidden');
    if (isReprintMode) {
      recipeStatus.value = 'repeat';
    } else {
      recipeStatus.value = 'new';
    }
    iterationOfRow.classList.add('hidden');
    iterationOf.value = '';
    reuseUpc.value = '';
  }

  // Label previews
  nutritionPreview.src = data.nutrition_label;
  recipePreview.src = data.recipe_label;
  upcCode.textContent = data.upc;

  // Media warning
  const media = data.printer_media;
  if (media && media.current && !media.match) {
    mediaWarningConfirm.textContent = `Warning: Rollo has ${media.current} labels loaded — need 1.5x1.5`;
    mediaWarningConfirm.classList.remove('hidden');
  } else {
    mediaWarningConfirm.classList.add('hidden');
  }

  // Reset print state
  printStatus.classList.add('hidden');
  printError.classList.add('hidden');

  inputSection.classList.add('hidden');
  confirmSection.classList.remove('hidden');
}

// --- Load a stored recipe into the confirmation panel ---
async function loadStoredRecipe(entry) {
  const macros = entry.macros || {};
  const title = entry.full_name;
  const suffix = entry.suffix || '';
  const ingredients = entry.ingredients || [];
  const upc = entry.upc || '';
  const totalWeight = parseInt(entry.total_weight) || 0;

  // Generate labels from stored data (no Anthropic API call)
  const genResult = await api('/api/generate', {
    method: 'POST',
    body: JSON.stringify({
      title,
      cal: macros.cal || 0,
      fat: macros.fat || 0,
      protein: macros.protein || 0,
      carb: macros.carb || 0,
      serving: entry.serving_size || '100g',
      total_weight: totalWeight,
      ingredients,
      suffix,
      status: 'repeat',
      upc,
      iteration_of: '',
    }),
  });

  if (!genResult.success) {
    alert(`Failed to generate labels: ${genResult.error}`);
    return;
  }

  // Build currentData in the same shape as /api/parse returns
  currentData = {
    title,
    suffix,
    upc,
    total_weight: totalWeight,
    nutrition_label: genResult.data.nutrition_label,
    recipe_label: genResult.data.recipe_label,
    nutrition_filename: genResult.data.nutrition_filename,
    recipe_filename: genResult.data.recipe_filename,
    similar_recipes: [],
    printer_media: {},
    macros: {
      ingredients: ingredients.map(ingr => ({
        original: ingr,
        grams: parseInt(ingr) || 0,
        cal: 0, fat: 0, protein: 0, carb: 0,
      })),
      totals: { grams: totalWeight, cal: 0, fat: 0, protein: 0, carb: 0 },
      per_100g: macros,
      warnings: [],
    },
  };

  isReprintMode = true;
  showStoredRecipe(entry, genResult.data);
}

function showStoredRecipe(entry, genData) {
  const macros = entry.macros || {};
  const ingredients = entry.ingredients || [];

  recipeName.value = entry.full_name;
  recipeSuffix.value = entry.suffix || '';

  // Ingredient table — simple list (no per-ingredient macros for stored recipes)
  ingredientTableBody.innerHTML = '';
  ingredients.forEach(ingr => {
    const tr = document.createElement('tr');
    const grams = parseInt(ingr) || '';
    tr.innerHTML = `
      <td>${escHtml(ingr)}</td>
      <td>${grams}</td>
      <td></td><td></td><td></td><td></td>
    `;
    ingredientTableBody.appendChild(tr);
  });

  // Hide totals row (no per-ingredient breakdown for stored recipes)
  const cells = totalsRow.querySelectorAll('td');
  cells[1].textContent = entry.total_weight || '';
  cells[2].textContent = '';
  cells[3].textContent = '';
  cells[4].textContent = '';
  cells[5].textContent = '';

  // Per 100g
  per100Cal.value = macros.cal || 0;
  per100Fat.value = macros.fat || 0;
  per100Protein.value = macros.protein || 0;
  per100Carb.value = macros.carb || 0;

  // No warnings for stored recipes
  calorieWarning.classList.add('hidden');
  similarWarning.classList.add('hidden');

  // Label previews
  nutritionPreview.src = genData.nutrition_label;
  recipePreview.src = genData.recipe_label;
  upcCode.textContent = genData.upc || entry.upc || '';

  mediaWarningConfirm.classList.add('hidden');

  // Pre-set to repeat
  recipeStatus.value = 'repeat';
  iterationOfRow.classList.add('hidden');

  // Reset print state
  printStatus.classList.add('hidden');
  printError.classList.add('hidden');

  inputSection.classList.add('hidden');
  confirmSection.classList.remove('hidden');
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Status change handler
recipeStatus.addEventListener('change', () => {
  if (recipeStatus.value === 'iteration' || recipeStatus.value === 'repeat') {
    iterationOfRow.classList.remove('hidden');
  } else {
    iterationOfRow.classList.add('hidden');
  }
});

// Back button
backBtn.addEventListener('click', () => {
  confirmSection.classList.add('hidden');
  inputSection.classList.remove('hidden');
  isReprintMode = false;
});

// --- Print ---
printBtn.addEventListener('click', async () => {
  if (!currentData) return;

  printBtn.disabled = true;
  printBtn.classList.add('loading');
  printBtn.textContent = 'Printing';
  printError.classList.add('hidden');
  printStatus.classList.add('hidden');

  try {
    const status = recipeStatus.value;

    // For new recipes or iterations, save to recipes.md via generate
    if (status !== 'repeat' && !isReprintMode) {
      const macros = currentData.macros || {};
      const ingredients = (macros.ingredients || []).map(i => i.original);

      const genResult = await api('/api/generate', {
        method: 'POST',
        body: JSON.stringify({
          title: recipeName.value.trim(),
          cal: parseInt(per100Cal.value) || 0,
          fat: parseFloat(per100Fat.value) || 0,
          protein: parseFloat(per100Protein.value) || 0,
          carb: parseFloat(per100Carb.value) || 0,
          serving: '100g',
          total_weight: currentData.total_weight || 0,
          ingredients,
          suffix: recipeSuffix.value,
          status,
          upc: currentData.upc || '',
          iteration_of: status === 'iteration' ? iterationOf.value : '',
        }),
      });

      if (!genResult.success) {
        printError.textContent = genResult.error || 'Save failed';
        printError.classList.remove('hidden');
        return;
      }
    }

    // Print
    const nCopies = parseInt(nutritionCopies.value) || 0;
    const rCopies = parseInt(recipeCopies.value) || 0;

    if (nCopies > 0 || rCopies > 0) {
      const printResult = await api('/api/print', {
        method: 'POST',
        body: JSON.stringify({
          nutrition_filename: currentData.nutrition_filename,
          recipe_filename: currentData.recipe_filename,
          nutrition_copies: nCopies,
          recipe_copies: rCopies,
        }),
      });

      if (printResult.success) {
        printStatus.textContent = `Printed: ${(printResult.data.printed || []).join(', ')} to ${printResult.data.printer}. UPC: ${currentData.upc}`;
        printStatus.className = 'success';
        printStatus.classList.remove('hidden');
      } else {
        printError.textContent = `Print failed: ${printResult.error}`;
        printError.classList.remove('hidden');
      }
    } else {
      printStatus.textContent = `Labels ready. UPC: ${currentData.upc}`;
      printStatus.className = 'success';
      printStatus.classList.remove('hidden');
    }

    loadHistory();
  } catch (e) {
    printError.textContent = `Error: ${e.message}`;
    printError.classList.remove('hidden');
  } finally {
    printBtn.disabled = false;
    printBtn.classList.remove('loading');
    printBtn.textContent = 'Print';
  }
});

// --- New Recipe (reset) ---
function resetToInput() {
  confirmSection.classList.add('hidden');
  inputSection.classList.remove('hidden');
  ingredientsInput.value = '';
  currentData = null;
  isReprintMode = false;
  printStatus.classList.add('hidden');
  printError.classList.add('hidden');
  loadHistory();
}

// --- History ---
async function loadHistory() {
  try {
    const r = await api('/api/recipes');
    if (!r.success) return;
    renderHistory(r.data || []);
  } catch { /* ignore */ }
}

function renderHistory(entries, filter = '') {
  historyList.innerHTML = '';
  const lf = filter.toLowerCase();

  entries
    .filter(e => !lf || e.full_name.toLowerCase().includes(lf) ||
            (e.ingredients || []).some(i => i.toLowerCase().includes(lf)))
    .reverse()
    .forEach(entry => {
      const div = document.createElement('div');
      div.className = 'history-item';
      const macros = entry.macros || {};
      div.innerHTML = `
        <div class="hi-name">${escHtml(entry.full_name)}</div>
        <div class="hi-meta">
          ${entry.date || ''} &middot;
          ${macros.cal || 0}cal | ${macros.fat || 0}gF | ${macros.protein || 0}gP | ${macros.carb || 0}gC /100g
          &middot; UPC: ${entry.upc || ''}
        </div>
      `;
      div.addEventListener('click', () => loadStoredRecipe(entry));
      historyList.appendChild(div);
    });

  if (!historyList.children.length) {
    historyList.innerHTML = '<div class="history-item"><div class="hi-meta">No recipes yet.</div></div>';
  }
}

historySearch.addEventListener('input', async () => {
  try {
    const r = await api('/api/recipes');
    if (r.success) renderHistory(r.data || [], historySearch.value);
  } catch { /* ignore */ }
});

// --- Helpers ---
function escHtml(s) {
  const d = document.createElement('div');
  d.textContent = s || '';
  return d.innerHTML;
}

// --- Init ---
checkHealth();
loadHistory();
