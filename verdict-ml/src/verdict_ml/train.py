from __future__ import annotations

import sys

from .link import train as link_train
from .page import train as page_train


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in {"-h", "--help"}:
        print("usage: verdict-train {page,link} [options]")
        raise SystemExit(0 if args else 2)

    command = args[0]
    sys.argv = [f"verdict-train {command}", *args[1:]]
    if command == "page":
        page_train.main()
        return
    if command == "link":
        link_train.main()
        return

    print(f"unknown command: {command}", file=sys.stderr)
    print("usage: verdict-train {page,link} [options]", file=sys.stderr)
    raise SystemExit(2)


if __name__ == "__main__":
    main()
