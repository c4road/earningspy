import sys 
from distutils.core import setup
from setuptools import find_packages
import pathlib

version = "0.1.0"
if "--version" in sys.argv:
    index = sys.argv.index("--version")
    version = sys.argv[index + 1]
    sys.argv.pop(index)
    sys.argv.pop(index)


with pathlib.Path("requirements.txt").open() as requirements_file:
    install_requires = [
        line.strip() for line in requirements_file if (
            line.strip() and not line.startswith("#") and not line.startswith("--"))
    ]
        

setup(
    name="earningspy",
    packages=find_packages(),
    version=version,
    license="MIT",
    description="Like if you can predict earnigns using AI",
    author="Alberto Rincones",
    author_email="alberto.rincones@code4road.com",
    url="https://github.com/c4road/earningspy",
    download_url="https://earningspy-923699018646.d.codeartifact.us-east-1.amazonaws.com/pypi/EarningSpy/earningspy",
    keywords=["earnings", "finance", "AI", "finviz", "scraper"],
    install_requires=install_requires,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Information Technology",
        "License :: Other/Proprietary License",
        "Topic :: Scientific/Engineering :: Data Analysis"
        "Programming Language :: Python :: 3.10"
    ],
    package_data={'': ['earningspy/local_data/from-Feb2023EarningsCalendar.csv']},
    include_package_data=True,
)
