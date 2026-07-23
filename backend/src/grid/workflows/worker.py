"""Placeholder Temporal worker entrypoint.

Real workflow/activity registration lands in Phase 3. For now this just proves the
`worker` container boots and stays alive so `deploy/compose.dev.yaml` is complete.
"""

import time


def main() -> None:
    print("grid worker: no workflows registered yet (Phase 3) — idling")
    while True:
        time.sleep(3600)


if __name__ == "__main__":
    main()
