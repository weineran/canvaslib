from optparse import OptionParser
import urllib2
import json
import os
import csv
import sys
import subprocess
#from autograde import get_file_local_or_full, get_dir_local_or_full
from download_submission import get_assignment_name_and_id


parser = OptionParser(usage="Usage: %prog [options]",
                      description="Download all students' submissions for a given assignment.")
parser.add_option("-c", "--course-id",
                  dest="course_id", default=None, type=int,
                  help="The Canvas course_id.  e.g. 43589")
parser.add_option("-a", "--assignment-name",
                  dest="assignment_name", default=None,
                  help="The name of the assignment to download.  e.g. 'proj4'")
parser.add_option("-i", "--assignment-id",
                  dest="assignment_id", default=None, type=int,
                  help="The Canvas assignment_id of the assignment to download.")
parser.add_option("-d", "--parent-directory",
                  dest="parent_directory", default="./",
                  help="The path to download the submissions to.  Each submission will be downloaded to a subdirectory "
                       "of the parent directory: <download_directory>/<netid>/<assignment_name>/")
parser.add_option("-r", "--roster",
                  dest="roster", default=None, type=str,
                  help="The path to a .csv file containing a class roster.  At a minimum, should have columns labeled "
                       "'netid' and 'user_id'.")
parser.add_option("-L", "--assignment_list",
                  dest="assignment_list", default=None, type=str,
                  help="The path to a .csv file containing a list of assignments.  At a minimum, should have columns labeled "
                       "'assignment_name' and 'assignment_id'.")
parser.add_option("-t", "--token-json-file",
                  dest="token_json_file", default=None, type=str,
                  help="The path to a .json file containing the Canvas authorization token.")


def get_or_make_directory(parent_directory, subdirectory):
    assert os.path.isdir(parent_directory), "parent_directory is not a directory: %s" % parent_directory

    target_directory = os.path.join(parent_directory, subdirectory)
    if os.path.isdir(target_directory):
        return target_directory
    else:
        os.mkdir(target_directory, 0755)
        return target_directory

if __name__ == "__main__":
    (options, args) = parser.parse_args()

    course_id = options.course_id
    assert isinstance(course_id, int), "course_id is not an int: %s" % course_id

    script_dir = os.path.dirname(os.path.realpath(__file__))

    #token_json_file = get_file_local_or_full(script_dir, options.token_json_file)
    token_json_file = options.token_json_file
    assert os.path.isfile(token_json_file), "token_json_file is not a file: %s" % token_json_file

    #roster_file = get_file_local_or_full(script_dir, options.roster)
    roster_file = options.roster
    assert os.path.isfile(roster_file), "roster_file is not a file: %s" % roster_file

    #parent_directory = get_dir_local_or_full(script_dir, options.parent_directory)
    parent_directory = options.parent_directory
    assert os.path.isdir(parent_directory), "parent_directory is not a directory: %s" % parent_directory

    #assignment_list = get_file_local_or_full(script_dir, options.assignment_list)
    assignment_list = options.assignment_list
    assert os.path.isfile(assignment_list), "assignment_list is not a file: %s" % assignment_list

    assignment_name = options.assignment_name
    assignment_id = options.assignment_id

    assignment_name, assignment_id = get_assignment_name_and_id(assignment_name, assignment_id, assignment_list)

    plist = {}
    with open(roster_file) as csvfile:
        reader = csv.DictReader(csvfile)
        for student in reader:
            user_id = student["user_id"]
            netid = student["netid"]

            if len(netid) < 1 or len(user_id) < 1:
                continue

            netid_directory = get_or_make_directory(parent_directory, netid)
            assignment_directory = os.path.join(netid_directory, assignment_name)

            print("downloading submission for netid: " + netid)
            p = subprocess.Popen(["python", "download_submission.py",
                                  "-c", str(course_id),
                                  "-a", assignment_name,
                                  "-i", str(assignment_id),
                                  "-u", user_id,
                                  "-n", netid,
                                  "-r", roster_file,
                                  "-L", assignment_list,
                                  "-d", assignment_directory,
                                  "-t", token_json_file])
            plist[netid] = p

    for netid in plist:
        p = plist[netid]
        p.wait()
        print(netid + " " + str(p.returncode))


