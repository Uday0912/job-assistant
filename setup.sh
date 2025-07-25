#!/bin/bash
pip install --upgrade pip
pip install -r requirements.txt

# Download and install spaCy model from wheel
wget https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl
pip install en_core_web_sm-3.7.1-py3-none-any.whl

# Link it to spaCy
python -m spacy link en_core_web_sm en_core_web_sm
