# pyiwsl

`pyiwsl` is a Python package designed for processing and analyzing optics and photonics experimental data, such as measurements from optical spectrum analyzers (OSA) and power meters, as well as for handling integrated photonics CAD design data. The package also aims to support open quantum simulation frameworks.

## Install

```bash
pip install pyiwsl
```

```
pyiwsl/
├─ src/
│ ├─ example/
│ │ └─ optics_splicing.py # Example script demonstrating optics-related usage
│ │
│ └─ pyiwsl/
│ ├─ **init**.py # Package root and public entry point
│ ├─ core.py # Core utilities and shared logic
│ ├─ optics/
│ │ ├─ **init**.py # Public API for optics-related functionality
│ │ └─ pmmanager.py # PMManager log parser (fixed-width / whitespace-aware)
│ └─ cad/ # Placeholder for future CAD-related extensions
│
├─ tests/
│ ├─ optics/
│ │ ├─ data_pmmanager.txt # Sample PMManager log file used for testing
│ │ └─ test_pmmanager.py # External-file-based tests for the PMManager parser
│ └─ test_core.py # Unit tests for core utilities
│
├─ pyproject.toml # Project metadata, dependencies, and build configuration
├─ README.md # Project documentation
├─ LICENSE # License information
└─ dist/ # Built distribution artifacts (wheel / sdist)
```
