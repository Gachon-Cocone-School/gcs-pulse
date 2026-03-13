from setuptools import find_packages, setup


setup(
    name="gcs-pulse-cli",
    version="0.1.0",
    description="Stateful CLI harness for GCS Pulse backend",
    package_dir={"": "src"},
    packages=find_packages(where="src", include=["gcs_pulse*"]),
    include_package_data=True,
    install_requires=[
        "click>=8.1.7",
    ],
    entry_points={
        "console_scripts": [
            "gcs-pulse-cli=gcs_pulse.gcs_pulse_cli:main",
        ]
    },
    python_requires=">=3.9",
)