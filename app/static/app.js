function openPreview(url){
  const u = new URL(window.location);
  // Use server-side preview to bypass X-Frame-Options/CSP for common cases
  u.searchParams.set('open_url', `/preview?url=${encodeURIComponent(url)}`);
  window.location = u.toString();
}

// Lazy health check badges
async function runHealthChecks(){
  const els = document.querySelectorAll('[data-check]');
  for (const el of els){
    const url = el.getAttribute('data-url');
    try{
      const r = await fetch(`/check?url=${encodeURIComponent(url)}`);
      const data = await r.json();
      if (data.ok){
        el.textContent = '— OK';
        el.style.color = '#56d364';
      } else {
        el.textContent = data.status ? `— ${data.status}` : '— viga';
        el.style.color = '#ff6b6b';
      }
    } catch(e){
      el.textContent = '— viga';
      el.style.color = '#ff6b6b';
    }
  }
}

window.addEventListener('DOMContentLoaded', runHealthChecks);

// Bulk actions
function selectedIds(){
  return Array.from(document.querySelectorAll('#bookTable tbody input[type="checkbox"]:checked')).map(x=>x.value);
}
function bulkDelete(){
  const ids = selectedIds();
  if(ids.length===0) return;
  if(!confirm(`Kustuta ${ids.length} kirjet?`)) return;
  const form = document.getElementById('bulkForm');
  document.getElementById('bulkIds').value = ids.join(',');
  form.action = '/bookmarks/bulk_delete';
  form.method = 'post';
  form.submit();
}
function bulkMove(){
  const ids = selectedIds();
  if(ids.length===0) return;
  const target = document.getElementById('bulkTarget').value;
  const form = document.getElementById('bulkForm');
  document.getElementById('bulkIds').value = ids.join(',');
  const extra = document.createElement('input');
  extra.type='hidden'; extra.name='target_topic_id'; extra.value=target;
  form.appendChild(extra);
  form.action = '/bookmarks/bulk_move';
  form.method = 'post';
  form.submit();
}
function toggleAll(master){
  document.querySelectorAll('#bookTable tbody input[type="checkbox"]').forEach(cb=>{ cb.checked = master.checked; });
}

// DnD: drag row to sidebar folder
let draggedBookmarkId = null;
function onDragStart(ev, id){
  draggedBookmarkId = id;
  ev.dataTransfer.setData('text/plain', String(id));
}
window.onDragStart = onDragStart;

async function onDropToTopic(ev, topicId){
  ev.preventDefault();
  const id = draggedBookmarkId || ev.dataTransfer.getData('text/plain');
  if(!id) return;
  try{
    const form = new FormData();
    form.append('target_topic_id', String(topicId));
    await fetch(`/bookmarks/move/${id}`, { method:'POST', body: form });
    // reload to reflect
    location.href = `/?topic_id=${topicId}`;
  } catch(e){}
}
window.onDropToTopic = onDropToTopic;

// Resizable vertical panes (sidebar and preview)
function initResizableColumns(){
  const root = document.querySelector('.layout');
  if(!root) return;

  // Load saved widths
  const savedSidebar = localStorage.getItem('sidebarWidth');
  const savedPreview = localStorage.getItem('previewWidth');
  if(savedSidebar){
    document.documentElement.style.setProperty('--sidebar-w', savedSidebar);
  }
  if(savedPreview){
    document.documentElement.style.setProperty('--preview-w', savedPreview);
  }

  let dragging = null; // 'left' or 'right'
  let startX = 0;
  let startSidebar = 0;
  let startPreview = 0;

  function onPointerMove(ev){
    if(!dragging) return;
    const dx = ev.clientX - startX;
    if(dragging === 'left'){
      const newPx = Math.max(180, startSidebar + dx); // min 180px
      document.documentElement.style.setProperty('--sidebar-w', newPx + 'px');
    } else if(dragging === 'right'){
      const viewport = window.innerWidth;
      const newPx = Math.max(260, startPreview - dx); // invert: dragging handle left/right
      const clamped = Math.min(Math.max(newPx, 260), Math.floor(viewport * 0.7));
      document.documentElement.style.setProperty('--preview-w', clamped + 'px');
    }
  }
  function onPointerUp(){
    if(dragging === 'left'){
      localStorage.setItem('sidebarWidth', getComputedStyle(document.documentElement).getPropertyValue('--sidebar-w').trim());
    } else if(dragging === 'right'){
      localStorage.setItem('previewWidth', getComputedStyle(document.documentElement).getPropertyValue('--preview-w').trim());
    }
    dragging = null;
    document.body.classList.remove('dragging');
    window.removeEventListener('pointermove', onPointerMove);
    window.removeEventListener('pointerup', onPointerUp);
  }

  root.querySelectorAll('.col-resize').forEach(handle => {
    handle.addEventListener('pointerdown', ev => {
      dragging = handle.getAttribute('data-side');
      startX = ev.clientX;
      const sidebarW = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--sidebar-w'));
      const previewW = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--preview-w'));
      startSidebar = isNaN(sidebarW) ? 280 : sidebarW;
      startPreview = isNaN(previewW) ? Math.floor(window.innerWidth * 0.4) : previewW;
      // ensure we capture pointer even if cursor leaves handle
      try { handle.setPointerCapture(ev.pointerId); } catch(_) {}
      document.body.classList.add('dragging');
      window.addEventListener('pointermove', onPointerMove);
      window.addEventListener('pointerup', onPointerUp);
      ev.preventDefault();
    });

    // Double-click: reset or cycle through presets
    handle.addEventListener('dblclick', () => {
      const side = handle.getAttribute('data-side');
      if (side === 'left'){
        // cycle sidebar widths (px)
        const presets = [220, 280, 340];
        const key = 'sidebarPresetIndex';
        let idx = parseInt(localStorage.getItem(key) || '1', 10); // default to 280 (index 1)
        idx = (idx + 1) % presets.length;
        const px = presets[idx];
        document.documentElement.style.setProperty('--sidebar-w', px + 'px');
        localStorage.setItem('sidebarWidth', px + 'px');
        localStorage.setItem(key, String(idx));
      } else if (side === 'right'){
        // cycle preview widths as fractions of viewport
        const presets = [0.3, 0.4, 0.5, 0.6];
        const key = 'previewPresetIndex';
        let idx = parseInt(localStorage.getItem(key) || '1', 10); // default to 0.4 (index 1)
        idx = (idx + 1) % presets.length;
        const px = Math.floor(window.innerWidth * presets[idx]);
        document.documentElement.style.setProperty('--preview-w', px + 'px');
        localStorage.setItem('previewWidth', px + 'px');
        localStorage.setItem(key, String(idx));
      }
    });
  });
}

window.addEventListener('DOMContentLoaded', initResizableColumns);

// Generic file picker that submits via a real form for maximum compatibility
function pickAndUpload(acceptTypes, targetUrl){
  const input = document.createElement('input');
  input.type = 'file';
  input.name = 'file';
  if (acceptTypes){
    input.setAttribute('accept', acceptTypes);
  }
  input.style.position = 'fixed';
  input.style.top = '0';
  input.style.left = '0';
  input.style.opacity = '0';
  input.style.width = '1px';
  input.style.height = '1px';

  const form = document.createElement('form');
  form.method = 'POST';
  form.enctype = 'multipart/form-data';
  form.action = targetUrl;
  form.style.position = 'fixed';
  form.style.top = '0';
  form.style.left = '0';
  form.style.opacity = '0';
  form.style.width = '1px';
  form.style.height = '1px';

  form.appendChild(input);

  input.addEventListener('change', () => {
    if (!input.files || input.files.length === 0){
      document.body.removeChild(form);
      return;
    }
    form.submit();
    // Let the browser navigate; cleanup is unnecessary as page unloads
  }, { once: true });

  document.body.appendChild(form);
  input.click();
}

// Main select menu actions
function menuAction(val){
  switch(val){
    case 'import_html':
      window.location = '/ui/import/html';
      break;
    case 'import_csv':
      window.location = '/ui/import/csv';
      break;
    case 'import_json':
      window.location = '/ui/import/json';
      break;
    case 'export_html':
      window.location = '/export';
      break;
    case 'export_csv':
      window.location = '/export.csv';
      break;
    case 'export_json':
      window.location = '/export.json';
      break;
    case 'backup':
      window.location = '/backup';
      break;
    case 'restore':
      window.location = '/ui/restore';
      break;
    case 'sample_csv':
      window.location = '/sample.csv';
      break;
    case 'sample_json':
      window.location = '/sample.json';
      break;
  }
}
window.menuAction = menuAction;



