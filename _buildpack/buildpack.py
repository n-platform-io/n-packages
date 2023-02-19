import argparse
import subprocess
import sys

import yaml
import os

from dependency_algorithm import Dependencies


def resolve_dependencies(pks: dict, package: str = "") -> (list, list, list):
    _p = pks.copy()
    packages = pks['packages']
    type(packages)
    to_build = {}
    to_run = {}
    to_check = {}

    if not package:
        # print("Resolving all packages")
        # print(packages.items())
        for k, v in packages.items():
            to_run[k], to_build[k], to_check[k] = resolve_dependencies(_p.copy(), k)
            # print("RUN TREE LOOKS LIKE THIS")
            # print(to_run)
            # print("BUILD TREE LOOKS LIKE THIS")
            # print(to_build)
            # print("CHECK  TREE LOOKS LIKE THIS")
            # print(to_check)
            # print(f"GOING OVER SUBDEPS OF: {k}")
            for key in to_run[k]:
                # print(f"TO RUN_ KEY: {key}")
                if key in to_run.keys(): continue
                to_run[key], to_build[key], to_check[key] = resolve_dependencies(_p.copy(), key)
            for key in to_build[k]:
                # print(f"TO build_ KEY: {key}")
                if key in to_build.keys(): continue
                to_run[key], to_build[key], to_check[key] = resolve_dependencies(_p.copy(), key)
            for key in to_check[k]:
                # print(f"TO check_ KEY: {key}")
                if key in to_check.keys(): continue
                to_run[key], to_build[key], to_check[key] = resolve_dependencies(_p.copy(), key)



    else:
        try:
            # print(f"SINGLE: Resolving dependency for: {package}")
            if packages[package]['requirements'] is None:
                packages[package]['requirements'] = []
            if packages[package]['requirements-make'] is None:
                packages[package]['requirements-make'] = []
            if packages[package]['requirements-check'] is None:
                packages[package]['requirements-check'] = []
            pkg_rundeps = packages[package]['requirements']
            pkg_makedeps = packages[package]['requirements'] + packages[package]['requirements-make']
            pkg_checkdeps = packages[package]['requirements-check']
            # print(f"PACKage {package} needs:")
            # print(f"To run: {pkg_rundeps}")
            # print(f"To make: {pkg_makedeps}")
            # print(f"To check: {pkg_checkdeps}")

        except KeyError:
            print(f"[WARN] LACK KEY for package: {package} in job file")
            return [], [], []

        # print(f"Will resolve dependency tree for {package}")
        to_run[package] = pkg_rundeps
        to_build[package] = pkg_makedeps
        to_check[package] = pkg_checkdeps
        # print(f"To run {package}: {pkg_rundeps} ")
        # print(f"To make {package}: {pkg_makedeps} ")
        # print(f"To check {package}: {pkg_checkdeps} ")
        # print(f"Tree to build: {to_build}, run: {to_run}, check: {to_check} ")
        #
        # print("Now we will resolve following run dependencies")
        # print(f"Rundeps for {package} is {pkg_rundeps}")
        for pkg in pkg_rundeps:
            # print(f"One of rundeps for {package} is {pkg}")
            # print(f"Will spawn now the resolution for package {pkg}")
            to_runp, to_make, to_chk = resolve_dependencies(_p, pkg)
            # print(f"Resolution for {pkg} finished with following results")
            # print(to_runp, to_make, to_chk)
            # print(f"Will now add the package {pkg} dependencies to the trees.")
            # print(f"Let's compare the trees. BEGORE")
            # print(to_run)
            # print(to_build)
            # print(to_check)
            to_run[pkg] = to_runp

            # print(f"AFTER")
            # print(to_run)
            # print(to_build)
            # print(to_check)

        # print(f"builddeps for {package}: {pkg_makedeps}")
        for pkg in pkg_makedeps:
            to_runp, to_make, to_chk = resolve_dependencies(_p, pkg)
            to_run[pkg] = to_runp
            to_build[pkg] = to_make

        # print(f"checkdeps for {package}: {pkg_checkdeps}")
        for pkg in pkg_checkdeps:
            to_runp, to_make, to_chk = resolve_dependencies(_p, pkg)
            to_check[pkg] = to_chk

        # print("So, we've built the trees")
        # print("Trees look like this:")

    # print("RUNDEPS")
    # print(to_run)
    # print("To check")
    # print(to_check)
    # print("To build")
    # print(to_build)

    _rundeps = Dependencies(to_run).resolve_dependencies()
    _builddeps = Dependencies(to_build).resolve_dependencies()
    _checkdeps = Dependencies(to_check).resolve_dependencies()
    if package:
        _rundeps.remove(package)
        _builddeps.remove(package)
        _checkdeps.remove(package)
    return _rundeps, _builddeps, _checkdeps


repo_dir = os.getcwd()
print("workdir")
print(repo_dir)
version = "0.0.1"

parser = argparse.ArgumentParser(
    prog=f"N Operating System Buildpack v{version}",
    description="Builds packages for N Operating System",
)

parser.add_argument('--action', required=False, default="buildall")
parser.add_argument('--filename', required=False, default="packages.yaml")
parser.add_argument('--package', required=False)

args = parser.parse_args()
print(args)

with open('packages.yaml', 'r') as f:
    packages = yaml.full_load(f)

if args.action == "reposync_danger":
    print(packages)
    for package, v in packages['packages'].items():
        print(package, v)
        if not "requirements" in packages.keys():
            packages['packages'][package] = dict()
            print(f"Processing: {packages['packages'][package]}")
            packages['packages'][package]['requirements'] = list()
            packages['packages'][package]['requirements-make'] = list()
            packages['packages'][package]['requirements-check'] = list()

    print(packages)
    with open("packages.yaml", "w") as f:
        yaml.dump(packages, f)

if args.action == "buildall":
    rundeps, builddeps, checkdeps = resolve_dependencies(packages)
    for element in rundeps:
        print(f"Building runtime dependency: {element}")
        os.chdir(repo_dir)
        os.chdir(f"packages/{element}")
        subprocess.run(f"PKGDEST={repo_dir}/out makepkg --noconfirm -sr", shell=True, check=True)


elif args.action == "build":
    print(f"Building runtime dependency: {args.package}")
    os.chdir(repo_dir)
    os.chdir(f"packages/{args.package}")
    subprocess.run(f"PKGDEST={repo_dir}/out makepkg --noconfirm -sr", shell=True, check=True)

elif args.action == "check":
    err = False
    rundeps, builddeps, checkdeps = resolve_dependencies(packages, args.package)
    print(f"Rundeps: {rundeps}")
    print(f"builddeps: {builddeps}")
    print(f"checkdeps: {checkdeps}")
    for dep in rundeps:
        try:
            os.chdir("packages/" + dep)
        except OSError:
            err = True
            print(f"ERR: There is no package {dep} required to run {args.package}")

    for dep in builddeps:
        try:
            os.chdir("packages/" + dep)
        except OSError:
            err = True
            print(f"ERR: There is no package {dep} required to build {args.package}")

    for dep in checkdeps:
        try:
            os.chdir("packages/" + dep)
        except OSError:
            err = True
            print(f"ERR: There is no package {dep} required to check {args.package}")

    if err:
        sys.exit(2)

elif args.action == "checkall":
    err = False
    rundeps, builddeps, checkdeps = resolve_dependencies(packages)
    print(f"Packages will be installed in this order: {rundeps}")
    print(f"Packages will be built in this order: {builddeps}")
    print(f"Packages will be checked in this order: {checkdeps}")
    for dep in rundeps:
        try:
            os.chdir("packages/" + dep)
        except OSError:
            err = True
            print(f"ERR: There is no package {dep} required to run something in OS")

    for dep in builddeps:
        try:
            os.chdir("packages/" + dep)
        except OSError:
            err = True
            print(f"ERR: There is no package {dep} required to build OS")

    for dep in checkdeps:
        try:
            os.chdir("packages/" + dep)
        except OSError:
            err = True
            print(f"ERR: There is no package {dep} required to perform tests in OS")

    if err:
        sys.exit(2)
