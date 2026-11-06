import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="git-archaeologist",
    version="0.1.0",
    author="Mianm-l",
    description="Find out WHY a line of code exists before you touch it. Bypasses formatting churn and tracks origin context.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Mianm-l/git-archaeologist",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Version Control :: Git",
        "Topic :: Software Development :: Quality Assurance",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "git-archaeologist=git_archaeologist.cli:main",
        ],
    },
)
