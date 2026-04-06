use zellij_tile::prelude::*;
use std::collections::BTreeMap;

mod fuzzy;

#[derive(Default)]
struct ZchatPalette;

register_plugin!(ZchatPalette);

impl ZellijPlugin for ZchatPalette {
    fn load(&mut self, _configuration: BTreeMap<String, String>) {
        request_permission(&[
            PermissionType::ReadApplicationState,
            PermissionType::ChangeApplicationState,
            PermissionType::RunCommands,
        ]);
        subscribe(&[
            EventType::Key,
            EventType::TabUpdate,
            EventType::SessionUpdate,
            EventType::RunCommandResult,
        ]);
    }

    fn update(&mut self, _event: Event) -> bool {
        false
    }

    fn render(&mut self, _rows: usize, _cols: usize) {
        println!("zchat palette");
    }
}
