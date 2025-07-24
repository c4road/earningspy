from earningspy.__version__ import __version__
from setuptools import setup, find_packages
import pathlib

with pathlib.Path("requirements.txt").open() as requirements_file:
    install_requires = [
        line.strip() for line in requirements_file
        if line.strip() and not line.startswith("#") and not line.startswith("--")
    ]

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="earningspy",
    version=__version__,
    license="MIT",
    description="Python toolkit for PEAD research and earnings calendar analysis.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Alberto Rincones",
    author_email="alberto.rincones@code4road.com",
    url="https://github.com/c4road/earningspy",
    keywords=["earnings", "finance", "AI", "scraper", "PEAD", "quant"],
    install_requires=install_requires,
    python_requires="==3.10.*",
    packages=find_packages(exclude=["tests", "docs"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Information Technology",
        "License :: OSI Approved :: MIT License",
        "Topic :: Scientific/Engineering :: Data Analysis",
        "Programming Language :: Python :: 3.10",
    ],
)