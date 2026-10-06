#!/usr/bin/env node
'use strict';

/*
 * Tests for the Katlin language server.
 *
 * Two layers:
 *
 *   1. Unit tests for parseDiagnostics, driven by captured `katlin check`
 *      output. Fast, and they pin the exact shapes the compiler emits.
 *   2. End-to-end tests that spawn the real server, speak JSON-RPC to it over
 *      stdio, and assert the diagnostics that come back. These exercise the
 *      framing, the request/notification handling and the compiler
 *      invocation, none of which the unit tests touch.
 *
 * Run: node editors/vscode/server/test.js   (or: npm test, from editors/vscode)
 */

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const { parseDiagnostics, defaultCompilerPath } = require('./server.js');

const COMPILER = process.env.KATLIN_BIN || defaultCompilerPath();

let passed = 0;
let failed = 0;
const failures = [];

function ok(name) {
    passed++;
    console.log('  \x1b[1;32mPASS\x1b[0m  ' + name);
}

function bad(name, detail) {
    failed++;
    failures.push(name);
    console.log('  \x1b[1;31mFAIL\x1b[0m  ' + name);
    if (detail) console.log('        ' + String(detail).split('\n').join('\n        '));
}

function eq(name, expected, actual) {
    if (expected === actual) ok(name);
    else bad(name, 'expected ' + JSON.stringify(expected) + '\n     got ' + JSON.stringify(actual));
}

function truthy(name, value, detail) {
    if (value) ok(name);
    else bad(name, detail || 'value was falsy');
}

// ---------------------------------------------------------------------------
// 1. Parser unit tests
// ---------------------------------------------------------------------------

const BORROW_OUTPUT = [
    'error: cannot borrow `x` as mutable more than once at a time',
    '  --> /tmp/ktl/buffer.ktl:5',
    '   = note: #strict forbids aliased mutable references (&)',
    '   = note: 1 #strict error(s); compilation aborted',
    ''
].join('\n');

const BACKEND_OUTPUT = [
    '.build/buffer.c:9:5: error: use of undeclared identifier \'undefined_thing\'',
    '    9 |     undefined_thing = 1;',
    '      |     ^~~~~~~~~~~~~~~',
    '1 error generated.',
    'error: /tmp/ktl/buffer.ktl failed to type-check',
    ''
].join('\n');

const CLEAN_OUTPUT = '\u2713 /tmp/ktl/buffer.ktl: no errors\n';

function testParser() {
    console.log('\nparser');

    const text = 'a\nb\nc\nd\ne\nf\n';

    const borrow = parseDiagnostics(BORROW_OUTPUT, text);
    eq('borrow: one diagnostic', 1, borrow.length);
    eq('borrow: severity is Error', 1, borrow[0].severity);
    eq('borrow: line maps to 4 (0-based)', 4, borrow[0].range.start.line);
    truthy('borrow: message kept', /cannot borrow/.test(borrow[0].message), borrow[0].message);
    truthy('borrow: note kept', /aliased mutable references/.test(borrow[0].message), borrow[0].message);
    truthy(
        'borrow: summary note dropped',
        !/#strict error\(s\)/.test(borrow[0].message),
        borrow[0].message
    );

    const backend = parseDiagnostics(BACKEND_OUTPUT, text);
    eq('backend: exactly one diagnostic', 1, backend.length);
    eq('backend: anchored at line 0', 0, backend[0].range.start.line);
    truthy(
        'backend: carries the clang message',
        /undeclared identifier/.test(backend[0].message),
        backend[0].message
    );
    truthy(
        'backend: says the position is unavailable',
        /no source position/.test(backend[0].message),
        backend[0].message
    );
    truthy(
        'backend: generic type-check line suppressed',
        !/failed to type-check/.test(backend[0].message),
        backend[0].message
    );

    eq('clean output yields no diagnostics', 0, parseDiagnostics(CLEAN_OUTPUT, text).length);
    eq('empty output yields no diagnostics', 0, parseDiagnostics('', text).length);

    // ANSI must not confuse the match.
    const coloured = '\x1b[1;31merror\x1b[0m: boom\n  \x1b[1;34m-->\x1b[0m f.ktl:2\n';
    const ansi = parseDiagnostics(coloured, 'x\ny\nz\n');
    eq('ansi: one diagnostic', 1, ansi.length);
    eq('ansi: line parsed', 1, ansi[0].range.start.line);
    eq('ansi: message parsed', 'boom', ansi[0].message);

    // A line number past the end of the document must not throw.
    const past = parseDiagnostics('error: x\n  --> f.ktl:999\n', 'one line\n');
    eq('out-of-range line does not throw', 1, past.length);
}

// ---------------------------------------------------------------------------
// 2. End-to-end client
// ---------------------------------------------------------------------------

function makeClient(child) {
    let buffer = Buffer.alloc(0);
    let nextId = 1;
    const pending = new Map();
    const diagnosticWaiters = [];
    const received = [];

    child.stdout.on('data', (chunk) => {
        buffer = Buffer.concat([buffer, chunk]);
        for (;;) {
            const headerEnd = buffer.indexOf('\r\n\r\n');
            if (headerEnd === -1) return;
            const header = buffer.slice(0, headerEnd).toString('ascii');
            const m = /Content-Length:\s*(\d+)/i.exec(header);
            if (!m) {
                buffer = buffer.slice(headerEnd + 4);
                continue;
            }
            const len = parseInt(m[1], 10);
            const start = headerEnd + 4;
            if (buffer.length < start + len) return;
            const body = buffer.slice(start, start + len).toString('utf8');
            buffer = buffer.slice(start + len);

            let msg;
            try {
                msg = JSON.parse(body);
            } catch (_) {
                continue;
            }

            if (msg.id !== undefined && pending.has(msg.id)) {
                pending.get(msg.id)(msg);
                pending.delete(msg.id);
            } else if (msg.method === 'textDocument/publishDiagnostics') {
                received.push(msg.params);
                while (diagnosticWaiters.length > 0) {
                    diagnosticWaiters.shift()(msg.params);
                }
            }
        }
    });

    function send(message) {
        const payload = Buffer.from(JSON.stringify(message), 'utf8');
        child.stdin.write('Content-Length: ' + payload.length + '\r\n\r\n');
        child.stdin.write(payload);
    }

    return {
        received,
        request(method, params) {
            const id = nextId++;
            return new Promise((resolve) => {
                pending.set(id, resolve);
                send({ jsonrpc: '2.0', id, method, params });
            });
        },
        notify(method, params) {
            send({ jsonrpc: '2.0', method, params });
        },
        nextDiagnostics(timeoutMs) {
            return new Promise((resolve, reject) => {
                const timer = setTimeout(
                    () => reject(new Error('timed out waiting for publishDiagnostics')),
                    timeoutMs || 20000
                );
                diagnosticWaiters.push((p) => {
                    clearTimeout(timer);
                    resolve(p);
                });
            });
        }
    };
}

const BORROW_SOURCE = [
    '#strict',
    'fn bump(int &a) { a = a + 1; }',
    'fn main {',
    '    mut int x = 1;',
    '    bump(&x, &x);',
    '}',
    ''
].join('\n');

const CLEAN_SOURCE = 'fn main {\n    println("hello");\n}\n';

const TYPE_ERROR_SOURCE = 'fn main {\n    undefined_thing = 1;\n}\n';

async function testEndToEnd() {
    console.log('\nend-to-end (real server over stdio)');

    if (!fs.existsSync(COMPILER)) {
        bad('compiler available', 'not found at ' + COMPILER + '; run ./build.sh first');
        return;
    }

    const child = spawn(process.execPath, [path.join(__dirname, 'server.js'), COMPILER], {
        stdio: ['pipe', 'pipe', 'pipe']
    });

    let serverStderr = '';
    child.stderr.on('data', (d) => (serverStderr += d));

    const exited = new Promise((resolve) => child.on('close', resolve));
    const client = makeClient(child);

    const init = await client.request('initialize', { processId: null, rootUri: null, capabilities: {} });
    eq('initialize returns serverInfo', 'katlin-lsp', init.result && init.result.serverInfo.name);
    eq('initialize advertises full text sync', 1, init.result.capabilities.textDocumentSync);

    client.notify('initialized', {});

    // Clean buffer: a publish is still expected, with no diagnostics.
    const uriA = 'file:///tmp/ktl/clean.ktl';
    client.notify('textDocument/didOpen', {
        textDocument: { uri: uriA, languageId: 'katlin', version: 1, text: CLEAN_SOURCE }
    });
    let diags = await client.nextDiagnostics();
    eq('clean file publishes to the right uri', uriA, diags.uri);
    eq('clean file reports no diagnostics', 0, diags.diagnostics.length);

    // Borrow violation: one diagnostic on line 5 (0-based 4).
    const uriB = 'file:///tmp/ktl/borrow.ktl';
    client.notify('textDocument/didOpen', {
        textDocument: { uri: uriB, languageId: 'katlin', version: 1, text: BORROW_SOURCE }
    });
    diags = await client.nextDiagnostics();
    eq('borrow file reports one diagnostic', 1, diags.diagnostics.length);
    eq('borrow diagnostic line', 4, diags.diagnostics[0].range.start.line);
    eq('borrow diagnostic severity', 1, diags.diagnostics[0].severity);

    // Fixing the buffer must clear the diagnostics.
    const fixed = BORROW_SOURCE.replace('bump(&x, &x);', 'bump(&x);');
    client.notify('textDocument/didChange', {
        textDocument: { uri: uriB, version: 2 },
        contentChanges: [{ text: fixed }]
    });
    diags = await client.nextDiagnostics();
    eq('fixing the buffer clears diagnostics', 0, diags.diagnostics.length);

    // A backend error still surfaces, as a single file-level diagnostic.
    const uriC = 'file:///tmp/ktl/typeerr.ktl';
    client.notify('textDocument/didOpen', {
        textDocument: { uri: uriC, languageId: 'katlin', version: 1, text: TYPE_ERROR_SOURCE }
    });
    diags = await client.nextDiagnostics();
    truthy('backend error produces a diagnostic', diags.diagnostics.length >= 1, JSON.stringify(diags));
    if (diags.diagnostics.length >= 1) {
        truthy(
            'backend diagnostic mentions the C backend',
            /backend/i.test(diags.diagnostics[0].message),
            diags.diagnostics[0].message
        );
    }

    // Closing clears the collection.
    client.notify('textDocument/didClose', { textDocument: { uri: uriC } });
    diags = await client.nextDiagnostics();
    eq('closing a document clears its diagnostics', 0, diags.diagnostics.length);

    // Shutdown/exit.
    await client.request('shutdown', null);
    client.notify('exit', null);
    const code = await exited;
    eq('clean shutdown exits 0', 0, code);
    eq('server wrote nothing to stderr', '', serverStderr.trim());
}

// ---------------------------------------------------------------------------

(async function main() {
    console.log('Katlin language server tests');
    console.log('  compiler: ' + COMPILER);

    testParser();
    try {
        await testEndToEnd();
    } catch (err) {
        bad('end-to-end run completed', err && err.stack ? err.stack : String(err));
    }

    console.log('\n==> ' + passed + ' passed, ' + failed + ' failed');
    if (failed > 0) {
        console.log('    failed: ' + failures.join(', '));
        process.exit(1);
    }
    console.log('==> all green');
})();
