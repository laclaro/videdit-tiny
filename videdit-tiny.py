#!/usr/bin/python3

import os
import sys
import subprocess
import argparse
import datetime

ffmpeg_bin = "/usr/bin/ffmpeg"
ffprobe_bin = "/usr/bin/ffprobe"
exiftool_bin = "/usr/bin/exiftool"
ffmpeg_default_opts = ["-c:a", "aac", "-crf", "19"]
ffmpeg_quick_opts = ["-c:a", "aac", "-crf", "30"]
timeshift = "02:00"

__author__ = "Henning Hollermann"
__email__ = "laclaro@mail.com"
__version__ = "04/2020"
__license__ = "http://creativecommons.org/licenses/by-nc-sa/3.0/"
__usage__ = "{0} is a script to faciliate certain frequently ocurring video editing \
and conversion tasks. Use --help for more info.".format(os.path.basename(sys.argv[0]))

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--inputfile", required=True, action='append', 
                        help="Add input video file")
parser.add_argument("--quick", default=False, action='store_true', 
                        help="Quick mode: copy audio, use fast compression")
parser.add_argument("--dry", default=False, action='store_true', 
                        help="Do not execute commands, print only.")
parser.add_argument("--overwrite", default=False, action='store_true', 
                        help="Overwrite existing files.")
parser.add_argument("--rename", default=False, action='store_true', 
                        help="Rename output video based on image file from given imagedir "
                        "with the closest timestamp")
parser.add_argument("--imagedir", default="./", 
                        help="Directory with image files to guess the file name "
                        "for the video from the exif metadata.")
parser.add_argument("-v", "--version", action='store_true', help="Print version")

actionsgroup = parser.add_argument_group('ACTIONS')
actionsgroup.add_argument("--cut", action="store_true", help="Cut video")
actionsgroup.add_argument("--fade", default=True, action="store_true", 
                            help="Fade in video and fade out video. Default: 0.4 s")
actionsgroup.add_argument("--scale", action="store_true", 
                            help="Change video resolution encoding as mp4")
actionsgroup.add_argument("--transpose", choices=["CCWFlip", "90", "-90", "180", "CWFlip"],
                            help="Transpose or rotate video")
actionsgroup.add_argument("--mp4", action="store_true", 
                            help="Only encode input video files as mp4. This overrides " 
                            "cut, scale, fade and transpose.")

scalegroup = parser.add_argument_group('Arguments to --scale')
scalegroup.add_argument("-s", action='append', choices=["66","50","33", "720", "540", "320"], 
                            help="Add output video resolution. Default: 66%% (720p for HD input video)")

fadegroup = parser.add_argument_group('Arguments to --fade')
fadegroup.add_argument("-fadetime", default="0.3", 
                            help="Time to fadein and fadeout video. Default: 0.3 sec")
fadegroup.add_argument("-fadeblack", default="0.1", 
                            help="Time to delay fade, creating black time at "
                            "the beginning and the end of the video. Default: 0.1 sec")

cutgroup = parser.add_argument_group('Arguments to --cut')
cutgroup.add_argument("-ss", default="00:00:00", help="Starting time in seconds or in "
                            "format hh:mm:ss to cut from. Default: video beginning")
cutgroup.add_argument("-to", default="end", help="End time in format hh:mm:ss to cut to.")


def convert(source,target,arguments):
    """
    Convert video file based on the options passed to the script. In dry-mode
    this function only prints the ffmpeg command.
    """
    if args.quick:
        ffmpeg_arguments = arguments + ffmpeg_quick_opts
    else:
        ffmpeg_arguments = arguments + ffmpeg_default_opts
        
    if args.dry:
        print(ffmpeg_bin,'-i', source, *arguments, target)
    else:
        subprocess.check_call([ffmpeg_bin,'-i', source, *arguments, target])
        copy_timstamps(source,target)


def copy_timstamps(sourcefile,targetfile):
    """
    This function uses exiftool and the datetimeoriginal of the source file to set the 
    modification time and the exif datetimeoriginal of the target file
    """
    exclude_tags=["--ImageSize", "--ImageWidth","--ImageHeight"]
    subprocess.check_call([exiftool_bin, '-ee', '-overwrite_original', '-tagsFromFile', 
                sourcefile, *exclude_tags, targetfile])
    subprocess.check_call([exiftool_bin, '-overwrite_original', '-DateTimeOriginal<${datetimeoriginal}+'+timeshift,
                targetfile])
    timestamp = subprocess.check_output(exiftool_bin + " -DateTimeOriginal -S -s -d \'%Y-%m-%d %H:%M:%S%z\' " + sourcefile,
                  shell=True)
    subprocess.check_call(['touch', '-d', timestamp, targetfile])


def get_small_edge(file):
    """Use ffprobe to determine the length video's short edge"""
    vidsize = subprocess.check_output(ffprobe_bin + " -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 " + file, 
                shell=True)
    size = vidsize.decode("utf-8").split("\n")[0].split("x")
    l = [int(i) for i in size]
    return min(l)

def get_duration(file):
    """Use ffprobe to determine the duration of a video file"""
    duration = subprocess.check_output(ffprobe_bin + " -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 " + file,
                shell=True)
    return duration

def get_timestr(seconds):
    """Construct hh:mm:ss string from seconds."""
    return str(datetime.timedelta(seconds=float(seconds)))

def get_sec(time_str):
    """Get seconds from time string hh:mm:ss"""
    h, m, s = time_str.split(':')
    return int(h) * 3600 + int(m) * 60 + float(s)

def check_inputfile_exists():
    """Check if all input files exist, returns True on success"""
    all_exist = True
    for file in args.inputfile:
        if not os.path.isfile(file):
            print("No such file '{}'".format(file), file=sys.stderr)
            all_exist = False
    return all_exist

def get_closest_filepath(file,tolerance=300):
    """Uses exiftool to find the file with the closest exif timestamp compared to the input video file"""
    vid_timestamp = int(subprocess.check_output(exiftool_bin + " -datetimeoriginal -S -s -d %s -T " + file, 
                    shell=True).decode("utf-8").split("\n")[0])
    image_table = subprocess.check_output(exiftool_bin + " -filepath -datetimeoriginal " 
                    "-S -s -r -d %s -T -if \'$mimetype =~ m\"^image/[^x]\"\' " + args.imagedir, 
                    shell=True).decode("utf-8").split("\n")
    files = [item.split("\t")[0] for item in image_table if item]
    times = []
    for item in image_table:
        if item:
            try:
                times.append(int(item.split("\t")[1]))
            except:
                times.append(0)
    time_diff = [abs(time-vid_timestamp) for time in times]
    min_time_diff = min(time_diff)
    image_closest_time = time_diff.index(min_time_diff)
    if min_time_diff > tolerance:
        print("Warning: No related file found for file {} using the one with the closest "
        "timestamp ({} seconds):\n{}".format(file,min_time_diff,files[image_closest_time]))
    return files[image_closest_time]


def scale():
    """construct multiple scale filter:v according to -s scale arguments"""
    scale_filter={"66": "scale=iw/3*2:ih/3*2",
                  "50": "scale=iw/2:ih/2",
                  "33": "scale=iw/3:ih/3",
                  "720": "scale=iw/3*2:ih/3*2",
                  "540": "scale=iw/2:ih/2",
                  "320": "scale=iw/3:ih/3"}
    if not args.s:
        print("Warning: --scale without resolution given. Use 66%.")
        args.s = ["720"]
    if any(s in ["720", "540", "320"] for s in args.s):
        print("An absolute resolution was given. This script will interpret it as <given res.>/1080.") 
    # drop duplicate resolutions
    args.s = list(set(args.s))
    # return subset of scale_filter dictionary
    return {r: scale_filter[r] for r in args.s}


def transpose():
    """Construct transpose filter"""
    transpose={"CCWFlip":"transpose=0",
               "90":"transpose=1",
               "-90":"transpose=2",
               "180":"transpose=2,transpose=2",
               "CWFlip":"transpose=3"}
    return transpose[args.transpose]


def cut():
    """Return cut video arguments"""
    if not ':' in args.ss:
        args.ss = get_timestr(float(args.ss))
    if not args.to:
        arg.to="end"
    elif not ':' in args.to:
        args.to = get_timestr(float(args.to))
    return ["-ss", args.ss, "-to", args.to]


def fade(file):
    """Construct fade filter filter:v and filter:a"""
    d_in = d_out = round(float(args.fadetime),2)
    black = round(float(args.fadeblack),2)
    if args.cut:
        st_in=black+get_sec(args.ss)
        st_out=round(get_sec(args.to)-d_out-black,2)
    else:
        duration = get_duration(file)
        st_in=0
        st_out=round(float(duration)-d_out,2)
    fade_filter_a = "afade=in:st={0}:d={1},afade=out:st={2}:d={3}".format(st_in,d_in,st_out,d_out)
    fade_filter_v = "fade=in:st={0}:d={1},fade=out:st={2}:d={3}".format(st_in,d_in,st_out,d_out)
    return [fade_filter_v,fade_filter_a]


def main():
    ffmpeg_args = ['-map_metadata', '0', '-movflags', 'use_metadata_tags']
    ffmpeg_filter_v = {}
    ffmpeg_filter_a = []
    cutopts=""
    transpose_filter=""
    outid = ""
    scale_filter={"100":""}

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

    if args.fade:
        filter_v = True
        filter_a = True
    
    # for rotate and scale we compose a filter:v string 
    if filter_v:
        if args.scale:
            res_list = args.s
        else:
            # res_list 100 means: "do not scale at all" (returns empty filter)
            res_list = ["100"]
        for r in res_list:
            ffmpeg_filter_v[r] = ['-filter:v',','.join([transpose_filter,scale_filter[r]]).strip(",")]
    
    for file in args.inputfile:
        # use exiftool to get the file with the closest timestamp
        closest_filepath = get_closest_filepath(file)
        # if mp4 is specified, do nothing else
        if args.mp4:
            outfile = os.path.splitext(file)[0] + outid + '.mp4'
            suggested_outfile = os.path.splitext(closest_filepath)[0] + '_' + os.path.basename(outfile)
            if args.rename:
                outfile = suggested_outfile
            else:
                print("Tip: You could rename the file manually to {} or set the --rename flag.".format(suggested_outfile))
            convert(file,outfile,ffmpeg_args)
        else:
            # process cut options
            # if args.to was not given, set it to the end of the file
            if args.cut and args.to == "end":
                args.to = get_timestr(get_duration(file))
                ffmpeg_args[-1] = args.to
            if filter_v:
                # construct the fade video and audio filters
                fade_filter_v,fade_filter_a = fade(file)
                if args.fade:
                    ffmpeg_filter_a = ['-filter:a',fade_filter_a]
                # scaling filters and output file names are adjusted for every chosen resolution
                for r in ffmpeg_filter_v.keys():
                    outfile = file + outid + "_" + r + '.mp4'
                    suggested_outfile = os.path.splitext(closest_filepath)[0] \
                                            + '_' + os.path.basename(outfile)
                    if args.rename:
                        outfile = suggested_outfile
                    else:
                        print("Tip: You could rename the file manually to {} or set the --rename flag.".format(suggested_outfile))
                    if args.fade:
                        ffmpeg_filter_v[r][1] = ",".join([ffmpeg_filter_v[r][1],fade_filter_v]).strip(",")
                    
                    # run ffmpeg (only prints command in DRY mode)
                    convert(file,outfile,ffmpeg_args + ffmpeg_filter_v[r] + ffmpeg_filter_a)


if __name__ == '__main__':

    # if no argument given, display usage and exit
    if len(sys.argv) == 1:
        print(__usage__)
        sys.exit()

    # process command line arguments
    args = parser.parse_args()
    
    # exit if an input file does not exist
    if not check_inputfile_exists():
        sys.exit()
    
    # run the script
    if args.dry:
        print("Running in DRY mode, so not changing any files.")
    main()
