# 🔗 Alloy

**The API-driven, universal package manager that bridges the gap between system-level requirements and Python environments.**

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://python.org)
[![Architecture: API-First](https://img.shields.io/badge/Architecture-API--First-purple.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Installing Python packages that rely on C++ extensions, OS-level binaries, or specific system headers can be a nightmare. Standard `pip` is great for pure Python, but it can't install `cmake`, `build-essential`, or `libssl-dev` for you. 

**Alloy** solves this. It acts as a meta-manager: you tell it what Python library you want, and Alloy automatically queries its centralized Web API, detects your host OS, interacts with your native package manager (`apt`, `brew`, `dnf`, `choco`), and perfectly configures your environment before installing the Python library.

## ✨ Features

- **⚡ API-First Architecture:** No massive Git clones or bloated local databases. Alloy fetches exactly the recipes it needs from the central API on the fly.
- **🧠 Smart OS Detection:** Automatically detects your OS family (Linux, macOS, Windows) and distribution (Ubuntu, CentOS, Debian, etc.).
- **⚙️ Native OS Integration:** Seamlessly passes commands to `apt`, `dnf`, `brew`, and `choco` based on your machine.
- **📏 Strict Version Constraints:** Resolves dependencies based on exact OS versions (e.g., handling Ubuntu 18.04 differently than Ubuntu 22.04).
- **💉 Environment Variables:** Automatically configures `CC`, `CXX`, `CFLAGS`, and `LDFLAGS` so C++ compilers know exactly where to find newly installed system headers.

---

## 📦 Installation

*(Note: Alloy is currently in development.)*

```bash
# Clone the repository
git clone https://github.com/yourusername/alloy.git
cd alloy

# Install Alloy globally
pip install .
```

---

## 🚀 Quick Start

Using Alloy is as simple as using `pip` or `apt`, but it handles the entire stack from the OS to Python.

```bash
# Update the local search index
alloy update

# Search the API for available packages
alloy search opencv

# Install a library (Alloy handles system deps + pip install)
alloy install opencv-python

# View what system packages Alloy will install without doing it
alloy install opencv-python --dry-run
```

---

## 🛠️ CLI Commands

| Command | Description |
|---|---|
| `alloy update` | Fetches a lightweight index of available packages from the Alloy API. |
| `alloy search <query>` | Searches the local index for matching Python libraries. |
| `alloy install <pkg>` | Fetches the recipe from the API, installs OS dependencies, and runs pip. |
| `alloy remove <pkg>` | Uninstalls the package (with options to clean up orphaned OS dependencies). |
| `alloy info <pkg>` | Displays the OS requirements specific to *your* current machine. |
| `alloy clean` | Clears the local recipe cache (`~/.alloy/cache/`) to free up disk space. |

---

## 🏗️ How It Works (The API Architecture)

When you run `alloy install hypocv`, here is what happens under the hood:

1. **API Request:** Alloy checks its local cache (`~/.alloy/cache/recipes/`). If the recipe isn't there, it pings the central Web API (`GET /v1/packages/hypocv/recipe`).
2. **OS Evaluation:** Alloy parses the downloaded YAML recipe and compares it against your local machine (e.g., identifying that you are running Ubuntu 22.04).
3. **Execution:** Alloy runs the pre-install scripts, invokes `apt-get install`, sets the environment variables, and executes the Python build steps.

### Example Recipe
Here is what the API serves back to your machine—a declarative YAML syntax defining exactly how the library should be handled on different operating systems:

```yaml
package:
  name: hypocv
  version: "1.2.0"
  description: "A high-performance computer vision library with C++ bindings."
  python_requires: ">=3.8"
  python_dependencies:
    - numpy>=1.21.0
    - pybind11>=2.10.0

system_requirements:
  linux:
    ubuntu:
      - os_version: ">=20.04"
        package_manager: "apt"
        packages:
          - build-essential
          - cmake
          - python3-dev
          - libopencv-dev
        env_vars:
          CMAKE_BUILD_TYPE: "Release"
  macos:
    all:
      - os_version: ">=11.0"
        package_manager: "brew"
        packages:
          - cmake
          - opencv
        env_vars:
          CPPFLAGS: "-I/usr/local/opt/opencv/include"
          LDFLAGS: "-L/usr/local/opt/opencv/lib"
```

---

## 🤝 Contributing to the Registry

Alloy’s strength comes from its registry of recipes. We want to support as many complex Python libraries as possible! 

If you constantly struggle to install a specific Python library because of C++ or system requirements, you can add it to the Alloy database.

1. Fork the **Alloy Registry** repository.
2. Create a new `<library-name>.yaml` file following the schema.
3. Test it locally using `alloy install ./<library-name>.yaml`.
4. Submit a Pull Request. Once merged, it will automatically be available globally via the Alloy API!

See our [Contribution Guidelines](CONTRIBUTING.md) for more details on writing robust OS version constraints.

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.