#!/usr/bin/python3

import os
import sys
import subprocess
import argparse
import datetime

ffmpeg_bin = "/usr/bin/ffmpeg"
ffmpeg_default_opts = ["-c:a", "aac", "-crf", "19"]
ffmpeg_quick_opts = ["-c:a", "copy", "-crf", "25"]
timeshift = 2

__author__ = "Henning Hollermann"
__email__ = "laclaro@mail.com"
__version__ = "04/2020"
__license__ = "http://creativecommons.org/licenses/by-nc-sa/3.0/"
__usage__ = "{0} is a script to faciliate certain frequently ocurring video editing \
and conversion tasks. Use --help for more info.".format(os.path.basename(sys.argv[0]))

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--inputfile", required=True, action='append', help="Add input video file")
parser.add_argument("--quick", default=False, action='store_true', help="Quick mode: copy audio, use fast compression")
parser.add_argument("--overwrite", default=False, action='store_true', help="Overwrite existing files.")
parser.add_argument("-v", "--version", action='store_true', help="Print version")

actionsgroup = parser.add_argument_group('ACTIONS')
actionsgroup.add_argument("--cut", action="store_true", help="Cut video")
actionsgroup.add_argument("--scale", action="store_true", help="Change video resolution encoding as mp4")
actionsgroup.add_argument("--mp4", action="store_true", help="Encode input video files as mp4. This overrides cut, scale and transpose.")
actionsgroup.add_argument("--transpose", choices=["CCWFlip", "90", "-90", "180", "CWFlip"], help="Transpose or rotate video")

scalegroup = parser.add_argument_group('Arguments to --scale')
scalegroup.add_argument("-s", action='append', choices=["66","50","33", "720", "540", "320"], help="Add output video resolution")

cutgroup = parser.add_argument_group('Arguments to --cut')
cutgroup.add_argument("-ss", default="00:00:00", help="Starting time in format hh:mm:ss to cut from. Default: video beginning")
cutgroup.add_argument("-to", help="End time in format hh:mm:ss to cut to.")


def run_ffmpeg(source,target,arguments):
    if args.quick:
        print(ffmpeg_bin,'-i', source, *arguments, *ffmpeg_quick_opts, target)
        subprocess.check_call([ffmpeg_bin,'-i', source, *arguments, *ffmpeg_quick_opts, target])
    else:
        print(ffmpeg_bin,'-i', source, *arguments, *ffmpeg_default_opts, target)
        subprocess.check_call([ffmpeg_bin,'-i', source, *arguments, *ffmpeg_default_opts, target])

def get_small_edge(file):
    vidsize = subprocess.check_output(" ".join(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", file]), 
                shell=True)
    size = vidsize.decode("utf-8").split("\n")[0].split("x")
    l = [int(i) for i in size]
    return min(l)


def sync_metadata(sourcefile,targetfile):
    exclude_tags=["--ImageSize", "--ImageWidth","--ImageHeight"]
    subprocess.check_call(['exiftool', '-ee', '-overwrite_original', '-tagsFromFile', sourcefile, *exclude_tags, targetfile])
    # timezone shift required?
    # subprocess.check_call(['exiftool',        '-overwrite_original', '-datetimeoriginal+={}'.format(timeshift), targetfile])
    timestamp = datetime.datetime.fromtimestamp(os.path.getmtime(sourcefile)).strftime('%Y-%m-%d %H:%M:%S')
    subprocess.check_call(['touch', '-d', timestamp, targetfile])

def scale():
    scale_filter={"66": "scale=iw/3*2:ih/3*2",
                  "50": "scale=iw/2:ih/2",
                  "33": "scale=iw/3:ih/3",
                  "720": "scale=iw/3*2:ih/3*2",
                  "540": "scale=iw/2:ih/2",
                  "320": "scale=iw/3:ih/3"}
    if not args.s:
        print("Warning: --scale without resolution given. Use 66%.")
        args.s = ["66"]
    if any(s in ["720", "540", "320"] for s in args.s):
        print("An absolute resolution was given. This script will interpret it as <given res.>/1080.") 
    # drop duplicate resolutions
    args.s = list(set(args.s))
    # return subset of scale_filter dictionary
    return {r: scale_filter[r] for r in args.s}

def transpose():
    transpose={"CCWFlip":"transpose=0",
               "90":"transpose=1",
               "-90":"transpose=2",
               "180":"transpose=2,transpose=2",
               "CWFlip":"transpose=3"}
    return transpose[args.transpose]

def cut():
    if not args.to:
        raise SyntaxError("--cut requires -to hh:mm:ss")
    return ["-ss", args.ss, "-to", args.to]

if __name__ == '__main__':

    # if no argument given, display usage
    if len(sys.argv) == 1:
        print(__usage__)
        sys.exit()

    args = parser.parse_args()

    ffmpeg_args = ['-map_metadata', '0', '-movflags', 'use_metadata_tags']
    ffmpeg_filter_v = {}
    cutopts=""
    transpose_filter=""
    outid = ""
    scale_filter={}

    if args.cut:
        cutopts = cut()
        outid = outid + "_cut"
        ffmpeg_args.extend(cutopts)

    if args.scale:
        filter_v = True
        scale_filter = scale()
    
    if args.transpose:
        filter_v = True
        outid = outid + "_" + args.transpose
        transpose_filter = transpose()

    if args.quick:
        outid = outid + "_quick"

    # for rotate and scale we compose a filter:v string 
    if filter_v:
        if args.scale:
            res_list = args.s
        else:
            res_list = 1
        for r in res_list:
            ffmpeg_filter_v[r] = ['-filter:v',','.join([transpose_filter,scale_filter[r]]).strip(",")]
    
    for file in args.inputfile:
        # if mp4 is specified, do nothing else
        if args.mp4:
            outfile = file + ".mp4"
            run_ffmpeg(file,outfile,ffmpeg_args)
            sync_metadata(file,outfile)
        elif filter_v:
            for r in ffmpeg_filter_v.keys():
                outfile = file + "_" + r + outid + '.mp4'
                run_ffmpeg(file,outfile,ffmpeg_args + ffmpeg_filter_v[r])
                sync_metadata(file,outfile)
                new_outfile = outfile.replace(r,str(get_small_edge(outfile)))
                if not os.path.exists(new_outfile) or args.overwrite:
                    os.rename(outfile,new_outfile)
                else:
                    print("Error: not renaming {} to {}. File exists.".format(outfile,new_outfile))
