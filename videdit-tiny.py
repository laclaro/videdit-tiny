#!/usr/bin/python3

import os
import sys
import subprocess
import argparse
import datetime

ffmpeg_bin = "/usr/bin/ffmpeg"
ffmpeg_default_opts=["-c:a", "aac", "-crf", "19"]

__author__ = "Henning Hollermann"
__email__ = "laclaro@mail.com"
__version__ = "04/2020"
__license__ = "http://creativecommons.org/licenses/by-nc-sa/3.0/"
__usage__ = "{0} is a script to faciliate certain frequently ocurring video editing \
and conversion tasks. Use --help for more info.".format(os.path.basename(sys.argv[0]))

parser = argparse.ArgumentParser()
parser.add_argument("--cut", action="store_true", help="Cut time")
parser.add_argument("--scale", action="store_true", help="Video Resolution")
parser.add_argument("--rotate", action="store_true", help="Rotate")
parser.add_argument("-i", "--inputfile", required=True, action='append', help="Add input video file")
parser.add_argument("-v", "--version",dest = "version", help="Version")

scalegroup = parser.add_argument_group('scale')
scalegroup.add_argument("-r", action='append', default=["720"], choices=["1080","720","540","320"], help="Add output video resolution")

rotategroup = parser.add_argument_group('rotate')
rotategroup.add_argument("-R", choices=["CCWFlip", "90", "-90", "CWFlip"], help="Rotate video")

cutgroup = parser.add_argument_group('cut')
cutgroup.add_argument("-ss", default="00:00:00", help="Starting time in format hh:mm:ss to cut from.")
cutgroup.add_argument("-to", help="End time in format hh:mm:ss to cut to.")


def run_ffmpeg(source,target,args):
    subprocess.check_call([ffmpeg_bin, '-i', source, *args, target ])

def sync_metadata(sourcefile,targetfile):
    tags_to_copy=[]
    subprocess.check_call(['exiftool', '-overwrite_original', '-x', 'Image Size', '-tagsFromFile', sourcefile, targetfile])
    # mtime = os.stat(sourcefile).st_mtime
    timestamp = datetime.datetime.fromtimestamp(os.path.getmtime(sourcefile)).strftime('%Y-%m-%d %H:%M:%S')
    subprocess.check_call(['touch', '-d', timestamp, targetfile])

def scale():
#    scaleparser = parser.add_subparsers()
#    scaleparser.add_argument("-r", action='append', default=["720"], choices=["1080","720","540","320"], help="Add output video resolution")
#    scaleparser.add_argument("-i", "--inputfile", required=True, action='append', help="Add input video file")
#    args = scaleparser.parse_args(args)
    scale_filter={"1080":["scale=iw:ih"], 
                  "720": ["scale=iw/3*2:ih/3*2"],
                  "540": ["scale=iw/2:ih/2"],
                  "320": ["scale=iw/3:ih/3"]}
    # drop duplicate resolutions
    args.r = list(set(args.r))

    return [scale_filter[res] for res in args.r]

#    for file in args.inputfile:
#        for res in args.r:
#            print(args.inputfile)
#            targetfile = os.path.splitext(file)[0] + '_' + res + 'p' + '.mp4'
#            run_ffmpeg(file,targetfile,[*scale_filter[res],*ffmpeg_default_opts])
#            sync_metadata(file,targetfile)

def mp4():
    pass

def aac():
    """ Convert audio to aac
    """
    pass

def rotate():
#    rotateparser = parser.add_subparsers()
#    rotateparser.add_argument("-R", destination="angle",default=["CCWFlip"], help="Rotate video")
##    parser.add_argument("-i", "--inputfile", required=True, action='append', help="Add input video file")
#    args = rotateparser.parse_args(args)
    transpose={"CCWFlip":"0",
               "90":"1",
               "-90":"2",
               "CWFlip":"3"}
    if not args.R:
        raise SyntaxError("--rotate requires -R")
    else:
        return [("transpose={}".format(transpose[args.R[0]]))]

def cut():
#    cutparser = parser.add_subparsers()
#    cutparser.add_argument("-ss", default="00:00:00", help="Starting time in format hh:mm:ss to cut from.")
#    cutparser.add_argument("-to", required=True, help="End time in format hh:mm:ss to cut to.")
#    parser.add_argument("-i", "--inputfile", required=True, action='append', help="Add input video file")
#    args = cutparser.parse_args()
    if not args.to:
        raise SyntaxError("--cut requires -to hh:mm:ss")
    else:
        print(args.to)

    return ["-ss", args.ss, "-to", args.to]
    


if __name__ == '__main__':

    # if no argument given, display usage
    if len(sys.argv) == 1:
        print(__usage__)
        sys.exit()

    args = parser.parse_args()

#    commands = {'scale': scale(sys.argv[1:])
#    }
#    commands[sys.argv[0]]

    ffmpeg_args = ['map_metadata', '0']

    cutopts=""
    rotateopts=""
    scaleopts=""
    if args.cut:
        print(args.cut)
        cutopts = cut()
        ffmpeg_args.append(*cutopts)

    if args.rotate:
        rotateopts = rotate()

    if args.scale:
        scaleopts = scale()

#    if args.rotate or args.scale:
#        ffmpeg_args.append('-filter:v',*rotateopts,*ffmpeg_default_opts)

    print(cutopts,rotateopts,scaleopts)

    
