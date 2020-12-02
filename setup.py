from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="goodenough",
    version="0.0",
    description="(* ^ ω ^)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/marcgurevitx/goodenough",
    author="Marc Gurevitx",
    author_email="marcgurevitx@gmail.com",
    license="The Unlicense",
    py_modules=["goodenough"],
)
