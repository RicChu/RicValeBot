# Map Arrival Route Design

## Goal

Do not send route or random-walk WASD input until the active map's post-teleport minimap image is detected. After the recorded WASD route ends, begin the existing bounded random patrol.

## Design

- Add a small `MapArrivalWaitController` with `idle`, `waiting_for_arrival`, and `arrived` states.
- On a program-driven teleport departure, start this controller instead of starting the scripted route immediately.
- Each captured frame uses the active map profile's dedicated arrival-minimap template. The controller blocks movement until it observes that minimap.
- When the controller reaches `arrived`, start the scripted route. While it is waiting, no WASD source may run.
- Build the existing `WalkingController` for both `random` and `scripted_route` modes. Once the scripted route reaches `arrived`, the normal random-walk branch runs on the next poll.
- The wait controller is cancelled with login/death recovery. Each map profile provides an optional template path and threshold.

## Error Handling

The controller deliberately remains waiting if it has not observed the destination minimap. Login and death reset the state, avoiding a stale pending route.

## Tests

- An arrival waiter blocks before the destination minimap appears and becomes ready when it appears.
- Teleport departure starts the wait rather than the scripted route.
- A scripted-route configuration creates a random walker for post-route patrol.
