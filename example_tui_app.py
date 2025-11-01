#!/usr/bin/env python3
"""
Simple example TUI application for testing the TUI MCP server.
This is a basic interactive menu application.
"""

import sys


def main():
    print("=" * 60)
    print("  Welcome to the Example TUI Application")
    print("=" * 60)
    print()
    print("Please choose an option:")
    print("  1. Say Hello")
    print("  2. Show Info")
    print("  3. Counter")
    print("  q. Quit")
    print()

    counter = 0

    while True:
        try:
            choice = input("> ").strip().lower()

            if choice == '1':
                print("Hello, TUI Tester!")
                print()
            elif choice == '2':
                print("This is an example TUI application.")
                print("Created for testing the MCP TUI Test server.")
                print()
            elif choice == '3':
                counter += 1
                print(f"Counter value: {counter}")
                print()
            elif choice == 'q':
                print("Goodbye!")
                sys.exit(0)
            else:
                print(f"Unknown option: {choice}")
                print("Please choose 1, 2, 3, or q")
                print()

        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            sys.exit(0)


if __name__ == "__main__":
    main()
