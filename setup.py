from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = [line.strip() for line in f if line.strip() and not line.startswith("#")]

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
