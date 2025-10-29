// Generic helper to add new inline formset rows on the product form
(function(){
  function addRow(prefix){
    const totalEl = document.getElementById(`id_${prefix}-TOTAL_FORMS`);
    const container = document.getElementById(`${prefix}Container`);
    const template = document.getElementById(`template-${prefix}`);
    if (!totalEl || !container || !template) return;
    const idx = parseInt(totalEl.value, 10);
    const html = template.innerHTML.replace(/__prefix__/g, String(idx));
    const tmp = document.createElement('div');
    tmp.innerHTML = html.trim();
    container.appendChild(tmp.firstElementChild);
    totalEl.value = String(idx + 1);
  }

  document.addEventListener('click', function(e){
    const btn = e.target.closest('.add-formset');
    if (!btn) return;
    const prefix = btn.getAttribute('data-formset');
    if (prefix) addRow(prefix);
  });
})();

