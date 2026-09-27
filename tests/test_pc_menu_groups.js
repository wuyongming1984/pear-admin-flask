const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { JSDOM } = require('../frontend-desktop/node_modules/jsdom');
const root = path.resolve(__dirname, '..');
const dom = new JSDOM(`<script src="http://localhost/static/component/layui/layui.js"></script>
  <div id="sideMenu"><ul>
  <li><a href="#"><span>First</span></a><dl class="layui-nav-child" style="height:1px;overflow:hidden;padding-top:0px"><dd><a href="#">Leaf</a></dd></dl></li>
  <li><a href="#">Second</a><dl class="layui-nav-child"><dd>Item</dd></dl></li>
  </ul></div>`, { runScripts: 'outside-only', url: 'http://localhost/' });
dom.window.eval(fs.readFileSync(path.join(root, 'static/component/layui/layui.js'), 'utf8'));
dom.window.layui.use(['jquery'], () => {
  try {
    const win = dom.window;
    win.$ = win.layui.jquery;
    const source = fs.readFileSync(path.join(root, 'static/component/pear/module/menu.js'), 'utf8');
    win.eval(source.slice(source.indexOf('  function resetGroupLayout('), source.indexOf('  function createMenu(')));
    win.bindGroupToggle({ elem: 'sideMenu', accordion: true });
    win.bindGroupToggle({ elem: 'sideMenu', accordion: true });
    const groups = win.document.querySelectorAll('li');
    let legacyClicks = 0, leafClicks = 0;
    groups[0].querySelector('a').addEventListener('click', () => legacyClicks++);
    groups[0].querySelector('dd a').addEventListener('click', () => leafClicks++);
    groups[0].querySelector('span').click();
    assert(groups[0].classList.contains('layui-nav-itemed'));
    assert.equal(groups[0].querySelector('dl').style.height, '');
    assert.equal(groups[0].querySelector('dl').style.overflow, '');
    assert.equal(legacyClicks, 0, 'Legacy animation must not run alongside group toggling');
    groups[0].querySelector('dd a').click();
    assert.equal(leafClicks, 1, 'Leaf navigation must remain intact');
    for (let i = 1; i <= 20; i++) {
      const selected = groups[i % 2];
      selected.querySelector('a').click();
      assert(selected.classList.contains('layui-nav-itemed'));
      assert(!groups[(i + 1) % 2].classList.contains('layui-nav-itemed'));
    }
    groups[0].querySelector('a').click();
    assert(!groups[0].classList.contains('layui-nav-itemed'));
    console.log('Menu stale-height recovery, accordion switching, repeat binding, collapse and leaf navigation passed');
  } catch (error) { console.error(error); process.exitCode = 1; }
  finally { dom.window.close(); }
});
