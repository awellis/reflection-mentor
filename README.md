# reflection-mentor

## Setup python environment

We're using a combination of miniforge and pip to manage the python environment.
`mamba` is a faster version of `conda` that we'll use to create the environment.

On MacOS/Linux, install `miniforge` using the following commands:


```bash
curl -L -O "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh"
bash Miniforge3-$(uname)-$(uname -m).sh
```

Then, `cd` into `reflection-mentor`. Create an environment using `mamba` and activate it. 
 
```shell
cd reflection-mentor
```

```shell
mamba create --prefix env python=3.11
```
    
```shell
mamba activate ./env 
```

Next, use `pip` to install the packages we need for the project.

```shell
pip install -r requirements.txt
```

## Run chainlit app

```shell
chainlit run app.py -h
```
