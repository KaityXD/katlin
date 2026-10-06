//! Zed extension for Katlin.
//!
//! The language itself (grammar, highlights, brackets, indents, outline) is
//! declared in `extension.toml` and `languages/katlin/`. The only thing that
//! needs code is telling Zed how to launch the language server, which is the
//! dependency-free Node program that already ships with the repository.

use std::fs;
use zed_extension_api::{self as zed, settings::LspSettings, LanguageServerId, Result};

struct KatlinExtension;

impl KatlinExtension {
    /// Resolve the language server command.
    ///
    /// Order:
    ///   1. an explicit `lsp.katlin.binary` in the user's settings.json
    ///   2. the checkout this extension was installed from
    ///   3. `katlin-lsp` on $PATH
    fn language_server_binary(
        &self,
        language_server_id: &LanguageServerId,
        worktree: &zed::Worktree,
    ) -> Result<(String, Vec<String>)> {
        let settings = LspSettings::for_worktree(language_server_id.as_ref(), worktree).ok();
        if let Some(binary) = settings.and_then(|s| s.binary) {
            if let Some(path) = binary.path {
                return Ok((path, binary.arguments.unwrap_or_default()));
            }
        }

        let node = worktree
            .which("node")
            .ok_or_else(|| "node was not found on $PATH; the Katlin language server needs it".to_string())?;

        let root = worktree.root_path();
        let server = format!("{root}/editors/vscode/server/server.js");
        let compiler = format!("{root}/bin/katlin");

        if fs::metadata(&server).is_ok() {
            let mut args = vec![server];
            // The server can find the compiler itself, but passing it means a
            // checkout with an unusual layout still works.
            if fs::metadata(&compiler).is_ok() {
                args.push(compiler);
            }
            return Ok((node, args));
        }

        if let Some(server) = worktree.which("katlin-lsp") {
            return Ok((server, vec![]));
        }

        Err(format!(
            "could not find the Katlin language server.\n\
             Expected it at {server}, or `katlin-lsp` on $PATH.\n\
             Set `lsp.katlin.binary.path` in your settings to override."
        ))
    }
}

impl zed::Extension for KatlinExtension {
    fn new() -> Self {
        Self
    }

    fn language_server_command(
        &mut self,
        language_server_id: &LanguageServerId,
        worktree: &zed::Worktree,
    ) -> Result<zed::Command> {
        let (command, args) = self.language_server_binary(language_server_id, worktree)?;
        Ok(zed::Command {
            command,
            args,
            env: vec![],
        })
    }
}

zed::register_extension!(KatlinExtension);
