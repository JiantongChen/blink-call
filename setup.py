from setuptools import find_packages, setup

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

with open("VERSION", encoding="utf-8") as f:
    version = f.read().strip()

setup(
    name="blink_call",
    version=version,
    packages=find_packages(),
    author="BlinkCall Team",
    install_requires=requirements,
)
