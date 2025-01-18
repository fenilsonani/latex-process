# latex_process/plugins/example_plugin.py

from latex_process.latex_processor import LatexProcess

def example_plugin(processor: 'LatexProcess'):
    """
    An example plugin that adds a custom message before compilation.
    """
    processor.logger.info("Example Plugin: Pre-compilation step.")

example_plugin.is_plugin = True
