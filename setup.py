from setuptools import setup, find_packages

setup(
    name="oure",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "numpy>=1.24.0",
        "scipy>=1.10.0",
        "sgp4>=2.23",
        "click>=8.1",
        "requests>=2.28"
    ],
    entry_points={
        "console_scripts": [
            "oure=oure.cli.commands:cli",
        ]
    }
)
