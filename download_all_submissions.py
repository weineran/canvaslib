from optparse import OptionParser
import os
import subprocess
from utils import get_token, download_all_objects_to_list, get_assignment_name_and_id, get_netid_from_user_id, \
                  build_canvas_url, make_new_directory, write_to_log
import sys


parser = OptionParser(usage="Usage: %prog [options]",
                      description="Download all students' submissions for a given assignment.  Not all arguments are "
                                  "required.  For example, try:                                                  "
                                  "$ python " + __file__ + " -c <course_id> -a <assignment_name>")
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
                  dest="parent_directory", default="submissions/",
                  help="The path to download the submissions to.  Each submission will be downloaded to a subdirectory "
                       "of the parent directory: <parent_directory>/<netid>/<assignment_name>/")
parser.add_option("-o", "--download-filename",
                  dest="download_filename", default=None, type=str,
                  help="The name to give the downloaded files.  If omitted, the name of each student's uploaded file "
                       "will be used.")
parser.add_option("-m",
                  dest="make_assignment_directory", action="store_true", default=False,
                  help="If the directory <assignment_name> doesn't exist, should it be created?")
parser.add_option("-v", "--verbose",
                  dest="verbose", action="store_true", default=False,
                  help="Should additional output be printed?")


def get_or_make_directory(parent_directory, subdirectory):
    assert os.path.isdir(parent_directory), "parent_directory is not a directory: %s" % parent_directory

    target_directory = os.path.join(parent_directory, subdirectory)
    if os.path.isdir(target_directory):
        return target_directory
    else:
        os.mkdir(target_directory, 0755)
        return target_directory


def build_submissions_url(course_id, assignment_id, page_num):
    api_subdirectories = ["courses", course_id, "assignments", assignment_id, "submissions"]
    params = {"page_num": page_num}
    url = build_canvas_url(api_subdirectories, params)

    return url


if __name__ == "__main__":
    (options, args) = parser.parse_args()

    download_filename = options.download_filename

    verbose = options.verbose

    course_id = options.course_id
    assert isinstance(course_id, int), "course_id is not an int: %s" % course_id

    script_dir = os.path.dirname(os.path.realpath(__file__))

    token_json_file = os.path.join(script_dir, "resources","token.json")
    assert os.path.isfile(token_json_file), "token_json_file is not a file: %s" % token_json_file

    roster_file = os.path.join(script_dir, "resources", "roster.csv")
    assert os.path.isfile(roster_file), "roster_file is not a file: %s" % roster_file

    parent_directory = options.parent_directory
    if not os.path.isdir(parent_directory):
        parent_directory = make_new_directory("parent_directory", parent_directory)

    assignment_list = os.path.join(script_dir, "resources", "assignments.csv")
    assert os.path.isfile(assignment_list), "assignment_list is not a file: %s" % assignment_list

    make_assignment_directory = options.make_assignment_directory

    assignment_name = options.assignment_name
    assignment_id = options.assignment_id

    assignment_name, assignment_id = get_assignment_name_and_id(assignment_name, assignment_id, assignment_list, course_id)

    token = get_token(token_json_file)
    url = build_submissions_url(course_id, assignment_id, page_num=1)
    submissions = []
    download_all_objects_to_list(url, token, mylist=submissions)

    plist = {}
    count = 0
    weird_skips = 0
    for submission in submissions:
        user_id = submission["user_id"]
        netid = get_netid_from_user_id(user_id, roster_file)

        if len(netid) < 1 or len(str(user_id)) < 1:
            msg = "%s: skipping netid [%s] user_id [%s]" % (__file__, netid, user_id)
            print(msg)
            write_to_log(msg)
            weird_skips += 1
            continue

        # if there are no attempted submissions, then there is nothing to download
        # (note that the submission might have an 'id' assigned if we have already uploaded a grade for this student,
        #  e.g. if their partner submitted the assignment)
        if submission["attempt"] == None:
            if verbose:
                msg = "%s: No submission for netid [%s] user_id [%s].  Skipping." % (__file__, netid, user_id)
                print(msg)
                write_to_log(msg)
            continue

        netid_directory = get_or_make_directory(parent_directory, netid)
        assignment_directory = os.path.join(netid_directory, assignment_name)

        args = ["python", "download_submission.py",
                  "-c", str(course_id),
                  "-a", assignment_name,
                  "-i", str(assignment_id),
                  "-u", str(user_id),
                  "-n", netid,
                  "-d", assignment_directory,
                ]

        if make_assignment_directory:
            args.extend(["-m"])

        if download_filename is not None:
            args.extend(["-o", download_filename])

        args_as_string = " ".join(args)
        if verbose:
            print("calling " + args_as_string)
        p = subprocess.Popen(args)
        plist[netid] = p

    for netid in plist:
        p = plist[netid]
        p.wait()
        if p.returncode == 0:
            count += 1

    msg = "%d submissions downloaded" % count
    print(msg)
    write_to_log(msg)

    msg = "%d weird skips (see canvaslib.log)" % weird_skips
    print(msg)
    write_to_log(msg)


