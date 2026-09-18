import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';

const source = await readFile(new URL('../comfy_extensions/H3_Director_Entry/web/director-entry.js', import.meta.url), 'utf8');
const workflow = JSON.parse(await readFile(new URL('../workflows/comfy-ui/director-single-t2v.json', import.meta.url)));

// Behavioural adapter contract test, not a substitute for the pinned live DOM.
class Element {
    children = []; listeners = {}; parentNode = null;
    append(...children) {
        for (const child of children) {
            child.remove(); child.parentNode = this; this.children.push(child);
        }
    }
    remove() {
        if (this.parentNode) this.parentNode.children = this.parentNode.children.filter(c => c !== this);
        this.parentNode = null;
    }
    setAttribute() {}
    addEventListener(name, fn) { this.listeners[name] = fn; }
    focus() { this.focused = true; }
}

async function boot({ search = '?director=1', resume = false, failFetch = false, missing = false, busy = false } = {}) {
    const body = new Element(), host = new Element(), root = new Element();
    host.append(root);
    let flushes = 0, renders = 0, fetches = 0, loads = 0, ticks = 0;
    const editor = { root, flushTimelineSync() { flushes++; }, scheduleSettleRender() { renders++; } };
    const node = { type: 'MiniMaxH3Director', _minimaxEditor: editor };
    const oldGraph = { id: resume ? workflow.id : 'user-graph', _nodes: [node], edited: 'keep me' };
    const savedTabs = [oldGraph];
    let extension;
    const app = {
        graph: oldGraph, extensionManager: { spinner: busy },
        registerExtension(ext) { extension = ext; },
        async loadGraphData(data, clean, restore, filename) {
            assert.equal(filename, null); assert.equal(clean, true); assert.equal(restore, true);
            assert.equal(data.id, workflow.id);
            extension.beforeConfigureGraph();
            loads++;
            this.graph = { ...data, _nodes: missing ? [] : [node] };
            savedTabs.push(this.graph);
        },
    };
    const errors = [];
    const context = vm.createContext({
        URL, URLSearchParams, HTMLDialogElement: Element,
        location: { search, href: `http://localhost/${search}` },
        history: { state: {}, replaceState(_state, _title, url) { context.returnUrl = String(url); } },
        document: { body, createElement: tag => Object.assign(new Element(), { tag }) },
        console: { error() {} }, alert: error => errors.push(error),
        setTimeout(fn) { ticks++; app.extensionManager.spinner = false; fn(); },
        async fetch(url) {
            fetches++; assert.equal(String(url), '/h3-director/workflow');
            return { ok: !failFetch, status: 404, json: async () => structuredClone(workflow) };
        },
    });
    const module = new vm.SourceTextModule(source, {
        context, initializeImportMeta(meta) { meta.url = 'http://localhost/extensions/H3_Director_Entry/director-entry.js'; },
    });
    await module.link(specifier => specifier.endsWith('/api.js')
        ? new vm.SyntheticModule(['api'], function () { this.setExport('api', { fetchApi: context.fetch }); }, { context })
        : new vm.SyntheticModule(['app'], function () { this.setExport('app', app); }, { context }));
    await module.evaluate(); extension.setup();
    // Drain the asynchronous entry, including bounded missing-node timeout.
    for (let i = 0; i < 1000; i++) await Promise.resolve();
    return { app, extension, body, root, host, oldGraph, savedTabs, errors, context,
        counts: () => ({ flushes, renders, fetches, loads, ticks }) };
}

for (const search of ['', '?director=0']) {
    const t = await boot({ search });
    assert.equal(t.counts().fetches, 0); assert.equal(t.body.children.length, 0);
}
const t = await boot({ busy: true });
assert.equal(t.counts().loads, 1); assert.equal(t.counts().ticks, 1);
assert.equal(t.savedTabs[0], t.oldGraph); assert.equal(t.oldGraph.edited, 'keep me');
const dialog = t.body.children[0];
assert.equal(dialog.tag, 'section'); assert.equal(t.root.parentNode, dialog);
t.app.graph.edited = 'Director edit';
dialog.children[1].children[0].onclick();
assert.equal(t.root.parentNode, t.host); assert.equal(t.body.children.length, 0);
assert.equal(t.app.graph.edited, 'Director edit'); assert.equal(t.counts().flushes, 1);
assert.equal(t.context.returnUrl, 'http://localhost/');

const resumed = await boot({ resume: true });
assert.equal(resumed.counts().loads, 0); assert.equal(resumed.app.graph, resumed.oldGraph);
resumed.extension.beforeConfigureGraph();
assert.equal(resumed.root.parentNode, resumed.host);
const consumedEscape = await boot();
consumedEscape.body.children[0].listeners.keydown({ key: 'Escape', defaultPrevented: true,
    preventDefault() { assert.fail('already handled by native menu'); }, stopPropagation() {} });
assert.equal(consumedEscape.body.children.length, 1);
assert.equal(consumedEscape.root.parentNode, consumedEscape.body.children[0]);
const escaped = await boot();
let prevented = false;
escaped.body.children[0].listeners.keydown({ key: 'Escape', preventDefault() { prevented = true; }, stopPropagation() {} });
assert.ok(prevented); assert.equal(escaped.root.parentNode, escaped.host);
// Real Comfy lifecycle destroys old nodes before beforeConfigureGraph.
const destroyed = await boot();
const deadEditor = destroyed.app.graph._nodes[0]._minimaxEditor;
destroyed.root.remove(); deadEditor.root = null;
destroyed.app.graph._nodes[0]._minimaxEditor = null;
destroyed.app.graph._nodes = [];
const beforeDestroyCleanup = destroyed.counts();
destroyed.extension.beforeConfigureGraph();
assert.equal(destroyed.body.children.length, 0);
assert.equal(destroyed.root.parentNode, null);
assert.equal(destroyed.counts().flushes, beforeDestroyCleanup.flushes);
assert.equal(destroyed.counts().renders, beforeDestroyCleanup.renders);
const flushError = await boot();
flushError.app.graph._nodes[0]._minimaxEditor.flushTimelineSync = () => { throw Error('sync failed'); };
assert.throws(() => flushError.extension.beforeConfigureGraph(), /sync failed/);
assert.equal(flushError.body.children.length, 0);
assert.equal(flushError.root.parentNode, flushError.host);
for (const options of [{ failFetch: true }, { missing: true }, { search: '?director=1&url=https://invalid/' }]) {
    const failed = await boot(options);
    assert.equal(failed.errors.length, 1); assert.equal(failed.body.children.length, 0);
    if (options.search || options.failFetch) assert.equal(failed.counts().loads, 0);
}
console.log('Director adapter: opt-in, startup wait, native temporary load/resume, same-DOM return/Escape, failure paths passed');
