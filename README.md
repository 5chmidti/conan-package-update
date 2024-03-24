# conan-package-update - Automatically Update A `conanfile.py` Receipt

```console
$ python -m venv ./venv
$ pip install -r requirements.txt
$ python conan_package_versions.py /path/to/package/
INFO     checking /path/to/package/
INFO     requirements: ['ctre/3.2.1', 'fmt/10.2.1', 'spdlog/1.13.0']
INFO     updates found for /path/to/package/
INFO     updates: [('ctre', '3.2.1', '3.8.1')]
update package ctre from 3.2.1 to 3.8.1? [y/n]:
```

This tool allows easy updates for dependencies inside a `conanfile.py`.
The tool does not check if there are any version conflicts.
