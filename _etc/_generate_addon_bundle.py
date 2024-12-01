"""
Simple script to bundle src/ with LICENSE.txt as addon zip file.

:Author: jupiterbjy@gmail.com
:Version: 2024-12-01
:License: MIT
"""

import pathlib
import zipfile
from typing import Iterator


ROOT = pathlib.Path(__file__).parent.parent
ADDON_NAME = "llama-mesh-blender"


def fetch_src_recursive_gen(
    path: pathlib.Path, ext_whitelist=(".py",)
) -> Iterator[pathlib.Path]:
    """Recursively fetch files"""

    if path.is_file() and path.suffix in ext_whitelist:
        yield path
        return

    for child in path.iterdir():
        yield from fetch_src_recursive_gen(child)


def create_zip():
    """Create zip file from src/ and LICENSE.txt"""

    with zipfile.ZipFile(
        ROOT / (ADDON_NAME + ".zip"), "w", compression=zipfile.ZIP_DEFLATED
    ) as zip_fp:

        print("Writing LICENSE")
        zip_fp.write(ROOT / "LICENSE", arcname=f"/{ADDON_NAME}/LICENSE")

        src_path = ROOT / "src"

        for path in fetch_src_recursive_gen(ROOT / "src"):
            print(f"Writing {path}")
            zip_fp.write(
                path, arcname=f"/{ADDON_NAME}/" + str(path.relative_to(src_path))
            )


if __name__ == "__main__":
    create_zip()
