# WEBM Converters

This is Dataloop's App that converts a video to a WEBM format.   

What is WEBM?:  
WEBM is an open, royalty-free, media file format designed for the web.

## How Does It Work?

The base class has the following methods:

* run (the main function)
* webm_converter
* _convert_to_webm_opencv
* _convert_to_webm_ffmpeg
* verify_webm_conversion
* validate_video

The user has to choose the converter method (opencv/ffmpeg).  
The function run starts by downloading the file and sending it to the converter function. 
This converts the file and saves it in the working directory. 
After that, it checks that the video is valid. If it is not valid, it will add info to the metadata
and at the end upload the file to the platform.

## Create App (Service)

Run the code in the file [deploy_webm](deploy_webm.py)


## Contribute

We welcome any type of contribution! For bug or feature requests please open an issue.
