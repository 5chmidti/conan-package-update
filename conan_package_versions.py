import inspect
import os
import re
from sys import argv, path
from types import ModuleType
from packaging import version


def get_requires_lists(conan_package: ModuleType) -> str | None:
    for _, obj in inspect.getmembers(conan_package):
        if inspect.isclass(obj):
            requires: list[tuple[str, str]] = list(
                filter(lambda val: val[0] == "requires", inspect.getmembers(obj))
            )
            if len(requires) == 0:
                continue
            return requires[0][1]
    return None


def get_name_version_pair(package: str) -> tuple[str, str]:
    return (
        package[: package.find("/")],
        package[package.find("/") + 1 :],
    )


update_type = tuple[str, str, str]


def get_package_update(package: str) -> update_type | None:
    package_name, package_version = get_name_version_pair(package)
    stream = os.popen(f"conan search {package_name} -r conancenter --raw | tail -n1")
    output = stream.read().strip()
    _, found_package_version = get_name_version_pair(output)

    if version.parse(package_version) < version.parse(found_package_version):
        return (package_name, package_version, found_package_version)


def update_conanfile(updates: list[update_type]):
    with open("conanfile.py", "r") as conanfile:
        data = conanfile.read()
        for name, old, new in updates:
            data = re.sub(f"{name}/{old}", f"{name}/{new}", data)
    with open("conanfile.py", "w") as conanfile:
        conanfile.write(data)


def get_updates(requires_list: str):
    updates: list[update_type] = []
    for package in requires_list:
        update = get_package_update(package)
        if update is None:
            continue
        updates.append(update)
    return updates


if __name__ == "__main__":
    project_path = argv[1]

    path.insert(1, project_path)
    conan_package: ModuleType = __import__("conanfile")

    os.chdir(project_path)

    requires_list = get_requires_lists(conan_package)
    if requires_list is None:
        exit()

    updates = get_updates(requires_list)

    update_conanfile(updates)
