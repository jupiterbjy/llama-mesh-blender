"""
Custom llama.cpp binary wrapper to avoid accessing blender's pip unnecessarily,
while keeping these as one whole module for who-knows-when situations.

This automatically downloads llama.cpp compiled binary without compilation for supported platforms.
Also assumes gguf to be window-safe and url-safe at same time.

:Author: jupiterbjy@gmail.com
:Version: 2024-11-31
:License: MIT
"""

import itertools
import platform
import pathlib

# import os
import io

# import asyncio
import subprocess
from http.client import HTTPResponse
from typing import BinaryIO, Iterator

# Mac workaround
# os.environ["no_proxy"] = "*"

from urllib.request import urlopen


__all__ = ["LlamaCppWrapper"]


"""
MEMO

import platform
print(platform.system(), platform.processor(), platform.machine(), sep="\n")

Windows
AMD64 Family 25 Model 33 Stepping 0, AuthenticAMD
AMD64


Linux

x86_64
(J4105 doesn't have name!??)


Darwin
arm
arm64
"""


# --- Configs ---

# Real tempting to use logger but well guess I'll use print for now

# target llama.cpp binary version
_LLAMA_CPP_BUILD = "b4227"

# llama.cpp param (other than -m)
_LLAMA_CPP_PARAM = " ".join(
    [
        "-ngl 999",
        "-fa",
        # "-c 8192",
        # "-t 0.0",
        # "-cnv",
        # '-p "You are an helpful assistant."',
        # "2>null"
    ]
)


# --- Globals ---

_ROOT = pathlib.Path(__file__).parent

# file path with platform info at first line, build version at second line.
_VER_INFO_FILE = _ROOT / "version_info"
_VER_INFO_FILE.touch(exist_ok=True)


# gguf directory
_GGUF_DIR = _ROOT / "gguf"
_GGUF_DIR.mkdir(exist_ok=True)


_SYSTEM_TO_FILE_NAME = {
    "Linux": "ubuntu",
    # ^^^ as a debian main IDK if I like this conversion...
    "Windows": "win-vulkan",
    "Darwin": "macos",
    # ^^^ hope this works, I don't own mac to test this
}


_ARCH_TO_FILE_NAME = {
    "AMD64": "x64",
    "x86_64": "x64",
    "arm64": "arm64",
}


# llama.cpp binary directory
_BINARY_DIR = _ROOT / "bin"
_BINARY_DIR.mkdir(exist_ok=True)

# llama.cpp binary's zip file name
_BINARY_ZIP_NAME = "llama-{build}-bin-{system}-{arch}.zip".format(
    build=_LLAMA_CPP_BUILD,
    system=_SYSTEM_TO_FILE_NAME[platform.system()],
    arch=_ARCH_TO_FILE_NAME[platform.machine()],
)


# llama.cpp download url
_BINARY_URL = (
    "https://github.com/ggerganov/llama.cpp/releases/download/{build}/{file}".format(
        build=_LLAMA_CPP_BUILD,
        file=_BINARY_ZIP_NAME,
    )
)


# llama.cpp executable's name
_BINARY_FILE_NAME = {
    "Windows": "llama-cli.exe",
    "Linux": "llama-cli",
    "Darwin": "llama-cli",
}[platform.system()]


# --- Utilities ---


def _progressive_download(url: str, save_file: BinaryIO):
    """Progressively downloads and write into given io

    Raises:
        URLError: when url format is invalid

        HTTPError: when request is failed
    """

    cycler = itertools.cycle("-\\|/")

    with urlopen(url) as resp:
        resp: HTTPResponse

        # yep pathlib works for url too in some way, rather than urllib
        baked_msg = f"Downloading {pathlib.Path(url).name}"

        # prep progress meter; if size is 0 then disable it
        size = int(resp.headers["Content-Length"])
        get_progress_text = (
            (lambda: f"{int(100.0 * save_file.tell() / size):3}%")
            if size
            else (lambda: "")
        )

        while chunk := resp.read(524288):
            print(
                baked_msg,
                get_progress_text(),
                next(cycler),
                end="\r",
                flush=True,
            )
            save_file.write(chunk)

        print()


def _ensure_binary():
    """Makes sure the binary is downloaded and exists"""

    print("Checking for llama.cpp binary")

    # read version info. Assuming if file exists then it's not tempered.
    _content = _VER_INFO_FILE.read_text("utf-8").strip().splitlines()
    if _content:
        old_binary_os = _content[0]
        old_binary_build = _content[1]
    else:
        old_binary_os = ""
        old_binary_build = ""

    # check if it matches current
    if old_binary_os == platform.system() and old_binary_build == _LLAMA_CPP_BUILD:
        return

    print("Downloading new llama.cpp binary")

    # else remove existing binary
    for file in _BINARY_DIR.iterdir():
        file.unlink(missing_ok=True)

    # download binary - maybe we need no network check?
    zip_data = io.BytesIO()
    _progressive_download(_BINARY_URL, zip_data)

    # extract binary without subdir because only windows binary doesn't have it
    import zipfile

    with zipfile.ZipFile(zip_data, "r") as zip_ref:
        for zipped_file in zip_ref.namelist():

            # I'd save importing os just to get file name
            (_BINARY_DIR / pathlib.Path(zipped_file).name).write_bytes(
                zip_ref.read(zipped_file)
            )

    # write version info
    _VER_INFO_FILE.write_text(f"{platform.system()}\n{_LLAMA_CPP_BUILD}", "utf-8")


def _ensure_gguf(model_url: str):
    """Ensures the gguf file is downloaded and exists"""

    print("Checking for gguf file")

    model_name = pathlib.Path(model_url).name
    model_path = _GGUF_DIR / model_name

    # check if it exists
    if model_path.exists():
        return

    print("Downloading new gguf file")

    # download binary - maybe we need no network check?
    dl_path = model_path.with_suffix(".temp")
    with dl_path.open("wb") as dl_file:
        _progressive_download(model_url, dl_file)

    # if successful, rename
    dl_path.rename(model_path)


# --- Classes ---


class LlamaCppWrapper:
    """Simple wrapper for llama.cpp that only support oneshot prompt.

    Originally was intended to be used with -cnv flag but couldn't determine end of conversation
    so this is going to be one shot load - prompt - unload mess. Expect loading-unloading of model
    for each generation. I know this is bad but I don't have much time.
    """

    _ensure_binary()
    binary_path = _BINARY_DIR / _BINARY_FILE_NAME

    def __init__(self, model_url: str):

        model_name = pathlib.Path(model_url).name
        self.model_path = _GGUF_DIR / model_name

        # self.chat_format = chat_format.replace("{system_prompt}", system_prompt)

        _ensure_gguf(model_url)

        # print("Loading", model_name)

        # self.process: Union[asyncio.subprocess.Process, None] = None

    # async def ensure_process(self):
    #     """Ensure the process is created - unused now"""
    #
    #     if self.process is not None:
    #         return
    #
    #     self.process = await asyncio.create_subprocess_shell(
    #         f"{self.binary_path} {_LLAMA_CPP_PARAM} -m {self.model_path}",
    #         stdin=asyncio.subprocess.PIPE,
    #         stdout=asyncio.subprocess.PIPE,
    #         stderr=asyncio.subprocess.PIPE,
    #     )
    #
    #     # wait for load and initial messages
    #     while line := await self.process.stderr.readline():
    #         if b"Running in interactive mode" in line:
    #             break

    def generate_oneshot(self, prompt: str, *args) -> Iterator[str]:
        """Send oneshot request and yield output line by line

        Args:
            prompt: prompt to send
            *args: extra llama.cpp param strings, i.e. `-fa`, `-t 0.0`, `-c 512`, etc

        Yields:
            Generated obj line starting with either v or f.
        """

        process = subprocess.Popen(
            f'"{self.binary_path}" {_LLAMA_CPP_PARAM} {" ".join(args)} -m "{self.model_path}" -p "{prompt}"',
            stdout=subprocess.PIPE,
            # stderr=subprocess.PIPE,
            # ^^^ to suppress llama.cpp output
        )

        try:
            while line := process.stdout.readline():
                print(line.decode("utf-8"))
                yield line.decode("utf-8").strip()

            process.wait()

        finally:
            # print("Stopping. Output was\n", process.stderr.read().decode("utf-8"))
            process.kill()

        # await self.ensure_process()
        #
        # send prompt
        # self.process.stdin.write(
        #     # f"{self.chat_format.format(prompt=prompt)}\n".encode("utf-8")
        #     f"{prompt}\n".encode("utf-8")
        # )
        # await self.process.stdin.drain()
        #
        # # yield output per line
        # while line := await self.process.stdout.readline():
        #     yield line.decode("utf-8").strip()
        #
        # self.close()

    # def close(self):
    #     """Closes the process."""
    #
    #     if self.process is not None:
    #         print("Closing llama.cpp process")
    #
    #         self.process.kill()
    #         self.process = None


# --- Drivers ---


def _debug():

    print("IN DEBUG MODE")

    url = "https://huggingface.co/bartowski/LLaMA-Mesh-GGUF/resolve/main/LLaMA-Mesh-Q8_0.gguf"

    model = LlamaCppWrapper(url)
    try:
        # await model.ensure_process()

        while prompt := input("Prompt: "):
            print("[GEN START]")

            for line in model.generate_oneshot(prompt):
                print(line)

            print("[GEN END]\n")

    finally:
        pass
        # model.close()


if __name__ == "__main__":
    # asyncio.run(_debug())
    _debug()
