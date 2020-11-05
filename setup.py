import pathlib
import setuptools
from typing import List


def _get_dependencies(requirements_file: pathlib.Path) -> List[str]:
    """
    Return requirements from a requirements file.
    This expects a requirements file with no ``--find-links`` lines.
    """
    lines = requirements_file.read_text().strip().split('\n')
    deps = []
    for dep in lines:
        if dep.startswith('#'):
            continue
        if dep.startswith('git+https://'):
            pkg_string = dep.split('#egg=')[1]
            pkg, version = pkg_string.split('-')
            dep = pkg + ' @ ' + dep
        deps.append(dep)
    return deps


INSTALL_REQUIRES = _get_dependencies(
    requirements_file=pathlib.Path('requirements.txt'),
)

DEV_REQUIRES = _get_dependencies(
    requirements_file=pathlib.Path('dev-requirements.txt'),
)

LONG_DESCRIPTION = pathlib.Path('README.rst').read_text()

setuptools.setup(
    name="ms",
    version="0.1.0",
    author="Tim Weidner",
    author_email="timaa2k@gmail.com",
    description="Mothership CLI",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/x-rst",
    url="https://github.com/timaa2k/ms",
    include_package_data=True,
    packages=setuptools.find_packages(where='src'),
    package_dir={'': 'src'},
    zip_safe=False,
    install_requires=INSTALL_REQUIRES + ['motherlib @ git+https://github.com/timaa2k/motherlib@master#egg=motherlib-0.1.0'],
    extras_require={
        'dev': DEV_REQUIRES,
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GPLv3 License",
        "Operating System :: OS Independent",
    ],
    dependency_links=[],
    entry_points={"console_scripts": ["ms=ms:cli"]},
)
