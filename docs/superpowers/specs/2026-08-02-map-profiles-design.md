# Map Profiles Design

## Goal

Use one YAML selector to switch map-specific teleport, scripted-route, and low-priority template-target settings.

## Configuration

`active_map` names one entry in `maps`. Each map entry provides:

- `teleport_template_path`: destination tile used by the town Waystone flow.
- `target_template_paths`: image files or folders used only when HSV finds no health-bar target.
- `movement_script_path`: optional WASD script replayed after the program completes a town teleport.

Town UI templates, HSV rules, skills, and generic walking controls remain global. This avoids duplicating shared controls for every map.

## Runtime Behaviour

1. Resolve the active map during configuration loading. A missing active map is a configuration error.
2. The Waystone controller uses the active map destination image.
3. After teleport departure, optional scripted-route playback uses the active map movement script.
4. Target detection runs HSV first. If HSV yields one or more targets, template target detection is skipped.
5. When HSV yields no targets, scan the active map's target templates. A matching template becomes one target and follows existing Task 1 / center-skill behaviour: pointer movement plus key `3`, and independent center-radius key `2` when applicable.
6. A map may leave target templates or a movement script empty; the relevant fallback feature is then disabled without affecting HSV or other maps.

## Error Handling and Tests

- Validate `active_map` exists and map paths are strings.
- Unit-test active-map parsing, selected Waystone destination, selected scripted route, and HSV-over-template priority.
- Preserve the existing template detector threshold and action timing; this work adds no new key or click action.
