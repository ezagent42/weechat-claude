use zellij_tile::prelude::*;
use std::collections::BTreeMap;

#[derive(Default)]
struct ZchatStatus {
    project_name: String,
    agent_count: usize,
}

register_plugin!(ZchatStatus);

impl ZellijPlugin for ZchatStatus {
    fn load(&mut self, _configuration: BTreeMap<String, String>) {
        set_selectable(false);
        request_permission(&[PermissionType::ReadApplicationState]);
        subscribe(&[EventType::TabUpdate, EventType::SessionUpdate]);
    }

    fn update(&mut self, _event: Event) -> bool {
        false
    }

    fn render(&mut self, _rows: usize, _cols: usize) {
        print!("zchat");
    }
}
