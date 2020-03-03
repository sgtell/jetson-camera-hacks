#!/usr/bin/python
# MIT License
#
# camera-draw-save.py, by Steve Tell
# Based on JetsonHacks simple-camera.py
# Copyright (c) 2019 JetsonHacks
# See license
#
# Using a V4L2 camera or a CSI camera (such as the Raspberry Pi Version 2) connected to a
# NVIDIA Jetson Nano Developer Kit and using OpenCV,
# 
# attempt to stream video over the network.
#
# one should be able to view the stream with a gstreamer command like this:
#   gst-launch-1.0 -vvv -e udpsrc port=5805 ! application/x-rtp,encoding-name=JPEG,payload=26 ! rtpjpegdepay ! jpegdec ! autovideosink
#
# but I don't have it working yet
#

import cv2
import time
from PIL import ImageFont, ImageDraw, Image
import sys
import argparse
import os
import glob
import sre

localsave_frames = False;

# make python suck less
def printf(format, *args):
     """Format args with the first argument as format string, and print.
     If the format is not a string, it is converted to one with str.
     You must use printf('%s', x) instead of printf(x) if x might
     contain % or backslash characters."""
     sys.stdout.write(str(format) % args)
def fprintf(fp, format, *args): fp.write(str(format) % args)


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
#     printf("dirname=%s\n", dirname);
     os.mkdir(dirname);
     return dirname;

# get_pipeline_string returns a GStreamer pipeline string.
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

def get_write_pipeline_string(width=320,
                          height=200,
                          framerate=30,
                          bitrate=1000,
                          host="localhost",
                          port=5805):

    
#    return "appsrc ! video/x-raw, format=(string)BGR, width=(int)%d, height=(int)%d, framerate=(fraction)%d/1 ! videoconvert ! omxh264enc bitrate=%d ! video/x-h264, stream-format=(string)byte-stream ! h264parse ! rtph264pay ! udpsink host=%s port=%d" % (width, height, framerate, bitrate, host, port);
#    return "appsrc ! video/x-raw, format=(string)BGR, width=(int)%d, height=(int)%d, framerate=(fraction)%d/1 ! videoconvert ! jpegenc ! rtpjpegpay video/x-jpeg, stream-format=(string)byte-stream ! udpsink host=%s port=%d " % (width, height, framerate, host, port);
    return "appsrc ! videoconvert ! jpegenc ! rtpjpegpay ! udpsink host=%s port=%d " % (host, port);

def stream_camera(dirname, camsetup, host):
    framecount = 0;
    savecount = 0;
    
    # To flip the image, modify the flip_method parameter (0 and 2 are the most common)
    pipeline = get_pipeline_string(camsetup, flip_method=0);
    cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
    if not cap.isOpened():
        print("Unable to open camera " + pipeline)
        exit(1);

    wpipe = get_write_pipeline_string(640, 480, host=host);
    printf("write_pipeline=\"%s\n", wpipe);
    fourcc = cv2.VideoWriter_fourcc('M','J','P','G') 
#    strm = cv2.VideoWriter_GStreamer();
    strm = cv2.VideoWriter();
#    strm =  cv2.VideoWriter(wpipe, );
    strm.open(wpipe, fourcc, 30, (640, 480), True);
    t_start = time.time();
    t_done = 0;

    t_lastcap = 0;
    for i in range(0,2000):
            ret_val, img = cap.read()
            if(ret_val == 0):
                printf("capture %d failed retval=%d\n", framecount, ret_val);
                exit(2);
            #printf("cap retval=%d img=%s\n", ret_val, type(img));

            # get image dimensions and draw center crosshair
            shape = img.shape;
            img_width = shape[1]; 
            img_height = shape[0];
            if(framecount == 0):
                printf("capture %dx%d\n", img_width, img_height);
	    cv2.line(img,(img_height/2, 0),(img_height/2, img_width),(255,0,255),1)
	    cv2.line(img,(0, img_width/2),(img_height, img_width/2),(255,0,255),1)

            framecount += 1;

    	    strm.write(img);

            t_now = time.time();
            if(localsave_frames):
              if(framecount > 10 and (t_now - t_lastcap) > 3.0 ):
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
	parser.add_argument('host', metavar='H', type=str, nargs=1,
                   help='Host to stream to')
	args = parser.parse_args()
        camsetup = args.camsetup[0];
        dest_host = args.host[0];
        printf("camera setup %d; streaming to %s\n", camsetup, dest_host);

        if(localsave_frames):
 		dirname = get_next_image_dir();
        else:
           	dirname = "./";
	stream_camera(dirname, camsetup, dest_host);
