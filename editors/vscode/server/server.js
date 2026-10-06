#!/usr/bin/env node
'use strict';

/*
 * A language server for Katlin.
 *
 * It is deliberately small: diagnostics come from running `katlin check` on
 * the buffer as it changes, and nothing else is implemented yet (no
 * completion, hover or go-to-definition). That is enough to put real error
 * markers in an editor, which is the part that was missing.
 *
 * Protocols and framing are hand-rolled against JSON-RPC 2.0 over stdio, so
 * the server has no dependencies and runs with a bare `node`.
 *
 * Two things are worth knowing about the diagnostics themselves:
 *
 *   - Errors the Katlin front end reports (borrow-checker violations, a
 *     missing `fn main`, an unreadable file) carry a real source line and are
 *     published as normal squiggles.
 *   - Errors the C backend reports do NOT. The compiler emits C, hands it to
 *     clang, and clang reports positions in the generated `.build/<name>.c`
 *     file. There is no mapping back to the Katlin source, so rather than
 *     underline a line that might be wrong, those are published as a single
 *     diagnostic at the top of the file with the raw clang message. The
 *     message tells you what is wrong; `katlin check` tells you where.
 */

const { spawn, spawnSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const SEVERITY = { error: 1, warning: 2, information: 3, hint: 4 };

// ---------------------------------------------------------------------------
// Locating the compiler
// ---------------------------------------------------------------------------

// Resolution order: an explicit override, then the checkout this server lives
// inside (editors/vscode/server/ -> ../../../bin/katlin), then $PATH.
function defaultCompilerPath() {
    const candidates = [
        process.env.KATLIN_BIN,
        path.resolve(__dirname, '..', '..', '..', 'bin', 'katlin')
    ];
    for (const c of candidates) {
        if (c && fs.existsSync(c)) return c;
    }
    return 'katlin';
}

// ---------------------------------------------------------------------------
// Diagnostic parsing
// ---------------------------------------------------------------------------

const ANSI = /\x1b\[[0-9;]*m/g;

// `katlin check` prints two different shapes.
const RE_CLANG = /^(.*?):(\d+):(\d+):\s*(error|warning|note):\s*(.*)$/;
const RE_KATLIN = /^(error|warning):\s*(.*)$/;
const RE_LOCATION = /^\s*-->\s*(.*?):(\d+)\s*$/;
const RE_CONTEXT = /^\s*=\s*(note|help|warning):\s*(.*)$/;
// A summary the borrrow checker appends; not part of any one diagnostic.
const RE_SUMMARY = /^\d+\s+#strict error\(s\)/;

function lineRange(textLines, lineNumber) {
    const idx = Math.max(0, lineNumber - 1);
    const line = textLines[idx] !== undefined ? textLines[idx] : '';
    return {
        start: { line: idx, character: 0 },
        end: { line: idx, character: line.length }
    };
}

function firstLineRange() {
    return { start: { line: 0, character: 0 }, end: { line: 0, character: 0 } };
}

/**
 * Turn the output of `katlin check` into LSP diagnostics.
 * Exported so the test harness can exercise it directly.
 */
function parseDiagnostics(output, text) {
    const clean = String(output || '').replace(ANSI, '');
    const lines = clean.split(/\r?\n/);
    const textLines = String(text || '').split(/\r?\n/);

    const diagnostics = [];
    const backendErrors = [];

    for (let i = 0; i < lines.length; i++) {
        const raw = lines[i];

        // Backend output: file.c:LINE:COL: error: ...
        const clang = RE_CLANG.exec(raw);
        if (clang) {
            if (clang[4] === 'error') backendErrors.push(clang[5].trim());
            continue;
        }

        const head = RE_KATLIN.exec(raw);
        if (!head) continue;

        const severity = head[1] === 'warning' ? SEVERITY.warning : SEVERITY.error;
        const messageParts = [head[2].trim()];
        let lineNumber = null;

        // The location and any `= note:` lines follow the message.
        for (let j = i + 1; j < lines.length; j++) {
            const nxt = lines[j];
            if (/^\s*$/.test(nxt)) break;

            const loc = RE_LOCATION.exec(nxt);
            if (loc) {
                lineNumber = parseInt(loc[2], 10);
                continue;
            }
            const ctx = RE_CONTEXT.exec(nxt);
            if (ctx) {
                if (!RE_SUMMARY.test(ctx[2])) messageParts.push(ctx[2].trim());
                continue;
            }
            break;
        }

        // A backend failure already produced a more specific diagnostic below.
        if (backendErrors.length > 0 && /failed to type-check/.test(messageParts[0])) {
            continue;
        }

        diagnostics.push({
            range: lineNumber !== null ? lineRange(textLines, lineNumber) : firstLineRange(),
            severity,
            source: 'katlin',
            message: messageParts.join('\n')
        });
    }

    if (backendErrors.length > 0) {
        const unique = [...new Set(backendErrors)];
        const shown = unique.slice(0, 3);
        let message =
            'C backend error (the compiler reports these against generated C, ' +
            'so no source position is available):\n' + shown.map((m) => '  - ' + m).join('\n');
        if (unique.length > shown.length) {
            message += '\n  ...and ' + (unique.length - shown.length) + ' more';
        }
        message += '\nRun `katlin check <file>` to see the full clang output.';
        diagnostics.push({
            range: firstLineRange(),
            severity: SEVERITY.error,
            source: 'katlin',
            message
        });
    }

    return diagnostics;
}

/**
 * Run `katlin check` on a buffer.
 *
 * The buffer is written to a scratch directory that is also the working
 * directory, so the compiler's `.build/` output lands there and not in the
 * user's project. Nothing but the reported line numbers is taken from the
 * result, so the scratch path never leaks into diagnostics.
 */
function runCheck(compiler, text, callback) {
    let dir;
    try {
        dir = fs.mkdtempSync(path.join(os.tmpdir(), 'katlin-lsp-'));
    } catch (err) {
        return callback(err, null);
    }
    const src = path.join(dir, 'buffer.ktl');
    const cleanup = () => {
        try {
            fs.rmSync(dir, { recursive: true, force: true });
        } catch (_) {
            /* best effort */
        }
    };

    try {
        fs.writeFileSync(src, text);
    } catch (err) {
        cleanup();
        return callback(err, null);
    }

    const child = spawn(compiler, ['check', src], {
        cwd: dir,
        stdio: ['ignore', 'pipe', 'pipe']
    });

    let out = '';
    child.stdout.on('data', (d) => (out += d));
    child.stderr.on('data', (d) => (out += d));

    let done = false;
    const finish = (err) => {
        if (done) return;
        done = true;
        cleanup();
        callback(err, out);
    };

    // A wedged compiler must not wedge the editor.
    const timer = setTimeout(() => {
        try {
            child.kill('SIGKILL');
        } catch (_) {
            /* already gone */
        }
        finish(new Error('katlin check timed out'));
    }, 20000);

    child.on('error', (err) => {
        clearTimeout(timer);
        finish(err);
    });
    child.on('close', () => {
        clearTimeout(timer);
        finish(null);
    });
}

// ---------------------------------------------------------------------------
// JSON-RPC over stdio
// ---------------------------------------------------------------------------

function createConnection(input, output) {
    let buffer = Buffer.alloc(0);
    const handlers = new Map();
    let onNotification = () => {};

    input.on('data', (chunk) => {
        buffer = Buffer.concat([buffer, chunk]);
        for (;;) {
            const headerEnd = buffer.indexOf('\r\n\r\n');
            if (headerEnd === -1) return;

            const header = buffer.slice(0, headerEnd).toString('ascii');
            const match = /Content-Length:\s*(\d+)/i.exec(header);
            if (!match) {
                buffer = buffer.slice(headerEnd + 4);
                continue;
            }
            const length = parseInt(match[1], 10);
            const bodyStart = headerEnd + 4;
            if (buffer.length < bodyStart + length) return;

            const body = buffer.slice(bodyStart, bodyStart + length).toString('utf8');
            buffer = buffer.slice(bodyStart + length);

            let message;
            try {
                message = JSON.parse(body);
            } catch (_) {
                continue;
            }

            if (message.id !== undefined && message.method) {
                const handler = handlers.get(message.method);
                const result = handler ? handler(message.params || {}) : null;
                send({
                    jsonrpc: '2.0',
                    id: message.id,
                    result: result === undefined ? null : result
                });
            } else if (message.method) {
                onNotification(message.method, message.params || {});
            }
        }
    });

    function send(message) {
        const payload = Buffer.from(JSON.stringify(message), 'utf8');
        output.write('Content-Length: ' + payload.length + '\r\n\r\n');
        output.write(payload);
    }

    return {
        send,
        onRequest: (method, handler) => handlers.set(method, handler),
        onNotification: (fn) => {
            onNotification = fn;
        }
    };
}

// ---------------------------------------------------------------------------
// Server
// ---------------------------------------------------------------------------

function createServer(options) {
    const compiler = (options && options.compiler) || defaultCompilerPath();
    const connection = createConnection(process.stdin, process.stdout);

    const documents = new Map(); // uri -> text
    const versions = new Map(); // uri -> monotonically increasing check id
    let shuttingDown = false;

    const capabilities = {
        textDocumentSync: 1, // full
        diagnosticProvider: undefined
    };

    function publish(uri, diagnostics) {
        connection.send({
            jsonrpc: '2.0',
            method: 'textDocument/publishDiagnostics',
            params: { uri, diagnostics }
        });
    }

    function checkDocument(uri) {
        const text = documents.get(uri);
        if (text === undefined) return;

        const id = (versions.get(uri) || 0) + 1;
        versions.set(uri, id);

        runCheck(compiler, text, (err, output) => {
            // A newer edit superseded this result.
            if (versions.get(uri) !== id) return;
            if (documents.get(uri) === undefined) return;

            if (err) {
                publish(uri, [
                    {
                        range: firstLineRange(),
                        severity: SEVERITY.error,
                        source: 'katlin',
                        message: 'katlin: ' + err.message
                    }
                ]);
                return;
            }
            publish(uri, parseDiagnostics(output, documents.get(uri)));
        });
    }

    connection.onRequest('initialize', () => ({
        capabilities,
        serverInfo: { name: 'katlin-lsp', version: '0.1.0' }
    }));

    connection.onRequest('shutdown', () => {
        shuttingDown = true;
        return null;
    });

    connection.onNotification((method, params) => {
        switch (method) {
            case 'initialized':
                break;

            case 'textDocument/didOpen':
                documents.set(params.textDocument.uri, params.textDocument.text);
                checkDocument(params.textDocument.uri);
                break;

            case 'textDocument/didChange': {
                const uri = params.textDocument.uri;
                const changes = params.contentChanges || [];
                if (changes.length > 0) {
                    // Full sync: the last change carries the whole document.
                    documents.set(uri, changes[changes.length - 1].text);
                }
                checkDocument(uri);
                break;
            }

            case 'textDocument/didSave':
                if (params.textDocument && documents.has(params.textDocument.uri)) {
                    checkDocument(params.textDocument.uri);
                }
                break;

            case 'textDocument/didClose': {
                const uri = params.textDocument.uri;
                documents.delete(uri);
                versions.delete(uri);
                publish(uri, []);
                break;
            }

            case 'exit':
                process.exit(shuttingDown ? 0 : 1);
                break;

            default:
                break;
        }
    });

    // A client that vanishes must not leave us running.
    process.stdin.on('end', () => process.exit(0));

    return { connection, compiler, parseDiagnostics };
}

module.exports = {
    parseDiagnostics,
    runCheck,
    defaultCompilerPath,
    createConnection,
    createServer
};

if (require.main === module) {
    const requested = process.argv[2];
    createServer({
        compiler: requested && fs.existsSync(requested) ? requested : undefined
    });
}
