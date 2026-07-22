from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

# get version from __version__ variable in dehaat_procurement/__init__.py
from dehaat_procurement import __version__ as version

setup(
    name="dehaat_procurement",
    version=version,
    description="DeHaat Procurement Workflow & Warehouse Receiving Application",
    author="DeHaat Engineering",
    author_email="engineering@dehaat.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
)
