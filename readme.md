# Figure Digitizer from a PDF
A hobby project to extract and digitize a figure in a pdf file, particularly a scientific paper.
Recent scientific papers contains vector graphic, i.e., the digital data.
Why don't you use this for your analysis?
# Requirement
It requires
+ numpy
+ pymupdf
+ pyqt5
+ pyqtwebengine

# Known problems
+ The selection position is disaligned from the actual figure
+ The scroll position is reset after every selection
+ Some markers are not recognized as a set of markers but a set of lines