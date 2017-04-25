# weatherbot
Uses Open Weathermap API to give information about current weather at specified location.
Additionally uses NLTK to extract location from sentence.

It seems like NLTK does not recognize named entities if they aren't capitalized. 
Hence, using this approach is not really viable.

Usage:

Using a virtual environment is a good way to isolate the project: 

```python
apt-get install python-virtualenv / alternatively: pip install python-virtualenv
```

After installing virtualenv we can create a new environment, activate it and install all project dependencies:

```python
virtualenv NewEnvironment
source activate NewEnvironment
pip install slackclient
pip install pyowm
pip install nltk
```

Lastly, the app can be started using:

```python
python app.py
```

To deactivate and exit the environment:

```python
source deactivate
```

To remove it:

```python
rm -r NewEnvironment
```
