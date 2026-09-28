"""A program that loads native code as an SQLite extension: the launcher must stop it."""
import sqlite3

connection = sqlite3.connect(":memory:")
connection.enable_load_extension(True)
print("sqlite extension enabled")
