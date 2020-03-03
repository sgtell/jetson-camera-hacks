#!/usr/bin/python
# MIT License
#
# camera-draw-save.py, by Steve Tell
# Based on JetsonHacks simple-camera.py
# Copyright (c) 2019 JetsonHacks
# See license
#
# Using a USB/V4L2 camera or a CSI camera (such as the Raspberry Pi Version 2) connected to a
# NVIDIA Jetson Nano Developer Kit using OpenCV, demonstrate how to
# capture frames, draw lines on them, and save some of them to a file
#

import cv2
import time
from PIL import ImageFont, ImageDraw, Image
import sys
import argparse
import os
import glob
import sre

def printf(format, *args):
     """Format args with the first argument as format string, and print.
     If the format is not a string, it is converted to one with str.
     You must use printf('%s', x) instead of printf(x) if x might
     contain % or backslash characters."""
     sys.stdout.write(str(format) % args)
def fprintf(fp, format, *args): fp.write(str(format) % args)

# make the next numbered directory in which to store image files
# TODO: find a mounted usb stick on which to put them,
# instead of current directory
def get_next_image_dir():
     dnbase = "./imgs";
     lst = glob.glob(dnbase + '-[0-9][0-9][0-9][0-9]');
     if(lst):
            lst.sort();
            print lst
            last = lst[ len(lst)-1 ];
            m = sre.search(sre.compile(dnbase + "-(\d+)$"), last);
            nlast = int(m.group(1))
            fno = nlast + 1;
     else:
            fno = 1;
     dirname = (dnbase + "-%04d") % (fno);
     printf("dirname=%s\n", dirname);
     os.mkdir(dirname);
     return dirname;

# get_pipeline_string - returns a GStreamer pipeline string.
def get_pipeline_string(
          camsetup=0,
    capture_width=1280,
    capture_height=720,
    display_width=1280,
    display_height=720,
    framerate=60,
    flip_method=0,
):
    if(camsetup == 0):
	# pipeline for capturing from the CSI camera
	# Defaults to 1280x720 @ 60fps
	# Flip the image by setting the flip_method (most common values: 0 and 2)
	# display_width and display_height determine the size of the window on the screen
	return (
        "nvarguscamerasrc ! "
        "video/x-raw(memory:NVMM), "
        "width=(int)%d, height=(int)%d, "
        "format=(string)NV12, framerate=(fraction)%d/1 ! "
        "nvvidconv flip-method=%d ! "
        "video/x-raw, width=(int)%d, height=(int)%d, format=(string)BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=(string)BGR ! appsink"
        % (
            capture_width,
            capture_height,
            framerate,
            flip_method,
            display_width,
            display_height,
        )
        );
    elif(camsetup == 1):
	return "v4l2src device=/dev/video1 ! videoconvert ! appsink";


def show_camera(dirname, camsetup):
    framecount = 0;
    savecount = 0;
    
    # To flip the image, modify the flip_method parameter (0 and 2 are the most common)
    pipeline = get_pipeline_string(camsetup, flip_method=0);
    cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
    if not cap.isOpened():
        print("Unable to open camera " + pipeline)
        exit(1);
        
    t_start = time.time();
    t_done = 0;

    t_lastcap = 0;
    for i in range(0,300):
            ret_val, img = cap.read()
            if(ret_val == 0):
                printf("capture %d failed retval=%d\n", framecount, ret_val);
                exit(2);
            #printf("cap retval=%d img=%s\n", ret_val, type(img));

            # get image dimensions and draw center crosshair
            shape = img.shape;
            img_width = shape[0]; 
            img_height = shape[1]; 
	    cv2.line(img,(img_height/2, 0),(img_height/2, img_width),(255,0,255),1)
	    cv2.line(img,(0, img_width/2),(img_height, img_width/2),(255,0,255),1)

            framecount += 1;

            t_now = time.time();
            if(framecount > 10 and (t_now - t_lastcap) > 1.0 ):
                 # skip the first few frames, then save one per second
	            savecount += 1;
	 	    save_fname = "%s/img-%04d.jpg" % (dirname, savecount);
	 	    cv2.imwrite(save_fname,img);
                    printf("saved %s\n", save_fname);
                    t_lastcap = t_now;
            
    t_done = time.time();
    t_total = t_done - t_start;
    print("%d frames in %.3f seconds; %.3f/sec\n"%(framecount, t_total, framecount/t_total));
    cap.release()

    

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="camera demo");
	parser.add_argument('camsetup', metavar='C', type=int, nargs=1, default=0,
                   help='select one of our supported camera setups')
	args = parser.parse_args()
        camsetup = args.camsetup[0];
        printf("camera setup %d\n", camsetup);

        dirname = get_next_image_dir();
	show_camera(dirname, camsetup);
