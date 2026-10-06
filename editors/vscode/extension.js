'use strict';

/*
 * VS Code client for the Katlin language server.
 *
 * The server itself (server/server.js) is a plain Node program that speaks
 * LSP over stdio and has no dependencies, so it can be driven by any editor.
 * This file only wires it into VS Code.
 *
 * Requires `npm install` in this directory (for vscode-languageclient).
 */

const fs = require('fs');
const path = require('path');
const vscode = require('vscode');
const { LanguageClient, TransportKind } = require('vscode-languageclient/node');

let client;

/**
 * Where is the compiler?
 *
 *   1. the `katlin.compilerPath` setting
 *   2. `bin/katlin` inside the first workspace folder (a Katlin checkout)
 *   3. `katlin` on $PATH
 *
 * The server falls back the same way on its own, so passing nothing is fine.
 */
function resolveCompiler() {
    const configured = vscode.workspace.getConfiguration('katlin').get('compilerPath');
    if (configured) return configured;

    for (const folder of vscode.workspace.workspaceFolders || []) {
        const candidate = path.join(folder.uri.fsPath, 'bin', 'katlin');
        if (fs.existsSync(candidate)) return candidate;
    }
    return 'katlin';
}

function activate(context) {
    const serverModule = context.asAbsolutePath(path.join('server', 'server.js'));

    const serverOptions = {
        run: {
            module: serverModule,
            transport: TransportKind.stdio,
            args: [resolveCompiler()]
        },
        debug: {
            module: serverModule,
            transport: TransportKind.stdio,
            args: [resolveCompiler()],
            options: { execArgv: ['--nolazy', '--inspect=6009'] }
        }
    };

    const clientOptions = {
        documentSelector: [{ scheme: 'file', language: 'katlin' }],
        synchronize: {
            fileEvents: vscode.workspace.createFileSystemWatcher('**/*.ktl')
        },
        outputChannelName: 'Katlin Language Server'
    };

    client = new LanguageClient(
        'katlinLanguageServer',
        'Katlin Language Server',
        serverOptions,
        clientOptions
    );

    client.start();
    context.subscriptions.push({ dispose: () => client && client.stop() });
}

function deactivate() {
    if (!client) return undefined;
    return client.stop();
}

module.exports = { activate, deactivate };
