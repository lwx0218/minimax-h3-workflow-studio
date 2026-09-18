import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// ponytail: pinned frontend 1.49.6 + Director editor DOM, not a standalone app.
const requested = new URLSearchParams(location.search).get("director") === "1";
let closeEditor;

async function waitFor(getValue) {
    for (let i = 0; i < 300; i++) {
        const value = getValue();
        if (value) return value;
        await new Promise(resolve => setTimeout(resolve, 100));
    }
    throw new Error("Director 初始化超时；请返回普通画布检查节点和工作流。");
}

function showEditor(node) {
    const editor = node._minimaxEditor;
    const root = editor.root;
    const host = root.parentNode;
    if (!host) {
        throw new Error("当前浏览器或 Director DOM 不兼容；请使用普通画布。");
    }
    // Non-modal: upstream @mention menus are appended to document.body.
    const dialog = document.createElement("section");
    dialog.setAttribute("aria-label", "MiniMax H3 Director");
    // Upstream clipboard guards recognize this ancestor class.
    dialog.className = "h3-director-entry mmx-host";
    const style = document.createElement("style");
    style.textContent = `.h3-director-entry { display:block; position:fixed; inset:0; width:100vw; height:100vh;
        max-width:none; max-height:none; margin:0; border:0; padding:12px;
        box-sizing:border-box; overflow:auto; background:#151515; color:#eee; z-index:1000; }
        .h3-director-entry > nav { display:flex; gap:12px; align-items:center; margin-bottom:12px; }
        .h3-director-entry > nav button { padding:8px; cursor:pointer; }
        .h3-director-entry > .bd-wrap { width:100%; min-width:960px; }`;
    const nav = document.createElement("nav");
    const back = document.createElement("button");
    back.textContent = "返回画布 / 原生保存";
    back.type = "button";
    const note = document.createElement("span");
    note.textContent = "编辑保留在当前工作流；返回后使用 ComfyUI Save / Save As。不会自动运行。";
    nav.append(back, note);
    dialog.append(style, nav, root);
    document.body.append(dialog);
    // Keep upstream capture-phase timeline shortcuts, block canvas bubble shortcuts.
    dialog.addEventListener("keydown", event => {
        if (event.key === "Escape" && !event.defaultPrevented) {
            event.preventDefault();
            closeEditor?.();
        }
        event.stopPropagation();
    });
    closeEditor = () => {
        // ComfyUI clears old nodes BEFORE beforeConfigureGraph. Never revive a
        // destroyed editor, even though this closure still holds its old root.
        const alive = node._minimaxEditor === editor && editor.root === root &&
            app.graph._nodes.includes(node);
        try {
            if (alive) editor.flushTimelineSync();
        } finally {
            if (alive) host.append(root);
            dialog.remove();
            closeEditor = undefined;
            const url = new URL(location.href);
            url.searchParams.delete("director");
            history.replaceState(history.state, "", url);
            if (alive) editor.scheduleSettleRender();
        }
    };
    back.onclick = () => closeEditor?.();
    back.focus();
    editor.scheduleSettleRender();
}

async function enterDirector() {
    // No competing native template/share URL loads after startup's spinner clears.
    if ([...new URLSearchParams(location.search).keys()].some(key => key !== "director")) {
        throw new Error("Director 专用入口只接受 /?director=1；其他参数请使用普通画布。");
    }
    await waitFor(() => app.extensionManager?.spinner === false);
    const response = await api.fetchApi("/h3-director/workflow");
    if (!response.ok) throw new Error(`Director 工作流加载失败 (${response.status})`);
    const workflow = await response.json();
    // Resume edits in this project's restored graph; otherwise create an unnamed
    // native temporary tab. Never reuse a saved filename or write user storage.
    if (app.graph.id !== workflow.id) {
        await app.loadGraphData(workflow, true, true, null);
    }
    const node = await waitFor(() => app.graph._nodes.find(node =>
        node.type === "MiniMaxH3Director" && node._minimaxEditor?.root));
    if (typeof node._minimaxEditor.flushTimelineSync !== "function" ||
        typeof node._minimaxEditor.scheduleSettleRender !== "function") {
        throw new Error("Director 接口已变化；请使用普通画布并复核适配器。");
    }
    showEditor(node);
}

app.registerExtension({
    name: "H3.DirectorEntry",
    setup() {
        if (requested) {
            void enterDirector().catch(error => {
                closeEditor?.();
                console.error(error);
                alert(error.message);
            });
        }
    },
    beforeConfigureGraph() {
        // Native graph changes must never leave a stale detached editor visible.
        closeEditor?.();
    },
});
