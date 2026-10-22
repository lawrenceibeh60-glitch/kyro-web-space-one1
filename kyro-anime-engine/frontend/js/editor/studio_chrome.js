const $ = id => document.getElementById(id);
const dropdown = $('studioDropdown');
const menuButtons = [...document.querySelectorAll('.studio-menu-trigger')];

const MENUS = {
  file: [
    ['Save Project', 'save', 'Ctrl+S'],
    ['Export Animation…', 'exportBtn', 'Ctrl+E'],
    ['Import Project JSON…', 'importBtn'],
    ['New Drawing Exposure', 'newDrawing'],
    ['New Geometry Graph', 'geoNewGraph']
  ],
  edit: [
    ['Undo', 'undo', 'Ctrl+Z'],
    ['Redo', 'redo', 'Ctrl+Shift+Z'],
    ['Duplicate Layer', 'duplicateLayer', 'Shift+D'],
    ['Delete Layer', 'deleteLayer'],
    ['Clear Current Exposure', 'clearExposure']
  ],
  view: [
    ['Toggle Viewport Grid', 'gridToggle'],
    ['Toggle Onion Skin', 'onionToggle'],
    ['Focus / Restore Canvas', 'canvasFocus'],
    ['Reset Workspace Layout', 'p_reset']
  ],
  animation: [
    ['Play / Pause', 'play', 'Space'],
    ['First Frame', 'firstF', 'Home'],
    ['Previous Frame', 'prevF', '←'],
    ['Next Frame', 'nextF', '→'],
    ['Last Frame', 'lastF', 'End'],
    ['Toggle Loop', 'loop'],
    ['Toggle Auto-Key', 'autokey'],
    ['Add Timeline Marker', 'addMarker'],
    ['Create Blank Drawing', 'newDrawing'],
    ['Duplicate Exposure', 'duplicateDrawing'],
    ['Hold Exposure', 'holdDrawing']
  ],
  workspace: [
    ['Draw Workspace', 'workspace:draw'],
    ['Animate Workspace', 'workspace:animate'],
    ['Edit Workspace', 'workspace:edit'],
    ['Studio Workspace', 'workspace:studio'],
    ['Geometry Nodes Workspace', 'workspace:nodes']
  ]
};

let openMenu = null;
function closeMenu() {
  dropdown.hidden = true;
  dropdown.replaceChildren();
  menuButtons.forEach(button => button.setAttribute('aria-expanded', 'false'));
  openMenu = null;
}
function runCommand(command) {
  if (command.startsWith('workspace:')) {
    const id = command.slice('workspace:'.length);
    document.querySelector(`#wtabs [data-ws="${id}"]`)?.click();
    return;
  }
  const target = $(command);
  if (!target) return;
  if (command === 'p_reset') {
    document.querySelector('#propertiesTabs [data-tab="prefs"]')?.click();
    document.querySelector('[data-tab="prefs"]')?.click();
  }
  target.click();
}
function showMenu(name, trigger) {
  if (openMenu === name && !dropdown.hidden) {
    closeMenu();
    return;
  }
  dropdown.replaceChildren();
  const commands = MENUS[name] || [];
  commands.forEach(([label, command, shortcut], index) => {
    if (name === 'edit' && index === 0 || name === 'animation' && index === 0) {
      if (index > 0) {
        const separator = document.createElement('div');
        separator.className = 'menu-separator';
        separator.setAttribute('role', 'separator');
        dropdown.append(separator);
      }
    }
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'studio-command';
    button.setAttribute('role', 'menuitem');
    const text = document.createElement('span');
    text.textContent = label;
    button.append(text);
    if (shortcut) {
      const key = document.createElement('span');
      key.className = 'shortcut';
      key.textContent = shortcut;
      button.append(key);
    }
    button.addEventListener('click', () => {
      closeMenu();
      runCommand(command);
    });
    dropdown.append(button);
  });
  dropdown.hidden = false;
  openMenu = name;
  menuButtons.forEach(button => button.setAttribute('aria-expanded', String(button === trigger)));
}
menuButtons.forEach(button => button.addEventListener('click', event => {
  event.stopPropagation();
  showMenu(button.dataset.menu, button);
}));
document.querySelectorAll('[data-command]').forEach(button => {
  button.addEventListener('click', () => runCommand(button.dataset.command));
});
document.addEventListener('pointerdown', event => {
  if (!dropdown.hidden && !dropdown.contains(event.target) && !event.target.closest('.studio-menu-trigger')) closeMenu();
});
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && !dropdown.hidden) {
    closeMenu();
    menuButtons.find(button => button.dataset.menu === openMenu)?.focus();
  }
});
const frameReadout = $('frameReadout');
const context = $('studioFrameContext');
if (frameReadout && context) {
  const updateFrame = () => {
    const match = frameReadout.textContent.match(/\d+/);
    context.textContent = `FRAME ${String(match ? Number(match[0]) : 1).padStart(3, '0')}`;
  };
  new MutationObserver(updateFrame).observe(frameReadout, { childList: true, subtree: true, characterData: true });
  updateFrame();
}
