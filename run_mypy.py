#!/usr/bin/python3
# SPDX-FileCopyrightText: 2022 Jeff Epler, written for Adafruit Industries
#
# SPDX-License-Identifier: Unlicense
"""Automatically run mypy. Use from pre-commit"""
import os
import pathlib
import subprocess
import tomlkit


def print_check_call(command):
    """Keep the user aware of commands being executed"""
    print("# Running", " ".join(command))
    subprocess.check_call(command)


os.chdir(pathlib.Path(__file__).parent)

pip_command = ["pip", "install", "--no-input", "--quiet", "--editable", "."]
print_check_call(pip_command)

with open("pyproject.toml") as f:
    meta = tomlkit.load(f)
mypy_command = ["mypy"]
if meta["tool"].get("adafruit", {}).get("mypy-strict", True):
    mypy_command.append("--strict")
for module in meta["tool"]["setuptools"].get("py-modules", []):
    mypy_command.extend(["-m", module])
for module in meta["tool"]["setuptools"].get("packages", []):
    mypy_command.extend(["-p", module])

print_check_call(mypy_command)
