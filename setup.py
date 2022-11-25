from setuptools import setup, find_packages


setup(
    name="serverlesspack",
    version="0.5.4",
    packages=find_packages(),
    include_package_data=True,
    install_requires=["click", "PyYAML", "pydantic", "boto3", "distlib", "importlib-metadata", "colorama", "asciitree", "tqdm"],
    entry_points={
        "console_scripts": [
            "serverlesspack = serverlesspack:package_cli",
        ],
    },
    url="https://github.com/Robinson04/serverlesspack",
    license="MIT",
    author="Inoft",
    author_email="robinson@inoft.com",
    description="A bundler for Python serverless applications on AWS Lambda, with tree shaking, code packaging, dependencies resolution as Lambda layers and expressive bundling configurations.",
)

