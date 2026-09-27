const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname, '../static/component/pear/module/admin.js'), 'utf8');
const code = source.slice(source.indexOf('    function setCollapsed('), source.indexOf('\n    /**', source.indexOf('    function setCollapsed(')));
function scenario(shell, menu) {
  const classes = {'.pear-admin': new Set(shell ? ['pear-mini'] : []), '#sideMenu':new Set(menu ? ['pear-nav-mini'] : []), '.collapse .layui-icon':new Set()};
  const $ = selector => ({is:name=>classes[selector].has(name.slice(1)),toggleClass(name,on){if(on)classes[selector].add(name);else classes[selector].delete(name);return this;}});
  const sideMenu={isCollapse:false,collapse(){const c=classes['#sideMenu'];if(c.has('pear-nav-mini'))c.delete('pear-nav-mini');else c.add('pear-nav-mini');}};
  const ctx={$,sideMenu};vm.createContext(ctx);vm.runInContext(code,ctx);
  const check=value=>{assert.equal(classes['.pear-admin'].has('pear-mini'),value);assert.equal(classes['#sideMenu'].has('pear-nav-mini'),value);assert.equal(sideMenu.isCollapse,value);};
  ctx.setCollapsed(true);check(true);ctx.setCollapsed(true);check(true);
  ctx.collapse();check(false);ctx.collapse();check(true);
  ctx.setCollapsed(false);check(false);ctx.setCollapsed(false);check(false);
}
for(const shell of [false,true])for(const menu of [false,true])scenario(shell,menu);
console.log('Sidebar initial-state repair, repeated set, expand and collapse regressions passed');

const menuSource = fs.readFileSync(require('node:path').join(__dirname, '../static/component/pear/module/menu.js'), 'utf8');
const hoverCode = menuSource.slice(menuSource.indexOf('  function isHoverMenu('), menuSource.indexOf('  function rationalizeHeaderControlWidth('));
const child = { classes: new Set(['layui-nav-hover']), style: { top: '130px', left: '60px' } };
const hoverContext = { $: selector => ({
  off() { return this; }, unbind() { return this; },
  removeClass(name) { assert.equal(selector, '#sideMenu .layui-nav-child'); child.classes.delete(name); return this; },
  css(values) { Object.assign(child.style, values); return this; },
}) };
vm.createContext(hoverContext);
vm.runInContext(hoverCode, hoverContext);
hoverContext.isHoverMenu(false, { elem: 'sideMenu' });
assert.equal(child.classes.has('layui-nav-hover'), false, 'Expanded submenus must leave fixed flyout positioning');
assert.equal(child.style.top, '', 'Expanded submenus must release inline vertical offsets');
assert.equal(child.style.left, '', 'Expanded submenus must release inline horizontal offsets');
console.log('Expanded submenu flyout cleanup regression passed');
