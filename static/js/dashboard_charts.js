(function(){
  const $ = (sel, ctx=document) => ctx.querySelector(sel);
  const rangeSel = $('#analyticsRange');
  const ctx = document.getElementById('revProfitChart');
  const groupSel = document.getElementById('analyticsGroup');
  const csvLink = document.getElementById('analyticsCsv');
  if (!ctx) return;
  const gctx = ctx.getContext('2d');

  function cssVar(name, fallback){
    const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return v || fallback;
  }
  function hexToRgba(hex, alpha){
    hex = (hex || '').replace('#','');
    if (hex.length === 3){ hex = hex.split('').map(h=>h+h).join(''); }
    const num = parseInt(hex || '000000',16);
    const r = (num >> 16) & 255, g = (num >> 8) & 255, b = num & 255;
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }
  function gradient(color){
    const gr = gctx.createLinearGradient(0, 0, 0, ctx.height);
    gr.addColorStop(0, hexToRgba(color, 0.35));
    gr.addColorStop(1, hexToRgba(color, 0.06));
    return gr;
  }
  function formatNumber(n){
    try{ return new Intl.NumberFormat(undefined, {maximumFractionDigits: 2}).format(n); }catch(_){ return n; }
  }

  let chart;
  async function loadData(days, group){
    const qs = new URLSearchParams({days: String(days), group: (group||'day')});
    const resp = await fetch(`/dashboard/analytics.json?${qs.toString()}`, {credentials: 'same-origin'});
    if (!resp.ok) return null;
    return await resp.json();
  }

  function render(data){
    const labels = data.labels;
    const revenue = data.datasets.revenue;
    const profit = data.datasets.profit;
    const net = data.datasets.net_sales;
    // Theme-aware colors
    const colorText = cssVar('--rh-accent', '#e5e7eb');
    const colorGrid = cssVar('--rh-border', '#3a3a3a');
    const colorGold = cssVar('--rh-gold', '#d4af37');
    const colorBlue = '#3b82f6';
    const colorGreen = '#22c55e';
    const cur = ctx.dataset.currency || '₹';

    // If Chart.js is unavailable, draw a simple canvas chart fallback
    if (typeof window.Chart === 'undefined'){
      simpleCanvasChart(ctx, {labels, revenue, profit, net, colorText, colorGrid});
      return;
    }

    const cfg = {
      type: 'line',
      data: {
        labels,
        datasets: [
          {label: 'Revenue', data: revenue, borderColor: colorGold, backgroundColor: gradient(colorGold), tension:.35, fill:true, pointRadius:2, pointHoverRadius:5},
          {label: 'Net Sales', data: net, borderColor: colorBlue, backgroundColor: gradient(colorBlue), tension:.35, fill:true, pointRadius:2, pointHoverRadius:5},
          {label: 'Estimated Profit', data: profit, borderColor: colorGreen, backgroundColor: gradient(colorGreen), tension:.35, fill:true, pointRadius:2, pointHoverRadius:5},
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        stacked: false,
        plugins: {
          legend: { position: 'bottom', labels: { color: colorText } },
          tooltip: { callbacks: { label: (pt)=> `${pt.dataset.label}: ${cur}${formatNumber(pt.parsed.y)}` } }
        },
        scales: {
          x: { grid: { color: hexToRgba(colorGrid, 0.25) }, ticks: { color: colorText } },
          y: { beginAtZero: true, grid: { color: hexToRgba(colorGrid, 0.25) }, ticks: { color: colorText, callback: (v)=> `${cur}${formatNumber(v)}` } }
        }
      }
    };
    if (chart) { chart.destroy(); }
    chart = new Chart(ctx, cfg);
  }

  function simpleCanvasChart(canvas, series){
    const c = canvas.getContext('2d');
    const W = canvas.width = canvas.clientWidth || canvas.width;
    const H = canvas.height = canvas.clientHeight || canvas.height;
    const m = {l: 48, r: 16, t: 16, b: 26};
    const axW = W - m.l - m.r, axH = H - m.t - m.b;
    const labels = series.labels;
    const datasets = [
      {data: series.revenue, color: '#d4af37', name: 'Revenue'},
      {data: series.profit, color: '#22c55e', name: 'Profit'},
    ];
    const all = datasets.flatMap(d=>d.data);
    const max = Math.max(1, ...all);
    const min = Math.min(0, ...all);
    const x = (i)=> m.l + (labels.length<=1 ? 0 : (i*(axW/(labels.length-1))));
    const y = (v)=> m.t + axH - (axH * (v-min)/(max-min));
    // clear
    c.clearRect(0,0,W,H);
    c.font = '12px system-ui, -apple-system, Segoe UI, Roboto, Arial';
    c.fillStyle = series.colorText || '#e5e7eb';
    // grid
    c.strokeStyle = series.colorGrid || 'rgba(100,100,100,.3)';
    c.lineWidth = 1;
    for(let i=0;i<5;i++){
      const yy = m.t + (i*(axH/4));
      c.beginPath(); c.moveTo(m.l, yy); c.lineTo(W-m.r, yy); c.stroke();
    }
    // axes
    c.strokeStyle = series.colorText || '#e5e7eb';
    c.beginPath(); c.moveTo(m.l, m.t); c.lineTo(m.l, m.t+axH); c.lineTo(W-m.r, m.t+axH); c.stroke();
    // lines
    datasets.forEach(ds=>{
      c.strokeStyle = ds.color; c.lineWidth = 2; c.beginPath();
      ds.data.forEach((v,i)=>{ const xx=x(i), yy=y(v); if(i===0) c.moveTo(xx,yy); else c.lineTo(xx,yy); });
      c.stroke();
    });
    // legend
    let lx=m.l, ly= m.t+8;
    datasets.forEach(ds=>{ c.fillStyle=ds.color; c.fillRect(lx, ly-8, 10, 10); c.fillStyle=series.colorText||'#e5e7eb'; c.fillText(ds.name, lx+14, ly); lx+=90; });
  }

  async function refresh(){
    const days = rangeSel ? rangeSel.value : '30';
    const group = groupSel ? groupSel.value : 'day';
    const data = await loadData(days, group);
    if (data) render(data);
    if (csvLink){
      const qs = new URLSearchParams({days: String(days), group: group});
      csvLink.href = `/dashboard/analytics.csv?${qs.toString()}`;
    }
  }

  if (rangeSel){ rangeSel.addEventListener('change', refresh); }
  if (groupSel){ groupSel.addEventListener('change', refresh); }

  function ensureChartLoaded(cb){
    if (window.Chart) { cb(); return; }
    var s = document.createElement('script');
    s.src = 'https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js';
    s.async = true;
    s.onload = cb;
    s.onerror = function(){ console.warn('Chart.js failed to load from CDN'); };
    document.head.appendChild(s);
  }

  // Draw once immediately (will use simple canvas fallback if Chart.js isn't ready)
  refresh();
  // Then try to load Chart.js and redraw with full features if available
  ensureChartLoaded(refresh);
})();
