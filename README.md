# cs722 - Machine Learning 

## Course Project : Pixel Recurrent Neural Networks

by 

 Akshata Chalke (01116014)
 Prateek Keerthi (01119787)
 Herambeshwar Pendyala (01130541)


Directory Details
- code : for implementation and code
- report : for report
- presentation : for the presentation

Directory Contents
- presentation 
	- Pixel RNN - Final Presentation.pptx : presentation given in the class 
- report
	- cs722_report_final.pdf : report for the course project
- code 
	- cs722-pixelRNN-implemention.ipynb : main file to execute 
	- cs722-diagonalBiLSTM.ipynb : implementation of diagonal BiLSTM 
	- helpers : contains all the helper functions in 3 .py files
		- helpers.ops.py : contains all the helper functions for implementation of 2-D Convolution, 1-D convolution, bidirectionalLSTM, diagonal BiLSTM, skew, unskew.
		- helpers.utils.py : contains all the helper functions saving the image files, occlude, create and checking for directory, occludeing, masking, downloading and extracting a dataset.	
		- helpers.statistic.py : contains all the helper functions related to model_saving and model_loading.		
	- output : contains outputs from previous runs
	- run : result of main file is stored here
	- pixelRNN : outputs of diagonal BiLSTM are stored in this directory
	- logs : contains logs of main .ipynb file
	- MNIST-Data : Dataset Directory

***note*** : please do not delete any directory


Dependencies before executing below code
- ***Language*** : python 3.6 or above
- ***Libraries*** : tqdm, numpy, matplotlib, urllib, logging, pprint
- ***Framework*** : tensorflow v1.14

Steps to execute code on any machine
- ***All the dependencies mentioned above must be installed***
- Do not delete any directory.
- open jupyter notebook.
- open cs722-pixelRNN-implemention.ipynb and start executing each cell one after another to see the implementation of the project.
- open  cs722-diagonalBiLSTM.ipynb and start executing each cell one after another to see implementation of Diagonal BiLSTM.