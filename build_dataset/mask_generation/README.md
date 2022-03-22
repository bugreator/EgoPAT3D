Egocentric Intent Dataset
===========
### ModelTraining.ipynb

The ModelTraining.ipynb file was written for use with Google Colaboratory. It uses <code>cv2</code> to load images from a directory of mask files and a directory of corresponding color images. Labels for training a model on pixel HSV values are prepared by giving the hand pixels a value of "1" and non-hand pixels a value of "0." A simple <code>scikit-learn RandomForestClassifier</code> is trained on the dataset and a <code>model.pkl</code> file for the model is created using <code>joblib.dump</code>.

### HandPrediction.py

<code>HandPrediction.py</code> is a script that loads <code>model.pkl</code> and uses <code>multiprocessing</code> to map a pool of workers to the <code>create_mask</code> function in <code>HandPredictionModel.py</code>. To do this, the names of all color frame images are put into a list with <code>fnmatch</code> and then used as an input for the <code>create_mask function</code> in <code>HandPredictionModel.py</code>. 

### HandPredictionModel.py

A mask is generated by the <code>create_mask</code> function using <code>model.pkl</code> and <code>pure-predict</code> (a Python package that makes <code>scikit-learn</code> models predict faster) to make predictions on images loaded by <code>cv2</code>. Pixels that are predicted to be hand pixels are colored white and pixels predicted to be non-hand pixels are black. A morphological opening operation (removing layers of pixels of regions followed by adding layers of pixels to the remaining regions) is used on the generated masks to reduce noise and leave mostly hand pixels in the produced image.

### Models

This folder contains the trained models in the format <code>scene_number.pkl</code>. 