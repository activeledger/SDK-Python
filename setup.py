import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="activeLedgerSDK",
    version="0.0.0",
    author="Jialin",
    author_email="jyu@agilitysciences.com",
    description="Python SDK for activeledger",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/jialin-yu/python-sdk",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)