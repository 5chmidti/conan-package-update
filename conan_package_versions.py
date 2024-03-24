import importlib
import inspect
import os
import pathlib
import re
from sys import path
from types import ModuleType
from packaging import version
from rich.prompt import Confirm
from rich.logging import RichHandler
import logging
from argparse import ArgumentParser, BooleanOptionalAction
from conan import ConanFile

FORMAT = "%(message)s"
logging.basicConfig(
    level="INFO", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)

log = logging.getLogger("rich")


def get_requirements(potential_class: type):
    instance = potential_class()
    if "requirements" in dir(instance):
        instance.requirements()
    if "build_requirements" in dir(instance):
        instance.build_requirements()

    return map(lambda x: repr(x.ref), instance.requires.values())


def get_requires_lists(conan_package: ModuleType) -> list[str]:
    res: list[str] = []
    for _, potential_class in inspect.getmembers(conan_package):
        if inspect.isclass(potential_class):
            classtree = inspect.getclasstree([ConanFile, potential_class])
            for classes in classtree:
                for tree_for_class in classes:
                    if isinstance(tree_for_class, list):
                        package, maybe_conan_file_type = tree_for_class[0]
                        assert maybe_conan_file_type[0] == ConanFile
                        res += get_requirements(package)

    log.info(f"requirements: {res}")
    return res


def get_name_version_pair(package: str) -> tuple[str, str]:
    return (
        package[: package.find("/")],
        package[package.find("/") + 1 :],
    )


update_type = tuple[str, str, str]


def get_package_update(package: str) -> update_type | None:
    package_name, package_version = get_name_version_pair(package)
    stream = os.popen(f"conan search {package_name} -r conancenter 2>&1 | tail -n1")
    output = stream.read().strip()
    _, found_package_version = get_name_version_pair(output)

    try:
        if version.parse(package_version) < version.parse(found_package_version):
            return (package_name, package_version, found_package_version)
    except version.InvalidVersion:
        if package_version < found_package_version:
            return (package_name, package_version, found_package_version)


def update_conanfile(project_path: str, updates: list[update_type]):
    file_path = pathlib.Path(project_path + "/conanfile.py")
    with open(file_path.absolute(), "r") as conanfile:
        data = conanfile.read()
        for name, old, new in updates:
            data = re.sub(f"{name}/{old}", f"{name}/{new}", data)
    with open(file_path.absolute(), "w") as conanfile:
        conanfile.write(data)


def get_updates(requires_list: list[str]):
    return [
        update
        for update in map(lambda package: get_package_update(package), requires_list)
        if update is not None
    ]


def init_argparse() -> ArgumentParser:
    parser = ArgumentParser(
        description="Update conan packages in a conanfile",
    )
    parser.add_argument(
        "paths",
        metavar="path",
        help="conanfile or project root",
        type=str,
        nargs="+",
    )
    parser.add_argument(
        "--single",
        "-s",
        help="interative update on a per package basis",
        type=bool,
        action=BooleanOptionalAction
    )
    return parser


def run_for_project(project_path: str, single:bool):
    log.info(f"checking {project_path}")
    if not has_conanfile(project_path):
        log.info(f"no conanfile found in {project_path}")
        return

    path.insert(0, project_path)
    conan_package: ModuleType = importlib.import_module("conanfile")
    requires_list = get_requires_lists(conan_package)
    importlib.reload(conan_package)  # ?
    if len(requires_list) == 0:
        path.remove(project_path)
        log.info(f"empty requires list")
        return

    updates = get_updates(requires_list)

    if updates:
        log.info(f"updates found for {project_path}")
        log.info(f"updates: {updates}")
        if single:
            for update in updates:
                if Confirm.ask(f"update package {update[0]} from {update[1]} to {update[2]}?"):
                    update_conanfile(project_path,[update])
        else:
            if Confirm.ask("update conanfile?"):
                update_conanfile(project_path, updates)

    path.remove(project_path)


def get_folder_path(path: str):
    if os.path.isfile(path):
        return os.path.dirname(path)
    return path


def has_conanfile(path: str):
    return os.path.exists(path + "/conanfile.py")


if __name__ == "__main__":
    parser = init_argparse()
    args = parser.parse_args()

    project_path: list[str] = args.paths
    for project in project_path:
        run_for_project(get_folder_path(project),args.single)

