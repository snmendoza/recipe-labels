/* Recipe Labels — client logic + Web Speech API */

const BASE = document.querySelector('meta[name="base-path"]')?.content || '';

// --- DOM refs ---
const ingredientsInput = document.getElementById('ingredients-input');
const micBtn = document.getElementById('mic-btn');
const parseBtn = document.getElementById('parse-btn');
const parseError = document.getElementById('parse-error');

const confirmSection = document.getElementById('confirm-section');
const inputSection = document.getElementById('input-section');
const resultSection = document.getElementById('result-section');

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
const recipeStatus = document.getElementById('recipe-status');
const iterationOfRow = document.getElementById('iteration-of-row');
const iterationOf = document.getElementById('iteration-of');
const reuseUpc = document.getElementById('reuse-upc');
const nutritionCopies = document.getElementById('nutrition-copies');
const recipeCopies = document.getElementById('recipe-copies');
const backBtn = document.getElementById('back-btn');
const generateBtn = document.getElementById('generate-btn');
const generateError = document.getElementById('generate-error');

const nutritionPreview = document.getElementById('nutrition-preview');
const recipePreview = document.getElementById('recipe-preview');
const upcCode = document.getElementById('upc-code');
const printStatus = document.getElementById('print-status');
const reprintBtn = document.getElementById('reprint-btn');
const downloadBtn = document.getElementById('download-btn');
const newRecipeBtn = document.getElementById('new-recipe-btn');

const historySearch = document.getElementById('history-search');
const historyList = document.getElementById('history-list');
const healthStatus = document.getElementById('health-status');

// --- State ---
let currentData = null;    // parsed macro data from /api/parse
let generatedData = null;  // result from /api/generate

// --- API helper ---
async function api(path, options = {}) {
  const url = `${BASE}${path}`;
  const resp = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  return resp.json();
}

// --- Health check ---
async function checkHealth() {
  try {
    const r = await api('/api/health');
    if (r.success && r.data?.status === 'ok') {
      healthStatus.className = 'status-dot ok';
      healthStatus.title = `Printer: ${r.data.printer || 'none'} | Recipes: ${r.data.recipes_count}`;
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

  recognition.onend = () => {
    micBtn.classList.remove('recording');
  };

  recognition.onerror = () => {
    micBtn.classList.remove('recording');
  };
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

// --- Parse ---
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

  recipeName.value = `${data.suggested_name} ${data.suffix}`;
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
  if (similar.length) {
    const names = similar.map(s => `${s.name} (${Math.round(s.similarity * 100)}%)`).join(', ');
    similarWarning.textContent = `Similar recipes found: ${names}`;
    similarWarning.classList.remove('hidden');
    recipeStatus.value = 'iteration';
    iterationOfRow.classList.remove('hidden');
    iterationOf.value = similar[0].name;
    reuseUpc.value = similar[0].upc || '';
  } else {
    similarWarning.classList.add('hidden');
    recipeStatus.value = 'new';
    iterationOfRow.classList.add('hidden');
    iterationOf.value = '';
    reuseUpc.value = '';
  }

  inputSection.classList.add('hidden');
  confirmSection.classList.remove('hidden');
  resultSection.classList.add('hidden');
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
});

// --- Generate ---
generateBtn.addEventListener('click', async () => {
  generateBtn.disabled = true;
  generateBtn.classList.add('loading');
  generateBtn.textContent = 'Generating';
  generateError.classList.add('hidden');

  try {
    const title = recipeName.value.trim();
    const status = recipeStatus.value;
    const macros = currentData?.macros || {};
    const totals = macros.totals || {};
    const ingredients = (macros.ingredients || []).map(i => i.original);

    const body = {
      title,
      cal: parseInt(per100Cal.value) || 0,
      fat: parseFloat(per100Fat.value) || 0,
      protein: parseFloat(per100Protein.value) || 0,
      carb: parseFloat(per100Carb.value) || 0,
      serving: '100g',
      total_weight: totals.grams || 0,
      ingredients,
      suffix: recipeSuffix.value,
      status,
      upc: status === 'repeat' ? reuseUpc.value : '',
      iteration_of: status === 'iteration' ? iterationOf.value : '',
    };

    const r = await api('/api/generate', {
      method: 'POST',
      body: JSON.stringify(body),
    });

    if (!r.success) {
      generateError.textContent = r.error || 'Generation failed';
      generateError.classList.remove('hidden');
      return;
    }

    generatedData = r.data;
    showResult(r.data, body);

    // Auto-print if copies > 0
    const nCopies = parseInt(nutritionCopies.value) || 0;
    const rCopies = parseInt(recipeCopies.value) || 0;
    if (nCopies > 0 || rCopies > 0) {
      await doPrint(r.data, nCopies, rCopies);
    }
  } catch (e) {
    generateError.textContent = `Error: ${e.message}`;
    generateError.classList.remove('hidden');
  } finally {
    generateBtn.disabled = false;
    generateBtn.classList.remove('loading');
    generateBtn.textContent = 'Generate & Print';
  }
});

function showResult(data, body) {
  nutritionPreview.src = data.nutrition_label;
  recipePreview.src = data.recipe_label;
  upcCode.textContent = data.upc;

  confirmSection.classList.add('hidden');
  resultSection.classList.remove('hidden');
}

async function doPrint(data, nCopies, rCopies) {
  try {
    const r = await api('/api/print', {
      method: 'POST',
      body: JSON.stringify({
        nutrition_filename: data.nutrition_filename,
        recipe_filename: data.recipe_filename,
        nutrition_copies: nCopies,
        recipe_copies: rCopies,
      }),
    });

    if (r.success) {
      printStatus.textContent = `Printed: ${(r.data.printed || []).join(', ')} to ${r.data.printer}`;
      printStatus.classList.remove('hidden');
    } else {
      printStatus.textContent = `Print failed: ${r.error}`;
      printStatus.className = 'error';
      printStatus.classList.remove('hidden');
    }
  } catch (e) {
    printStatus.textContent = `Print error: ${e.message}`;
    printStatus.className = 'error';
    printStatus.classList.remove('hidden');
  }
}

// Reprint
reprintBtn.addEventListener('click', async () => {
  if (!generatedData) return;
  printStatus.classList.add('hidden');
  await doPrint(generatedData, parseInt(nutritionCopies.value) || 1, parseInt(recipeCopies.value) || 1);
});

// Download
downloadBtn.addEventListener('click', () => {
  if (!generatedData) return;
  [generatedData.nutrition_label, generatedData.recipe_label].forEach(url => {
    const a = document.createElement('a');
    a.href = url;
    a.download = '';
    a.click();
  });
});

// New recipe
newRecipeBtn.addEventListener('click', () => {
  resultSection.classList.add('hidden');
  inputSection.classList.remove('hidden');
  ingredientsInput.value = '';
  currentData = null;
  generatedData = null;
  printStatus.classList.add('hidden');
  loadHistory();
});

// --- History ---
async function loadHistory() {
  try {
    const r = await api('/api/recipes');
    if (!r.success) return;

    const entries = r.data || [];
    renderHistory(entries);
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
      div.addEventListener('click', () => {
        // Populate for reprint or iteration
        ingredientsInput.value = (entry.ingredients || []).join(', ');
        inputSection.classList.remove('hidden');
        confirmSection.classList.add('hidden');
        resultSection.classList.add('hidden');
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
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
