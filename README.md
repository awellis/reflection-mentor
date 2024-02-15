# reflection-mentor

## Setup python environment

We're using a combination of miniconda and pip to manage the python environment.
First, install [miniconda](https://docs.conda.io/projects/miniconda/en/latest/)
as per the instructions on the website. 

`mamba` is a faster version of `conda` that we'll use to create the environment.


On Ubuntu, install `micromamba` using the following commands:


```bash
"${SHELL}" <(curl -L micro.mamba.pm/install.sh)
```

Then, create the environment using the following commands (using either `mamba` or `micromamba`):  

```python
mamba create --prefix env python=3.11 numpy pandas jupyter ipython
mamba activate ./env 
```
or 

```python
micromamba create --prefix env python=3.11 numpy pandas jupyter ipython
micromamba activate env 
```

Next, use `pip` to install the packages we need for the project.

```python
pip install -r requirements.txt
```

## Run chainlit app

```python
chainlit run app.py -h
```