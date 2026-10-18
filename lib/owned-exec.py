#!/usr/bin/env python3
"""Create a dedicated POSIX session before replacing this process with a client."""
import os
import sys


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: owned-exec.py PROGRAM [ARG ...]")
    program = sys.argv[1]
    arguments = sys.argv[1:]
    os.setsid()
    os.execv(program, arguments)


if __name__ == "__main__":
    main()
