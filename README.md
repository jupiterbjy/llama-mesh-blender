# llama-mesh-blender

WARNING: This is SEVERELY slow and quality is REAL BAD. Fix is on the way(sorta)


Simple mesh generation addon using Quantized LLaMA-Mesh, with zero python package dependencies,  
because not everyone have time to compile from source & download cublas, just to get disappointed!

<sup>(hence I neglected all the optimization)</sup>

## Usage

download [llama-mesh-blender.zip](llama-mesh-blender.zip) in this repo & install in blender.

Menu is added at `Add > Mesh > Generate Mesh`.

On first prompt this will download matching llama.cpp binaries from [llama.cpp](https://github.com/ggerganov/llama.cpp),
download Q8 LLaMA-Mesh model from [huggingface](https://huggingface.co/bartowski/LLaMA-Mesh-GGUF) so be patient!
