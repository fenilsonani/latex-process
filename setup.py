from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="latex-process",
    version="0.1.0",
    author="Fenil Sonani",
    author_email="contact@fenilsonani.com",
    description="A package to process LaTeX code and generate PDFs.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/fenilsonani/latex-process",  # Replace with your repo URL
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[],  # Add any dependencies if necessary
    entry_points={
        'console_scripts': [
            'latex-process=latex_process.latex_processor:main',
        ],
    },
)
