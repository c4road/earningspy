from distutils.core import setup
from setuptools import find_packages

setup(
    name="earningspy",
    packages=find_packages(),
    version="0.1.0",
    license="MIT",
    description="Finviz Scrapper with additional tools",
    author="Alberto Rincones",
    author_email="aa.rincones@gmail.com",
    url="https://github.com/c4road/earningspy",
    download_url="https://github.com/c4road/earningspy/archive/v1.4.6.tar.gz",
    keywords=["finviz", "api", "screener", "finviz api", "charts", "scraper"],
    install_requires=[
        "wheel",
        "lxml",
        "requests",
        "aiohttp",
        "urllib3",
        "cssselect",
        "user_agent",
        "beautifulsoup4",
        "tqdm",
        "tenacity",
    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
    ],
    package_data={'': ['earningspy/local_data/from-Feb2023EarningsCalendar.csv']},
    include_package_data=True,
)
