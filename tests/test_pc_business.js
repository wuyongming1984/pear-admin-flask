// Offline regressions for actual PC form callbacks; no server or database required.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.join(__dirname, '..');
const source = file => fs.readFileSync(path.join(root, 'templates', file), 'utf8');

const project = source('project/info/project_info.html');
const uploadStart = project.indexOf('    upload.render({');
const uploadEnd = project.indexOf('\n    });', uploadStart) + '\n    });'.length;
let options;
const context = {
  upload: { render: value => { options = value; } },
  window: { location: { origin: 'http://offline' } },
  localStorage: { getItem: () => 'test' },
  attachmentList: [{ id: 1, url: '/old.pdf' }],
  pendingUploads: 0, uploadSession: 0, uploadSessions: {}, uploadFiles: {},
  renderAttachmentList() {}, updateAttachmentsData() {},
  generateAttachmentCode: () => 'A002', currentProjectName: 'Project',
  $: () => ({ val: () => 'Project' }), layer: { msg() {} }
};
vm.runInNewContext(project.slice(uploadStart, uploadEnd), context);
// Layui indexes are opaque IDs, never array offsets.
const item = { code: 0, data: { id: 9, url: '/new.pdf', filename: 'new.pdf', size: 30 } };
if (options.choose) options.choose({ pushFile: () => ({ 'opaque-file-42': { name: 'new.pdf' } }) });
if (options.before) options.before({ preview: cb => cb('opaque-file-42', { name: 'new.pdf' }) });
options.done(item, 'opaque-file-42');
assert.equal(context.attachmentList.length, 2);
assert.equal(context.attachmentList[1].url, '/new.pdf');
assert.equal(context.attachmentList[0].url, '/old.pdf');
if (options.choose) options.choose({ pushFile: () => ({ 'failed-file': { name: 'failed.pdf' } }) });
options.done({ code: -1, msg: 'Upload failed' }, 'failed-file');
assert.equal(context.attachmentList.length, 2, 'failed uploads must not add attachments');
assert.equal(context.pendingUploads, 0);
options.choose({ pushFile: () => ({ 'late-file': { name: 'late.pdf' } }) });
context.uploadSession++;
options.done(item, 'late-file');
assert.equal(context.attachmentList.length, 2, 'late uploads cannot leak into another project modal');
options.choose({ pushFile: () => ({ 'network-error': {} }) });
options.error('network-error');
assert.equal(context.pendingUploads, 0, 'network failure releases the upload guard');
console.log('PC project attachment callback regressions passed');

for (const [file, filter] of [
  ['project/info/project_info.html', 'project-form-btn'],
  ['supplier/info/supplier_info.html', 'supplier-form-btn'],
  ['payer/info/payer_info.html', 'payer-form-btn'],
  ['order_pay/info/order_info.html', 'order-form-btn'],
  ['order_pay/info/pay_info.html', 'save']
]) {
  const html = source(file);
  const match = new RegExp('form\\.on\\([\'\"]submit\\(' + filter + '\\)[\'\"]').exec(html);
  // The handler ends with its final return false and closing registration.
  const tail = html.slice(match.index).match(/return false;\s*\n\s*\}\);/);
  const callbackSource = html.slice(match.index, match.index + tail.index + tail[0].length);
  let submit, requests = [];
  const jq = () => ({ val: () => '', prop() { return this; }, addClass() { return this; }, removeClass() { return this; } });
  jq.ajax = options => requests.push(options);
  const sandbox = { form: { on: (_, handler) => { submit = handler; } },
    $: jq, makeRequest: jq.ajax, window: { location: { origin: '' } },
    localStorage: { getItem: () => 'test' }, layer: { msg() {} },
    attachmentList: [], selectedInvoices: [], pendingUploads: 0,
    formSubmitting: false, formSaved: false, formReady: true,
    orderId: '0', currentPaymentId: null, initialOrderId: null, savedOrderId: null,
    API: { PAY: '/api/v1/pay/' }, isPrintAfterSave: false };
  vm.runInNewContext(callbackSource, sandbox);
  submit({ field: { id: '0' } });
  submit({ field: { id: '0' } });
  assert.equal(requests.length, 1, file + ': repeated clicks must send only one request');
  requests[0].complete();
  submit({ field: { id: '0' } });
  assert.equal(requests.length, 2, file + ': failed requests must permit retry');
  if (file.startsWith('order_pay/')) {
    requests[1].complete();
    sandbox.formReady = false;
    submit({ field: { id: '0' } });
    assert.equal(requests.length, 2, 'failed detail load cannot overwrite attachments/invoices');
    sandbox.formReady = true;
    sandbox.pendingUploads = 1;
    submit({ field: { id: '0' } });
    assert.equal(requests.length, 2, 'saving must wait for attachment uploads');
  }
  for (const [index, script] of [...html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)].entries()) {
    if (/type=["']text\/html/.test(script[1])) continue;
    new vm.Script(script[2], { filename: file + ':' + index });
  }
}
console.log('PC submission concurrency regressions passed');

for (const file of ['order_pay/order_base.html', 'order_pay/pay_base.html']) {
  const html = source(file);
  for (const script of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)) {
    if (/type=["']text\/html/.test(script[1])) continue;
    new vm.Script(script[2], { filename: file });
  }
}

// Filling an edit form must await every option chunk, including entries beyond 500.
const payment = source('order_pay/info/pay_info.html');
const chunkStart = payment.indexOf('function renderSelectInChunks(');
const chunkEnd = payment.indexOf('\n      // 将原来的填充逻辑', chunkStart);
let optionsHtml = '', frames = [];
const chunks = { $: () => ({ html: text => { optionsHtml = text; }, append: text => { optionsHtml += text; } }),
  form: { render() {} }, requestAnimationFrame: callback => frames.push(callback) };
vm.runInNewContext(payment.slice(chunkStart, chunkEnd), chunks);
const ready = chunks.renderSelectInChunks('#payee', 'Choose', Array.from({ length: 501 }, (_, id) => id), id => `<option>${id}</option>`);
assert.equal(typeof ready.then, 'function', 'chunk renderer must return a completion promise');
assert.equal(optionsHtml.includes('<option>500</option>'), false);
frames.shift()();
ready.then(() => {
  assert.ok(optionsHtml.includes('<option>500</option>'));
  console.log('PC deferred select initialization regression passed');
});
