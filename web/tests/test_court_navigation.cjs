const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { test } = require('node:test');
const { runInNewContext } = require('node:vm');
const source = readFileSync(`${__dirname}/../static/js/app.js`, 'utf8');

class Element extends EventTarget {
  constructor() {
    super();
    this.children = [];
    this.attributes = {};
    this.dataset = {};
    this.style = { setProperty(name, value) { this[name] = value; } };
  }
  append(...children) { this.children.push(...children); }
  setAttribute(name, value) { this.attributes[name] = value; }
  removeAttribute(name) { delete this.attributes[name]; }
  focus() { this.focused = true; }
  contains(target) { return target === this || this.children.includes(target); }
}

function initialize(reducedMotion = false, courtView = false) {
  const keys = courtView ? ['notifications', 'capacity', 'history'] : ['event', 'hall', 'members'];
  const sections = keys.map((key, index) => {
    const section = Object.assign(new Element(), {
      id: `${courtView ? 'court' : 'form'}-section-${key}`,
      dataset: { courtSection: `${courtView ? '' : 'form-'}${key}` },
      top: index * 600, open: false,
    });
    if (courtView && key === 'capacity') section.dataset.sectionTitle = 'Members';
    const summary = new Element();
    section.querySelector = (selector) => ({
      h2: { textContent: key },
      '.form-section-number': courtView ? null : { textContent: `0${index + 1}` },
      summary,
    }[selector]);
    section.getBoundingClientRect = () => ({ top: section.top });
    section.scrollIntoView = (options) => { section.scrollOptions = options; };
    return section;
  });
  const navigator = Object.assign(new Element(), { hidden: true });
  const label = new Element();
  const links = new Element();
  const trigger = new Element();
  let capturedPointer = null;
  trigger.setPointerCapture = (id) => { capturedPointer = id; };
  trigger.hasPointerCapture = (id) => capturedPointer === id;
  trigger.releasePointerCapture = () => { capturedPointer = null; };
  trigger.getBoundingClientRect = () => {
    const left = Number.parseFloat(navigator.style.left || '18');
    const top = Number.parseFloat(navigator.style.top || '718');
    return { left, top, width: 280, height: 64, right: left + 280, bottom: top + 64 };
  };
  navigator.querySelector = (selector) => ({
    '[data-current-section]': label, '[data-section-links]': links, summary: trigger,
  }[selector]);
  const document = Object.assign(new EventTarget(), {
    documentElement: { scrollHeight: 2200 },
    querySelector(selector) {
      if (selector === '[data-section-navigator]') return navigator;
      if (selector === '.site-header') return { getBoundingClientRect: () => ({ bottom: 72 }) };
      return null;
    },
    querySelectorAll(selector) {
      return selector === '[data-court-section]' || selector.includes('.court-form > details[data-court-section]') ? sections : [];
    },
    createElement: () => new Element(),
    createTextNode: (textContent) => ({ textContent }),
  });
  const timers = [];
  const window = Object.assign(new EventTarget(), {
    location: { protocol: 'https:' }, scrollY: 0, innerHeight: 800, innerWidth: 1000,
    requestAnimationFrame(callback) { callback(); },
    setTimeout(callback) { timers.push(callback); },
    matchMedia: () => ({ matches: reducedMotion }),
  });
  runInNewContext(source, { document, window, localStorage: { getItem: () => null } });
  return { navigator, sections, label, links, trigger, window, document, timers };
}

test('navigation tracks scrolling and selects the last section at the page bottom', () => {
  const { navigator, sections, label, links, window } = initialize();
  assert.equal(navigator.hidden, false);
  assert.equal(links.children.length, 3);
  assert.equal(links.children[1].href, '#form-section-hall');
  assert.equal(label.textContent, '01 · event');
  sections[0].top = -500;
  sections[1].top = 90;
  window.dispatchEvent(new Event('scroll'));
  assert.equal(label.textContent, '02 · hall');
  assert.equal(links.children[1].attributes['aria-current'], 'location');
  assert.equal(links.children[0].attributes['aria-current'], undefined);
  window.scrollY = 1400;
  window.dispatchEvent(new Event('scroll'));
  assert.equal(label.textContent, '03 · members');
});

test('jumping opens the target, closes navigation, moves focus, and respects reduced motion', () => {
  for (const reducedMotion of [false, true]) {
    const { navigator, sections, label, links } = initialize(reducedMotion);
    navigator.open = true;
    const event = new Event('click', { cancelable: true });
    links.children[1].dispatchEvent(event);
    assert.equal(event.defaultPrevented, true);
    assert.equal(sections[1].open, true);
    assert.equal(navigator.open, false);
    assert.equal(sections[1].querySelector('summary').focused, true);
    assert.equal(sections[1].scrollOptions.behavior, reducedMotion ? 'instant' : 'smooth');
    assert.equal(label.textContent, '02 · hall');
  }
});

test('Escape restores focus to the trigger and outside clicks close navigation', () => {
  const { navigator, trigger, document } = initialize();
  navigator.open = true;
  const escape = new Event('keydown');
  escape.key = 'Escape';
  navigator.dispatchEvent(escape);
  assert.equal(navigator.open, false);
  assert.equal(trigger.focused, true);
  navigator.open = true;
  document.dispatchEvent(new Event('click'));
  assert.equal(navigator.open, false);
});

test('court view navigation numbers visible sections and uses descriptive capacity labels', () => {
  const { navigator, sections, links, label, window } = initialize(false, true);
  assert.equal(label.textContent, '01 · notifications');
  assert.equal(links.children[1].href, '#court-section-capacity');
  assert.equal(links.children[1].children[1].textContent, 'Members');
  navigator.open = true;
  links.children[1].dispatchEvent(new Event('click', { cancelable: true }));
  assert.equal(sections[1].open, true);
  assert.equal(navigator.open, false);
  assert.equal(label.textContent, '02 · Members');
  sections[0].top = -500;
  sections[1].top = -200;
  sections[2].top = 90;
  window.dispatchEvent(new Event('scroll'));
  assert.equal(label.textContent, '03 · history');
});

function pointer(trigger, type, x, y, extra = {}) {
  const event = Object.assign(new Event(type, { cancelable: true }), {
    pointerId: 1, button: 0, clientX: x, clientY: y, ...extra,
  });
  trigger.dispatchEvent(event);
  return event;
}

test('dragging toward any edge leaves a reachable handle and suppresses the drag click', () => {
  for (const [edge, x, y, expected] of [
    ['left', -500, 728, ['left', '-236px']],
    ['right', 1500, 728, ['left', '956px']],
    ['top', 28, -1000, ['top', '-20px']],
    ['bottom', 28, 1500, ['top', '756px']],
  ]) {
    const { navigator, trigger, timers } = initialize();
    navigator.open = true;
    pointer(trigger, 'pointerdown', 28, 728);
    pointer(trigger, 'pointermove', x, y);
    assert.equal(navigator.open, false);
    pointer(trigger, 'pointerup', x, y);
    assert.equal(navigator.dataset.tucked, edge);
    assert.equal(navigator.style[expected[0]], expected[1]);
    assert.equal(navigator.dataset.dragging, undefined);
    const click = new Event('click', { cancelable: true });
    trigger.dispatchEvent(click);
    assert.equal(click.defaultPrevented, true);
    timers.forEach((callback) => callback());
    const nextClick = new Event('click', { cancelable: true });
    trigger.dispatchEvent(nextClick);
    assert.equal(nextClick.defaultPrevented, false);
  }
});

test('a tucked navigator can be dragged back with touch or revealed by opening it', () => {
  const { navigator, trigger } = initialize();
  pointer(trigger, 'pointerdown', 28, 728, { pointerType: 'touch' });
  pointer(trigger, 'pointermove', -252, 728);
  pointer(trigger, 'pointerup', -252, 728);
  assert.equal(navigator.dataset.tucked, 'left');
  pointer(trigger, 'pointerdown', 20, 728, { pointerType: 'touch' });
  pointer(trigger, 'pointermove', 300, 728);
  pointer(trigger, 'pointerup', 300, 728);
  assert.equal(navigator.dataset.tucked, undefined);
  assert.equal(navigator.style.left, '44px');
  pointer(trigger, 'pointerdown', 54, 728);
  pointer(trigger, 'pointermove', -500, 728);
  pointer(trigger, 'pointerup', -500, 728);
  navigator.open = true;
  navigator.dispatchEvent(new Event('toggle'));
  assert.equal(navigator.dataset.tucked, undefined);
  assert.equal(navigator.style.left, '12px');
  assert.ok(Number.parseFloat(navigator.style.top) >= 12);
});

test('small pointer movements preserve clicks; cancellation releases capture', () => {
  const { navigator, trigger } = initialize();
  pointer(trigger, 'pointerdown', 28, 728);
  pointer(trigger, 'pointermove', 30, 729);
  pointer(trigger, 'pointerup', 30, 729);
  assert.equal(navigator.style.left, undefined);
  const click = new Event('click', { cancelable: true });
  trigger.dispatchEvent(click);
  assert.equal(click.defaultPrevented, false);
  pointer(trigger, 'pointerdown', 28, 728);
  pointer(trigger, 'pointermove', -500, 728);
  pointer(trigger, 'pointercancel', -500, 728);
  assert.equal(trigger.hasPointerCapture(1), false);
  assert.equal(navigator.dataset.dragging, undefined);
});

test('resizing keeps a tucked handle reachable and menus open within the viewport', () => {
  const { navigator, trigger, window } = initialize();
  pointer(trigger, 'pointerdown', 28, 728);
  pointer(trigger, 'pointermove', 1500, 728);
  pointer(trigger, 'pointerup', 1500, 728);
  window.innerWidth = 400;
  window.innerHeight = 600;
  window.dispatchEvent(new Event('resize'));
  assert.equal(navigator.style.left, '356px');
  assert.ok(Number.parseFloat(navigator.style.top) <= 556);
  navigator.open = true;
  navigator.dispatchEvent(new Event('toggle'));
  assert.equal(navigator.style.left, '108px');
  assert.equal(navigator.style.top, '524px');
  pointer(trigger, 'pointerdown', 118, 534);
  pointer(trigger, 'pointermove', 118, 30);
  pointer(trigger, 'pointerup', 118, 30);
  navigator.open = true;
  navigator.dispatchEvent(new Event('toggle'));
  assert.equal(navigator.dataset.menuBelow, 'true');
  assert.ok(Number.parseFloat(navigator.style['--section-menu-height']) > 44);
});
