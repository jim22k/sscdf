from setuptools import setup, find_packages

setup(
    name="sscdf",
    version="0.0.1",
    description="Implementation of binsparse format for python-graphblas using netCDF4 as a container",
    author="Anaconda, Inc.",
    packages=find_packages(include=["sscdf", "sscdf.*"]),
    include_package_data=True,
    install_requires=["python-graphblas", "netcdf4"]
)