const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { test } = require('node:test');
const { runInNewContext } = require('node:vm');

const source = readFileSync(`${__dirname}/../static/js/app.js`, 'utf8');

function checkbox(checked = false) {
  return Object.assign(new EventTarget(), { checked, indeterminate: false, disabled: false });
}

function initialize({ roll = [], cleared = [], protocol = 'https:' } = {}) {
  const columns = { roll, cleared };
  const form = {
    querySelectorAll(selector) {
      return selector.includes('reserved_roll') ? columns.roll : columns.cleared;
    },
  };
  const toggles = Object.fromEntries(Object.keys(columns).map((column) => [
    column,
    Object.assign(checkbox(), { dataset: { statusAll: column }, form }),
  ]));
  const section = Object.assign(new EventTarget(), {
    dataset: { courtSection: 'participants' }, open: true,
  });
  const document = {
    documentElement: {},
    cookie: '',
    querySelector: () => null,
    querySelectorAll(selector) {
      if (selector === '[data-status-all]') return Object.values(toggles);
      if (selector === '[data-court-section]') return [section];
      return [];
    },
    addEventListener() {},
  };
  runInNewContext(source, {
    document, window: { location: { protocol } }, localStorage: { getItem: () => null },
  });
  return { toggles, section, document };
}

function change(input, checked) {
  input.checked = checked;
  input.dispatchEvent(new Event('change'));
}

test('bulk roll call includes reserved and online members and leaves clearing unchanged', () => {
  const reserved = checkbox(true);
  const online = checkbox(false);
  const cleared = checkbox(true);
  const { toggles } = initialize({ roll: [reserved, online], cleared: [cleared] });
  assert.equal(toggles.roll.indeterminate, true);
  assert.equal(toggles.roll.checked, false);
  change(toggles.roll, true);
  assert.equal(reserved.checked, true);
  assert.equal(online.checked, true);
  assert.equal(toggles.roll.indeterminate, false);
  change(toggles.roll, false);
  assert.equal(reserved.checked, false);
  assert.equal(online.checked, false);
  assert.equal(cleared.checked, true);
});

test('clearing supports bulk changes and individual changes update the mixed state', () => {
  const members = [checkbox(true), checkbox(true)];
  const roll = checkbox(true);
  const { toggles } = initialize({ roll: [roll], cleared: members });
  assert.equal(toggles.cleared.checked, true);
  change(members[0], false);
  assert.equal(toggles.cleared.checked, false);
  assert.equal(toggles.cleared.indeterminate, true);
  change(members[1], false);
  assert.equal(toggles.cleared.indeterminate, false);
  change(toggles.cleared, true);
  assert.ok(members.every((member) => member.checked));
  change(toggles.cleared, false);
  assert.ok(members.every((member) => !member.checked));
  assert.equal(roll.checked, true);
});

test('empty columns disable their bulk checkbox', () => {
  const { toggles } = initialize();
  for (const toggle of Object.values(toggles)) {
    assert.equal(toggle.disabled, true);
    assert.equal(toggle.checked, false);
    assert.equal(toggle.indeterminate, false);
  }
});

test('section toggles persist both states in a year-long cookie', () => {
  for (const protocol of ['https:', 'http:']) {
    const { section, document } = initialize({ protocol });
    for (const open of [false, true]) {
      section.open = open;
      section.dispatchEvent(new Event('toggle'));
      assert.equal(document.cookie,
        `court_section_participants=${open ? 'expanded' : 'collapsed'};path=/;max-age=31536000;samesite=lax${protocol === 'https:' ? ';secure' : ''}`);
    }
  }
});
