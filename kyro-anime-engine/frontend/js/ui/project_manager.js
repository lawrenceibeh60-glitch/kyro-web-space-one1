// frontend/js/ui/project_manager.js - home page: list / create / delete projects
import { Projects } from '../api/projects.js';
import { toast } from './notifications.js';

const $ = id => document.getElementById(id);

async function refresh() {
  const list = $('list');
  list.innerHTML = '';
  let items = [];
  try { items = await Projects.list(); } catch (e) { toast(e.message, 'err'); return; }

  if (!items.length) {
    const li = document.createElement('li');
    li.className = 'empty-projects';
    li.textContent = 'No projects yet - create a project or open the animation demo to get started.';
    list.append(li);
    return;
  }

  for (const p of items) {
    const li = document.createElement('li');
    const a = document.createElement('a');
    a.href = 'editor.html?project=' + encodeURIComponent(p.id);
    a.textContent = p.name;

    const small = document.createElement('small');
    small.textContent = p.modified || '';
    a.append(small);

    const del = document.createElement('button');
    del.textContent = 'Delete';
    del.onclick = async () => {
      if (!confirm(`Delete "${p.name}"?`)) return;
      try {
        await Projects.remove(p.id);
        await refresh();
      } catch (e) {
        toast(e.message, 'err');
      }
    };

    li.append(a, del);
    list.append(li);
  }
}

async function importProjectFile(file) {
  if (!file) return;
  try {
    const text = await file.text();
    const json = JSON.parse(text);
    const p = await Projects.import(json);
    location.href = 'editor.html?project=' + encodeURIComponent(p.id);
  } catch (e) {
    const msg = e?.message || 'Invalid JSON project file';
    toast(msg, 'err');
  }
}

$('create').onclick = async () => {
  try {
    const p = await Projects.create($('newName').value.trim() || 'Untitled');
    location.href = 'editor.html?project=' + encodeURIComponent(p.id);
  } catch (e) {
    toast(e.message, 'err');
  }
};

$('demo').onclick = async () => {
  try {
    const p = await Projects.template('bounce');
    location.href = 'editor.html?project=' + encodeURIComponent(p.id);
  } catch (e) {
    toast(e.message, 'err');
  }
};

document.querySelectorAll('[data-template]').forEach(button => {
  button.onclick = async () => {
    button.disabled = true;
    try {
      const p = await Projects.template(button.dataset.template);
      location.href = 'editor.html?project=' + encodeURIComponent(p.id);
    } catch (e) {
      toast(e.message, 'err');
    } finally {
      button.disabled = false;
    }
  };
});

$('importBtn').onclick = () => $('importFile').click();
$('importFile').onchange = async e => {
  const file = e.target.files?.[0];
  if (file) { await importProjectFile(file); e.target.value = ''; }
};

refresh();
