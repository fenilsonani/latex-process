# tests/test_latex_processor.py

import unittest
from latex_process import LatexProcess
import os
import shutil

class TestLatexProcess(unittest.TestCase):
    def setUp(self):
        self.latex_code = r"""
        \documentclass{article}
        \begin{document}
        Hello, World!
        \end{document}
        """
        self.processor = LatexProcess(output_dir="test_output", output_filename="test_document.pdf")
        self.processor.cache_enable("test_output/.cache")

    def tearDown(self):
        if os.path.exists("test_output"):
            shutil.rmtree("test_output")

    def test_compile_success(self):
        pdf_path = self.processor.process(from_string=True)
        self.assertTrue(os.path.exists(pdf_path))

    def test_compile_failure(self):
        invalid_latex = r"""
        \documentclass{article}
        \begin{document}
        \invalidcommand
        \end{document}
        """
        with self.assertRaises(Exception):
            self.processor.process(from_string=True)

    def test_template_rendering(self):
        template_content = r"""
        \documentclass{article}
        \begin{document}
        Hello, {{ name }}!
        \end{document}
        """
        with open("test_output/template.tex", "w") as f:
            f.write(template_content)
        self.processor.template = "test_output/template.tex"
        context = {"name": "Tester"}
        self.processor.render_template(context)
        self.assertIn("Hello, Tester!", self.processor.latex_code)

    def test_bibliography(self):
        self.latex_code += r"\bibliography{references}"
        self.processor.latex_code = self.latex_code
        # Assume references.bib exists
        with open("test_output/references.bib", "w") as f:
            f.write("""
            @article{test,
                author = {Author, A.},
                title = {Test Article},
                journal = {Journal of Testing},
                year = {2021},
            }
            """)
        self.processor.add_bibliography("test_output/references.bib")
        pdf_path = self.processor.process(from_string=True)
        self.assertTrue(os.path.exists(pdf_path))

    def test_security_scan(self):
        malicious_latex = r"""
        \documentclass{article}
        \begin{document}
        \write18{echo "Malicious Code"}
        \end{document}
        """
        self.processor.load_from_string(malicious_latex)
        issues = self.processor.security_scan()
        self.assertIn(r'\write18{echo "Malicious Code"}', issues)

    def test_plugin_loading(self):
        def test_plugin(processor: 'LatexProcess'):
            processor.logger.info("Test Plugin Executed.")

        test_plugin.is_plugin = True
        self.processor.add_plugin(test_plugin)
        self.processor.process(from_string=True)
        # Check logs manually or implement log retrieval

if __name__ == "__main__":
    unittest.main()
