from nuitka import PythonFlavors
import sys
import os

print(f"Executable: {sys.executable}")
print(f"Flavour: {PythonFlavors.getPythonFlavorName()}")

print(f"Prefix Path: {PythonFlavors.getSystemPrefixPath()}")
print(f"Env GH Actions: {os.getenv('GITHUB_ACTIONS') == 'true'}")
print(f"Is GH Action Python: {PythonFlavors.isGithubActionsPython()}")

try:
    print(f"Homebrew Path:: {PythonFlavors.getHomebrewInstallPath()}")
except Exception as e:
    print(f"Except Homebrew Path ({e}).")
