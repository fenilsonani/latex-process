# Ultimate LaTeX Processing Tool

Welcome to the **Ultimate LaTeX Processing Tool** (powered by the `LatexProcess` class). This Python package provides a streamlined way to compile, render, and manage LaTeX documents, featuring advanced functionalities such as:

- Multiple LaTeX engines (`pdflatex`, `xelatex`, `lualatex`, `latexmk`)
- Automatic bibliography handling (`bibtex` or `biber`)
- Plugin architecture for extending capabilities
- Support for exporting to various formats (PDF, DVI, HTML, EPUB, DOCX) via Pandoc
- Jinja2 template rendering
- Watchdog-based file watching and automatic recompilation
- Logging with Rich integration
- Basic security scanning (placeholder functionality)
- Async compilation

---

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Quick Start](#quick-start)
  - [Command-Line Usage](#command-line-usage)
  - [API Usage](#api-usage)
- [Plugins](#plugins)
- [Advanced Features](#advanced-features)
  - [Template Rendering](#template-rendering)
  - [Watching a File for Changes](#watching-a-file-for-changes)
  - [Async Compilation](#async-compilation)
  - [Exporting to Different Formats](#exporting-to-different-formats)
  - [Security Scan](#security-scan)
- [Logging](#logging)
- [Contributing](#contributing)
- [License](#license)

---

## Features

1. **Multiple LaTeX Engines**  
   Compile your .tex file using `pdflatex`, `xelatex`, `lualatex`, or `latexmk`.

2. **Bibliography Handling**  
   Automatically processes bibliographies via either `bibtex` or `biber`.

3. **Export to Various Formats**  
   Convert LaTeX documents to PDF, DVI, HTML, EPUB, or DOCX using Pandoc.

4. **File Watching**  
   Recompile automatically on file changes with the help of [watchdog](https://github.com/gorakhargosh/watchdog).

5. **Plugin Architecture**  
   Extend core functionality with plugin modules or custom plugin functions.

6. **Logging and Debugging**  
   Rich-integrated logging, with colorized and nicely formatted logs.

7. **Security Scan (Basic)**  
   Detect certain LaTeX commands that may be unsafe (placeholder functionality).

8. **Async Support**  
   Asynchronous LaTeX compilation using Python's `asyncio`.

---

## Requirements

- **Python 3.7+**  
- **LaTeX Distribution** (e.g., TeX Live, MiKTeX) that provides:
  - `pdflatex`, `xelatex`, `lualatex`, or `latexmk`
- **Bibliography Tools** (if needed):
  - `bibtex` or `biber`
- **Pandoc** (if you want to export to HTML, EPUB, DOCX, etc.)
- **Jinja2** (if you want to render LaTeX templates)
- **watchdog** (if you want to watch `.tex` files for changes)

---

## Installation

You can install this package from source or add it to your `pyproject.toml / requirements.txt` after creating a new Python project.

**Installing from Source (Local):**

```bash
git clone https://github.com/yourusername/latex-process-tool.git
cd latex-process-tool
pip install .
```

*(If you plan to develop or modify the code, you can install in editable mode with `pip install -e .`.)*

---

## Quick Start

Below are two ways to use the Ultimate LaTeX Processing Tool: via the command line and via the Python API.

### Command-Line Usage

After installation, you can run the tool via:

```bash
python -m your_package_name --help
```

or if you’ve set up a console script, something like:

```bash
ultlatex --help
```

**Basic usage**:

```bash
python -m your_package_name \
  <input.tex> \
  -o output/document.pdf \
  --engine pdflatex \
  --bibtool bibtex \
  --format pdf \
  --log-level INFO
```

**Parameters**:
- `input`: Path to a `.tex` file. Use `-` to read from `stdin`.
- `-o, --output`: Output file path (e.g., `output/document.pdf`).
- `-e, --engine`: Choose LaTeX engine (`pdflatex`, `xelatex`, `lualatex`, `latexmk`).
- `-b, --bibtool`: Select bibliography tool (`bibtex` or `biber`).
- `-f, --format`: Output format (`pdf`, `dvi`, `html`, `epub`, or `docx`).
- `-t, --template`: Path to a Jinja2 LaTeX template.
- `--log-level`: Logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL).

**Example**:

```bash
python -m your_package_name \
  main.tex \
  -o my_paper.pdf \
  -e pdflatex \
  -b bibtex \
  -f pdf \
  --log-level DEBUG
```

### API Usage

In your Python scripts or notebooks, you can use the `LatexProcess` class directly:

```python
from your_package_name.latex_process import LatexProcess

processor = LatexProcess(
    engine='pdflatex',
    bib_tool='bibtex',
    output_format='pdf',
    output_dir='output',
    output_filename='document.pdf'
)

# Load from file
processor.load_from_file("main.tex")

# Compile
try:
    output_path = processor.compile()
    print(f"Compilation successful! Output at: {output_path}")
except Exception as e:
    print(f"Compilation failed: {e}")
```

Or load LaTeX content from a string:

```python
latex_code = r"""
\documentclass{article}
\begin{document}
Hello from LaTeX string!
\end{document}
"""

processor.load_from_string(latex_code)
output_path = processor.compile()
print(f"Output generated at: {output_path}")
```

---

## Plugins

You can extend the tool’s functionality by adding plugins. A plugin is any callable that accepts a `LatexProcess` instance as its only argument. For instance:

```python
def my_custom_plugin(processor: LatexProcess):
    # Do something with processor
    processor.logger.info("My Custom Plugin is running...")

my_custom_plugin.is_plugin = True  # Mark it as a plugin

processor.add_plugin(my_custom_plugin)
```

The tool also looks for plugins in a `plugins` directory (if `load_plugins()` is called). Any `.py` file in that directory with callables marked with `is_plugin = True` will be automatically loaded.

---

## Advanced Features

### Template Rendering

If you have a LaTeX template that uses [Jinja2](https://jinja.palletsprojects.com/), set the `template` parameter and call `render_template()` with a context dictionary:

```python
processor = LatexProcess(template="path/to/template.tex")
context = {"title": "My Document", "author": "Jane Doe"}
processor.render_template(context)
output_path = processor.compile()
```

### Watching a File for Changes

Automatically recompile when a `.tex` file changes using the `watch` method. This requires [watchdog](https://pypi.org/project/watchdog/) to be installed.

```python
processor.watch("main.tex", interval=5)
```

This will watch `main.tex` and recompile every time it detects a file modification, polling every 5 seconds.

### Async Compilation

Run LaTeX compilation in an asynchronous context:

```python
import asyncio
from your_package_name.latex_process import LatexProcess

async def main():
    processor = LatexProcess()
    processor.load_from_file("main.tex")
    output_path = await processor.compile_async()
    print(f"Compiled asynchronously, output at: {output_path}")

asyncio.run(main())
```

### Exporting to Different Formats

In addition to PDF, you can export to DVI, HTML, EPUB, or DOCX by specifying the `output_format`. For convenience, you may use helper methods:

```python
# Export to HTML
processor.export_html("output.html")

# Export to EPUB
processor.export_epub("output.epub")

# Export to DOCX
processor.export_docx("output.docx")
```

These methods internally call Pandoc, so ensure Pandoc is installed.

### Security Scan

A basic security scan checks for certain LaTeX commands that might be unsafe, such as `\write18`. This functionality is a placeholder and not comprehensive.

```python
issues = processor.security_scan()
if issues:
    print("Security issues found:", issues)
else:
    print("No security issues detected.")
```

---

## Logging

By default, the logging level is `INFO` and outputs to the console with Rich styling. You can adjust this level:

```python
import logging
processor.set_logging_level(logging.DEBUG)
```

You can also add a logging plugin to log to a file:

```python
processor.add_logging_plugin()  # By default logs to `latex_process.log` in the output directory
```

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository.
2. Create a new feature branch.
3. Make your changes or additions.
4. Write tests if appropriate.
5. Submit a Pull Request.

We appreciate your help in making this tool better.

---

## License

This project is licensed under the [MIT License](LICENSE). You’re free to use, modify, and distribute this software with attribution.