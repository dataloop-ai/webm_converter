# WEBM Converters

This is a Dataloop App that convert a videos to a webm format   

What is webm:  
WebM is an open, royalty-free, media file format designed for the web.

## How This Works 

The base class has the following methods:

* run (the main function)
* webm_converter
* _convert_to_webm_opencv
* _convert_to_webm_ffmpeg
* verify_webm_conversion
* validate_video

the user have to choose the converter method (opencv/ffmpeg)  
the function run start by download the file and send it to the converter function 
that convert the file and save it in the working directory 
after that checking the video that is valid, if it is not valid will add an info to the metadata
and at the end upload the file to the platform

## Create App (Service)

run the code in the file [deploy_webm](deploy_webm.py)


## Contribute

We welcome any type of contribute! For bug or feature requests please open an issue.