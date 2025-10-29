// Utilities for managing Django formsets and dependent selects in the custom dashboard
(function(){
  const $ = (sel, ctx=document) => ctx.querySelector(sel);
  const $$ = (sel, ctx=document) => Array.from(ctx.querySelectorAll(sel));

  // Order items formset handling
  const mgmtTotal = document.getElementById('id_orderitem_set-TOTAL_FORMS');
  const container = document.getElementById('itemsContainer');
  const addBtn = document.getElementById('addItemBtn');
  const emptyTpl = document.getElementById('empty-form-template');
  const variantMap = window.VARIANT_MAP || {};

  function updateVariantOptions(row){
    const prodSel = row.querySelector('select[name$="-product"]');
    const varSel = row.querySelector('select[name$="-variant"]');
    if (!prodSel || !varSel) return;
    const pid = prodSel.value;
    const options = [{id:"", text:"---------"}].concat(variantMap[pid] || []);
    varSel.innerHTML = "";
    for(const opt of options){
      const o = document.createElement('option');
      o.value = opt.id; o.textContent = opt.text;
      varSel.appendChild(o);
    }
  }

  function hookRow(row){
    const prodSel = row.querySelector('select[name$="-product"]');
    if (prodSel){ prodSel.addEventListener('change', () => updateVariantOptions(row)); }
    // Initialize on load
    updateVariantOptions(row);
  }

  function addForm(){
    const total = parseInt(mgmtTotal.value, 10);
    const html = emptyTpl.innerHTML.replace(/__prefix__/g, String(total));
    const frag = document.createElement('div');
    frag.innerHTML = html.trim();
    const row = frag.firstElementChild;
    container.appendChild(row);
    mgmtTotal.value = String(total + 1);
    hookRow(row);
  }

  if (mgmtTotal && container && addBtn && emptyTpl){
    addBtn.addEventListener('click', addForm);
    $$('.formset-item', container).forEach(hookRow);
  }
})();

