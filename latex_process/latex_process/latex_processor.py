import os
import subprocess
import shutil
from pathlib import Path
import logging
import asyncio
import sys
from jinja2 import Template
from typing import Optional, List, Dict, Any, Callable
import tempfile
from rich.console import Console
from rich.logging import RichHandler
import argparse
import importlib.util

# Constants for supported engines and bibliography tools
SUPPORTED_ENGINES = ['pdflatex', 'xelatex', 'lualatex', 'latexmk']
SUPPORTED_BIBTOOLS = ['bibtex', 'biber']
SUPPORTED_OUTPUT_FORMATS = ['pdf', 'dvi', 'html', 'epub', 'docx']

# Initialize Rich Console for enhanced logging
console = Console()


class LatexProcessError(Exception):
    """Custom exception for LatexProcess-related errors."""
    pass


class LatexProcess:
    def __init__(self,
                 engine: str = 'pdflatex',
                 bib_tool: str = 'bibtex',
                 output_format: str = 'pdf',
                 output_dir: str = 'output',
                 output_filename: str = 'document.pdf',
                 template: Optional[str] = None,
                 additional_args: Optional[List[str]] = None,
                 log_level: int = logging.INFO):
        """
        Initialize the LatexProcess.

        :param engine: LaTeX engine to use ('pdflatex', 'xelatex', 'lualatex', 'latexmk').
        :param bib_tool: Bibliography tool to use ('bibtex', 'biber').
        :param output_format: Desired output format ('pdf', 'dvi', 'html', 'epub', 'docx').
        :param output_dir: Directory to save output files.
        :param output_filename: Name of the output file.
        :param template: Path to a LaTeX template file.
        :param additional_args: Additional command-line arguments for the LaTeX engine.
        :param log_level: Logging verbosity level.
        """
        self.engine = engine.lower()
        self.bib_tool = bib_tool.lower()
        self.output_format = output_format.lower()
        self.output_dir = Path(output_dir)
        self.output_filename = output_filename
        self.template = template
        self.additional_args = additional_args or []
        self.latex_code = ""
        self.dependencies = []  # List of file paths
        self.plugins: List[Callable[['LatexProcess'], None]] = []
        self._validate_initial_settings()
        self.create_output_directory()
        self.logger = self._setup_logger(log_level)
        self.console = console

    def _setup_logger(self, log_level: int) -> logging.Logger:
        """
        Setup the logger with the specified log level and RichHandler.

        :param log_level: Logging level.
        :return: Configured logger.
        """
        logger = logging.getLogger(self.__class__.__name__)
        logger.setLevel(log_level)
        handler = RichHandler(rich_tracebacks=True)
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        if not logger.handlers:
            logger.addHandler(handler)
        return logger

    def _validate_initial_settings(self):
        """
        Validate initial settings such as engine, bibliography tool, and output format.
        """
        if self.engine not in SUPPORTED_ENGINES:
            raise ValueError(f"Unsupported LaTeX engine: {self.engine}. Supported engines: {SUPPORTED_ENGINES}")
        if self.bib_tool and self.bib_tool not in SUPPORTED_BIBTOOLS:
            raise ValueError(f"Unsupported bibliography tool: {self.bib_tool}. Supported tools: {SUPPORTED_BIBTOOLS}")
        if self.output_format not in SUPPORTED_OUTPUT_FORMATS:
            raise ValueError(f"Unsupported output format: {self.output_format}. Supported formats: {SUPPORTED_OUTPUT_FORMATS}")
        if not shutil.which(self.engine):
            raise LatexProcessError(f"LaTeX engine '{self.engine}' not found. Please install it.")
        if self.bib_tool and not shutil.which(self.bib_tool):
            raise LatexProcessError(f"Bibliography tool '{self.bib_tool}' not found. Please install it.")

    def create_output_directory(self):
        """
        Ensure the output directory exists.
        """
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_from_file(self, tex_file: str):
        """
        Load LaTeX code from a .tex file.

        :param tex_file: Path to the .tex file.
        """
        tex_path = Path(tex_file)
        if not tex_path.is_file():
            raise FileNotFoundError(f"TeX file not found: {tex_file}")
        self.latex_code = tex_path.read_text(encoding='utf-8')
        self.logger.info(f"Loaded LaTeX code from {tex_file}")

    def load_from_string(self, latex_code: str):
        """
        Load LaTeX code from a string.

        :param latex_code: LaTeX code as a string.
        """
        self.latex_code = latex_code
        self.logger.info("Loaded LaTeX code from string.")

    def render_template(self, context: Dict[str, Any]):
        """
        Render the LaTeX code using a Jinja2 template.

        :param context: Context dictionary for template rendering.
        """
        if not self.template:
            raise LatexProcessError("No template specified for rendering.")
        template_path = Path(self.template)
        if not template_path.is_file():
            raise FileNotFoundError(f"Template file not found: {self.template}")
        template_content = template_path.read_text(encoding='utf-8')
        template = Template(template_content)
        self.latex_code = template.render(**context)
        self.logger.info(f"Rendered LaTeX code using template {self.template}")

    def add_dependency(self, file_path: str):
        """
        Add a file dependency (e.g., images, included files).

        :param file_path: Path to the dependency file.
        """
        dep_path = Path(file_path)
        if not dep_path.exists():
            self.logger.warning(f"Dependency file does not exist: {file_path}")
        else:
            self.dependencies.append(str(dep_path.resolve()))
            self.logger.info(f"Added dependency: {file_path}")

    def add_plugin(self, plugin_func: Callable[['LatexProcess'], None]):
        """
        Add a plugin function to extend functionality.

        :param plugin_func: A callable that takes the LatexProcess instance as an argument.
        """
        if callable(plugin_func):
            self.plugins.append(plugin_func)
            plugin_func(self)
            self.logger.info(f"Plugin {plugin_func.__name__} added.")
        else:
            raise ValueError("Plugin must be a callable.")

    def load_plugins(self, plugins_dir: Optional[str] = None):
        """
        Load all plugins from the specified directory.

        :param plugins_dir: Path to the plugins directory.
        """
        plugins_path = Path(plugins_dir) if plugins_dir else Path(__file__).parent / 'plugins'
        if not plugins_path.exists() or not plugins_path.is_dir():
            self.logger.warning(f"No plugins directory found at: {plugins_dir}")
            return
        for plugin_file in plugins_path.glob('*.py'):
            module_name = plugin_file.stem
            try:
                spec = importlib.util.spec_from_file_location(module_name, plugin_file)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                for attr in dir(module):
                    plugin = getattr(module, attr)
                    if callable(plugin) and hasattr(plugin, 'is_plugin') and plugin.is_plugin:
                        self.add_plugin(plugin)
                        self.logger.info(f"Loaded plugin: {attr}")
            except Exception as e:
                self.logger.error(f"Failed to load plugin {plugin_file}: {e}")

    def create_tex_file(self, filename: Optional[str] = None) -> Path:
        """
        Write the LaTeX code to a .tex file.

        :param filename: Optional custom filename for the .tex file.
        :return: Path to the .tex file.
        """
        tex_filename = filename or "document.tex"
        tex_path = self.output_dir / tex_filename
        self.output_dir.mkdir(parents=True, exist_ok=True)
        tex_path.write_text(self.latex_code, encoding='utf-8')
        self.logger.info(f"Wrote LaTeX code to {tex_path}")
        return tex_path

    def _run_command(self, command: List[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
        """
        Run a shell command and return the completed process.

        :param command: Command and arguments as a list.
        :param cwd: Directory to run the command in.
        :return: CompletedProcess instance.
        """
        self.logger.debug(f"Running command: {' '.join(command)} in {cwd or os.getcwd()}")
        try:
            process = subprocess.run(
                command,
                cwd=cwd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            self.logger.debug(process.stdout)
            if process.stderr:
                self.logger.debug(process.stderr)
            return process
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Command '{' '.join(command)}' failed with error:")
            self.logger.error(e.stderr)
            raise LatexProcessError(f"Command '{' '.join(command)}' failed.") from e

    def _has_bibliography(self) -> bool:
        """
        Check if the LaTeX code includes a bibliography.

        :return: True if bibliography is present, False otherwise.
        """
        return r'\bibliography' in self.latex_code or r'\addbibresource' in self.latex_code

    def compile(self, tex_filename: Optional[str] = None) -> Path:
        """
        Compile the LaTeX document.

        :param tex_filename: Optional custom .tex filename if different from default.
        :return: Path to the generated output file.
        """
        tex_path = self.create_tex_file(tex_filename)
        cwd = self.output_dir

        # Apply plugins before compilation
        for plugin in self.plugins:
            plugin(self)

        # Initial LaTeX compilation
        self.logger.info("Starting LaTeX compilation...")
        self._run_command([self.engine, "-interaction=nonstopmode", tex_path.name], cwd=cwd)

        # Bibliography processing
        if self.bib_tool and self._has_bibliography():
            self.logger.info("Processing bibliography...")
            self._run_command([self.bib_tool, tex_path.stem], cwd=cwd)

            # Re-run LaTeX to incorporate bibliography
            self.logger.info("Re-running LaTeX after bibliography...")
            self._run_command([self.engine, "-interaction=nonstopmode", tex_path.name], cwd=cwd)

        # Additional LaTeX runs for references, etc.
        self.logger.info("Finalizing LaTeX compilation...")
        for _ in range(2):
            self._run_command([self.engine, "-interaction=nonstopmode", tex_path.name], cwd=cwd)

        # Convert output if necessary
        output_file = self._convert_output()

        self.logger.info(f"Compilation successful. Output file: {output_file}")
        return output_file

    def _convert_output(self) -> Path:
        """
        Convert the output to the desired format if necessary.

        :return: Path to the converted output file.
        """
        tex_path = self.output_dir / "document.tex"
        base_name = tex_path.stem
        output_file = self.output_dir / self.output_filename

        if self.output_format == 'pdf':
            output_file = self.output_dir / f"{base_name}.pdf"
        elif self.output_format == 'dvi':
            output_file = self.output_dir / f"{base_name}.dvi"
        elif self.output_format == 'html':
            output_file = self.output_dir / f"{base_name}.html"
            self._run_command(['pandoc', '-s', f"{base_name}.tex", '-o', f"{base_name}.html"], cwd=self.output_dir)
        elif self.output_format == 'epub':
            output_file = self.output_dir / f"{base_name}.epub"
            self._run_command(['pandoc', '-s', f"{base_name}.tex", '-o', f"{base_name}.epub"], cwd=self.output_dir)
        elif self.output_format == 'docx':
            output_file = self.output_dir / f"{base_name}.docx"
            self._run_command(['pandoc', '-s', f"{base_name}.tex", '-o', f"{base_name}.docx"], cwd=self.output_dir)
        else:
            raise LatexProcessError(f"Unsupported output format: {self.output_format}")

        return output_file

    async def compile_async(self, tex_filename: Optional[str] = None) -> Path:
        """
        Asynchronously compile the LaTeX document.

        :param tex_filename: Optional custom .tex filename if different from default.
        :return: Path to the generated output file.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.compile, tex_filename)

    def open_output(self):
        """
        Open the generated output file with the default application.
        """
        output_path = self.get_output_path()
        if not output_path.exists():
            self.logger.error(f"Output file does not exist: {output_path}")
            return

        self.logger.info(f"Opening output file: {output_path}")
        try:
            if sys.platform.startswith('darwin'):
                subprocess.run(['open', str(output_path)], check=True)
            elif os.name == 'nt':
                os.startfile(str(output_path))
            elif os.name == 'posix':
                subprocess.run(['xdg-open', str(output_path)], check=True)
            else:
                self.logger.warning("Unsupported OS for opening files automatically.")
        except Exception as e:
            self.logger.error(f"Failed to open output file: {e}")

    def watch(self, tex_file: str, interval: int = 5):
        """
        Watch a .tex file and recompile on changes.

        :param tex_file: Path to the .tex file.
        :param interval: Polling interval in seconds.
        """
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler

        class ChangeHandler(FileSystemEventHandler):
            def __init__(self, processor: 'LatexProcess', file_to_watch: Path):
                self.processor = processor
                self.file_to_watch = file_to_watch.resolve()

            def on_modified(self, event):
                if Path(event.src_path).resolve() == self.file_to_watch:
                    self.processor.logger.info(f"Detected change in {event.src_path}. Recompiling...")
                    try:
                        self.processor.compile()
                    except LatexProcessError as e:
                        self.processor.logger.error(f"Compilation failed: {e}")

        observer = Observer()
        path_to_watch = Path(tex_file).parent
        event_handler = ChangeHandler(self, Path(tex_file))
        observer.schedule(event_handler, str(path_to_watch), recursive=False)
        observer.start()
        self.logger.info(f"Watching for changes in {tex_file}...")

        try:
            while True:
                asyncio.sleep(interval)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

    def get_logs(self) -> str:
        """
        Retrieve the current logs.

        :return: Log messages as a string.
        """
        # Advanced implementation can store logs in a buffer
        # For simplicity, returning a placeholder
        return "Log retrieval not implemented."

    def export(self, format: str, destination: Optional[str] = None):
        """
        Export the document to a specified format.

        :param format: Desired format ('pdf', 'dvi', 'html', 'epub', 'docx').
        :param destination: Optional destination path.
        """
        self.output_format = format.lower()
        if destination:
            self.output_filename = Path(destination).name
            self.output_dir = Path(destination).parent
            self.create_output_directory()
        self.compile()
        self.logger.info(f"Exported document to {format} format.")

    def export_html(self, html_filename: Optional[str] = None):
        """
        Export the LaTeX document to HTML format using pandoc.

        :param html_filename: Optional custom HTML filename.
        """
        self.output_format = 'html'
        if html_filename:
            self.output_filename = html_filename
        self.compile()
        self.logger.info(f"Exported document to HTML format: {self.output_dir / self.output_filename}")

    def export_epub(self, epub_filename: Optional[str] = None):
        """
        Export the LaTeX document to EPUB format using pandoc.

        :param epub_filename: Optional custom EPUB filename.
        """
        self.output_format = 'epub'
        if epub_filename:
            self.output_filename = epub_filename
        self.compile()
        self.logger.info(f"Exported document to EPUB format: {self.output_dir / self.output_filename}")

    def export_docx(self, docx_filename: Optional[str] = None):
        """
        Export the LaTeX document to DOCX format using pandoc.

        :param docx_filename: Optional custom DOCX filename.
        """
        self.output_format = 'docx'
        if docx_filename:
            self.output_filename = docx_filename
        self.compile()
        self.logger.info(f"Exported document to DOCX format: {self.output_dir / self.output_filename}")

    def add_bibliography(self, bib_file: str):
        """
        Add a bibliography file.

        :param bib_file: Path to the .bib file.
        """
        self.add_dependency(bib_file)
        self.logger.info(f"Added bibliography file: {bib_file}")

    def cleanup(self):
        """
        Clean up auxiliary files generated during compilation.
        """
        aux_extensions = ['.aux', '.log', '.bbl', '.blg', '.toc', '.out', '.lof', '.lot', '.fls', '.fdb_latexmk']
        for ext in aux_extensions:
            aux_file = self.output_dir / f'document{ext}'
            if aux_file.exists():
                aux_file.unlink()
                self.logger.debug(f"Removed auxiliary file: {aux_file}")
        self.logger.info("Cleaned up auxiliary files.")

    def set_logging_level(self, level: int):
        """
        Set the logging level.

        :param level: Logging level (e.g., logging.DEBUG, logging.INFO).
        """
        self.logger.setLevel(level)
        self.logger.info(f"Logging level set to {logging.getLevelName(level)}")

    def get_output_path(self) -> Path:
        """
        Get the path to the generated output file.

        :return: Path object of the output file.
        """
        return self.output_dir / self.output_filename

    def cache_enable(self, cache_dir: Optional[str] = None):
        """
        Enable caching by specifying a cache directory.

        :param cache_dir: Path to the cache directory.
        """
        self.cache_dir = Path(cache_dir) if cache_dir else self.output_dir / '.cache'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Caching enabled. Cache directory: {self.cache_dir}")

    def cache_disable(self):
        """
        Disable caching by removing the cache directory.
        """
        if hasattr(self, 'cache_dir') and self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.logger.info("Caching disabled and cache directory removed.")

    def cache_clear(self):
        """
        Clear the cache by removing all cached files.
        """
        if hasattr(self, 'cache_dir') and self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info("Cache cleared.")

    def security_sandbox_enable(self):
        """
        (Removed Docker-based sandboxing; placeholder for future sandbox logic if needed)
        """
        self.logger.info("Security sandbox enable method is a placeholder (Docker removed).")

    def security_sandbox_disable(self):
        """
        Placeholder for disabling sandboxing (Docker removed).
        """
        self.logger.info("Security sandbox disable method is a placeholder (Docker removed).")

    def integrate_cloud_service(self, service_name: str, credentials: Dict[str, Any]):
        """
        Integrate with a cloud service for LaTeX processing.

        :param service_name: Name of the cloud service.
        :param credentials: Credentials for the cloud service.
        """
        # Placeholder for cloud integration logic
        self.logger.info(f"Integrated with cloud service: {service_name}")

    def get_error_details(self, log_content: str) -> List[Dict[str, Any]]:
        """
        Parse LaTeX log content and extract error details.

        :param log_content: Content of the LaTeX log file.
        :return: List of error details with line numbers and messages.
        """
        import re
        error_pattern = re.compile(r"! (.*)\nl\.(\d+)\.(\d+)")
        errors = []
        for match in error_pattern.finditer(log_content):
            message, line, column = match.groups()
            errors.append({
                "message": message,
                "line": int(line),
                "column": int(column)
            })
        return errors

    def process(self, input_source: Optional[str] = None, from_string: bool = False) -> Path:
        """
        High-level method to process LaTeX code from file or string.

        :param input_source: Path to the .tex file or LaTeX code string.
        :param from_string: If True, treat input_source as LaTeX code string.
        :return: Path to the generated output file.
        """
        if input_source:
            if from_string:
                self.load_from_string(input_source)
            else:
                self.load_from_file(input_source)
        return self.compile()

    def interactive_shell(self):
        """
        Launch an interactive shell for dynamic LaTeX processing and experimentation.
        """
        import code
        variables = globals().copy()
        variables.update(locals())
        shell = code.InteractiveConsole(locals=variables)
        shell.interact("Entering interactive LatexProcess shell. Type 'exit()' to quit.")

    def security_scan(self):
        """
        Perform a security scan on the LaTeX code to detect potentially malicious commands.

        :return: List of detected issues.
        """
        import re
        # Simple example: scan for shell escape commands
        malicious_patterns = [
            r'\\write18',  # Shell escape
            r'\\input\{[^}]*\}',  # Including external files
            r'\\include\{[^}]*\}',
            r'\\includegraphics\{[^}]*\}',  # Including images
        ]
        issues = []
        for pattern in malicious_patterns:
            matches = re.findall(pattern, self.latex_code)
            if matches:
                issues.extend(matches)
        if issues:
            self.logger.warning(f"Security issues detected: {issues}")
        else:
            self.logger.info("No security issues detected.")
        return issues

    def add_security_plugin(self):
        """
        Add a security plugin to enhance LaTeX code safety.
        """
        def security_plugin(processor: 'LatexProcess'):
            processor.security_scan()

        security_plugin.is_plugin = True
        self.add_plugin(security_plugin)

    def add_logging_plugin(self):
        """
        Add a logging plugin to enhance logging capabilities.
        """
        def logging_plugin(processor: 'LatexProcess'):
            # Example: Redirect logs to a file
            log_file = processor.output_dir / "latex_process.log"
            file_handler = logging.FileHandler(log_file, mode='w')
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            processor.logger.addHandler(file_handler)
            processor.logger.info(f"Logging plugin added. Logs are being written to {log_file}")

        logging_plugin.is_plugin = True
        self.add_plugin(logging_plugin)


def main():
    parser = argparse.ArgumentParser(description="Ultimate LaTeX Processing Tool")
    parser.add_argument('input', help="Path to the .tex file or '-' to read from stdin.")
    parser.add_argument('-o', '--output', default="output/document.pdf", help="Output file path.")
    parser.add_argument('-e', '--engine', default='pdflatex', choices=SUPPORTED_ENGINES, help="LaTeX engine to use.")
    parser.add_argument('-b', '--bibtool', default='bibtex', choices=SUPPORTED_BIBTOOLS, help="Bibliography tool to use.")
    parser.add_argument('-f', '--format', default='pdf', choices=SUPPORTED_OUTPUT_FORMATS, help="Output format.")
    parser.add_argument('-t', '--template', help="Path to a Jinja2 LaTeX template.")
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help="Logging level.")
    args = parser.parse_args()

    log_level = getattr(logging, args.log_level.upper(), logging.INFO)

    processor = LatexProcess(
        engine=args.engine,
        bib_tool=args.bibtool,
        output_format=args.format,
        output_dir=Path(args.output).parent,
        output_filename=Path(args.output).name,
        template=args.template,
        log_level=log_level,
    )

    # Add plugins if any
    processor.add_logging_plugin()
    processor.add_security_plugin()

    if args.input == '-':
        latex_code = sys.stdin.read()
        processor.load_from_string(latex_code)
    else:
        processor.load_from_file(args.input)

    try:
        output_path = processor.compile()
        print(f"Output generated at: {output_path}")
        processor.open_output()
    except LatexProcessError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
