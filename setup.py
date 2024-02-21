# -*- coding: utf-8 -*-

import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="oathyps", # Replace with your own username
    version="0.0.1",
    author="David Fuhrländer",
    author_email="d.fuhrlaender@uni-bremen.de",
    description="oathyps - A toolbox for simulation and analyses of hydrogen production systems",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="",
    package_dir={"": "src"},
    packages=setuptools.find_packages("src/"),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GPL-3.0-only ",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)
